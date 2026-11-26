# Roadmap SIEV VNG (rama `vng-rust`)

Videonistagmografia en Rust puro (eframe/egui). Estado al 2026-11-26.

Leyenda: `[x]` hecho · `[~]` hecho sin validar con la mascara · `[ ]` pendiente

---

## Fase 1 — Base: captura y seguimiento

- [x] Workspace Rust puro sin Tauri: `siev-tracking` (pipeline) + `siev-vng` (GUI egui) — `e021cb2`
- [x] Camara de la mascara (USB GS CAM 640x360 @ ~225 fps), reconexion automatica
- [x] Controles del sensor V4L2 (exposicion automatica recomendada)
- [x] Detector de pupila robusto: umbral por region oscura / valle, quitar reflejos del LED — `6001e5e`
- [x] Test de regresion de traza contra fixtures (`fixtures/`)
- [x] No caerse con camaras cuyos controles `v4l` no reconoce — `b20557d`

## Fase 2 — Analisis clinico en vivo

- [x] Nistagmo en vivo por ojo y eje: direccion, SPV, frecuencia — `6001e5e`
- [x] GUI clinica: video, tarjeta por ojo, trazados H/V y curva de SPV
- [x] Grabacion JSONL y reproduccion de secuencias PGM
- [x] IA de iris (YOLOv8n, ONNX) para ubicar cada ojo — reemplazada por el modelo propio (Fase 4)
- [x] Juez IA de ojo cerrado + video marcado de depuracion — `5d18674`
- [x] ~~El juez anula ojos entrecerrados~~: resuelto con la IA tutora (Fase 5) — `38daabe`

## Fase 3 — Calibracion a grados

Diseño acordado:
- Estimulos en el **monitor** del paciente (mas economico que una barra LED).
- **Estacion** (una vez por sala): monitor, cm por px con una regla en pantalla de 20 cm, distancia ojos-pantalla.
- **Mascara**: escala por defecto = mediana de las ultimas 10 calibraciones sin avisos de esa mascara. Un modelo nuevo de mascara arma su propio historial.
- **Paciente**: escala opcional (6 puntos, ~15 s); **cero obligatorio** de 1,5 s al iniciar cada prueba.
- No se pide distancia interpupilar ni distancia camara-ojo: el ajuste por puntos las absorbe.

Tareas:
- [~] Asistente de calibracion + ventana de estimulos a pantalla completa — `b20557d`
- [~] Ajuste por ojo con error, simetria, deriva del centro y control de signos
- [~] Historial `~/.config/siev-vng/calibraciones.json` y escala por defecto
- [~] Cero al iniciar prueba
- [ ] **Probar con la mascara real**: mirar a la derecha debe dar positivo; puntos y cero bien tomados
- [ ] **Medir la variacion de escala entre 5-10 personas**. Si varia < ~10 %, el defecto basta; si no, exigir calibracion para sacadas y seguimiento (en caloricas la escala se cancela)
- [ ] Guardar en el archivo del examen que calibracion se uso (fuente, escala, error)
- [ ] Informe: marcar "valores estimados sin calibracion" cuando corresponda
- [ ] Lista real de monitores (hoy se elige "Monitor 1-4")

## Fase 4 — Modelo propio por ojo (reemplazar YOLO/AGPL)

**Por que.** El YOLOv8n de Ultralytics (`siev_iris_r01.onnx`) es AGPL, pesa 12 MB, necesita
ONNX Runtime y su juez confundia entrecerrado con cerrado.

**Decision.** No hay clases de estado: el modelo solo **localiza el iris** (centro y radio, aunque el
parpado lo tape) y dice si esta presente. Sin iris = ojo cerrado. Es el criterio de la anotadora:
si no hay pupila, el ojo esta cerrado.

### 4.1 Datos

- [x] 10 videos anotados en Annotix (proyecto "Siev"): 5423 cuadros a 5 fps, 2 iris + cantos por cuadro, 477 mitades con ojo cerrado
- [x] Son de la **misma camara y mascara**; solo cambia la resolucion y el recorte del programa anterior (combinada letterboxed 640x480)
- [x] Hallazgo: el `annotations.json` del export **ignora los tramos de track apagados** (ojo cerrado) y trae la caja interpolada (415 de 477). El conversor lee el estado de los tracks en `project.json`
- [x] Dataset privado en Kaggle (`siev-ojo-annotix`), nunca en el repo
- [ ] **Anotar ~300-500 cuadros de la grabacion actual de la mascara** (recorte y resolucion del programa nuevo), con parpadeos y la ceja a la vista: lo que mas mejoraria el centro, el radio y los falsos positivos
- [ ] Mas personas y condiciones (maquillaje, lentes de contacto, mascara mal ajustada)

### 4.2 Conversion, modelo y entrenamiento — `5e869ab`

- [x] `tools/modelo_ojo/convertir_annotix.py`: mitades por ojo, OI espejado (una sola red para ambos ojos), reducidas 2x
- [x] Red tipo CenterNet totalmente convolucional (sirve con cualquier tamaño de entrada): mapa de calor del centro + desplazamiento + radio. Codigo y pesos MIT
- [x] Entrenamiento en Kaggle (`tools/modelo_ojo/kaggle/entrenar.py`), particion por video (2 videos de validacion), ojos cerrados muestreados al 15 %
- [x] Versiones: r01 (con el error del export), r02 (ojos cerrados corregidos), **r03** (cabeza depthwise + 1x1, 62.868 parametros, 240 KB)

### 4.3 Evaluacion

Validacion Annotix (umbral 0,5): deteccion 97-99 %, 0 % de falsos positivos en ojos cerrados,
error del centro ~6-7 px (mediana, imagen de 640 px).

Grabacion `fixtures/mascara_20261125_2min` con el pipeline completo (pupila detectada OD / OI):

| | Pupila | Cerrado |
|---|---|---|
| YOLO (IA cada 10 cuadros) | 69,5 % / 70,4 % | 25,0 % / 26,4 % |
| r03 tutora + recorte 64x64 | 69,3 % / 72,1 % | 23,8 % / 21,2 % |

- [x] Iguala o supera al YOLO; recupera parte de los entrecerrados (OI 35-39 % en el primer tramo, antes ~10 %)
- [ ] El centro del circulo de la IA queda corrido hacia el reflejo del LED y el radio sale inflado (cajas de Annotix holgadas). No afecta a la pupila medida; se corrige con datos de la mascara (4.1)

### 4.4 Inferencia en Rust — `38daabe`

- [x] Red escrita a mano (`siev-tracking/src/vng/siev_ojo.rs`), sin ONNX Runtime ni dependencias. Pesos en `.bin` plano (`tools/modelo_ojo/exportar_pesos.py`), version 1 (r01/r02) y 2 (r03)
- [x] Test de igualdad contra onnxruntime (< 1e-3)
- [x] AVX2+FMA detectado al arrancar; ruta generica para CPUs sin AVX2
- [x] Modo recorte: la IA corre en 64x64 alrededor de la zona conocida (0,67 ms por ojo en un Ryzen 7 PRO 4750U)
- [ ] Mas velocidad (opcional): formato de canales intercalados con intrinsics AVX2. Prototipo medido: depthwise paso 2 2,6x mas rapida, paso 1 mas lenta en version simple; techo ~0,5 ms por cuadro. Solo si el piso lo pide

## Fase 5 — Integracion del modelo — `38daabe`

- [x] `.bin` = modelo propio en Rust; `.onnx` = ort (para comparar). La app usa `siev_ojo_r03.bin` por defecto
- [x] **IA tutora, no juez**: el detector clasico corre siempre y la IA le da la zona. Tres estados por ojo:
  - IA ve el iris: circulo verde, la pupila se busca dentro
  - IA perdida: circulo magenta que sigue a la pupila (o a su velocidad), se sigue buscando
  - ojo cerrado (5 cuadros sin iris y sin pupila): no se busca ni se dibuja nada
- [x] La pupila solo vale dentro del circulo del iris: si cae fuera, la marca desaparece en vez de saltar
- [x] Ancla por ojo (la mascara va fija a la cabeza): la IA no puede saltar a la ceja; saltos lejanos requieren confirmacion
- [x] Suavizado adaptativo de la pista de la IA (quita el temblor sin frenar las sacadas)
- [x] `video_marcado` con modo `tiempo_real`
- [ ] Reiniciar el ancla al iniciar cada prueba
- [ ] Quitar YOLO/Ultralytics y ONNX Runtime del proyecto, y actualizar README y licencias
- [ ] Validar en vivo con la mascara y con pacientes reales

## Fase 6 — El equipo: requisitos y ajuste al PC — `38daabe`

Niveles clinicos: **60 fps** clinico · **90** vHIT basico · **120+** vHIT avanzado · **220** lujo.
Muchos clinicos preferiran menos fps y mas resolucion (la camara baja los fps sola al subir la resolucion).

- [x] Prueba del equipo (`vng/equipo.rs`): clip MJPEG real de la mascara por el pipeline completo; estima los fps por resolucion (el decode y el detector crecen con los pixeles, la IA en recorte no)
- [x] App: prueba al primer arranque (o si cambia la CPU), bloquea los formatos de camara que el PC no alcanza, aviso "PC no compatible" (< 60 fps) sin poder iniciar examenes
- [x] Regulador en vivo: si la carga pasa del 70 %, la IA corre cada 2-10 cuadros; aviso si ni asi da abasto
- [x] `tools/piso/`: experimento reproducible para medir otros equipos (funciona sin Rust copiando el binario)
- [ ] **Correr `tools/piso/medir_piso.sh` en PCs de gama baja reales** y confirmar la tabla estimada (Celeron/Pentium para 60-90 fps, N100/i3 6.ª gen para 120)
- [ ] Medir el costo de la GUI en iGPU debiles (el experimento no lo incluye)
- [ ] Listar los modos reales de la camara (resolucion/fps) y adaptar la reduccion antes de la IA a la resolucion, para que el iris le llegue del mismo tamaño

## Fase 7 — Pruebas clinicas (por definir)

- [ ] Protocolos: espontaneo, mirada, sacadas, seguimiento, posicionales, caloricas, vHIT
- [ ] Estimulos por prueba en el monitor (reusa la ventana de estimulos de la Fase 3)
- [ ] Informe del examen

## Otros

- [ ] LED IR por ESP8266 (`/dev/ttyUSB0`), no conectado en esta rama
