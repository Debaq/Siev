//! Controles de imagen de la camara (V4L2), aplicados en el sensor, antes de
//! la compresion MJPEG. Rinden mas que el brillo/contraste por software.
//!
//! Se abre un segundo descriptor del dispositivo: V4L2 permite fijar controles
//! mientras otro descriptor esta transmitiendo.

use serde::{Deserialize, Serialize};

// IDs estandar de V4L2 (linux/v4l2-controls.h)
pub const BRILLO: u32 = 0x0098_0900;
pub const CONTRASTE: u32 = 0x0098_0901;
pub const GAMMA: u32 = 0x0098_0910;
pub const NITIDEZ: u32 = 0x0098_091b;
pub const CONTRALUZ: u32 = 0x0098_091c;
pub const EXPOSICION_AUTO: u32 = 0x009a_0901;
pub const EXPOSICION: u32 = 0x009a_0902;
pub const EXPOSICION_PRIORIDAD: u32 = 0x009a_0903;

/// Valores del menu EXPOSICION_AUTO.
pub const EXPOSICION_MANUAL: i64 = 1;
pub const EXPOSICION_APERTURA: i64 = 3;

/// Controles que la app ofrece, en orden de presentacion.
pub const OFRECIDOS: [(u32, &str); 7] = [
    (EXPOSICION_AUTO, "Exposicion automatica"),
    (EXPOSICION, "Tiempo de exposicion"),
    (GAMMA, "Gamma"),
    (BRILLO, "Brillo (sensor)"),
    (CONTRASTE, "Contraste (sensor)"),
    (NITIDEZ, "Nitidez"),
    (CONTRALUZ, "Compensacion de contraluz"),
];

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ControlHw {
    pub id: u32,
    pub nombre: String,
    pub min: i64,
    pub max: i64,
    pub defecto: i64,
    pub actual: i64,
}

#[cfg(target_os = "linux")]
pub fn listar(indice: u32) -> Result<Vec<ControlHw>, String> {
    use v4l::control::Value;
    let dev = v4l::Device::new(indice as usize).map_err(|e| e.to_string())?;
    let desc = dev.query_controls().map_err(|e| e.to_string())?;
    let mut out = Vec::new();
    for (id, nombre) in OFRECIDOS {
        let Some(d) = desc.iter().find(|d| d.id == id) else { continue };
        let actual = match dev.control(id).map(|c| c.value) {
            Ok(Value::Integer(v)) => v,
            Ok(Value::Boolean(b)) => b as i64,
            _ => d.default,
        };
        out.push(ControlHw { id, nombre: nombre.into(), min: d.minimum, max: d.maximum, defecto: d.default, actual });
    }
    Ok(out)
}

#[cfg(target_os = "linux")]
pub fn fijar(indice: u32, id: u32, valor: i64) -> Result<(), String> {
    use v4l::control::{Control, Value};
    let dev = v4l::Device::new(indice as usize).map_err(|e| e.to_string())?;
    dev.set_control(Control { id, value: Value::Integer(valor) }).map_err(|e| format!("control {id:#x}={valor}: {e}"))
}

#[cfg(not(target_os = "linux"))]
pub fn listar(_indice: u32) -> Result<Vec<ControlHw>, String> {
    Ok(Vec::new())
}

#[cfg(not(target_os = "linux"))]
pub fn fijar(_indice: u32, _id: u32, _valor: i64) -> Result<(), String> {
    Ok(())
}

/// Tiempo de exposicion maximo (unidades UVC de 100 us) que cabe en un cuadro.
/// Verificado en la USB GS CAM: 141 (14,1 ms) -> 72 fps reales. En manual la
/// camara no expone ganancia, asi que la imagen se oscurece; en automatico
/// sube la ganancia interna y mantiene 225 fps.
pub fn exposicion_max_para(fps: u32) -> i64 {
    if fps == 0 { 10_000 } else { (10_000 / fps as i64).max(1) }
}
