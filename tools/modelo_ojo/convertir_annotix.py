"""Convierte una exportacion de Annotix (.tix descomprimido) en mitades por ojo.

Uso:
    python3 -I convertir_annotix.py <export_annotix> <salida>

Cada imagen de Annotix es la combinada de los dos ojos, letterboxed a 640x480.
Por cada imagen:
  - se recorta la franja util (filas no negras, calculada por video);
  - mitad izquierda = OD; mitad derecha = OI, espejada para que el lado nasal
    quede siempre a la derecha (asi una sola red sirve para ambos ojos);
  - se reduce a la mitad (gris, filtro de caja).

Etiqueta por mitad: presente (0/1), cx, cy, r del iris en px de la mitad reducida.
r = max(ancho, alto) / 2: con el parpado tapando, el ancho sigue siendo el diametro.

Ojo cerrado: la anotadora apaga el track del iris (keyframe `enabled: false`);
sin iris = ojo cerrado, no hay clase aparte. OJO: el annotations.json del
export IGNORA esos tramos y trae igual la caja interpolada (415 de 477 mitades
cerradas en el export de 2026-11-25). Por eso el estado se lee de los tracks
de project.json y manda sobre las cajas.

Salida: un .npz por video (imgs uint8 [M,H,W], lab float32 [M,4], cuadro, lado)
mas indice.json con el resumen.
"""

import json
import os
import sys

import numpy as np
from PIL import Image

ESCALA = 2  # reduccion
CLASE_IRIS = 0


def franja_util(rutas):
    """Filas y columnas no negras, union sobre una muestra de cuadros del video."""
    acc = None
    for r in rutas:
        a = np.asarray(Image.open(r).convert("L"), dtype=np.float32)
        acc = a if acc is None else np.maximum(acc, a)
    filas = np.where(acc.mean(axis=1) > 8)[0]
    return int(filas[0]), int(filas[-1]) + 1


def iris_vivo(proj):
    """{(video_id, cuadro): [OD vivo, OI vivo]} segun los tracks de iris."""
    vivo = {}
    for v in proj["videos"]:
        n = v["totalFrames"]
        for t in v["tracks"]:
            if t["classId"] != CLASE_IRIS or not t.get("enabled", True):
                continue
            kf = sorted(t["keyframes"], key=lambda k: k["frameIndex"])
            for j, k in enumerate(kf):
                if not k["enabled"]:
                    continue
                fin = kf[j + 1]["frameIndex"] if j + 1 < len(kf) else k["frameIndex"] + 1
                lado = 0 if k["bboxX"] + k["bboxWidth"] / 2 < 50 else 1  # coords del track en %
                for f in range(k["frameIndex"], min(fin, n)):
                    vivo.setdefault((v["id"], f), [False, False])[lado] = True
    return vivo


def main(origen, salida):
    os.makedirs(salida, exist_ok=True)
    ann = json.load(open(os.path.join(origen, "annotations.json")))
    proj = json.load(open(os.path.join(origen, "project.json")))
    nombres = {v["id"]: v["name"].rsplit(".", 1)[0] for v in proj["videos"]}
    vivo = iris_vivo(proj)

    por_video = {}
    for im in ann["images"]:
        vid = im["file"].split("_")[2]
        cuadro = int(im["file"].rsplit("_", 1)[1].split(".")[0])
        por_video.setdefault(vid, []).append((cuadro, im))

    indice = []
    for vid, items in sorted(por_video.items(), key=lambda kv: nombres[kv[0]]):
        items.sort(key=lambda t: t[0])
        rutas = [os.path.join(origen, "images", im["file"]) for _, im in items]
        y0, y1 = franja_util(rutas[:: max(1, len(rutas) // 30)])
        imgs, labs, cuadros, lados = [], [], [], []
        omitidas = 0
        cerrados_export = 0
        for (cuadro, im), ruta in zip(items, rutas):
            a = Image.open(ruta).convert("L")
            w = a.width
            mitad = w // 2
            banda = a.crop((0, y0, w, y1))
            iris = [x["data"] for x in im["annotations"] if x["class"] == CLASE_IRIS]
            for lado in (0, 1):  # 0 = OD (izquierda), 1 = OI (derecha, espejada)
                if lado == 0:
                    h = banda.crop((0, 0, mitad, y1 - y0))
                else:
                    h = banda.crop((mitad, 0, w, y1 - y0)).transpose(Image.FLIP_LEFT_RIGHT)
                h = h.resize((h.width // ESCALA, h.height // ESCALA), Image.BOX)
                cajas = []
                for b in iris:
                    cx = b["x"] + b["width"] / 2
                    cy = b["y"] + b["height"] / 2 - y0
                    if (cx < mitad) != (lado == 0):
                        continue
                    if lado == 1:
                        cx = mitad - (cx - mitad)
                    cajas.append((cx / ESCALA, cy / ESCALA, max(b["width"], b["height"]) / 2 / ESCALA))
                if not vivo.get((vid, cuadro), [False, False])[lado]:
                    cerrados_export += bool(cajas)
                    cajas = []
                if len(cajas) > 1:
                    omitidas += 1
                    continue
                lab = (1.0, *cajas[0]) if cajas else (0.0, 0.0, 0.0, 0.0)
                imgs.append(np.asarray(h, dtype=np.uint8))
                labs.append(lab)
                cuadros.append(cuadro)
                lados.append(lado)
        nombre = nombres[vid]
        labs = np.asarray(labs, dtype=np.float32)
        np.savez_compressed(
            os.path.join(salida, f"{nombre}.npz"),
            imgs=np.stack(imgs),
            lab=labs,
            cuadro=np.asarray(cuadros, dtype=np.int32),
            lado=np.asarray(lados, dtype=np.uint8),
        )
        fila = {
            "video": nombre,
            "mitades": len(imgs),
            "tam": list(imgs[0].shape),
            "franja_y": [y0, y1],
            "con_iris": int(labs[:, 0].sum()),
            "sin_iris": int((labs[:, 0] == 0).sum()),
            "omitidas_2_iris": omitidas,
            "cerrados_corregidos": cerrados_export,
            "r_mediana": round(float(np.median(labs[labs[:, 0] > 0, 3])), 1),
        }
        indice.append(fila)
        print(fila)
    json.dump(indice, open(os.path.join(salida, "indice.json"), "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
