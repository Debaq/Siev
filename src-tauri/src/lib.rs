use std::sync::{Mutex, Arc};
use tauri::{State, Window, Manager};

pub mod math;
pub mod hardware;
pub mod database;

use math::processor::{EyeProcessor, RawEyeData, ProcessedEyeData};
use hardware::manager::HardwareManager;
use database::service::DatabaseService;
use database::models::{Patient, Session, CreatePatientDto, UpdatePatientDto, Specialist};

// Application State
pub struct AppState {
    pub eye_processor: Mutex<EyeProcessor>,
    pub hardware_manager: Mutex<HardwareManager>,
    pub db: Arc<DatabaseService>,
}

// --- Math & Processing Commands ---

#[tauri::command]
fn process_eye_data_batch(
    batch: Vec<RawEyeData>,
    state: State<AppState>
) -> Vec<ProcessedEyeData> {
    let mut processor = state.eye_processor.lock().unwrap();
    processor.process_batch(batch)
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

// --- Database Commands ---

#[tauri::command]
async fn get_patients(
    search: Option<String>,
    state: State<'_, AppState>
) -> Result<Vec<Patient>, String> {
    state.db.get_patients(search).await
}

#[tauri::command]
async fn create_patient(
    data: CreatePatientDto,
    state: State<'_, AppState>
) -> Result<Patient, String> {
    state.db.create_patient(data).await
}

#[tauri::command]
async fn update_patient(
    id: i64,
    data: UpdatePatientDto,
    state: State<'_, AppState>
) -> Result<Patient, String> {
    state.db.update_patient(id, data).await
}

#[tauri::command]
async fn delete_patient(
    id: i64,
    state: State<'_, AppState>
) -> Result<(), String> {
    state.db.delete_patient(id).await
}

#[tauri::command]
async fn get_sessions(
    patient_id: i64,
    state: State<'_, AppState>
) -> Result<Vec<Session>, String> {
    state.db.get_sessions(patient_id).await
}

#[tauri::command]
async fn create_session(
    patient_id: i64,
    specialist_id: Option<i64>,
    description: Option<String>,
    state: State<'_, AppState>
) -> Result<Session, String> {
    state.db.create_session(patient_id, specialist_id, description).await
}

#[tauri::command]
async fn get_specialists(state: State<'_, AppState>) -> Result<Vec<Specialist>, String> {
    state.db.get_specialists().await
}

#[tauri::command]
async fn create_specialist(name: String, state: State<'_, AppState>) -> Result<Specialist, String> {
    state.db.create_specialist(name).await
}

#[tauri::command]
async fn delete_specialist(id: i64, state: State<'_, AppState>) -> Result<(), String> {
    state.db.delete_specialist(id).await
}

// --- Settings Commands ---

#[tauri::command]
async fn get_setting(
    key: String,
    state: State<'_, AppState>
) -> Result<Option<String>, String> {
    state.db.get_setting(&key).await
}

#[tauri::command]
async fn set_setting(
    key: String,
    value: String,
    state: State<'_, AppState>
) -> Result<(), String> {
    state.db.set_setting(&key, &value).await
}

#[tauri::command]
fn get_default_storage_path(app: tauri::AppHandle) -> String {
    app.path().document_dir()
       .map(|p| p.join("SIEV_Media").to_string_lossy().to_string())
       .unwrap_or_else(|_| "siev_data".to_string())
}

// --- System Commands ---

#[tauri::command]
fn get_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[tauri::command]
fn set_filtering_enabled(enabled: bool, state: State<AppState>) {
    let mut processor = state.eye_processor.lock().unwrap();
    processor.filtering_enabled = enabled;
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            // Log startup
            println!("SIEV Application started");
            println!("Version: {}", env!("CARGO_PKG_VERSION"));

            // Initialize Database Async
            let app_handle = app.handle();
            let db_service = tauri::async_runtime::block_on(async {
                DatabaseService::new(app_handle).await
            }).expect("Failed to initialize database");

            // Manage State
            app.manage(AppState {
                eye_processor: Mutex::new(EyeProcessor::new()),
                hardware_manager: Mutex::new(HardwareManager::new()),
                db: Arc::new(db_service),
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_version,
            process_eye_data_batch,
            reset_calibration,
            list_serial_ports,
            connect_hardware,
            disconnect_hardware,
            send_hardware_command,
            // DB Commands
            get_patients,
            create_patient,
            update_patient,
            delete_patient,
            get_sessions,
            create_session,
            get_specialists,
            create_specialist,
            delete_specialist,
            // Settings Commands
            get_setting,
            set_setting,
            get_default_storage_path,
            set_filtering_enabled
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
