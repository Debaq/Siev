export interface ModulesConfig {
    [key: string]: boolean;
    vng: boolean;
    stimulus_screen: boolean;
    vhit: boolean;
    static_posturography: boolean;
    imu_posturography: boolean;
    vemp: boolean;
    point_projector: boolean;
}

export interface InstitutionConfig {
    name: string;
    logo_path: string;
    address?: string;
    phone?: string;
    email?: string;
    extra_info?: string;
}

export interface StorageConfig {
    data_path: string;
    backup_enabled: boolean;
}

export interface GeneralConfig {
    institution: InstitutionConfig;
    storage: StorageConfig;
}

export interface VNGCameraConfig {
    camera_id: number;
    resolution_width: number;
    resolution_height: number;
    fps: number;
    exposure: number;
    contrast: number;
    brightness?: number; // Added to match session config
    flip_horizontal: boolean;
    flip_vertical: boolean;
    video_quality: number; // 1-100 (JPEG quality)
    video_scale: number;   // 0.1-1.0 (Resize factor)
}

export interface VNGLegacyParams {
    blur_enabled: boolean;
    blur_kernel: number;
    clahe_enabled: boolean;
    clahe_clip_limit: number;
    clahe_grid_size: number;
    morph_enabled: boolean;
    morph_close_iterations: number;
    morph_dilate_iterations: number;
}

export interface VNGPupilDetectionConfig {
    mode: 'legacy' | 'hybrid' | 'fast';
    search_window_multiplier: number;
    dark_threshold_percent: number;
    starburst_rays: number;
    starburst_min_gradient: number;
    fallback_threshold: number;
    // Hybrid params
    min_confidence_for_lock: number;  // Confianza mínima para aceptar detección (0-1)
    revalidation_interval: number;    // Frames entre re-validaciones
    legacy: VNGLegacyParams;
}

export interface ManualEyeRoi {
    top: number;
    bottom: number;
    nasal: number;
    temporal: number;
}

export interface VNGAlgorithmConfig {
    primary: 'yolo' | 'hough' | 'threshold';
    threshold: number;
    threshold_left?: number; // Added for per-eye threshold
    threshold_right?: number; // Added for per-eye threshold
    erode_left?: number;
    erode_right?: number;
    min_pupil_size: number;
    roi_enabled: boolean;
    yolo_frequency?: number;
    yolo_confidence?: number;
    nose_width?: number; // Added from session config
    eye_height?: number; // Added from session config
    smooth?: number;     // Added from session config
    use_yolo?: boolean;  // Added from session config
    show_debug?: boolean; // Added from session config
    manual_roi_right?: ManualEyeRoi; // Added from session config
    manual_roi_left?: ManualEyeRoi;  // Added from session config
}

export interface VNGHardwareConfig {
    serial_port: string;
    baudrate: number;
    ir_led_intensity: 0 | 1 | 2 | 3 | 4; // 5 levels: 0, 20, 40, 60, 80, 100%
    fixation_led_enabled: boolean;
    fixation_led_auto_off: number;
}

export interface VNGCalibrationConfig {
    pattern_type: '3_points' | '5_points' | '9_points';
    horizontal_angle: number;
    vertical_angle: number;
    point_duration: number;
    patient_distance_cm: number;
}

export interface ReportSection {
    id: string;
    label: string;
    enabled: boolean;
    order: number;
}

export interface VNGReportConfig {
    template: 'standard' | 'detailed' | 'minimal' | 'custom';
    sections: ReportSection[];
    export_format: 'pdf' | 'docx';
    include_logo: boolean;
    include_raw_data: boolean;
    include_graphs: boolean;
    compare_with_previous: boolean;
    diagram_style: 'claussen' | 'freyss' | 'butterfly';
}

export interface VNGConfig {
    camera: VNGCameraConfig;
    algorithm: VNGAlgorithmConfig;
    pupil_detection: VNGPupilDetectionConfig;
    hardware: VNGHardwareConfig;
    calibration: VNGCalibrationConfig;
    report: VNGReportConfig;
}

export interface StimulusDisplayConfig {
    monitor_name: string;
    monitor_index: number; // For OS positioning
    scale_factor: number;
    resolution_width: number;
    resolution_height: number;
    physical_width_mm: number;
    physical_height_mm: number;
    distance_cm: number; // Distance from patient eyes to screen
    is_calibrated: boolean;
    pixel_density: number; // PPI
}

export interface StimulusDefaultParams {
    calibration: {
        type: 'points_5' | 'points_7' | 'points_9';
        duration: number;
    };
    saccades: {
        min_amplitude: number;
        max_amplitude: number;
        min_interval: number;
        max_interval: number;
    };
    pursuit: {
        frequency: number;
        amplitudes: number[];
    };
    opk: {
        velocity: number;
        stripe_width_deg: number;
        direction: 'left' | 'right' | 'up' | 'down';
        fixation_enabled: boolean;
    };
    target: {
        size_deg: number;
        color: string;
        shape: string;
    }
}

export interface StimulusScreenConfig {
    display: StimulusDisplayConfig;
    defaults?: StimulusDefaultParams;
}

export interface AppConfig {
    modules: ModulesConfig;
    general: GeneralConfig;
    vng: VNGConfig;
    stimulus_screen: StimulusScreenConfig;
}
