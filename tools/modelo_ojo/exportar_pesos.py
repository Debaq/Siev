"""Exporta los pesos de siev_ojo (.onnx) al formato plano que lee siev_ojo.rs.

Uso (con onnx y onnxruntime disponibles, p. ej. via uv):
    uv run --no-project --with onnx --with onnxruntime --with numpy \
        python -I exportar_pesos.py siev_ojo_r01.onnx siev_ojo_r01.bin

Formato .bin (little endian):
    b"SOJO", u32 version, u32 cantidad de f32, f32[...]
    version 1 = arquitectura r01/r02 (23 Conv, cabeza 3x3 completa)
    version 2 = arquitectura r03 (24 Conv, cabeza depthwise + 1x1)
Los f32 son, por cada Conv en el orden del grafo, pesos [co][ci/grupo][kh][kw]
y luego bias [co]. La BatchNorm ya viene fusionada en la Conv por el export.

Ademas escribe <salida>.ref: entrada de prueba y salida esperada de
onnxruntime, para el test de igualdad del lado Rust:
    u32 alto, u32 ancho, f32 entrada[alto*ancho] (0..255),
    u32 n, f32 mapa[n] ([4][alto/4][ancho/4])
"""

import struct
import sys

import numpy as np
import onnx
import onnxruntime as ort
from onnx import numpy_helper



def main(ruta_onnx, salida):
    m = onnx.load(ruta_onnx)
    init = {i.name: numpy_helper.to_array(i) for i in m.graph.initializer}
    flot = []
    convs = [n for n in m.graph.node if n.op_type == "Conv"]
    for n in convs:
        w, b = init[n.input[1]], init[n.input[2]]
        flot.append(w.astype("<f4").ravel())
        flot.append(b.astype("<f4").ravel())
    todo = np.concatenate(flot)
    with open(salida, "wb") as f:
        version = {23: 1, 24: 2}[len(convs)]
        f.write(b"SOJO" + struct.pack("<II", version, todo.size))
        f.write(todo.tobytes())
    print(f"{len(convs)} conv, {todo.size} f32 -> {salida}")

    # referencia: imagen sintetica con estructura (gradiente + disco oscuro + ruido)
    rng = np.random.default_rng(7)
    alto, ancho = 112, 128
    yy, xx = np.mgrid[0:alto, 0:ancho]
    img = 150 + 40 * np.sin(xx / 9.0) + 30 * np.cos(yy / 7.0)
    img[(yy - 50) ** 2 + (xx - 70) ** 2 < 15 ** 2] = 40
    img = np.clip(img + rng.normal(0, 8, img.shape), 0, 255).astype(np.float32)
    s = ort.InferenceSession(ruta_onnx, providers=["CPUExecutionProvider"])
    mapa = s.run(None, {"imagen": img[None, None]})[0][0].astype("<f4")
    with open(salida + ".ref", "wb") as f:
        f.write(struct.pack("<II", alto, ancho))
        f.write(img.astype("<f4").tobytes())
        f.write(struct.pack("<I", mapa.size))
        f.write(mapa.tobytes())
    print("referencia", mapa.shape, "->", salida + ".ref")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
