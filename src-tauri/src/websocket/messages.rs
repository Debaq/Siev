use serde::{Deserialize, Serialize};
use crate::math::processor::ProcessedEyeData;

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum WsMessage {
    // Rust -> Frontend: Data Broadcast
    EyeData(ProcessedEyeData),
    VideoFrame {
        data: String, // Base64 JPEG
    },
    ImuData {
        yaw: f32,
        pitch: f32,
        roll: f32,
    },
    Status {
        python_connected: bool,
        hardware_connected: bool,
    },
    Error {
        source: String,
        message: String,
    },
    CamerasList {
        cameras: serde_json::Value,
    },

    // Frontend -> Rust: Commands
    ListCameras,
    StartCapture {
        camera_id: i32,
        width: u32,
        height: u32,
    },
    StopCapture,
    SetConfig {
        key: String,
        value: serde_json::Value,
    },
    ConnectHardware {
        port: String,
        baud_rate: u32,
    },
    DisconnectHardware,
    SendHardwareCommand {
        cmd: String,
    },
}
