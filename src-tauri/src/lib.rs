use std::sync::{Mutex, Arc};
use tauri::{State, Window, Manager};

pub mod database;
pub mod hardware;
pub mod math;
pub mod vng;
pub mod websocket;
pub mod storage;

use database::models::{CreatePatientDto, Patient, Session, Specialist, UpdatePatientDto};
use database::service::DatabaseService;
use hardware::manager::HardwareManager;
use math::processor::{EyeProcessor, ProcessedEyeData, RawEyeData};
use websocket::{WebSocketServer, WsMessage};
use crate::storage::bundle::{SievBundle, SessionManifest};
use crate::storage::recorder::SessionRecorder;
use crate::storage::review::{SessionReviewPayload, ChartEyeDataPoint};
use crate::vng::report::{VNGReportData, PatientReportData, SessionReportData};
use std::path::PathBuf;

// Application State
pub struct AppState {
    pub eye_processor: Arc<Mutex<EyeProcessor>>,
    pub hardware_manager: Arc<Mutex<HardwareManager>>,
    pub db: Arc<DatabaseService>,
    pub ws_server: Arc<WebSocketServer>,
    pub active_recorder: Arc<Mutex<Option<SessionRecorder>>>,
    pub native_video: Arc<vng::NativeVideoManager>,
    pub active_bundle_path: Arc<Mutex<Option<PathBuf>>>,
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
    if let Ok(Some(config_json)) = db.get_setting("app_config").await {
        if let Ok(config) = serde_json::from_str::<serde_json::Value>(&config_json) {
            if let Some(path_str) = config["general"]["storage"]["data_path"].as_str() {
                if !path_str.is_empty() {
                    return PathBuf::from(path_str);
                }
            }
        }
    }
    if let Ok(Some(path_str)) = db.get_setting("storage_path").await {
        if !path_str.is_empty() {
            return PathBuf::from(path_str);
        }
    }
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
    let patient = state.db.get_patient_by_id(patient_id).await?;
    let mut session = state.db.create_session(patient_id, specialist_id, description.clone()).await?;
    let root_path = get_effective_storage_path(&app, &state.db).await;
    let test_type = "VNG"; 
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
    // Store bundle path for calibration saving
    {
        let mut bp = state.active_bundle_path.lock().unwrap();
        *bp = Some(bundle.bundle_path.clone());
    }
    let video_path = bundle.get_video_path().to_string_lossy().to_string();
    let data_path = bundle.get_data_path().to_string_lossy().to_string();
    state.db.update_session_paths(session.id, Some(video_path.clone()), Some(data_path.clone())).await?;
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

// --- NATIVE VIDEO COMMANDS ---

#[tauri::command]
async fn is_python_connected(_state: State<'_, AppState>) -> Result<bool, String> {
    Ok(true) 
}

#[tauri::command]
async fn python_start_capture(
    camera_id: i32,
    width: u32,
    height: u32,
    fps: Option<u32>,
    app: tauri::AppHandle,
    state: State<'_, AppState>,
) -> Result<(), String> {
    // Intentar varias rutas para el modelo
    let model_path = app.path().resource_dir()
        .map(|p| p.join("backend/models/siev_vng_r01.onnx"))
        .ok()
        .filter(|p| p.exists())
        .or_else(|| {
            // Ruta relativa desde el proyecto (desarrollo)
            let dev_path = std::path::PathBuf::from("../backend/models/siev_vng_r01.onnx");
            if dev_path.exists() { Some(dev_path) } else { None }
        })
        .or_else(|| {
            // Ruta absoluta como fallback
            let abs_path = std::path::PathBuf::from("/home/nick/Escritorio/Proyectos/Siev/backend/models/siev_vng_r01.onnx");
            if abs_path.exists() { Some(abs_path) } else { None }
        })
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|| "backend/models/siev_vng_r01.onnx".to_string());

    println!("[SIEV] Usando modelo en: {}", model_path);
    state.native_video.start_capture(camera_id as u32, width, height, fps.unwrap_or(120), model_path)
}

#[tauri::command]
async fn python_stop_capture(state: State<'_, AppState>) -> Result<(), String> {
    state.native_video.stop_capture();
    Ok(())
}

#[tauri::command]
async fn python_list_cameras(_state: State<'_, AppState>) -> Result<Vec<vng::native_video::CameraInfo>, String> {
    vng::native_video::list_cameras()
}

#[tauri::command]
async fn list_camera_formats(camera_id: u32, _state: State<'_, AppState>) -> Result<Vec<vng::native_video::CameraFormatInfo>, String> {
    vng::native_video::list_camera_formats(camera_id)
}

#[tauri::command]
async fn python_set_pupil_config(
    threshold: i32,
    _mode: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.native_video.set_threshold(threshold as u8);
    Ok(())
}

#[tauri::command]
fn get_websocket_port(state: State<AppState>) -> u16 {
    state.ws_server.get_port()
}

// --- ROI Manual Commands ---

#[tauri::command]
fn set_manual_roi_right(
    top: f32,
    bottom: f32,
    nasal: f32,
    temporal: f32,
    state: State<AppState>,
) {
    state.native_video.set_manual_roi_right(top, bottom, nasal, temporal);
}

#[tauri::command]
fn set_manual_roi_left(
    top: f32,
    bottom: f32,
    nasal: f32,
    temporal: f32,
    state: State<AppState>,
) {
    state.native_video.set_manual_roi_left(top, bottom, nasal, temporal);
}

#[tauri::command]
fn get_manual_rois(state: State<AppState>) -> serde_json::Value {
    let (right, left) = state.native_video.get_manual_rois();
    serde_json::json!({
        "right": {
            "top": right.top,
            "bottom": right.bottom,
            "nasal": right.nasal,
            "temporal": right.temporal
        },
        "left": {
            "top": left.top,
            "bottom": left.bottom,
            "nasal": left.nasal,
            "temporal": left.temporal
        }
    })
}

#[tauri::command]
fn set_use_yolo(enabled: bool, state: State<AppState>) {
    state.native_video.set_use_yolo(enabled);
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
    _include_historical: bool,
    state: State<'_, AppState>
) -> Result<VNGReportData, String> {
    let session = state.db.get_session_by_id(session_id).await?.ok_or("Session not found")?;
    let patient = state.db.get_patient_by_id(session.patient_id).await?;
    let age = patient.birth_date.map(|bd| {
        let now = chrono::Local::now().naive_local();
        (now.signed_duration_since(bd).num_days() / 365) as i32
    });
    let patient_data = PatientReportData {
        id: patient.id,
        full_name: format!("{} {}", patient.first_name, patient.last_name),
        dni: patient.dni,
        birth_date: patient.birth_date.map(|d| d.format("%Y-%m-%d").to_string()),
        age,
        gender: patient.gender,
    };
    let specialist_name = if let Some(spec_id) = session.specialist_id {
        let specialists = state.db.get_specialists().await?;
        specialists.iter().find(|s| s.id == spec_id).map(|s| s.name.clone())
    } else { None };
    let session_data = SessionReportData {
        id: session.id, date: session.date.format("%Y-%m-%d %H:%M").to_string(),
        specialist_name, description: session.description,
    };
    let mut report_data = VNGReportData::new(patient_data, session_data);
    let test_results = state.db.get_vng_test_results(session_id, None).await?;
    for (_, test_type, results_json, _) in test_results {
        match test_type.as_str() {
            "saccade" => { if let Ok(result) = serde_json::from_str(&results_json) { report_data.saccades = Some(result); } }
            "pursuit" => { if let Ok(result) = serde_json::from_str(&results_json) { report_data.pursuit = Some(result); } }
            "okn" => { if let Ok(result) = serde_json::from_str(&results_json) { report_data.okn = Some(result); } }
            "positional" => { if let Ok(result) = serde_json::from_str(&results_json) { report_data.positional = Some(result); } }
            "caloric" => { if let Ok(result) = serde_json::from_str(&results_json) { report_data.caloric = Some(result); } }
            _ => {}
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
    state.db.save_vng_test_result(session_id, &test_type, &results_json, clinical_notes.as_deref()).await
}

#[tauri::command]
async fn get_vng_test_results(
    session_id: i64,
    test_type: Option<String>,
    state: State<'_, AppState>
) -> Result<Vec<serde_json::Value>, String> {
    let results = state.db.get_vng_test_results(session_id, test_type.as_deref()).await?;
    let parsed: Vec<serde_json::Value> = results.into_iter().filter_map(|(id, tt, json, notes)| {
            serde_json::from_str::<serde_json::Value>(&json).ok().map(|mut v| {
                if let Some(obj) = v.as_object_mut() {
                    obj.insert("id".into(), serde_json::json!(id));
                    obj.insert("test_type".into(), serde_json::json!(tt));
                    obj.insert("clinical_notes".into(), serde_json::json!(notes));
                }
                v
            })
        }).collect();
    Ok(parsed)
}

#[tauri::command]
async fn get_reference_values(
    test_type: Option<String>,
    age_group: Option<String>,
    state: State<'_, AppState>
) -> Result<Vec<serde_json::Value>, String> {
    let results = state.db.get_vng_reference_values(test_type.as_deref(), age_group.as_deref()).await?;
    let values: Vec<serde_json::Value> = results.into_iter().map(|(tt, metric, min, max, unit)| {
            serde_json::json!({"test_type": tt, "metric_name": metric, "min_normal": min, "max_normal": max, "unit": unit})
        }).collect();
    if values.is_empty() {
        let defaults = vng::metrics::get_default_reference_values();
        return Ok(defaults.into_iter().filter(|r| test_type.as_ref().map_or(true, |t| &r.test_type == t))
            .map(|r| { serde_json::json!({"test_type": r.test_type, "metric_name": r.metric_name, "min_normal": r.min_normal, "max_normal": r.max_normal, "unit": r.unit})})
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
    match test_type.as_str() {
        "jongkees" => {
            let (uw, dp) = vng::metrics::calculate_jongkees(params["rw"].as_f64().unwrap_or(0.0), params["rc"].as_f64().unwrap_or(0.0), params["lw"].as_f64().unwrap_or(0.0), params["lc"].as_f64().unwrap_or(0.0));
            Ok(serde_json::json!({"unilateral_weakness_percent": uw, "directional_preponderance_percent": dp, "uw_significant": uw.abs() > 22.0, "dp_significant": dp.abs() > 28.0}))
        }
        "fixation_index" => {
            let fi = vng::metrics::calculate_fixation_index(params["spv_dark"].as_f64().unwrap_or(0.0), params["spv_fixation"].as_f64().unwrap_or(0.0));
            Ok(serde_json::json!({"fixation_index": fi, "is_normal": fi > 60.0}))
        }
        "pursuit_gain" => {
            let gain = vng::metrics::calculate_pursuit_gain(params["eye_velocity"].as_f64().unwrap_or(0.0), params["target_velocity"].as_f64().unwrap_or(0.0));
            Ok(serde_json::json!({"gain": gain, "is_normal": gain >= 0.8 && gain <= 1.0}))
        }
        _ => Err(format!("Unknown test type: {}", test_type))
    }
}

#[tauri::command]
async fn open_external_display(app: tauri::AppHandle) -> Result<bool, String> {
    let label = "external-display";
    if let Some(window) = app.get_webview_window(label) {
        let _ = window.set_focus();
        let _ = window.unminimize();
        return Ok(false);
    }
    let window = tauri::WebviewWindowBuilder::new(&app, label, tauri::WebviewUrl::App("/#/external-display".into()))
        .title("SIEV Pantalla Externa").inner_size(600.0, 450.0).resizable(true).focused(true).decorations(false).build().map_err(|e| e.to_string())?;
    let _ = window.set_focus();
    Ok(true)
}

// --- Session Review Commands ---

#[tauri::command]
async fn load_session_review(
    session_id: i64,
    _app: tauri::AppHandle,
    state: State<'_, AppState>,
) -> Result<SessionReviewPayload, String> {
    // 1. Look up session in DB
    let session = state.db.get_session_by_id(session_id).await?
        .ok_or_else(|| format!("Session {} not found", session_id))?;

    // 2. Deduce bundle path from data_path
    let data_path = session.data_path
        .ok_or_else(|| "Session has no data path".to_string())?;
    let bundle_path = PathBuf::from(&data_path)
        .parent()
        .map(|p| p.to_path_buf())
        .ok_or_else(|| "Cannot deduce bundle path".to_string())?;

    // 3. Build review payload (data + metrics)
    let max_points = 2000;
    let mut payload = storage::review::build_session_review(&bundle_path, session_id, max_points)?;

    // 4. Convert H.264 -> MP4 if needed
    let raw_video = bundle_path.join("video").join("raw_capture.mp4");
    let playback = bundle_path.join("video").join("playback.mp4");

    if raw_video.exists() && !playback.exists() {
        let (width, height) = storage::video_convert::detect_video_dimensions(&raw_video, 640, 480);
        storage::video_convert::convert_h264_to_mp4(&raw_video, &playback, width, height, 30)?;
    }

    // 5. Return the file path - frontend converts it with convertFileSrc()
    if playback.exists() {
        payload.video_url = Some(playback.to_string_lossy().to_string());
        payload.video_available = true;
    }

    Ok(payload)
}

#[tauri::command]
async fn get_eye_data_window(
    session_id: i64,
    start_time: f64,
    end_time: f64,
    max_points: Option<usize>,
    state: State<'_, AppState>,
) -> Result<Vec<ChartEyeDataPoint>, String> {
    let session = state.db.get_session_by_id(session_id).await?
        .ok_or_else(|| format!("Session {} not found", session_id))?;

    let data_path = session.data_path
        .ok_or_else(|| "Session has no data path".to_string())?;

    let window_data = storage::review::load_eye_data_window(
        &PathBuf::from(&data_path),
        start_time,
        end_time,
    )?;

    let target = max_points.unwrap_or(2000);
    let base_ts = window_data.first().map(|d| d.timestamp).unwrap_or(0.0);

    // Convert to chart data points with LTTB
    if window_data.len() <= target {
        return Ok(window_data.iter().map(|d| ChartEyeDataPoint {
            t: d.timestamp - base_ts + start_time,
            lx: d.left.map(|l| l[0]),
            ly: d.left.map(|l| l[1]),
            rx: d.right.map(|r| r[0]),
            ry: d.right.map(|r| r[1]),
        }).collect());
    }

    // Downsample using LTTB on right eye horizontal
    let time_vals: Vec<(f64, f64)> = window_data.iter().map(|d| {
        let t = d.timestamp - base_ts + start_time;
        let v = d.right.map(|r| r[0]).or(d.left.map(|l| l[0])).unwrap_or(0.0);
        (t, v)
    }).collect();

    let downsampled = storage::review::downsample_lttb(&time_vals, target);
    let target_times: Vec<f64> = downsampled.iter().map(|(t, _)| *t).collect();

    let mut result = Vec::with_capacity(target_times.len());
    let mut search_start = 0;

    for target_t in &target_times {
        let mut best_idx = search_start;
        let mut best_diff = ((window_data[search_start].timestamp - base_ts + start_time) - target_t).abs();

        for i in (search_start + 1)..window_data.len() {
            let diff = ((window_data[i].timestamp - base_ts + start_time) - target_t).abs();
            if diff < best_diff {
                best_diff = diff;
                best_idx = i;
            } else if diff > best_diff {
                break;
            }
        }

        search_start = best_idx;
        let d = &window_data[best_idx];
        result.push(ChartEyeDataPoint {
            t: d.timestamp - base_ts + start_time,
            lx: d.left.map(|l| l[0]),
            ly: d.left.map(|l| l[1]),
            rx: d.right.map(|r| r[0]),
            ry: d.right.map(|r| r[1]),
        });
    }

    Ok(result)
}

#[tauri::command]
async fn recalibrate_session(
    session_id: i64,
    calibration: math::processor::CalibrationSnapshot,
    _app: tauri::AppHandle,
    state: State<'_, AppState>,
) -> Result<SessionReviewPayload, String> {
    let session = state.db.get_session_by_id(session_id).await?
        .ok_or_else(|| format!("Session {} not found", session_id))?;

    let data_path = session.data_path
        .ok_or_else(|| "Session has no data path".to_string())?;
    let bundle_path = PathBuf::from(&data_path)
        .parent()
        .map(|p| p.to_path_buf())
        .ok_or_else(|| "Cannot deduce bundle path".to_string())?;

    // Load old calibration for relative correction
    let old_calibration = SievBundle::load_calibration(&bundle_path)
        .map_err(|e| format!("No previous calibration found: {}", e))?;

    // Save new calibration
    SievBundle::save_calibration(&bundle_path, &calibration)
        .map_err(|e| format!("Failed to save calibration: {}", e))?;

    // Rebuild with recalibrated data
    let mut payload = storage::review::build_recalibrated_review(
        &bundle_path, session_id, 2000, &calibration, &old_calibration,
    )?;

    // Set video path if available - frontend converts with convertFileSrc()
    let playback = bundle_path.join("video").join("playback.mp4");
    if playback.exists() {
        payload.video_url = Some(playback.to_string_lossy().to_string());
    }

    Ok(payload)
}

#[tauri::command]
async fn get_video_conversion_status(
    session_id: i64,
    state: State<'_, AppState>,
) -> Result<serde_json::Value, String> {
    let session = state.db.get_session_by_id(session_id).await?
        .ok_or_else(|| format!("Session {} not found", session_id))?;

    let data_path = session.data_path
        .ok_or_else(|| "Session has no data path".to_string())?;
    let bundle_path = PathBuf::from(&data_path)
        .parent()
        .map(|p| p.to_path_buf())
        .ok_or_else(|| "Cannot deduce bundle path".to_string())?;

    let raw_exists = bundle_path.join("video").join("raw_capture.mp4").exists();
    let mp4_exists = storage::video_convert::playback_mp4_exists(&bundle_path);

    Ok(serde_json::json!({
        "raw_exists": raw_exists,
        "mp4_exists": mp4_exists,
        "status": if mp4_exists { "ready" } else if raw_exists { "needs_conversion" } else { "no_video" }
    }))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            println!("SIEV Application started (Native Video Mode)");

            // Intentar cargar el icono de la ventana explícitamente (Crítico para Linux)
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_title("SIEV - Video-Oculografía");
                
                // Cargar y decodificar el icono desde los recursos
                let icon_path = app.path().resource_dir().unwrap().join("icons/32x32.png");
                if let Ok(icon_bytes) = std::fs::read(icon_path) {
                    if let Ok(img) = image::load_from_memory(&icon_bytes) {
                        let rgba = img.to_rgba8();
                        let (width, height) = rgba.dimensions();
                        let tauri_image = tauri::image::Image::new(rgba.as_raw(), width, height);
                        let _ = window.set_icon(tauri_image);
                    }
                }
            }

            let app_handle = app.handle();
            let db_service = tauri::async_runtime::block_on(async { DatabaseService::new(app_handle).await }).expect("Failed to initialize database");
            let db_for_state = Arc::new(db_service);
            let active_recorder: Arc<Mutex<Option<SessionRecorder>>> = Arc::new(Mutex::new(None));
            let active_bundle_path: Arc<Mutex<Option<PathBuf>>> = Arc::new(Mutex::new(None));
            let hardware_manager = Arc::new(Mutex::new(HardwareManager::new()));
            let (ws_server, mut ws_commands) = WebSocketServer::new();
            let ws_server = Arc::new(ws_server);
            let ws_clone = Arc::clone(&ws_server);
            tauri::async_runtime::spawn(async move { if let Err(e) = ws_clone.start("127.0.0.1:0").await { eprintln!("WebSocket server error: {}", e); } });

            let eye_processor = Arc::new(Mutex::new(EyeProcessor::new()));
            let native_video = Arc::new(vng::NativeVideoManager::new(Arc::clone(&ws_server), Arc::clone(&eye_processor), Arc::clone(&active_recorder)));

            let native_cmds = Arc::clone(&native_video);
            let ws_for_handler = Arc::clone(&ws_server);
            let eye_proc_for_ws = Arc::clone(&eye_processor);
            let bundle_path_for_ws = Arc::clone(&active_bundle_path);
            let recorder_for_ws = Arc::clone(&active_recorder);
            let db_for_ws = Arc::clone(&db_for_state);
            let app_handle_for_ws = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                while let Some(msg) = ws_commands.recv().await {
                    match msg {
                        WsMessage::ListCameras => {
                            match vng::native_video::list_cameras() {
                                Ok(cameras) => {
                                    let cameras_json: Vec<serde_json::Value> = cameras.iter().map(|c| {
                                        serde_json::json!({
                                            "id": c.index,
                                            "name": c.name,
                                            "path": format!("/dev/video{}", c.index)
                                        })
                                    }).collect();
                                    ws_for_handler.broadcast(&WsMessage::CamerasList {
                                        cameras: serde_json::Value::Array(cameras_json),
                                    });
                                }
                                Err(e) => {
                                    eprintln!("[SIEV] Error listando cámaras: {}", e);
                                    ws_for_handler.broadcast(&WsMessage::Error {
                                        source: "camera".to_string(),
                                        message: e,
                                    });
                                }
                            }
                        }
                        WsMessage::ListResolutions { camera_id } => {
                            match vng::native_video::list_camera_formats(camera_id as u32) {
                                Ok(formats) => {
                                    let resolutions: Vec<String> = formats.iter()
                                        .map(|f| format!("{}x{}@{}", f.width, f.height, f.fps))
                                        .collect();
                                    ws_for_handler.broadcast(&WsMessage::ResolutionsList {
                                        resolutions,
                                        camera_id,
                                    });
                                }
                                Err(e) => {
                                    eprintln!("[SIEV] Error listando formatos: {}", e);
                                    ws_for_handler.broadcast(&WsMessage::Error {
                                        source: "camera".to_string(),
                                        message: e,
                                    });
                                }
                            }
                        }
                        WsMessage::StartCapture { camera_id, width, height, fps } => {
                            let model_path = app_handle_for_ws.path().resource_dir()
                                .map(|p| p.join("backend/models/siev_vng_r01.onnx"))
                                .ok()
                                .filter(|p| p.exists())
                                .or_else(|| {
                                    let dev_path = std::path::PathBuf::from("../backend/models/siev_vng_r01.onnx");
                                    if dev_path.exists() { Some(dev_path) } else { None }
                                })
                                .or_else(|| {
                                    let abs_path = std::path::PathBuf::from("/home/nick/Escritorio/Proyectos/Siev/backend/models/siev_vng_r01.onnx");
                                    if abs_path.exists() { Some(abs_path) } else { None }
                                })
                                .map(|p| p.to_string_lossy().to_string())
                                .unwrap_or_else(|| "backend/models/siev_vng_r01.onnx".to_string());
                            let _ = native_cmds.start_capture(camera_id as u32, width, height, fps, model_path);
                        }
                        WsMessage::StopCapture => { native_cmds.stop_capture(); }
                        WsMessage::SetConfig { key, value } => {
                            match key.as_str() {
                                "bin_threshold" => { if let Some(val) = value.as_u64() { native_cmds.set_threshold(val as u8); } }
                                "threshold" => {
                                    // Puede ser un array [right, left] o un número único
                                    if let Some(arr) = value.as_array() {
                                        let right = arr.get(0).and_then(|v| v.as_u64()).unwrap_or(40) as u8;
                                        let left = arr.get(1).and_then(|v| v.as_u64()).unwrap_or(40) as u8;
                                        native_cmds.set_thresholds(right, left);
                                    } else if let Some(val) = value.as_u64() {
                                        native_cmds.set_threshold(val as u8);
                                    }
                                }
                                "nose_width" => { if let Some(val) = value.as_f64() { native_cmds.set_nose_width(val as f32); } }
                                "eye_height" => { if let Some(val) = value.as_f64() { native_cmds.set_eye_height(val as f32); } }
                                "use_yolo" => { if let Some(val) = value.as_bool() { native_cmds.set_use_yolo(val); } }
                                "show_debug" => { if let Some(val) = value.as_bool() { native_cmds.set_show_debug(val); } }
                                "manual_roi_right" => {
                                    if let Some(obj) = value.as_object() {
                                        let top = obj.get("top").and_then(|v| v.as_f64()).unwrap_or(0.1) as f32;
                                        let bottom = obj.get("bottom").and_then(|v| v.as_f64()).unwrap_or(0.9) as f32;
                                        let nasal = obj.get("nasal").and_then(|v| v.as_f64()).unwrap_or(0.1) as f32;
                                        let temporal = obj.get("temporal").and_then(|v| v.as_f64()).unwrap_or(0.9) as f32;
                                        native_cmds.set_manual_roi_right(top, bottom, nasal, temporal);
                                    }
                                }
                                "manual_roi_left" => {
                                    if let Some(obj) = value.as_object() {
                                        let top = obj.get("top").and_then(|v| v.as_f64()).unwrap_or(0.1) as f32;
                                        let bottom = obj.get("bottom").and_then(|v| v.as_f64()).unwrap_or(0.9) as f32;
                                        let nasal = obj.get("nasal").and_then(|v| v.as_f64()).unwrap_or(0.1) as f32;
                                        let temporal = obj.get("temporal").and_then(|v| v.as_f64()).unwrap_or(0.9) as f32;
                                        native_cmds.set_manual_roi_left(top, bottom, nasal, temporal);
                                    }
                                }
                                "smooth" => { if let Some(val) = value.as_f64() { native_cmds.set_smooth(val as f32); } }
                                "brightness" => { if let Some(val) = value.as_i64() { native_cmds.set_brightness(val as i32); } }
                                "contrast" => { if let Some(val) = value.as_f64() { native_cmds.set_contrast(val as f32); } }
                                "camera_setup" => {
                                    // Reiniciar captura con nueva configuración (start_capture maneja stop internamente)
                                    if let Some(obj) = value.as_object() {
                                        let camera_id = obj.get("camera_id").and_then(|v| v.as_i64()).unwrap_or(0) as u32;
                                        let width = obj.get("width").and_then(|v| v.as_u64()).unwrap_or(640) as u32;
                                        let height = obj.get("height").and_then(|v| v.as_u64()).unwrap_or(480) as u32;
                                        let fps = obj.get("fps").and_then(|v| v.as_u64()).unwrap_or(120) as u32;

                                        let model_path = app_handle_for_ws.path().resource_dir()
                                            .map(|p| p.join("backend/models/siev_vng_r01.onnx"))
                                            .ok()
                                            .filter(|p| p.exists())
                                            .or_else(|| {
                                                let dev_path = std::path::PathBuf::from("../backend/models/siev_vng_r01.onnx");
                                                if dev_path.exists() { Some(dev_path) } else { None }
                                            })
                                            .or_else(|| {
                                                let abs_path = std::path::PathBuf::from("/home/nick/Escritorio/Proyectos/Siev/backend/models/siev_vng_r01.onnx");
                                                if abs_path.exists() { Some(abs_path) } else { None }
                                            })
                                            .map(|p| p.to_string_lossy().to_string())
                                            .unwrap_or_else(|| "backend/models/siev_vng_r01.onnx".to_string());

                                        let _ = native_cmds.start_capture(camera_id, width, height, fps, model_path);
                                    }
                                }
                                "session_update" => {
                                    // Bulk update: unpack all fields and apply individually
                                    if let Some(obj) = value.as_object() {
                                        if let Some(val) = obj.get("brightness").and_then(|v| v.as_i64()) {
                                            native_cmds.set_brightness(val as i32);
                                        }
                                        if let Some(val) = obj.get("contrast").and_then(|v| v.as_f64()) {
                                            native_cmds.set_contrast(val as f32);
                                        }
                                        if let Some(arr) = obj.get("threshold").and_then(|v| v.as_array()) {
                                            let right = arr.get(0).and_then(|v| v.as_u64()).unwrap_or(40) as u8;
                                            let left = arr.get(1).and_then(|v| v.as_u64()).unwrap_or(40) as u8;
                                            native_cmds.set_thresholds(right, left);
                                        }
                                        if let Some(val) = obj.get("nose_width").and_then(|v| v.as_f64()) {
                                            native_cmds.set_nose_width(val as f32);
                                        }
                                        if let Some(val) = obj.get("eye_height").and_then(|v| v.as_f64()) {
                                            native_cmds.set_eye_height(val as f32);
                                        }
                                        if let Some(val) = obj.get("use_yolo").and_then(|v| v.as_bool()) {
                                            native_cmds.set_use_yolo(val);
                                        }
                                        if let Some(val) = obj.get("show_debug").and_then(|v| v.as_bool()) {
                                            native_cmds.set_show_debug(val);
                                        }
                                        if let Some(val) = obj.get("smooth").and_then(|v| v.as_f64()) {
                                            native_cmds.set_smooth(val as f32);
                                        }
                                        if let Some(roi_obj) = obj.get("manual_roi_right").and_then(|v| v.as_object()) {
                                            let top = roi_obj.get("top").and_then(|v| v.as_f64()).unwrap_or(0.1) as f32;
                                            let bottom = roi_obj.get("bottom").and_then(|v| v.as_f64()).unwrap_or(0.9) as f32;
                                            let nasal = roi_obj.get("nasal").and_then(|v| v.as_f64()).unwrap_or(0.1) as f32;
                                            let temporal = roi_obj.get("temporal").and_then(|v| v.as_f64()).unwrap_or(0.9) as f32;
                                            native_cmds.set_manual_roi_right(top, bottom, nasal, temporal);
                                        }
                                        if let Some(roi_obj) = obj.get("manual_roi_left").and_then(|v| v.as_object()) {
                                            let top = roi_obj.get("top").and_then(|v| v.as_f64()).unwrap_or(0.1) as f32;
                                            let bottom = roi_obj.get("bottom").and_then(|v| v.as_f64()).unwrap_or(0.9) as f32;
                                            let nasal = roi_obj.get("nasal").and_then(|v| v.as_f64()).unwrap_or(0.1) as f32;
                                            let temporal = roi_obj.get("temporal").and_then(|v| v.as_f64()).unwrap_or(0.9) as f32;
                                            native_cmds.set_manual_roi_left(top, bottom, nasal, temporal);
                                        }
                                        println!("[SIEV] Session update applied (bulk config sync)");
                                    }
                                }
                                _ => {}
                            }
                        }
                        WsMessage::StartRecording { session_id } => {
                            println!("[SIEV] StartRecording for session {}", session_id);
                            match db_for_ws.get_session_by_id(session_id).await {
                                Ok(Some(session)) => {
                                    // Start eye data recorder
                                    if let Some(data_path) = session.data_path {
                                        let path = PathBuf::from(&data_path);
                                        let recorder = SessionRecorder::start(path);
                                        let mut guard = recorder_for_ws.lock().unwrap();
                                        *guard = Some(recorder);
                                        println!("[SIEV] Data recording started -> {}", data_path);
                                    } else {
                                        eprintln!("[SIEV] Session {} has no data_path", session_id);
                                    }

                                    // Start video recorder
                                    if let Some(video_path) = session.video_path {
                                        let (cw, ch) = native_cmds.get_capture_dimensions();
                                        if cw > 0 && ch > 0 {
                                            let vpath = PathBuf::from(&video_path);
                                            match storage::VideoRecorder::start(vpath, cw, ch, 30) {
                                                Ok(vrec) => {
                                                    let vr_arc = native_cmds.get_video_recorder_arc();
                                                    let mut guard = vr_arc.lock().unwrap();
                                                    *guard = Some(vrec);
                                                    println!("[SIEV] Video recording started -> {}", video_path);
                                                }
                                                Err(e) => {
                                                    eprintln!("[SIEV] Failed to start video recorder: {}", e);
                                                }
                                            }
                                        } else {
                                            eprintln!("[SIEV] Cannot start video recording: capture not active");
                                        }
                                    }
                                }
                                Ok(None) => {
                                    eprintln!("[SIEV] Session {} not found", session_id);
                                }
                                Err(e) => {
                                    eprintln!("[SIEV] Error fetching session {}: {}", session_id, e);
                                }
                            }
                        }
                        WsMessage::StopRecording => {
                            println!("[SIEV] StopRecording");
                            // Stop eye data recorder
                            let recorder = {
                                let mut guard = recorder_for_ws.lock().unwrap();
                                guard.take()
                            };
                            if let Some(rec) = recorder {
                                rec.stop().await;
                                println!("[SIEV] Data recording stopped and saved");
                            }
                            // Stop video recorder
                            let video_recorder = {
                                let vr_arc = native_cmds.get_video_recorder_arc();
                                let mut guard = vr_arc.lock().unwrap();
                                guard.take()
                            };
                            if let Some(vrec) = video_recorder {
                                // Run blocking stop in a separate thread to avoid blocking async
                                tokio::task::spawn_blocking(move || {
                                    vrec.stop();
                                }).await.ok();
                                println!("[SIEV] Video recording stopped and saved");
                            }
                        }
                        WsMessage::CalibrationData { points, patient_distance } => {
                            let num_points = points.len();
                            let points_clone = points.clone();
                            let cal_data = math::processor::ManualCalibrationData {
                                points,
                                patient_distance,
                            };
                            let mut proc = eye_proc_for_ws.lock().unwrap();
                            proc.apply_manual_calibration(cal_data);
                            println!("[SIEV] Manual calibration applied ({} points, distance: {}cm)",
                                num_points, patient_distance);

                            // Save calibration to bundle if active
                            if let Some(mut snapshot) = proc.export_calibration_snapshot() {
                                snapshot.points = points_clone;
                                snapshot.patient_distance = patient_distance;
                                if let Some(ref bp) = *bundle_path_for_ws.lock().unwrap() {
                                    if let Err(e) = storage::bundle::SievBundle::save_calibration(bp, &snapshot) {
                                        eprintln!("[SIEV] Failed to save calibration: {}", e);
                                    }
                                }
                            }
                        }
                        _ => {}
                    }
                }
            });

            app.manage(AppState { eye_processor, hardware_manager, db: db_for_state, ws_server, active_recorder, native_video, active_bundle_path });
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if window.label() == "main" {
                    if let Some(state) = window.try_state::<AppState>() { state.native_video.stop_capture(); }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_version, get_websocket_port, process_eye_data_batch, reset_calibration, list_serial_ports, is_hardware_connected, connect_hardware, disconnect_hardware, send_hardware_command,
            is_python_connected, python_start_capture, python_stop_capture, python_list_cameras, list_camera_formats, python_set_pupil_config,
            get_patients, create_patient, update_patient, delete_patient, get_sessions, create_session, get_specialists, create_specialist, delete_specialist,
            get_setting, set_setting, get_default_storage_path, set_filtering_enabled, sync_storage, reset_application,
            get_vng_report_data, save_vng_test_result, get_vng_test_results, get_reference_values, calculate_vng_metrics, open_external_display,
            set_manual_roi_right, set_manual_roi_left, get_manual_rois, set_use_yolo,
            load_session_review, get_eye_data_window, recalibrate_session, get_video_conversion_status
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
