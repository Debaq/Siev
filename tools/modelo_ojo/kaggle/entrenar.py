"""Entrena siev_ojo: localizador de iris por ojo (red propia, MIT).

Kernel de Kaggle (script). Necesita el dataset privado tmvideo/siev-ojo-annotix
(un .npz por video, generado por tools/modelo_ojo/convertir_annotix.py).

Red totalmente convolucional estilo CenterNet:
  entrada  1 x H x W gris 0..255 (H, W multiplos de 16), una mitad de la imagen
           con el lado nasal a la derecha (OI espejado);
  salida   4 x H/4 x W/4: [logit de centro del iris, dx, dy, r/16].
Iris presente si sigmoid(pico) > umbral. Al ser convolucional, en la mascara
se aplica sobre la mitad completa (320x360 reducida a 160x180, rellenada a 192).

Salidas en /kaggle/working: siev_ojo_r01.onnx, siev_ojo_r01.pt, metricas.json, historial.csv.
"""

import argparse
import csv
import glob
import json
import math
import os
import random
import subprocess
import sys
import time

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "onnx", "onnxruntime", "onnxscript"], check=False)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
import torch.nn.functional as F  # noqa: E402

VAL_VIDEOS = ("test_1757512468", "test_1759581863")  # uno de cada sesion
H_IN, W_IN = 96, 128
STRIDE = 4


# ---------------------------------------------------------------- modelo
def cbr(i, o, s=1):
    return nn.Sequential(nn.Conv2d(i, o, 3, s, 1, bias=False), nn.BatchNorm2d(o), nn.ReLU(inplace=True))


def dw(i, o, s=1, d=1):
    return nn.Sequential(
        nn.Conv2d(i, i, 3, s, d, dilation=d, groups=i, bias=False), nn.BatchNorm2d(i), nn.ReLU(inplace=True),
        nn.Conv2d(i, o, 1, bias=False), nn.BatchNorm2d(o), nn.ReLU(inplace=True),
    )


class SievOjo(nn.Module):
    """cabeza="full": conv 3x3 48->32 (r01, r02). cabeza="dw": depthwise 3x3 +
    1x1 48->32 (r03), ~7x menos operaciones en la capa mas cara."""

    def __init__(self, cabeza="dw"):
        super().__init__()
        self.s2 = cbr(1, 16, 2)
        self.s4 = nn.Sequential(dw(16, 32, 2), dw(32, 32))
        self.s8 = nn.Sequential(dw(32, 64, 2), dw(64, 64), dw(64, 64, d=2))
        self.s16 = nn.Sequential(dw(64, 96, 2), dw(96, 96, d=2), dw(96, 96, d=4))
        self.u8 = dw(96 + 64, 64)
        self.u4 = dw(64 + 32, 48)
        if cabeza == "full":
            self.cab = nn.Sequential(nn.Conv2d(48, 32, 3, 1, 1), nn.ReLU(inplace=True), nn.Conv2d(32, 4, 1))
        else:
            self.cab = nn.Sequential(dw(48, 32), nn.Conv2d(32, 4, 1))
        self.cab[-1].bias.data[0] = -4.0  # prior de fondo

    def forward(self, x):
        x = x / 255.0 - 0.5
        a = self.s4(self.s2(x))
        b = self.s8(a)
        c = self.s16(b)
        b = self.u8(torch.cat([F.interpolate(c, scale_factor=2.0, mode="nearest"), b], 1))
        a = self.u4(torch.cat([F.interpolate(b, scale_factor=2.0, mode="nearest"), a], 1))
        return self.cab(a)


# ---------------------------------------------------------------- datos
def cargar(dir_datos):
    vids = {}
    for f in sorted(glob.glob(os.path.join(dir_datos, "**", "*.npz"), recursive=True)):
        z = np.load(f)
        vids[os.path.basename(f)[:-4]] = (z["imgs"], z["lab"])
    return vids


def objetivo(lab, h, w):
    """Mapa de calor gaussiano + regresion en la celda del centro."""
    ho, wo = h // STRIDE, w // STRIDE
    hm = np.zeros((ho, wo), np.float32)
    reg = np.zeros((3, ho, wo), np.float32)
    msk = np.zeros((ho, wo), np.float32)
    p, cx, cy, r = lab
    if p > 0:
        gx, gy = cx / STRIDE, cy / STRIDE
        ix, iy = int(gx), int(gy)
        if 0 <= ix < wo and 0 <= iy < ho:
            sig = 0.7 + r / STRIDE / 3.0
            ys, xs = np.mgrid[0:ho, 0:wo]
            hm = np.exp(-((xs - gx + 0.5) ** 2 + (ys - gy + 0.5) ** 2) / (2 * sig * sig)).astype(np.float32)
            hm[iy, ix] = 1.0
            reg[:, iy, ix] = (gx - ix, gy - iy, r / 16.0)
            msk[iy, ix] = 1.0
    return hm, reg, msk


class Aumentado(torch.utils.data.Dataset):
    def __init__(self, imgs, labs, n_por_epoca, frac_cerrados=0.15):
        self.imgs, self.labs, self.n = imgs, labs, n_por_epoca
        self.con = [k for k, l in enumerate(labs) if l[0] > 0]
        self.sin = [k for k, l in enumerate(labs) if l[0] == 0]
        self.frac = frac_cerrados if self.sin else 0.0

    def __len__(self):
        return self.n

    def __getitem__(self, _):
        k = random.choice(self.sin if random.random() < self.frac else self.con)
        img, (p, cx, cy, r) = self.imgs[k], self.labs[k]
        h0, w0 = img.shape
        s = math.exp(random.uniform(math.log(0.5), math.log(1.35)))  # mascara: r ~0.6x del dataset
        ang = random.uniform(-12, 12)
        if p > 0 and random.random() < 0.88:
            dx, dy = random.uniform(10, W_IN - 10), random.uniform(10, H_IN - 10)  # iris dentro del recorte
            ox, oy = cx, cy
        else:
            dx, dy = random.uniform(0, W_IN), random.uniform(0, H_IN)
            ox, oy = random.uniform(0, w0), random.uniform(0, h0)
        m = cv2.getRotationMatrix2D((ox, oy), ang, s)
        m[0, 2] += dx - ox
        m[1, 2] += dy - oy
        borde = random.choice([cv2.BORDER_REFLECT_101, cv2.BORDER_REPLICATE, cv2.BORDER_CONSTANT])
        out = cv2.warpAffine(img, m, (W_IN, H_IN), flags=cv2.INTER_LINEAR, borderMode=borde,
                             borderValue=random.randint(0, 255)).astype(np.float32)
        lab = (0.0, 0.0, 0.0, 0.0)
        if p > 0:
            nx, ny = m @ np.array([cx, cy, 1.0])
            if 0 <= nx < W_IN and 0 <= ny < H_IN:
                lab = (1.0, nx, ny, r * s)
        out = fotometrico(out, lab)
        hm, reg, msk = objetivo(lab, H_IN, W_IN)
        return torch.from_numpy(out[None]), torch.from_numpy(hm[None]), torch.from_numpy(reg), torch.from_numpy(msk[None])


def fotometrico(x, lab):
    if random.random() < 0.3 and lab[0] > 0:  # reflejos del LED IR
        for _ in range(random.randint(1, 3)):
            bx = lab[1] + random.uniform(-1.5, 1.5) * lab[3]
            by = lab[2] + random.uniform(-1, 1) * lab[3]
            cv2.circle(x, (int(bx), int(by)), random.randint(1, 3), 255.0, -1)
    x = x / 255.0
    x = np.clip(x, 0, 1) ** random.uniform(0.6, 1.6)
    x = (x - x.mean()) * random.uniform(0.55, 1.45) + x.mean() + random.uniform(-0.15, 0.15)
    x = x * 255.0
    if random.random() < 0.35:
        x = cv2.GaussianBlur(x, (0, 0), random.uniform(0.4, 1.6))
    if random.random() < 0.2:
        f = random.uniform(0.35, 0.7)
        x = cv2.resize(cv2.resize(x, None, fx=f, fy=f, interpolation=cv2.INTER_AREA), (W_IN, H_IN))
    x = x + np.random.randn(*x.shape).astype(np.float32) * random.uniform(0, 9)
    return np.clip(x, 0, 255).astype(np.float32)


# ---------------------------------------------------------------- perdida y decodificacion
def perdida(sal, hm, reg, msk):
    pr = torch.sigmoid(sal[:, :1]).clamp(1e-4, 1 - 1e-4)
    pos = hm.eq(1).float()
    neg = 1 - pos
    lp = -(torch.log(pr) * (1 - pr) ** 2 * pos).sum()
    ln = -(torch.log(1 - pr) * pr ** 2 * (1 - hm) ** 4 * neg).sum()
    npos = pos.sum().clamp(min=1)
    foc = (lp + ln) / npos
    l1 = (F.l1_loss(sal[:, 1:], reg, reduction="none") * msk).sum() / npos
    return foc + l1, foc.item(), l1.item()


def decodificar(sal):
    """Por imagen: (confianza, cx, cy, r) en px de la entrada."""
    pr = torch.sigmoid(sal[:, 0])
    b, ho, wo = pr.shape
    conf, idx = pr.view(b, -1).max(1)
    iy, ix = idx // wo, idx % wo
    ar = torch.arange(b, device=sal.device)
    dx, dy, rr = sal[ar, 1, iy, ix], sal[ar, 2, iy, ix], sal[ar, 3, iy, ix]
    return torch.stack([conf, (ix + dx) * STRIDE, (iy + dy) * STRIDE, rr * 16.0], 1)


def rellenar16(x):
    h, w = x.shape[-2:]
    ph, pw = (-h) % 16, (-w) % 16
    return F.pad(x, (0, pw, 0, ph), mode="replicate") if ph or pw else x


@torch.no_grad()
def evaluar(model, imgs, labs, dev, escala=1.0, umbral=0.3):
    model.eval()
    preds = []
    for i in range(0, len(imgs), 256):
        x = torch.from_numpy(imgs[i:i + 256].astype(np.float32))[:, None].to(dev)
        if escala != 1.0:
            x = F.interpolate(x, scale_factor=escala, mode="area")
        preds.append(decodificar(model(rellenar16(x))).cpu())
    pr = torch.cat(preds).numpy()
    gt = labs.copy()
    gt[:, 1:] *= escala
    con = gt[:, 0] > 0
    det = pr[:, 0] > umbral
    err = np.hypot(pr[:, 1] - gt[:, 1], pr[:, 2] - gt[:, 2]) / escala * 2  # px de la imagen 640 original
    ok = con & det
    rel = np.abs(pr[:, 3] - gt[:, 3]) / np.maximum(gt[:, 3], 1)
    return {
        "deteccion": float(det[con].mean()),
        "falsos_pos": float(det[~con].mean()) if (~con).any() else None,
        "n_sin_iris": int((~con).sum()),
        "err_px_med": float(np.median(err[ok])) if ok.any() else None,
        "err_px_p95": float(np.percentile(err[ok], 95)) if ok.any() else None,
        "err_radio_rel_med": float(np.median(rel[ok])) if ok.any() else None,
        "lejos_8px": float((err[ok] > 8).mean()) if ok.any() else None,
    }


# ---------------------------------------------------------------- principal
def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default="/kaggle/input")
    ap.add_argument("--out", default="/kaggle/working")
    ap.add_argument("--epocas", type=int, default=90)
    ap.add_argument("--lote", type=int, default=128)
    ap.add_argument("--semilla", type=int, default=42)
    ap.add_argument("--nombre", default="siev_ojo_r03")
    ap.add_argument("--cabeza", default="dw", choices=["full", "dw"])
    a = ap.parse_args()
    random.seed(a.semilla)
    np.random.seed(a.semilla)
    torch.manual_seed(a.semilla)

    dev = "cpu"
    if torch.cuda.is_available():
        try:
            torch.zeros(1, device="cuda").add_(1)
            dev = "cuda"
        except Exception as e:  # GPU no soportada por el torch instalado
            print("CUDA no usable:", e)
    print("dispositivo", dev, torch.__version__)

    vids = cargar(a.datos)
    print({k: len(v[0]) for k, v in vids.items()})
    tr = [(im, lb) for k, (I, L) in vids.items() if k not in VAL_VIDEOS for im, lb in zip(I, L)]
    tr_imgs, tr_labs = [t[0] for t in tr], [t[1] for t in tr]
    val = {k: vids[k] for k in VAL_VIDEOS}

    model = SievOjo(a.cabeza).to(dev)
    nparam = sum(p.numel() for p in model.parameters())
    print("parametros", nparam)
    ds = Aumentado(tr_imgs, tr_labs, n_por_epoca=len(tr_imgs))
    dl = torch.utils.data.DataLoader(ds, batch_size=a.lote, num_workers=4, drop_last=True,
                                     worker_init_fn=lambda w: (random.seed(a.semilla * 100 + w + int(time.time())),
                                                               np.random.seed((a.semilla * 100 + w) % 2**31)))
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4)
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=3e-3, total_steps=a.epocas * len(dl), pct_start=0.1)

    hist, mejor, mejor_ep = [], -1e9, -1
    os.makedirs(a.out, exist_ok=True)
    for ep in range(a.epocas):
        model.train()
        t0, suma = time.time(), [0.0, 0.0, 0]
        for x, hm, reg, msk in dl:
            x, hm, reg, msk = x.to(dev), hm.to(dev), reg.to(dev), msk.to(dev)
            l, lf, lr_ = perdida(model(x), hm, reg, msk)
            opt.zero_grad()
            l.backward()
            opt.step()
            sch.step()
            suma[0] += lf
            suma[1] += lr_
            suma[2] += 1
        fila = {"epoca": ep, "foc": suma[0] / suma[2], "l1": suma[1] / suma[2], "seg": round(time.time() - t0, 1)}
        if ep % 5 == 4 or ep == a.epocas - 1:
            for k, (I, L) in val.items():
                for esc in (1.0, 0.6):
                    m = evaluar(model, I, L, dev, esc)
                    fila[f"{k}@{esc}_det"] = m["deteccion"]
                    fila[f"{k}@{esc}_p95"] = m["err_px_p95"]
                    fila[f"{k}@{esc}_fp"] = m["falsos_pos"]
            # puntaje: deteccion media - falsos positivos medios - p95 medio/20 (ambas escalas)
            dets = [v for kk, v in fila.items() if kk.endswith("_det")]
            fps = [v for kk, v in fila.items() if kk.endswith("_fp") and v is not None]
            p95s = [v if v is not None else 50 for kk, v in fila.items() if kk.endswith("_p95")]
            punt = float(np.mean(dets) - (np.mean(fps) if fps else 0) - np.mean(p95s) / 20)
            fila["puntaje"] = punt
            if punt > mejor:
                mejor, mejor_ep = punt, ep
                torch.save(model.state_dict(), os.path.join(a.out, a.nombre + ".pt"))
        print(json.dumps(fila))
        hist.append(fila)

    with open(os.path.join(a.out, "historial.csv"), "w", newline="") as f:
        campos = sorted({k for h in hist for k in h}, key=lambda s: (s != "epoca", s))
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(hist)

    model.load_state_dict(torch.load(os.path.join(a.out, a.nombre + ".pt"), map_location=dev))
    metr = {"cabeza": a.cabeza, "mejor_epoca": mejor_ep, "parametros": nparam, "dispositivo": dev, "semilla": a.semilla,
            "val_videos": list(VAL_VIDEOS), "val": {}}
    for k, (I, L) in val.items():
        for esc in (1.0, 0.6):
            metr["val"][f"{k}@{esc}"] = evaluar(model, I, L, dev, esc)
    for u in (0.2, 0.3, 0.5, 0.7):
        metr[f"umbral_{u}"] = {k: {kk: evaluar(model, I, L, dev, 1.0, u)[kk] for kk in ("deteccion", "falsos_pos")}
                               for k, (I, L) in val.items()}

    # exportar ONNX con alto/ancho dinamicos
    model = model.cpu().eval()
    ej = torch.zeros(1, 1, 192, 160)
    ruta = os.path.join(a.out, a.nombre + ".onnx")
    torch.onnx.export(model, ej, ruta, input_names=["imagen"], output_names=["mapa"], opset_version=17,
                      dynamic_axes={"imagen": {0: "n", 2: "alto", 3: "ancho"}, "mapa": {0: "n", 2: "alto4", 3: "ancho4"}},
                      dynamo=False)
    try:
        import onnxruntime as ort
        s = ort.InferenceSession(ruta, providers=["CPUExecutionProvider"])
        x = np.random.randint(0, 255, (1, 1, 192, 160)).astype(np.float32)
        d = np.abs(s.run(None, {"imagen": x})[0] - model(torch.from_numpy(x)).detach().numpy()).max()
        t0 = time.time()
        for _ in range(200):
            s.run(None, {"imagen": x})
        metr["onnx_dif_max"] = float(d)
        metr["onnx_ms_cpu_192x160"] = (time.time() - t0) / 200 * 1000
    except Exception as e:
        metr["onnx_error"] = repr(e)
    metr["onnx_bytes"] = os.path.getsize(ruta)
    json.dump(metr, open(os.path.join(a.out, "metricas.json"), "w"), indent=1)
    print(json.dumps(metr, indent=1))


if __name__ == "__main__":
    principal()
