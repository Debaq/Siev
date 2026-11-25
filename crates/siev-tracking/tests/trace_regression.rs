//! FASE 1 — Prueba de regresion de traza, tolerancia CERO.
//!
//! Pasa una secuencia PGM determinista por el bucle de captura REAL (el mismo
//! codigo que corre en produccion, no una reimplementacion) y compara la traza
//! resultante, byte a byte, contra un patron de referencia.
//!
//! Esta prueba debe pasar al final de cada fase de la reorganizacion. Si falla,
//! el cambio altero el comportamiento y hay que revertirlo.
//!
//! Regenerar el patron:  SIEV_REGEN_TRACE=1 cargo test --test trace_regression
//! (Solo tras verificar que la diferencia proviene del toolchain, nunca para
//! silenciar un fallo.)
//!
//! La garantia de exactitud vale para el toolchain fijado en rust-toolchain.toml
//! y para el target x86_64-unknown-linux-gnu.

use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use siev_tracking::math::processor::EyeProcessor;
use siev_tracking::vng::native_video::NativeVideoManager;
use siev_tracking::vng::trace::PgmSequence;
use siev_tracking::bus::EventBus;

/// Parametros del detector para la corrida de referencia.
///
/// Fijados explicitamente, nunca heredados de `Default`. Ver [H-01] en
/// NOTAS_HALLAZGOS.md: el default de Rust para `manual_roi_right` deja una caja
/// de busqueda de 1 px de ancho. Aqui se usa el orden correcto, el mismo que
/// aplica el frontend (`useSessionConfig.ts:60`).
fn apply_reference_params(nv: &NativeVideoManager) {
    // Geometria: la fuente ya es un cuadro combinado (ver [H-07]), asi que el
    // recorte dual se deja casi en identidad para no recortar un recorte.
    nv.set_nose_width(0.0);
    nv.set_eye_height(0.5);

    // ROI manual, orden correcto (temporal < nasal en el ojo derecho)
    nv.set_manual_roi_right(0.1, 0.9, 0.9, 0.1);
    nv.set_manual_roi_left(0.1, 0.9, 0.1, 0.9);

    // Imagen: NO se llama a set_brightness ni a set_contrast a proposito.
    //
    // `set_contrast` espera la escala 0-100 de la UI y la mapea a 0.5-2.0
    // (`*c = 0.5 + (value/100)*1.5`), asi que el multiplicador identidad 1.0 no
    // es alcanzable de forma exacta por esa via: pasarle 1.0 da 0.515, que
    // levanta el negro a 62 y deja al detector sin un solo pixel bajo el umbral.
    // Ver [H-09]. Los defaults del constructor ya son brillo 0 y contraste 1.0,
    // con lo que `apply_brightness_contrast_luma` retorna de inmediato y la
    // transformacion es identidad exacta.
    nv.set_smooth(2.5);

    // Umbral fijo: el adaptativo (valor 0) tambien es determinista, pero un
    // umbral explicito deja la traza mas facil de interpretar.
    // Umbral por ojo. Son distintos a proposito: las fuentes de luz de la
    // mascara no iluminan homogeneamente, asi que en operacion el evaluador
    // ajusta cada ojo por separado. El campo es `[u8; 2]` justamente por eso.
    let (thr_r, thr_l) = umbrales_de_referencia();
    nv.set_thresholds(thr_r, thr_l);

    // Filtros de contorno
    nv.set_min_circularity(0.55);
    nv.set_min_area(30);
    nv.set_aspect_ratio_min(0.4);
    nv.set_aspect_ratio_max(2.5);

    // Estado inter-cuadro
    nv.set_blink_detection(true);
    // Ambos limites son fracciones de la ventana de busqueda, cuyo tamano
    // cambia 4.4x segun haya anclaje. `SIEV_RATIOS="blink,maxarea"` permite
    // recalibrarlos para medir el anclaje sin tocar el detector.
    let (br, mar) = match std::env::var("SIEV_RATIOS") {
        Ok(v) => { let mut i = v.split(',').map(|x| x.trim().parse::<f32>().unwrap());
                   (i.next().unwrap(), i.next().unwrap()) }
        Err(_) => (0.60, 0.60),
    };
    nv.set_blink_white_ratio(br);
    nv.set_max_area_ratio(mar);
    nv.set_lost_tolerance(5);
    nv.set_velocity_margin_factor(2.0);

    // Sin modelo: la condicion de referencia es --yolo off.
    // `SIEV_YOLO=<ruta.onnx>` lo activa para sondear el modelo.
    nv.set_use_yolo(std::env::var("SIEV_YOLO").is_ok());
    nv.set_show_debug(false);

    // NOTA: `erode` queda en su default [1, 1]. No existe setter. Ver [H-08].
}

/// Umbrales por ojo. `SIEV_THR="R,L"` permite barrerlos sin recompilar.
fn umbrales_de_referencia() -> (u8, u8) {
    match std::env::var("SIEV_THR") {
        Ok(v) => {
            let mut it = v.split(',').map(|x| x.trim().parse::<u8>().unwrap());
            (it.next().unwrap(), it.next().unwrap())
        }
        // Elegidos empiricamente con el detector real sobre este material.
        // Barrido en 30 cuadros y validacion en 150:
        //   ojo derecho   meseta 40..55, pico en 47  -> 148/150 (98.7%)
        //   ojo izquierdo ventana 54..62, centro 57  -> 150/150 (100%)
        // No hay umbral unico bueno para ambos: entre 30 y 50 el ojo izquierdo
        // no detecta nada. Las fuentes de luz de la mascara no iluminan de
        // forma homogenea, y por eso el campo es `[u8; 2]` y el evaluador
        // ajusta cada ojo por separado en operacion.
        Err(_) => (47, 57),
    }
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

#[test]
fn traza_identica_al_patron_de_referencia() {
    let root = repo_root();
    let seq_dir = match std::env::var("SIEV_SEQ_DIR") {
        Ok(d) => PathBuf::from(d),
        Err(_) => root.join("fixtures/seq_eyes_800"),
    };
    let ref_path = root.join("crates/siev-tracking/tests/fixtures/trace_ref.jsonl");

    if !seq_dir.is_dir() {
        eprintln!(
            "SALTADA: falta la secuencia en {}.\n\
             Regenerar con fixtures/README.md (ffmpeg -pix_fmt gray -f image2 %06d.pgm).",
            seq_dir.display()
        );
        return;
    }

    // 200 Hz sinteticos: dt constante, sin dependencia del reloj de pared.
    let seq = PgmSequence::open(&seq_dir, 200.0).expect("secuencia PGM ilegible");
    let n_frames = seq.len();

    let (bus, _rx) = EventBus::new();
    let nv = NativeVideoManager::new(
        Arc::new(bus),
        Arc::new(Mutex::new(EyeProcessor::new())),
        Arc::new(Mutex::new(None)),
    );
    apply_reference_params(&nv);

    // Ruta unica por proceso: dos corridas simultaneas compartiendo un archivo
    // fijo se pisan entre si y producen trazas entrelazadas.
    let out_path = std::env::temp_dir()
        .join(format!("siev_trace_actual_{}.jsonl", std::process::id()));

    // Ruta de modelo inexistente a proposito: con use_yolo=false la sesion ONNX
    // nunca se ejecuta, y no cargarla elimina a ort de la ecuacion determinista.
    let model = std::env::var("SIEV_YOLO").unwrap_or_else(|_| String::from("/nonexistent/no-yolo.onnx"));
    nv.run_pgm_sequence(seq, out_path.clone(), model)
        .expect("la corrida de la secuencia fallo");

    let actual = std::fs::read_to_string(&out_path).expect("no se escribio la traza");

    // Modo barrido: informa tasa de deteccion por ojo y sale sin comparar.
    if std::env::var("SIEV_SWEEP").is_ok() {
        let (tr, tl) = umbrales_de_referencia();
        for eye in ["right", "left"] {
            let lineas: Vec<&str> = actual.lines().filter(|l| l.contains(&format!("\"eye\":\"{}\"", eye))).collect();
            let det = lineas.iter().filter(|l| l.contains("\"status\":\"detected\"")).count();
            let blink = lineas.iter().filter(|l| l.contains("\"status\":\"blink\"")).count();
            eprintln!("[SWEEP] thr=({},{}) ojo={:5} detectado={:3}/{:3} parpadeo={:3}",
                tr, tl, eye, det, lineas.len(), blink);
        }
        return;
    }

    assert_eq!(
        actual.lines().count(),
        n_frames * 2,
        "se esperaban 2 lineas por cuadro ({} cuadros)",
        n_frames
    );

    // Guarda de sensibilidad: una traza degenerada (por ejemplo, todo "blink"
    // porque el material tiene relleno negro) hace que la prueba pase siempre,
    // pase lo que pase con el detector. Una red de seguridad que no puede
    // fallar no es una red de seguridad.
    verificar_traza_no_degenerada(&actual);

    if std::env::var("SIEV_REGEN_TRACE").is_ok() {
        std::fs::create_dir_all(ref_path.parent().unwrap()).unwrap();
        std::fs::write(&ref_path, &actual).unwrap();
        eprintln!("PATRON REGENERADO: {} ({} lineas)", ref_path.display(), actual.lines().count());
        return;
    }

    let expected = std::fs::read_to_string(&ref_path).unwrap_or_else(|_| {
        panic!(
            "falta el patron de referencia en {}.\n\
             Generarlo con: SIEV_REGEN_TRACE=1 cargo test --test trace_regression",
            ref_path.display()
        )
    });

    if actual == expected {
        return;
    }

    // Reporte util: primera divergencia, no un volcado de 1600 lineas.
    let (a, e): (Vec<_>, Vec<_>) = (actual.lines().collect(), expected.lines().collect());
    if a.len() != e.len() {
        panic!("distinto numero de lineas: actual={} referencia={}", a.len(), e.len());
    }
    for (i, (la, le)) in a.iter().zip(e.iter()).enumerate() {
        if la != le {
            panic!(
                "DIVERGENCIA EN LA TRAZA (tolerancia cero), linea {} de {}\n\
                 referencia: {}\n\
                 actual    : {}\n\n\
                 El cambio altero el comportamiento del detector. Revertir.",
                i + 1, a.len(), le, la
            );
        }
    }
}

/// La traza debe ejercitar de verdad al detector: si no hay detecciones ni
/// transiciones de estado, el patron no puede detectar ninguna regresion.
fn verificar_traza_no_degenerada(traza: &str) {
    let mut detected = 0usize;
    let mut transiciones = 0usize;
    let mut previo: Option<&str> = None;
    let mut estados = std::collections::BTreeSet::new();

    for linea in traza.lines() {
        // Extraccion textual simple: la traza es JSONL de forma fija.
        let status = linea
            .split("\"status\":\"")
            .nth(1)
            .and_then(|r| r.split('"').next())
            .unwrap_or("");
        estados.insert(status.to_string());
        if status == "detected" {
            detected += 1;
        }
        if let Some(p) = previo {
            if p != status {
                transiciones += 1;
            }
        }
        previo = Some(status);
    }

    let total = traza.lines().count();
    assert!(
        detected * 100 >= total * 20,
        "TRAZA DEGENERADA: solo {}/{} lineas con status=detected (<20%). \
         Estados presentes: {:?}. El patron no ejercita al detector y la prueba \
         pasaria ante cualquier regresion. Revisar el material de entrada \
         (ver [H-07] en NOTAS_HALLAZGOS.md).",
        detected, total, estados
    );
    assert!(
        transiciones >= 4,
        "TRAZA DEGENERADA: solo {} transiciones de estado. El patron no ejercita \
         el estado inter-cuadro (parpadeo, perdida, recuperacion), que es \
         justamente lo que la Fase 3 va a mover.",
        transiciones
    );
}
