# Roadmap SIEV VNG (rama `vng-rust`)

Videonistagmografia en Rust puro (eframe/egui). Estado al 2026-11-25.

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
- [x] IA de iris (YOLOv8n, ONNX) para ubicar cada ojo
- [x] Juez IA de ojo cerrado + video marcado de depuracion — `5d18674`
- [ ] Problema conocido: el juez anula ojos **entrecerrados** aunque la pupila se vea (se resuelve en Fase 4)

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

**Por que.** El modelo actual (`siev_iris_r01.onnx`, YOLOv8n de Ultralytics):
- es AGPL: obliga a liberar el codigo de la app si se distribuye;
- pesa 12 MB y necesita ONNX Runtime;
- solo tiene una clase (iris), asi que el juez confunde **entrecerrado** con **cerrado** y anula datos validos de pacientes mareados. Probado: ninguna regla simple (circularidad, radio) los separa.

**Objetivo.** Una red propia, pequeña, por ojo, con estado del ojo + iris, codigo y pesos MIT, inferencia en Rust puro.

### 4.1 Datos

- [ ] **Recibir los 10 videos completos anotados** (bloqueante)
- [ ] Inventario: cuantos cuadros, pacientes y sesiones hay, y cuantos casos de cada estado
- [ ] Revisar que los videos traigan ojos **entrecerrados** y **cerrados** en cantidad suficiente. Si no, grabar sesiones dirigidas: pedir al voluntario entrecerrar, parpadear y cerrar
- [ ] Juntar con lo ya anotado en Annotix "Siev" (2 videos de sep-2025, 818/1343 cuadros, sin entrecerrados)
- [ ] Corregir los errores conocidos de anotacion: cuadro 207 de `test_1757510394` y cuadros 45-50 de `test_1757511147`
- [ ] Variedad que el modelo debe ver: distintas personas, maquillaje o pestañas, lentes de contacto, reflejos del LED IR, brillo y exposicion distintos, mascara mal ajustada
- [ ] Privacidad: las imagenes de ojos son datos de salud. Dataset **siempre privado**, nunca en el repo, y con consentimiento de quienes aparecen

### 4.2 Criterio de anotacion

- [ ] Escribir la guia de anotacion con imagenes de ejemplo:
  - **abierto**: pupila completa o casi completa visible
  - **entrecerrado**: parpado tapa parte de la pupila pero el centro se puede estimar
  - **cerrado**: no se puede ubicar la pupila (incluye el parpadeo en curso)
- [ ] Que mide el centro: el del iris (como hoy) o el de la pupila. Decidirlo antes de anotar mas
- [ ] Dos personas anotan el mismo subconjunto para medir concordancia; los casos dudosos se definen en la guia
- [ ] Pre-anotar con el detector actual (pupila + IA) para que la anotadora solo corrija: acelera mucho

### 4.3 Conversion y particion

- [ ] Script que pasa la exportacion de Annotix a recortes por ojo. Las imagenes de Annotix son la combinada letterboxed a 640x480 (franja util y=120..360); cada ojo es una mitad
- [ ] Recorte ~128x96 gris (aspecto 4:3), con las etiquetas en coordenadas del recorte
- [ ] El ojo izquierdo se espeja para que ambos ojos queden con la misma orientacion; asi una sola red sirve para los dos
- [ ] Particion **por persona o sesion** (o como minimo por bloques contiguos de cuadros). Cuadros vecinos son casi identicos: separarlos al azar infla las metricas
- [ ] Conjunto de prueba congelado, que no se toca hasta la evaluacion final

### 4.4 Modelo y entrenamiento

- [ ] Arquitectura: CNN chica (~100-300k parametros, < 1 MB) con dos cabezas:
  - clasificacion de estado (3 clases)
  - regresion de centro (x, y) y radio del iris; opcional la apertura del parpado
- [ ] La perdida de regresion no cuenta en cuadros **cerrados** (no hay centro que medir)
- [ ] Desbalance: hay muchos mas abiertos que entrecerrados. Usar pesos por clase o muestreo balanceado
- [ ] Aumentos: brillo y contraste, desenfoque, ruido, reflejos IR sinteticos, pequeñas rotaciones y desplazamientos (sin espejar, ya se normalizo)
- [ ] Entrenar en Kaggle con GPU (no hay GPU ni torch local). Seguir el patron de un dataset privado + `kernel-metadata.json` con GPU, ya usado en otro proyecto
- [ ] Reproducibilidad: script o notebook de entrenamiento versionado en este repo (sin datos), semilla fija y version del dataset anotada

### 4.5 Evaluacion y criterio de aceptacion

- [ ] Metricas en el conjunto de prueba:
  - estado: matriz de confusion y F1 por clase. Lo clave es **entrecerrado vs cerrado**
  - centro: error en px (mediana y percentil 95)
  - radio: error relativo
- [ ] Prueba contra `fixtures/mascara_20261125_2min` (14273 cuadros, con entrecerrados en ~6229-6495 y ~11100-11240) usando `video_marcado`
- [ ] Debe igualar o mejorar los indicadores actuales: deteccion con ojo abierto OD 92,6 % / OI 95,6 %, correlacion OD-OI H 0,925 / V 0,982
- [ ] Debe **recuperar los entrecerrados** que el juez actual anula
- [ ] Velocidad < 1 ms por ojo en CPU, para correr en cada cuadro a ~225 fps
- [ ] Si no cumple: buscar los fallos con `video_marcado`, anotar esos casos, reentrenar (ciclo de mejora)

### 4.6 Exportacion e inferencia en Rust

- [ ] Elegir entre `tract` (carga ONNX, Rust puro) y `candle` (pesos safetensors). Medir velocidad y complejidad de cada uno
- [ ] Exportar los pesos en el formato elegido, con un nombre versionado (p. ej. `siev_ojo_r01`)
- [ ] Ficha del modelo: datos usados, metricas, fecha y limitaciones conocidas
- [ ] Decidir si los pesos van dentro del binario (< 1 MB lo permite) o como archivo aparte

## Fase 5 — Integracion del modelo

- [ ] Nuevo detector en `siev-tracking` detras de una opcion, para comparar contra el actual con la misma grabacion
- [ ] Logica por estado:
  - abierto: pupila como hoy, guiada por el centro del modelo
  - entrecerrado: buscar la pupila con mas tolerancia (forma parcial), o usar el centro del modelo si el detector clasico falla
  - cerrado: sin dato (hueco en la traza)
- [ ] Reemplazar al juez de ojo cerrado actual
- [ ] Test de regresion: traza y deteccion sobre los fixtures, con el nuevo modelo
- [ ] Si falta el archivo del modelo: seguir con el detector clasico y avisar en la GUI
- [ ] Quitar YOLO/Ultralytics y ONNX Runtime del proyecto, y actualizar README y licencias
- [ ] Validar en vivo con la mascara y con pacientes reales

### Mantenimiento del modelo

- [ ] Guardar en cada examen la version del modelo usada
- [ ] Juntar los casos dificiles que aparezcan en uso clinico, anotarlos y reentrenar por versiones (`r02`, `r03`…)
- [ ] Un modelo de mascara nuevo (otra camara u otra iluminacion) probablemente requiere datos nuevos y reentrenar

## Fase 6 — Pruebas clinicas (por definir)

- [ ] Protocolos: espontaneo, mirada, sacadas, seguimiento, posicionales, caloricas
- [ ] Estimulos por prueba en el monitor (reusa la ventana de estimulos de la Fase 3)
- [ ] Informe del examen

## Otros

- [ ] LED IR por ESP8266 (`/dev/ttyUSB0`), no conectado en esta rama
- [ ] Push de los commits locales (`6001e5e`, `5d18674`, `b20557d`)
