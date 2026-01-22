use std::sync::Mutex;
use tauri::{State, Window};

pub mod math;
pub mod hardware;

use math::processor::{EyeProcessor, RawEyeData, ProcessedEyeData};
use hardware::manager::HardwareManager;

// Application State
pub struct AppState {
    pub eye_processor: Mutex<EyeProcessor>,
    pub hardware_manager: Mutex<HardwareManager>,
}

// --- Math & Processing Commands ---

#[tauri::command]
fn process_eye_data(
    data: RawEyeData,
    state: State<AppState>
) -> ProcessedEyeData {
    let mut processor = state.eye_processor.lock().unwrap();
    processor.process(data)
}

#[tauri::command]
fn reset_calibration(state: State<AppState>) {
    let mut processor = state.eye_processor.lock().unwrap();
    processor.reset_calibration();
}

// --- Hardware Commands ---

#[tauri::command]
fn list_serial_ports(state: State<AppState>) -> Vec<String> {
    let manager = state.hardware_manager.lock().unwrap();
    manager.list_ports()
}

#[tauri::command]
fn connect_hardware(
    port: String, 
    baud_rate: u32, 
    window: Window, 
    state: State<AppState>
) -> Result<String, String> {
    let mut manager = state.hardware_manager.lock().unwrap();
    manager.connect(&port, baud_rate, window).map(|_| "Connected".to_string())
}

#[tauri::command]
fn disconnect_hardware(state: State<AppState>) {
    let mut manager = state.hardware_manager.lock().unwrap();
    manager.disconnect();
}

#[tauri::command]
fn send_hardware_command(cmd: String, state: State<AppState>) -> Result<(), String> {
    let manager = state.hardware_manager.lock().unwrap();
    manager.send_command(&cmd)
}

// --- System Commands ---

#[tauri::command]
fn get_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(AppState {
            eye_processor: Mutex::new(EyeProcessor::new()),
            hardware_manager: Mutex::new(HardwareManager::new()),
        })
        .invoke_handler(tauri::generate_handler![
            get_version,
            process_eye_data,
            reset_calibration,
            list_serial_ports,
            connect_hardware,
            disconnect_hardware,
            send_hardware_command
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}