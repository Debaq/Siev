// Types mirroring Rust structs for session review

export interface ChartEyeDataPoint {
    t: number;
    lx: number | null;
    ly: number | null;
    rx: number | null;
    ry: number | null;
}

export interface SaccadeMarker {
    start_time: number;
    end_time: number;
    amplitude: number;
    peak_velocity: number;
    duration_ms: number;
    direction: string;
}

export interface SPVTimePoint {
    time: number;
    spv: number;
}

export interface NystagmusBeatMarker {
    slow_start: number;
    slow_end: number;
    fast_end: number;
    spv: number;
    fast_velocity: number;
    amplitude: number;
    direction: string;
    deflection_points: [number, number][];
}

export interface ManualCalibrationPoint {
    id: string;
    angle_x: number;
    angle_y: number;
    pixel_right: { x: number; y: number };
    pixel_left: { x: number; y: number };
}

export interface CalibrationSnapshot {
    points: ManualCalibrationPoint[];
    patient_distance: number;
    left_center: [number, number];
    right_center: [number, number];
    left_scale: [number, number];
    right_scale: [number, number];
    timestamp: string;
}

export interface PatientSnapshot {
    id: number;
    first_name: string;
    last_name: string;
    dni: string | null;
    birth_date: string | null;
    gender: string | null;
}

export interface SessionManifest {
    version: string;
    created_at: string;
    patient: PatientSnapshot;
    test_type: string;
    description: string | null;
    specialist_id: number | null;
}

export interface VideoCropInfo {
    content_width: number;
    content_height: number;
    encoder_width: number;
    encoder_height: number;
}

export interface SessionReviewPayload {
    recording_id: number;
    manifest: SessionManifest;
    calibration: CalibrationSnapshot | null;
    duration_seconds: number;
    sample_rate_hz: number;
    total_samples: number;
    video_url: string | null;
    video_available: boolean;
    video_crop: VideoCropInfo | null;
    eye_data: ChartEyeDataPoint[];
    saccades: SaccadeMarker[];
    spv_timeline: SPVTimePoint[];
    nystagmus_beats: NystagmusBeatMarker[];
    deflection_points: [number, number][];
    overall_spv: number;
    pursuit_gain: number | null;
}

export interface TimelineState {
    currentTime: number;
    duration: number;
    isPlaying: boolean;
    playbackRate: number;
    zoomRange: [number, number] | null;
}
