# Notas de hallazgos

Observaciones encontradas durante la reorganizacion estructural para los
experimentos. **Ninguna fue corregida**: la restriccion del trabajo es no alterar
el comportamiento del detector. Cada entrada queda para evaluacion aparte.

Formato: `[ID] titulo — ubicacion — severidad aparente`

---

## [H-01] Default de `ManualEyeRoi` invierte el eje X del ojo derecho

**Ubicacion:** `src-tauri/src/vng/native_video.rs:211-219` (default) y
`:1057-1062` (uso).

**Observacion.** La caja de busqueda del ojo derecho se arma como:

```rust
let x1 = (roi_right_w as f32 * manual_right.temporal) as u32;
let x2 = (roi_right_w as f32 * manual_right.nasal) as u32;
[x1, y1, x2.max(x1 + 1), y2.max(y1 + 1)]
```

Requiere `temporal < nasal`. El `Default` es `nasal: 0.1, temporal: 0.9`, que da
`x1 = 0.9*w`, `x2 = 0.1*w`; el `.max(x1 + 1)` colapsa la caja a **1 pixel de
ancho**.

El ojo izquierdo (`:1069-1071`) usa el orden contrario (`x1 = nasal`,
`x2 = temporal`) y con los mismos defaults queda correcto. La asimetria es
intencional — el eje nasal-temporal se invierte entre ojos — pero el `Default`
solo es coherente con uno de los dos.

**Por que normalmente no se ve.** El frontend restringe los sliders por rango:
ojo derecho `temporal ∈ [0, 0.5]`, `nasal ∈ [0.5, 1]`; ojo izquierdo al reves
(`ControlPanel.tsx:594-616` y `:658-679`). En cuanto la UI envia `session_update`
o `manual_roi_right`, los valores quedan bien ordenados y el problema desaparece.

**Cuando si se ve.** Ver la resolucion de abajo: tambien en produccion.

**Severidad:** alta en banco y alta en produccion sobre perfil nuevo.

### Resolucion — se ejerce en produccion (verificado en codigo, 2026-09-13)

La pregunta era si en operacion real el ROI siempre queda fijado desde la
interfaz. **No.** Hay un camino concreto en que el default de Rust sobrevive toda
la sesion. Cadena completa:

1. `App.tsx:322-329` envia `start_capture`. La captura arranca **ya** con los
   defaults de Rust.
2. `App.tsx:341-356` envia a continuacion `session_update`, construido desde
   `appConfig.vng.algorithm`, que se lee como `(vng.algorithm || {}) as any`.
   El campo viaja **sin fallback**: `manual_roi_right: algo.manual_roi_right`.
   Todos los campos vecinos si tienen `?? default`; estos dos no.
3. `vng.algorithm.manual_roi_right` solo existe en la configuracion persistida si
   alguien movio antes el slider del ROI derecho: se escribe unicamente desde
   `updateAndSync` -> `onPersistentUpdate` (`useSessionConfig.ts:203-206`).
4. En un perfil donde nadie lo movio, el valor es `undefined`, `JSON.stringify`
   elimina la clave, y del lado Rust `obj.get("manual_roi_right")` devuelve
   `None`: el setter no se llama nunca (`lib.rs:1386-1393`).
5. Nada mas lo corrige al arrancar. `syncToBackend` (`useSessionConfig.ts:134`)
   si enviaria los defaults correctos, porque usa `effectiveValues`, pero su
   unico invocador es `updateAndSync` (`:230`) — o sea, solo cuando el operador
   mueve un control. No corre al montar.

**Los dos defaults no coinciden.** El del frontend es el correcto para la formula
del backend; el de Rust es su espejo:

| | `nasal` | `temporal` | `x1 = temporal*w` | `x2 = nasal*w` | ancho |
|---|---|---|---|---|---|
| `useSessionConfig.ts:60` (frontend) | 0.9 | 0.1 | 0.1w | 0.9w | 0.8w correcto |
| `ManualEyeRoi::default()` (Rust) | 0.1 | 0.9 | 0.9w | 0.1w | **1 px** |

El default del ojo izquierdo coincide en ambos lados.

**Condiciones en que se ejerce:** perfil nuevo o configuracion sin
`vng.algorithm.manual_roi_right`, y YOLO apagado (con YOLO la caja viene del
modelo y el default es irrelevante). El fallo es silencioso: el preview dibuja la
caja de 1 px y el ojo derecho simplemente no detecta nunca.

**Consecuencia para el manuscrito.** La frase "esta es la configuracion de
produccion" necesita matiz en la condicion A (`--yolo off`): la configuracion de
produccion *efectiva* depende de si el perfil del operador tiene el ROI
persistido. El `config.toml` publicado con los materiales debe declarar el ROI
explicito y el manuscrito debe decir que corresponde a un perfil ya configurado
por el operador, no al arranque en frio.

---

## [H-02] Las pistas de pupila de YOLO se calculan y se descartan

**Ubicacion:** `src-tauri/src/vng/native_video.rs:744-745`, `:1042-1043`.

`run_yolo_inference` detecta la clase 1 (pupila), la asocia al ojo mas cercano y
devuelve `pupil_right` / `pupil_left`. En el hilo de captura se guardan en
`_yolo_pupil_hint_right` / `_yolo_pupil_hint_left` — con guion bajo — y **nunca
se leen**. `detect_pupil_math_refined` no recibe ningun parametro de seed: el
tracker se apoya solo en `prev_pupil` + `velocity`.

Es decir, el modelo aporta unicamente la caja del ojo (clase 0). El costo de
inferencia de la clase 1 se paga sin usarse.

**Impacto en la documentacion.** El README dice "pupil detection via a refined
mathematical algorithm seeded with hints from a YOLO26 ONNX model". El "seeded
with hints" no corresponde al codigo actual. `docs/seguimiento-ocular.md` si lo
describe correctamente (seccion 3: "solo pistas, no posicion final" / la caja).

**Impacto en los experimentos.** Relevante para interpretar el barrido de
frecuencia de YOLO: lo que se esta midiendo es el efecto del **anclaje de la caja
del ojo**, no de una semilla de posicion de pupila. Conviene decirlo explicito en
el paper.

**Severidad:** no es un fallo funcional; es codigo muerto + discrepancia de
documentacion.

### Correccion (2026-09-13)

Escribi antes que esto era un "desajuste semantico" entre un modelo que detecta
pupilas y un codigo que espera ojos. **Es incorrecto y lo retiro.** El modelo
sigue la pupila por diseno; la clase se llama `OJO` pero eso es solo el nombre.
El padding de ±20/±40 sobre la caja de pupila construye deliberadamente un
sub-ROI alrededor de ella, que es lo que recorta pestanas y cejas. El diseno es
coherente.

Lo unico realmente muerto es `pupil_detections` (clase 1), que este modelo de una
sola clase nunca puede llenar. El problema real que encontre esta en [H-13], y no
es de nombres.

---

## [H-03] `last_emitted_deflection` es campo muerto

**Ubicacion:** `src-tauri/src/vng/nystagmus.rs:70`, `:85`, `:272`.

Se declara, se inicializa en 0 y se resetea a 0 en `reset()`. Nunca se lee ni se
incrementa. Aparentemente sobra de una version anterior de `try_emit_beat`, que
hoy trabaja siempre sobre los ultimos 3 puntos de deflexion.

**Severidad:** cosmetica.

---

## [H-04] `eprintln!` por cuadro ante shape inesperado del modelo

**Ubicacion:** `src-tauri/src/vng/native_video.rs:1398`.

Si `output0` no tiene forma `[1, 300, 6]`, se imprime el error y se descarta la
inferencia — pero sin memoria de que ya se aviso. Con un modelo de forma distinta
esto imprime una linea cada `yolo_frequency` cuadros durante toda la sesion.
El resto del bucle si usa contadores para limitar el ruido de log
(`consecutive_errors % 30`).

**Severidad:** baja (ruido de log / coste de I/O bajo carga).

---

## [H-06] `println!` / `eprintln!` en `processor.rs` — RESUELTO

**Ubicacion:** `src-tauri/src/math/processor.rs:255` (sin punto central) y
`:316-320` (resumen de calibracion aplicada).

**Decision (aprobada):** no se eliminan ni se inyecta un callback. Pasan a una
macro interna de `vng-core` tras `#[cfg(feature = "diagnostics")]`, que
`vng-app` activa y `vng-bench` deja apagada. La salida por stdout de produccion
no cambia ni una linea; el banco queda limpio; cero dependencias nuevas.

---

## [H-07] `raw_capture.mp4` no es la entrada cruda de la camara

**Ubicacion:** `src-tauri/src/vng/native_video.rs:1027-1032`, `lib.rs:1418-1432`.

El video que guarda el sistema en cada bundle `.siev` se llama `raw_capture.mp4`,
pero **no** es lo que entrega la camara. El tap de grabacion esta colocado
despues del recorte de ROI, del ensamblado del cuadro combinado y del ajuste de
brillo/contraste, y antes de la deteccion (esto es el punto de corte E-6, que se
decidio dejar donde esta).

Ademas, antes de codificar, las dimensiones del cuadro combinado se ajustan a la
resolucion estandar mas cercana que las contenga
(`nearest_standard_resolution`, `lib.rs:42-62`), y la diferencia entre contenido
y lienzo se guarda aparte en un `VideoCropInfo`. El material de `out/` que revise
esta a 640x480 por esta via.

**Consecuencias.**

1. Un video de bundle **no sirve como entrada fiel** para la Fase 1: volver a
   pasarlo por el pipeline recorta un recorte y aplica brillo/contraste dos
   veces. Sigue siendo utilizable como *fixture* de regresion — el mismo cuadro
   de entrada produce la misma traza, que es lo unico que la prueba comprueba —
   pero no representa la geometria real de captura.
2. El nombre del archivo induce a error para cualquiera que reutilice el material.
3. Hay que declararlo en metodos, tal como se acordo: el video grabado por el
   sistema es una etapa intermedia del pipeline, no la senal de la camara.

**Severidad:** alta como riesgo metodologico; ninguna funcional.

---

## [H-08] `erode` es un control de UI que no llega al backend

**Ubicacion:** `src-tauri/src/vng/native_video.rs` (no existe `set_erode`),
`src-tauri/src/lib.rs:1269-1318` (no existe la clave `"erode"` en el dispatch de
`SetConfig`), `frontend/src/App.tsx:349` y
`frontend/src/hooks/useSessionConfig.ts:146` (el frontend si lo envia).

El frontend incluye `erode: [algo.erode_right ?? 0, algo.erode_left ?? 0]` en
cada `session_update`. El backend no tiene setter para ese campo y su dispatch no
contempla la clave, asi que el valor se descarta en silencio.

**Consecuencia.** `erode` queda fijo en el default de Rust, `[1, 1]`
(`native_video.rs:290`), durante toda la vida del proceso. El valor que muestra
la interfaz (`0` por defecto) **no es el que usa el detector** (`1`). Son una o
mas iteraciones de erosion morfologica de diferencia sobre la mascara binaria,
justo antes de `find_contours`.

**Relevancia para los experimentos.** `erode` no es barrible por la via actual
de configuracion: habria que fijarlo en el `config.toml` del banco y llamarlo
directamente. Y si el manuscrito lista los parametros del detector, el valor
correcto de `erode` es 1, no el que aparece en la UI.

**Severidad:** media. No rompe nada, pero es una discrepancia entre configuracion
declarada y configuracion efectiva, que es exactamente el tipo de cosa que
invalida un "corrimos con estos parametros".

---

## [H-09] `set_contrast` usa una escala distinta de la que documenta el campo

**Ubicacion:** `src-tauri/src/vng/native_video.rs:330-336` (setter),
`:246` (comentario del campo), `:305` (default del constructor).

El campo se declara asi:

```rust
contrast: Arc<Mutex<f32>>,    // 0.0 a 3.0 (1.0 = sin cambio)
```

pero el setter no acepta ese rango: acepta la escala 0-100 de la UI y la mapea a
0.5-2.0.

```rust
pub fn set_contrast(&self, value: f32) {
    // Convertir de 0-100 a 0.5-2.0
    *c = 0.5 + (value / 100.0) * 1.5;
}
```

**Tres consecuencias.**

1. El rango real es **0.5-2.0**, no 0.0-3.0. El comentario del campo miente.
2. El valor identidad **1.0 no es alcanzable de forma exacta** por el setter:
   requiere `value = 33.333...`, que no es representable en binario. El unico
   modo de tener identidad exacta es no llamar al setter y quedarse con el
   default del constructor.
3. Quien lea el tipo del campo (`f32`, "1.0 = sin cambio") y llame
   `set_contrast(1.0)` obtiene **0.515**, casi el minimo de contraste. Eso
   comprime el rango a la mitad y **levanta el negro a 62**.

**Como aparecio.** Exactamente asi, escribiendo la prueba de regresion de la
Fase 1. Con contraste 0.515 ningun pixel de la imagen baja del umbral 40, la
compuerta de parpadeo dispara por su cota inferior (`white_ratio < 0.01`) y el
detector devuelve `blink` en el 100% de los cuadros sin llegar a ejecutarse.
Costo: varias horas y cinco hipotesis descartadas antes de volcar el buffer a
disco y comparar bytes.

**Relevancia para los experimentos.** Es la misma familia que [H-08]: parametro
declarado distinto del parametro efectivo. El frontend envia
`contrast: cam.contrast ?? 50` (`App.tsx:346`), o sea que **en produccion el
contraste efectivo por defecto es 1.25**, no 1.0. Una `NativeVideoManager` recien
construida esta en 1.0 hasta que la UI la toca. Si el manuscrito lista los
parametros del detector, el valor correcto es 1.25 para produccion y hay que
decir en que escala esta expresado.

**Severidad:** media como defecto de codigo, alta como trampa. No rompe la app
—la UI siempre habla en 0-100— pero garantiza que cualquier consumidor
programatico del `NativeVideoManager`, que es justo lo que sera `vng-bench`,
configure algo distinto de lo que cree.

---

## [H-10] `yolo_frequency` no tiene setter: la variable independiente del experimento no es ajustable

**Ubicacion:** `src-tauri/src/vng/native_video.rs:235` (campo), `:301` (default),
`:516` (unica lectura). No existe `set_yolo_frequency`. `src-tauri/src/lib.rs`
no contempla la clave en el dispatch de `SetConfig`.

`yolo_frequency` se fija en **10** en el constructor y no hay ninguna via para
cambiarlo: ni setter en `NativeVideoManager`, ni clave en el dispatch de
WebSocket, ni comando Tauri.

Del lado del frontend si hay control: `AlgorithmTab.tsx:47-48` muestra un campo
para `yolo_frequency` con default 4, que persiste a
`vng.algorithm.yolo_frequency` (`useSettingsConfig.ts:41`). Ese valor se guarda y
**nadie lo lee**. Es un control de interfaz sin efecto, igual que `erode`
en [H-08].

**Por que importa mas que los otros hallazgos.** El barrido de frecuencia de YOLO
es la **variable independiente del experimento** y la abscisa de la figura
central del paper. Hoy no es ajustable por ninguna via publica. `vng-bench`
tendra que exponerla explicitamente — es justo lo que pide la interfaz
`--yolo off|every:<N>`.

Ademas hay una discrepancia de valores: la UI sugiere 4, el backend usa 10. Si el
manuscrito declara la frecuencia de produccion, el valor efectivo es **10**.

**Severidad:** alta para el trabajo experimental. Ninguna para la app, que
funciona con el valor fijo.

---

## [H-11] El modelo ONNX no esta en el repositorio

**Ubicacion:** `backend/models/` contiene unicamente `.gitkeep` (0 bytes).
`resolve_model_path` (`src-tauri/src/lib.rs:23-39`) busca
`backend/models/siev_yolo26.onnx` en el directorio de recursos, en `../backend/
models/` y en una ruta absoluta embebida.

El archivo no existe en el arbol. Sin el, `Session::commit_from_file` falla, la
sesion queda en `None` y la rama de YOLO nunca se ejecuta: el sistema corre
siempre en modo matematico puro, aunque `use_yolo` este activo.

**Consecuencias.**

1. **La comparacion hibrida no se puede hacer hoy.** Medir el efecto de la
   frecuencia de anclaje requiere el modelo; sin el solo se puede medir la
   condicion `--yolo off`.
2. Es un requisito de reproducibilidad: el manifiesto de corrida tiene que
   registrar el hash del `.onnx`, y el modelo debe acompanar a los materiales
   publicados o estar referenciado de forma recuperable.
3. `resolve_model_path` tiene una ruta absoluta embebida a un directorio
   personal (`/home/nick/Escritorio/Proyectos/Siev/...`) como ultimo recurso.
   Funciona en esta maquina y en ninguna otra.

**Severidad:** bloqueante para el experimento principal.

---

## [H-12] El corte de confianza de YOLO esta hardcodeado y el resultado es hipersensible a el

**Ubicacion:** `src-tauri/src/vng/native_video.rs:1515`.

```rust
if confidence < 0.25 { continue; }
```

Sin setter, sin clave de configuracion, sin handler en `lib.rs`. El frontend tiene
un control `yolo_confidence` con default **0.5** (`AlgorithmTab.tsx:58`,
`useSettingsConfig.ts:42`) que persiste y que el backend **ignora por completo**:
`grep -rn yolo_confidence src-tauri/src/` no devuelve nada.

**Medicion sobre los 800 cuadros del fixture** (modelo re-exportado con nms=True):

| corte | tasa de anclaje |
|---:|---:|
| 0.25 (el del codigo) | 85.2% |
| 0.30 | 62.6% |
| 0.35 | 25.1% |

Diez centesimas mueven la tasa sesenta puntos. La confianza de la **segunda**
deteccion —siempre la debil— tiene mediana 0.324, justo en la zona empinada; la
primera va comoda entre 0.5 y 0.65.

**Relevancia.** `anchor_succeeded` es la abscisa de la figura central del paper, y
depende de un corte que nadie declaro y al que el resultado es extremadamente
sensible. Tiene que ir explicito en el `config.toml` publicado o la cifra no es
reproducible. Y la UI diciendo 0.5 mientras el codigo usa 0.25 es el cuarto
parametro declarado que no coincide con el efectivo, tras [H-08], [H-09] y [H-10].

**Severidad:** alta para el trabajo experimental.

---

## [H-13] Heuristicas expresadas como fraccion de una ventana cuyo tamano el sistema varia por diseno

**Ubicacion:** `src-tauri/src/vng/native_video.rs:1613-1623` (parpadeo) y
`:1632` (`max_area`).

Las dos heuristicas se miden contra la ventana de busqueda:

```rust
let white_ratio = white_count / (search_w * search_h) as f32;
if white_ratio > blink_white_ratio { /* parpadeo */ }
...
let max_area = (full_rw * full_rh) as f32 * max_area_ratio;
```

Pero el tamano de esa ventana **cambia 4.4x** segun el anclaje haya funcionado o
no, que es una decision de diseno del propio sistema:

| ventana | area | pupila (5736 px) ocupa |
|---|---:|---:|
| ROI manual `209x186` | 38874 px | 14.8% |
| caja anclada `78x114` | 8892 px | **64.5%** |

Mismo ojo, mismo estado fisiologico, misma pupila. Solo cambia el denominador.
Con los defaults (`blink_white_ratio = 0.60`, `max_area_ratio = 0.60`) la
condicion anclada supera ambos limites: el detector declara "parpadeo" antes de
llegar a la morfologia, y si lo superara, `max_area` (5335) rechazaria la pupila
(5736) por grande.

**Medicion, 800 cuadros, umbrales (47,57):**

| | ratios 0.60/0.60 | ratios 0.85/0.85 |
|---|---|---|
| YOLO off | 783 / 683 | 783 / 683 *(identico: control limpio)* |
| YOLO on | **74** / 722 (+707 parpadeos) | 762 / 785 |

Con YOLO apagado los ratios son inertes —la pupila nunca se acerca a los
limites— asi que el control aisla el efecto. Recalibrados, el ojo derecho pasa de
9.3% a 95.3%.

**No es un bug de programacion**, es un acoplamiento de diseno entre dos
subsistemas pensados para operar juntos que nunca llegaron a hacerlo: el ONNX
estaba en formato incompatible ([H-11]) y el anclaje jamas se ejecuto, asi que
nadie vio el fallo.

**Propuesta (no aplicada, requiere cambiar el detector).** Si ambos limites se
expresaran respecto del area **esperada de pupila** en vez del area de la
ventana, serian invariantes al anclaje. Es un cambio de diseno defendible como
contribucion del metodo, no una correccion de defecto.

---

## [H-14] El radio de clausura morfologica es la mitad de lo que necesitan los reflejos

**Ubicacion:** `src-tauri/src/vng/native_video.rs:1726`.

```rust
close_mut(scratch_thresh, Norm::LInf, 2);   // hardcodeado
```

La clausura existe para rellenar agujeros en la mascara binaria. Los agujeros
reales son los reflejos especulares de la iluminacion IR cayendo dentro de la
pupila. Medidos sobre el fixture, en la pupila del ojo izquierdo:

```
pupila (<=57):          4990 px
reflejo especular 1:      65 px   bbox 9x9   radio_equiv 4.5
reflejo especular 2:      54 px   bbox 8x8   radio_equiv 4.1
```

Con `LInf` radio 2 el elemento estructurante es 5x5 y cierra huecos de hasta ~4-5
px. Los reflejos miden **8-9 px**: le falta aproximadamente el doble de radio.

**Explica la respuesta no monotona al umbral** documentada en el barrido: en
umbral bajo sobrevive solo el nucleo oscuro, compacto y redondo; en umbral medio
la mancha crece hasta abrazar los reflejos, que la perforan y la clausura no
alcanza a cerrar, y la circularidad la rechaza; en umbral alto todo se inunda y
vuelve a ser compacta. Ojo derecho util en 40-55, ojo izquierdo en 54-62, con una
zona muerta intermedia en el izquierdo.

**Alternativa sin software.** El reflejo corneal es la imagen especular de la
fuente. Con iluminacion de menos de 1 USD, desplazar el LED fuera del eje optico
mueve el reflejo al iris o la esclera y elimina el problema en el origen. Mas
barato y mas robusto que subir el radio de clausura, que ademas engorda la pupila
y altera la estimacion de radio.

**Severidad:** media. Es un parametro hardcodeado que apunta exactamente al modo
de fallo dominante de este hardware y nunca se ajusto.

---

# Decisiones de diseno

No son hallazgos: son cortes decididos durante la reorganizacion que conviene
dejar escritos.

## [D-01] El tiempo entra como parametro a `vng-core`

`src-tauri/src/math/processor.rs:361` (`export_calibration_snapshot`) consulta
`chrono::Local::now()`. Es no determinismo dentro de codigo que migra a core.

**Decision:** el tiempo no se consulta dentro de core. `export_calibration_snapshot`
recibe el instante como parametro y es el llamador (`vng-app`) quien lee el
reloj. No afecta al seguimiento ni a la traza de regresion — solo sella el
snapshot de calibracion — pero deja `vng-core` determinista por construccion.

## [D-02] Snapshot de parametros: por cuadro en la app, congelado en el banco

`vng-app` mantiene el snapshot por cuadro, que es el comportamiento actual y
permite cambiar parametros a mitad de sesion desde la UI. `vng-bench` congela los
parametros al inicio de la corrida y no los toca. El protocolo experimental ya
compromete parametros fijos antes de la primera medicion; esto solo lo hace
explicito en codigo.

## [D-03] Punto de corte del grabador de video

Se queda donde esta: post brillo y contraste, pre deteccion. Ver [H-07] para la
consecuencia metodologica que hay que declarar.

---

# Verificaciones

## [V-01] Los dos bloques de actualizacion de estado son identicos

Requisito previo a unificarlos en `EyeTracker::process_frame` (Fase 3). Queda
escrito para que la pregunta "¿unificar esos bloques cambio algo?" tenga
respuesta documentada.

**Bloques comparados:** `native_video.rs:1099-1140` (ojo derecho) y `:1163-1202`
(ojo izquierdo), 42 y 40 lineas.

**Normalizacion aplicada** (solo renombres, ninguna reescritura):

```
_right\b   -> _EYE        _left\b  -> _EYE
pr         -> p           pl       -> p
smoothed_pr-> smoothed_p  smoothed_pl -> smoothed_p
(ojo derecho) -> (ojo EYE)  (ojo izquierdo) -> (ojo EYE)
espacios finales eliminados
```

**Diff normalizado completo:**

```diff
@@ -4,12 +4,10 @@
                         if blink_start_EYE.is_none() {
                             blink_start_EYE = Some(std::time::Instant::now());
                         } else if blink_start_EYE.unwrap().elapsed().as_millis() > 500 {
-                            // Parpadeo muy largo -> reset
                             last_pupil_EYE = None;
                             velocity_EYE = (0.0, 0.0);
                             blink_start_EYE = None;
                         }
-                        // No degradar velocidad ni incrementar lost_count
                     } else if p.found {
                         blink_start_EYE = None;
                         if let Some(ref prev) = last_pupil_EYE {
```

**Resultado:** las unicas diferencias son **dos lineas de comentario** presentes
solo en el bloque derecho (`// Parpadeo muy largo -> reset` y `// No degradar
velocidad ni incrementar lost_count`). Cero diferencias de codigo ejecutable:
mismo orden de ramas, mismos coeficientes (0.5/0.5 en el EMA de velocidad,
0.7/0.3 en el radio, 0.8 de decaimiento, 500 ms de parpadeo), mismas
asignaciones. La unificacion es segura.

**Bloque derecho, literal (`:1099-1140`):**

```rust
                if let Some(ref pr) = pupil_right {
                    if pr.confidence == -1.0 {
                        // Parpadeo detectado: congelar estado
                        if blink_start_right.is_none() {
                            blink_start_right = Some(std::time::Instant::now());
                        } else if blink_start_right.unwrap().elapsed().as_millis() > 500 {
                            // Parpadeo muy largo -> reset
                            last_pupil_right = None;
                            velocity_right = (0.0, 0.0);
                            blink_start_right = None;
                        }
                        // No degradar velocidad ni incrementar lost_count
                    } else if pr.found {
                        blink_start_right = None;
                        if let Some(ref prev) = last_pupil_right {
                            if prev.found {
                                let nvx = pr.center_x - prev.center_x;
                                let nvy = pr.center_y - prev.center_y;
                                velocity_right.0 = velocity_right.0 * 0.5 + nvx * 0.5;
                                velocity_right.1 = velocity_right.1 * 0.5 + nvy * 0.5;
                            }
                        }
                        // B5: Suavizado temporal del radio
                        let mut smoothed_pr = *pr;
                        if let Some(ref prev) = last_pupil_right {
                            if prev.found {
                                smoothed_pr.radius = prev.radius * 0.7 + pr.radius * 0.3;
                            }
                        }
                        last_pupil_right = Some(smoothed_pr);
                        lost_count_right = 0;
                    } else {
                        blink_start_right = None;
                        velocity_right.0 *= 0.8;
                        velocity_right.1 *= 0.8;
                        lost_count_right += 1;
                        if lost_count_right > lost_tolerance_val {
                            last_pupil_right = None;
                            velocity_right = (0.0, 0.0);
                        }
                    }
                }
```

**Bloque izquierdo, literal (`:1163-1202`):**

```rust
                if let Some(ref pl) = pupil_left {
                    if pl.confidence == -1.0 {
                        // Parpadeo detectado: congelar estado
                        if blink_start_left.is_none() {
                            blink_start_left = Some(std::time::Instant::now());
                        } else if blink_start_left.unwrap().elapsed().as_millis() > 500 {
                            last_pupil_left = None;
                            velocity_left = (0.0, 0.0);
                            blink_start_left = None;
                        }
                    } else if pl.found {
                        blink_start_left = None;
                        if let Some(ref prev) = last_pupil_left {
                            if prev.found {
                                let nvx = pl.center_x - prev.center_x;
                                let nvy = pl.center_y - prev.center_y;
                                velocity_left.0 = velocity_left.0 * 0.5 + nvx * 0.5;
                                velocity_left.1 = velocity_left.1 * 0.5 + nvy * 0.5;
                            }
                        }
                        // B5: Suavizado temporal del radio
                        let mut smoothed_pl = *pl;
                        if let Some(ref prev) = last_pupil_left {
                            if prev.found {
                                smoothed_pl.radius = prev.radius * 0.7 + pl.radius * 0.3;
                            }
                        }
                        last_pupil_left = Some(smoothed_pl);
                        lost_count_left = 0;
                    } else {
                        blink_start_left = None;
                        velocity_left.0 *= 0.8;
                        velocity_left.1 *= 0.8;
                        lost_count_left += 1;
                        if lost_count_left > lost_tolerance_val {
                            last_pupil_left = None;
                            velocity_left = (0.0, 0.0);
                        }
                    }
                }
```
