//! Bus de eventos en proceso: reemplaza al servidor WebSocket de la version
//! Tauri. El hilo de captura publica aqui y la GUI drena en cada repintado.
//!
//! Regla: el hilo de captura NUNCA se bloquea por un consumidor lento. Todo
//! envio es `try_send`; si el canal esta lleno el evento se descarta.

use std::sync::mpsc::{self, Receiver, SyncSender, TrySendError};
use std::sync::Mutex;

use image::RgbImage;

use crate::math::processor::ProcessedEyeData;

/// Eventos que publica el pipeline de seguimiento.
#[derive(Debug, Clone)]
pub enum TrackEvent {
    EyeData(ProcessedEyeData),
    CameraStatus { status: String }, // "disconnected", "connecting", "connected"
}

/// Extremo receptor para la GUI.
pub struct BusReceiver {
    pub events: Receiver<TrackEvent>,
    pub frames: Receiver<RgbImage>,
}

pub struct EventBus {
    events: SyncSender<TrackEvent>,
    frames: SyncSender<RgbImage>,
    notify: Mutex<Option<Box<dyn Fn() + Send + Sync>>>,
}

impl EventBus {
    pub fn new() -> (Self, BusReceiver) {
        // 4096 eventos ~ 20 s a 200 Hz: holgura de sobra para un repintado.
        let (etx, erx) = mpsc::sync_channel(4096);
        // Solo interesa el cuadro mas reciente.
        let (ftx, frx) = mpsc::sync_channel(2);
        (
            Self { events: etx, frames: ftx, notify: Mutex::new(None) },
            BusReceiver { events: erx, frames: frx },
        )
    }

    /// Callback invocado tras publicar un cuadro (p. ej. `ctx.request_repaint`).
    pub fn set_notifier(&self, f: impl Fn() + Send + Sync + 'static) {
        *self.notify.lock().unwrap() = Some(Box::new(f));
    }

    pub fn broadcast(&self, ev: &TrackEvent) {
        match self.events.try_send(ev.clone()) {
            Ok(()) | Err(TrySendError::Full(_)) | Err(TrySendError::Disconnected(_)) => {}
        }
    }

    pub fn broadcast_frame(&self, img: RgbImage) {
        let _ = self.frames.try_send(img);
        if let Some(f) = self.notify.lock().unwrap().as_ref() {
            f();
        }
    }
}
