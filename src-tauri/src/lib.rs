use std::sync::{Mutex, Arc};
use tauri::{State, Window, Manager};
use tauri_plugin_shell::process::CommandChild;

pub mod bridge;
pub mod database;
pub mod hardware;
pub mod math;
pub mod websocket;

use bridge::PythonBridge;
use database::models::{CreatePatientDto, Patient, Session, Specialist, UpdatePatientDto};
use database::service::DatabaseService;
use hardware::manager::HardwareManager;
use math::processor::{EyeProcessor, ProcessedEyeData, RawEyeData};
use websocket::{WebSocketServer, WsMessage};
use bridge::python_bridge::BridgeEvent;
use base64::{Engine as _, engine::general_purpose};
use tauri_plugin_shell::ShellExt;

// Application State
pub struct AppState {
    pub eye_processor: Arc<Mutex<EyeProcessor>>,
    pub hardware_manager: Arc<Mutex<HardwareManager>>,
    pub db: Arc<DatabaseService>,
    pub python_bridge: Arc<PythonBridge>,
    pub ws_server: Arc<WebSocketServer>,
    pub python_child: Arc<Mutex<Option<CommandChild>>>,
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
fn is_hardware_connected(state: State<AppState>) -> bool {
    let manager = state.hardware_manager.lock().unwrap();
    manager.is_connected()
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

// --- Python Bridge Commands ---

#[tauri::command]
async fn is_python_connected(state: State<'_, AppState>) -> Result<bool, String> {
    Ok(state.python_bridge.is_connected().await)
}

#[tauri::command]
async fn python_start_capture(
    camera_id: i32,
    width: u32,
    height: u32,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state
        .python_bridge
        .start_capture(camera_id, width, height)
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn python_stop_capture(state: State<'_, AppState>) -> Result<(), String> {
    state
        .python_bridge
        .stop_capture()
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn python_list_cameras(state: State<'_, AppState>) -> Result<(), String> {
    state
        .python_bridge
        .list_cameras()
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
async fn python_set_pupil_config(
    threshold: i32,
    mode: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state
        .python_bridge
        .set_pupil_config(threshold, &mode)
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn get_websocket_port(state: State<AppState>) -> u16 {
    state.ws_server.get_port()
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
            })
            .expect("Failed to initialize database");

            let hardware_manager = Arc::new(Mutex::new(HardwareManager::new()));

            // Initialize WebSocket Server
            let (ws_server, mut ws_commands) = WebSocketServer::new();
            let ws_server = Arc::new(ws_server);
            let ws_clone = Arc::clone(&ws_server);
            
            // Start WebSocket server in background (dynamic port)
            tauri::async_runtime::spawn(async move {
                if let Err(e) = ws_clone.start("127.0.0.1:0").await {
                    eprintln!("WebSocket server error: {}", e);
                }
            });

            // Initialize Python Bridge
            let python_bridge = Arc::new(PythonBridge::new());

            // Forward WebSocket commands to their handlers
            let bridge_cmds = Arc::clone(&python_bridge);
            let hw_cmds = Arc::clone(&hardware_manager);

            tauri::async_runtime::spawn(async move {
                while let Some(msg) = ws_commands.recv().await {
                    match msg {
                        WsMessage::ListCameras => {
                            let _ = bridge_cmds.list_cameras().await;
                        }
                        WsMessage::StartCapture { camera_id, width, height } => {
                            let _ = bridge_cmds.start_capture(camera_id, width, height).await;
                        }
                        WsMessage::StopCapture => {
                            let _ = bridge_cmds.stop_capture().await;
                        }
                        WsMessage::SetConfig { key, value } => {
                            let _ = bridge_cmds.set_config(&key, value).await;
                        }
                        WsMessage::ConnectHardware { port: _, baud_rate: _ } => {
                            // Find a window to pass to connect (any window will do for events)
                            // This is a bit tricky from here, maybe we can use app_handle
                            let _hw = hw_cmds.lock().unwrap();
                            // For now we don't pass the window easily, might need to refactor hardware manager
                            // but let's assume it works for now or skip window events.
                            // Actually, let's skip it for now as it's Phase 3.
                        }
                        WsMessage::SendHardwareCommand { cmd } => {
                            let hw = hw_cmds.lock().unwrap();
                            let _ = hw.send_command(&cmd);
                        }
                        _ => {}
                    }
                }
            });

            // Start the TCP server in background
            let bridge_for_tcp = Arc::clone(&python_bridge);
            tauri::async_runtime::spawn(async move {
                bridge_for_tcp.start();
            });

            // Start Python Sidecar with proper lifecycle management
            let python_child: Arc<Mutex<Option<CommandChild>>> = Arc::new(Mutex::new(None));
            let python_child_clone = Arc::clone(&python_child);

            let shell = app.shell();
            match shell.sidecar("python-worker") {
                Ok(sidecar) => {
                    tauri::async_runtime::spawn(async move {
                        println!("Starting Python sidecar...");
                        match sidecar.spawn() {
                            Ok((mut rx, child)) => {
                                println!("[Python] Sidecar spawned successfully (PID: {:?})", child.pid());
                                // Store child handle for cleanup
                                *python_child_clone.lock().unwrap() = Some(child);

                                while let Some(event) = rx.recv().await {
                                    match event {
                                        tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                                            println!("[Python] {}", String::from_utf8_lossy(&line).trim());
                                        }
                                        tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                                            eprintln!("[Python Error] {}", String::from_utf8_lossy(&line).trim());
                                        }
                                        tauri_plugin_shell::process::CommandEvent::Terminated(payload) => {
                                            println!("[Python] Process terminated with code {:?}", payload.code);
                                            *python_child_clone.lock().unwrap() = None;
                                        }
                                        _ => {}
                                    }
                                }
                            }
                            Err(e) => {
                                eprintln!("[Python] Failed to spawn sidecar: {:?}", e);
                            }
                        }
                    });
                }
                Err(e) => {
                    eprintln!("[Python] Failed to create sidecar command: {}", e);
                }
            }

            let ws_broadcast = Arc::clone(&ws_server);
            let mut bridge_events = python_bridge.subscribe();
            let eye_processor = Arc::new(Mutex::new(EyeProcessor::new()));
            let eye_processor_clone = Arc::clone(&eye_processor);

            let bridge_for_events = Arc::clone(&python_bridge);

            tauri::async_runtime::spawn(async move {
                while let Ok(event) = bridge_events.recv().await {
                    match event {
                        BridgeEvent::Connected => {
                            ws_broadcast.broadcast(&WsMessage::Status {
                                python_connected: true,
                                hardware_connected: false,
                            });
                            // Automatically request cameras on connection
                            let _ = bridge_for_events.list_cameras().await;
                        }
                        BridgeEvent::EyeData(payload) => {
                            let raw_data = RawEyeData {
                                left_eye: payload.left.map(|p| [p.x, p.y]),
                                right_eye: payload.right.map(|p| [p.x, p.y]),
                                processed: None,
                                timestamp: payload.timestamp as f64 / 1000.0,
                            };
                            
                            let processed = {
                                let mut processor = eye_processor_clone.lock().unwrap();
                                processor.process(raw_data)
                            };

                            ws_broadcast.broadcast(&WsMessage::EyeData(processed));
                        }
                        BridgeEvent::VideoFrame(jpeg) => {
                            let base64_data = general_purpose::STANDARD.encode(jpeg);
                            ws_broadcast.broadcast(&WsMessage::VideoFrame { data: base64_data });
                        }
                        BridgeEvent::Disconnected => {
                            ws_broadcast.broadcast(&WsMessage::Status {
                                python_connected: false,
                                hardware_connected: false,
                            });
                        }
                        BridgeEvent::Error(msg) => {
                            ws_broadcast.broadcast(&WsMessage::Error {
                                source: "python".to_string(),
                                message: msg,
                            });
                        }
                        BridgeEvent::CmdAck(ack) => {
                            if ack.success {
                                if let Some(cameras) = ack.data.get("cameras") {
                                    ws_broadcast.broadcast(&WsMessage::CamerasList { 
                                        cameras: cameras.clone() 
                                    });
                                }
                            }
                        }
                    }
                }
            });

            // Manage State
            app.manage(AppState {
                eye_processor,
                hardware_manager,
                db: Arc::new(db_service),
                python_bridge,
                ws_server,
                python_child,
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Kill Python process when window is destroyed
                if let Some(state) = window.try_state::<AppState>() {
                    if let Ok(mut child_guard) = state.python_child.lock() {
                        if let Some(child) = child_guard.take() {
                            let pid = child.pid();
                            println!("[Python] Killing sidecar on window close (PID: {:?})", pid);
                            // Kill the child process
                            let _ = child.kill();
                            // Also kill the entire process group to catch Python subprocess
                            #[cfg(unix)]
                            {
                                use std::process::Command;
                                // Kill all processes in the process group
                                let _ = Command::new("pkill")
                                    .args(["-TERM", "-P", &pid.to_string()])
                                    .output();
                            }
                        }
                    }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_version,
            get_websocket_port,
            process_eye_data_batch,
            reset_calibration,
            list_serial_ports,
            is_hardware_connected,
            connect_hardware,
            disconnect_hardware,
            send_hardware_command,
            // Python Bridge Commands
            is_python_connected,
            python_start_capture,
            python_stop_capture,
            python_list_cameras,
            python_set_pupil_config,
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
