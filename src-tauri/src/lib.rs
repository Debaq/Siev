use std::sync::{Mutex, Arc};
use tauri::{State, Window, Manager};
use tauri_plugin_shell::process::CommandChild;

pub mod bridge;
pub mod database;
pub mod hardware;
pub mod math;
pub mod vng;
pub mod websocket;
pub mod storage;

use bridge::PythonBridge;
use database::models::{CreatePatientDto, Patient, Session, Specialist, UpdatePatientDto};
use database::service::DatabaseService;
use hardware::manager::HardwareManager;
use math::processor::{EyeProcessor, ProcessedEyeData, RawEyeData};
use websocket::{WebSocketServer, WsMessage};
use bridge::python_bridge::BridgeEvent;
use tauri_plugin_shell::ShellExt;
use crate::storage::bundle::{SievBundle, SessionManifest};
use crate::storage::recorder::SessionRecorder;
use crate::vng::report::{VNGReportData, PatientReportData, SessionReportData};
use std::path::PathBuf;

// Application State
pub struct AppState {
    pub eye_processor: Arc<Mutex<EyeProcessor>>,
    pub hardware_manager: Arc<Mutex<HardwareManager>>,
    pub db: Arc<DatabaseService>,
    pub python_bridge: Arc<PythonBridge>,
    pub ws_server: Arc<WebSocketServer>,
    pub python_child: Arc<Mutex<Option<CommandChild>>>,
    pub active_recorder: Arc<Mutex<Option<SessionRecorder>>>,
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

async fn get_effective_storage_path(app: &tauri::AppHandle, db: &DatabaseService) -> PathBuf {
    // 1. Try to get from app_config JSON
    if let Ok(Some(config_json)) = db.get_setting("app_config").await {
        if let Ok(config) = serde_json::from_str::<serde_json::Value>(&config_json) {
            if let Some(path_str) = config["general"]["storage"]["data_path"].as_str() {
                if !path_str.is_empty() {
                    return PathBuf::from(path_str);
                }
            }
        }
    }

    // 2. Try legacy storage_path key
    if let Ok(Some(path_str)) = db.get_setting("storage_path").await {
        if !path_str.is_empty() {
            return PathBuf::from(path_str);
        }
    }

    // 3. Fallback to default
    app.path().document_dir()
       .map(|p| p.join("SIEV_Media"))
       .unwrap_or_else(|_| PathBuf::from("siev_data"))
}

#[tauri::command]
async fn create_session(
    patient_id: i64,
    specialist_id: Option<i64>,
    description: Option<String>,
    app: tauri::AppHandle,
    state: State<'_, AppState>
) -> Result<Session, String> {
    // 1. Get patient data
    let patient = state.db.get_patient_by_id(patient_id).await?;

    // 2. Create session record in DB
    let mut session = state.db.create_session(patient_id, specialist_id, description.clone()).await?;

    // 3. Determine storage path
    let root_path = get_effective_storage_path(&app, &state.db).await;

    // 4. Initialize SievBundle
    let test_type = "VNG"; // Default for now
    let bundle = SievBundle::new(&root_path, &patient, test_type, session.id);
    
    let manifest = SessionManifest {
        version: "1.0".to_string(),
        created_at: chrono::Local::now().to_rfc3339(),
        patient: (&patient).into(),
        test_type: test_type.to_string(),
        description: description,
        specialist_id,
    };

    bundle.init(&manifest).map_err(|e| format!("Failed to initialize storage: {}", e))?;

    // 5. Update session with paths
    let video_path = bundle.get_video_path().to_string_lossy().to_string();
    let data_path = bundle.get_data_path().to_string_lossy().to_string();
    
    state.db.update_session_paths(session.id, Some(video_path.clone()), Some(data_path.clone())).await?;
    
    // Update local session object to return
    session.video_path = Some(video_path);
    session.data_path = Some(data_path);

    Ok(session)
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

#[tauri::command]
async fn sync_storage(app: tauri::AppHandle, state: State<'_, AppState>) -> Result<(), String> {
    let root_path = get_effective_storage_path(&app, &state.db).await;
    state.db.sync_storage(&root_path).await
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
    fps: Option<u32>,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state
        .python_bridge
        .start_capture(camera_id, width, height, fps.unwrap_or(120))
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
async fn reset_application(state: State<'_, AppState>) -> Result<(), String> {
    state.db.reset_database().await
}

#[tauri::command]
fn get_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[tauri::command]
fn set_filtering_enabled(enabled: bool, state: State<AppState>) {
    let mut processor = state.eye_processor.lock().unwrap();
    processor.filtering_enabled = enabled;
}

// --- VNG Report Commands ---

#[tauri::command]
async fn get_vng_report_data(
    session_id: i64,
    include_historical: bool,
    state: State<'_, AppState>
) -> Result<VNGReportData, String> {
    // Get session
    let session = state.db.get_session_by_id(session_id).await?
        .ok_or("Session not found")?;

    // Get patient
    let patient = state.db.get_patient_by_id(session.patient_id).await?;

    // Calculate age if birth_date exists
    let age = patient.birth_date.map(|bd| {
        let now = chrono::Local::now().naive_local();
        let years = now.signed_duration_since(bd).num_days() / 365;
        years as i32
    });

    let patient_data = PatientReportData {
        id: patient.id,
        full_name: format!("{} {}", patient.first_name, patient.last_name),
        dni: patient.dni,
        birth_date: patient.birth_date.map(|d| d.format("%Y-%m-%d").to_string()),
        age,
        gender: patient.gender,
    };

    // Get specialist name if exists
    let specialist_name = if let Some(spec_id) = session.specialist_id {
        let specialists = state.db.get_specialists().await?;
        specialists.iter().find(|s| s.id == spec_id).map(|s| s.name.clone())
    } else {
        None
    };

    let session_data = SessionReportData {
        id: session.id,
        date: session.date.format("%Y-%m-%d %H:%M").to_string(),
        specialist_name,
        description: session.description,
    };

    let mut report_data = VNGReportData::new(patient_data, session_data);

    // Load test results from database
    let test_results = state.db.get_vng_test_results(session_id, None).await?;

    for (_, test_type, results_json, _) in test_results {
        match test_type.as_str() {
            "saccade" => {
                if let Ok(result) = serde_json::from_str(&results_json) {
                    report_data.saccades = Some(result);
                }
            }
            "pursuit" => {
                if let Ok(result) = serde_json::from_str(&results_json) {
                    report_data.pursuit = Some(result);
                }
            }
            "okn" => {
                if let Ok(result) = serde_json::from_str(&results_json) {
                    report_data.okn = Some(result);
                }
            }
            "positional" => {
                if let Ok(result) = serde_json::from_str(&results_json) {
                    report_data.positional = Some(result);
                }
            }
            "caloric" => {
                if let Ok(result) = serde_json::from_str(&results_json) {
                    report_data.caloric = Some(result);
                }
            }
            _ => {}
        }
    }

    // Load historical data if requested
    if include_historical {
        if let Ok(Some(prev_session)) = state.db.get_previous_session(patient.id, session_id).await {
            let prev_results = state.db.get_vng_test_results(prev_session.id, Some("caloric")).await?;

            if let Some((_, _, results_json, _)) = prev_results.first() {
                if let Ok(caloric) = serde_json::from_str(results_json) {
                    let prev_specialist = if let Some(spec_id) = prev_session.specialist_id {
                        let specialists = state.db.get_specialists().await?;
                        specialists.iter().find(|s| s.id == spec_id).map(|s| s.name.clone())
                    } else {
                        None
                    };

                    report_data.previous_session = Some(vng::report::PreviousSessionData {
                        session: SessionReportData {
                            id: prev_session.id,
                            date: prev_session.date.format("%Y-%m-%d %H:%M").to_string(),
                            specialist_name: prev_specialist,
                            description: prev_session.description,
                        },
                        caloric: Some(caloric),
                    });
                }
            }
        }
    }

    Ok(report_data)
}

#[tauri::command]
async fn save_vng_test_result(
    session_id: i64,
    test_type: String,
    results_json: String,
    clinical_notes: Option<String>,
    state: State<'_, AppState>
) -> Result<i64, String> {
    state.db.save_vng_test_result(
        session_id,
        &test_type,
        &results_json,
        clinical_notes.as_deref()
    ).await
}

#[tauri::command]
async fn get_vng_test_results(
    session_id: i64,
    test_type: Option<String>,
    state: State<'_, AppState>
) -> Result<Vec<serde_json::Value>, String> {
    let results = state.db.get_vng_test_results(session_id, test_type.as_deref()).await?;

    let parsed: Vec<serde_json::Value> = results
        .into_iter()
        .filter_map(|(id, tt, json, notes)| {
            serde_json::from_str::<serde_json::Value>(&json).ok().map(|mut v| {
                if let Some(obj) = v.as_object_mut() {
                    obj.insert("id".into(), serde_json::json!(id));
                    obj.insert("test_type".into(), serde_json::json!(tt));
                    obj.insert("clinical_notes".into(), serde_json::json!(notes));
                }
                v
            })
        })
        .collect();

    Ok(parsed)
}

#[tauri::command]
async fn get_reference_values(
    test_type: Option<String>,
    age_group: Option<String>,
    state: State<'_, AppState>
) -> Result<Vec<serde_json::Value>, String> {
    let results = state.db.get_vng_reference_values(
        test_type.as_deref(),
        age_group.as_deref()
    ).await?;

    let values: Vec<serde_json::Value> = results
        .into_iter()
        .map(|(tt, metric, min, max, unit)| {
            serde_json::json!({
                "test_type": tt,
                "metric_name": metric,
                "min_normal": min,
                "max_normal": max,
                "unit": unit
            })
        })
        .collect();

    // If empty, return defaults
    if values.is_empty() {
        let defaults = vng::metrics::get_default_reference_values();
        return Ok(defaults
            .into_iter()
            .filter(|r| test_type.as_ref().map_or(true, |t| &r.test_type == t))
            .map(|r| {
                serde_json::json!({
                    "test_type": r.test_type,
                    "metric_name": r.metric_name,
                    "min_normal": r.min_normal,
                    "max_normal": r.max_normal,
                    "unit": r.unit
                })
            })
            .collect());
    }

    Ok(values)
}

#[tauri::command]
async fn calculate_vng_metrics(
    _data_path: String,
    test_type: String,
    params: serde_json::Value,
) -> Result<serde_json::Value, String> {
    // This is a placeholder for actual metric calculation
    // In a real implementation, this would:
    // 1. Load eye tracking data from data_path
    // 2. Apply the appropriate analysis algorithm based on test_type
    // 3. Return calculated metrics

    match test_type.as_str() {
        "jongkees" => {
            let rw = params["rw"].as_f64().unwrap_or(0.0);
            let rc = params["rc"].as_f64().unwrap_or(0.0);
            let lw = params["lw"].as_f64().unwrap_or(0.0);
            let lc = params["lc"].as_f64().unwrap_or(0.0);

            let (uw, dp) = vng::metrics::calculate_jongkees(rw, rc, lw, lc);

            Ok(serde_json::json!({
                "unilateral_weakness_percent": uw,
                "directional_preponderance_percent": dp,
                "uw_significant": uw.abs() > 22.0,
                "dp_significant": dp.abs() > 28.0
            }))
        }
        "fixation_index" => {
            let spv_dark = params["spv_dark"].as_f64().unwrap_or(0.0);
            let spv_fixation = params["spv_fixation"].as_f64().unwrap_or(0.0);

            let fi = vng::metrics::calculate_fixation_index(spv_dark, spv_fixation);

            Ok(serde_json::json!({
                "fixation_index": fi,
                "is_normal": fi > 60.0
            }))
        }
        "pursuit_gain" => {
            let eye_vel = params["eye_velocity"].as_f64().unwrap_or(0.0);
            let target_vel = params["target_velocity"].as_f64().unwrap_or(0.0);

            let gain = vng::metrics::calculate_pursuit_gain(eye_vel, target_vel);

            Ok(serde_json::json!({
                "gain": gain,
                "is_normal": gain >= 0.8 && gain <= 1.0
            }))
        }
        _ => Err(format!("Unknown test type: {}", test_type))
    }
}

#[tauri::command]
async fn open_external_display(
    app: tauri::AppHandle
) -> Result<bool, String> {
    let label = "external-display";
    
    // Focus existing if open
    if let Some(window) = app.get_webview_window(label) {
        let _ = window.set_focus();
        let _ = window.unminimize();
        return Ok(false);
    }

    println!("Creating external display window");

    let win_builder = tauri::WebviewWindowBuilder::new(
        &app,
        label,
        tauri::WebviewUrl::App("/#/external-display".into())
    )
    .title("SIEV Pantalla Externa")
    .inner_size(600.0, 450.0) // Restaurar tamaño original más compacto
    .fullscreen(false)
    .resizable(true)
    .focused(true)
    .decorations(false) // SIN bordes del sistema (User request)
    .always_on_top(false);

    let window = win_builder.build().map_err(|e| e.to_string())?;
    
    let _ = window.set_focus();

    Ok(true)
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

            let db_for_ws = Arc::new(db_service);
            let db_for_state = Arc::clone(&db_for_ws);
            let active_recorder: Arc<Mutex<Option<SessionRecorder>>> = Arc::new(Mutex::new(None));
            let recorder_for_ws = Arc::clone(&active_recorder);

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
            let db_for_ws_loop = Arc::clone(&db_for_ws);
            let recorder_for_ws_loop = Arc::clone(&recorder_for_ws);

            tauri::async_runtime::spawn(async move {
                while let Some(msg) = ws_commands.recv().await {
                    match msg {
                        WsMessage::ListCameras => {
                            let _ = bridge_cmds.list_cameras().await;
                        }
                        WsMessage::ListResolutions { camera_id } => {
                            let _ = bridge_cmds.list_resolutions(camera_id).await;
                        }
                        WsMessage::StartCapture { camera_id, width, height, fps } => {
                            let _ = bridge_cmds.start_capture(camera_id, width, height, fps).await;
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
                        WsMessage::StartRecording { session_id } => {
                            if let Ok(Some(session)) = db_for_ws_loop.get_session_by_id(session_id).await {
                                if let Some(path) = session.data_path {
                                    let recorder = SessionRecorder::start(PathBuf::from(path));
                                    *recorder_for_ws_loop.lock().unwrap() = Some(recorder);
                                    println!("Started recording for session {}", session_id);
                                }
                            }
                        }
                        WsMessage::StopRecording => {
                            let recorder = recorder_for_ws_loop.lock().unwrap().take();
                            if let Some(r) = recorder {
                                r.stop().await;
                                println!("Stopped recording");
                            }
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
            let recorder_for_events = Arc::clone(&active_recorder);

            let bridge_for_events = Arc::clone(&python_bridge);

            tauri::async_runtime::spawn(async move {
                // Fase 3.1: Frame skipping - máximo 60fps al frontend
                let mut last_frame_time = std::time::Instant::now();
                let min_frame_interval = std::time::Duration::from_millis(16); // ~60fps

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

                            // Persistence: Record data if active
                            if let Ok(recorder_guard) = recorder_for_events.lock() {
                                if let Some(recorder) = recorder_guard.as_ref() {
                                    recorder.record(processed.clone());
                                }
                            }

                            ws_broadcast.broadcast(&WsMessage::EyeData(processed));
                        }
                        BridgeEvent::VideoFrame(jpeg) => {
                            // Fase 3.1: Frame skipping - solo enviar si pasó suficiente tiempo
                            let now = std::time::Instant::now();
                            if now.duration_since(last_frame_time) >= min_frame_interval {
                                ws_broadcast.broadcast_binary(jpeg);
                                last_frame_time = now;
                            }
                            // Si llegan frames muy rápido, se dropean silenciosamente
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
                                if let Some(resolutions) = ack.data.get("resolutions") {
                                    let camera_id = ack.data.get("camera_id")
                                        .and_then(|v| v.as_i64())
                                        .unwrap_or(0) as i32;
                                    let res_list: Vec<String> = resolutions.as_array()
                                        .map(|arr| arr.iter()
                                            .filter_map(|v| v.as_str().map(String::from))
                                            .collect())
                                        .unwrap_or_default();
                                    ws_broadcast.broadcast(&WsMessage::ResolutionsList {
                                        resolutions: res_list,
                                        camera_id,
                                    });
                                }
                            }
                        }
                    }
                }
            });

            // Manage State
            let db_for_setup = Arc::clone(&db_for_state);
            let app_handle_for_setup = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let root_path = get_effective_storage_path(&app_handle_for_setup, &db_for_setup).await;
                
                println!("Syncing storage from {:?}", root_path);
                if let Err(e) = db_for_setup.sync_storage(&root_path).await {
                    eprintln!("Failed to sync storage: {}", e);
                }
            });

            app.manage(AppState {
                eye_processor,
                hardware_manager,
                db: db_for_state,
                python_bridge,
                ws_server,
                python_child,
                active_recorder,
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Only act if the main window is closed to prevent killing python on side-window close
                if window.label() == "main" {
                    println!("Main window destroyed, cleaning up...");
                    
                    // Close ALL other windows
                    for (label, win) in window.app_handle().webview_windows() {
                        if label != "main" {
                            println!("Closing window: {}", label);
                            let _ = win.close();
                        }
                    }

                    // Kill Python process
                    if let Some(state) = window.try_state::<AppState>() {
                        if let Ok(mut child_guard) = state.python_child.lock() {
                            if let Some(child) = child_guard.take() {
                                let pid = child.pid();
                                println!("[Python] Killing sidecar on main window close (PID: {:?})", pid);
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
            set_filtering_enabled,
            sync_storage,
            reset_application,
            // VNG Report Commands
            get_vng_report_data,
            save_vng_test_result,
            get_vng_test_results,
            get_reference_values,
            calculate_vng_metrics,
            open_external_display
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
