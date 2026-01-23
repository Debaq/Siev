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
    flip_horizontal: boolean;
    flip_vertical: boolean;
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
    mode: 'hybrid' | 'fast' | 'legacy';
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

export interface VNGAlgorithmConfig {
    primary: 'yolo' | 'hough' | 'threshold';
    threshold: number;
    min_pupil_size: number;
    roi_enabled: boolean;
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

export interface VNGReportConfig {
    template: 'standard' | 'detailed' | 'minimal';
    include_sections: string[];
    export_format: 'pdf' | 'docx';
    include_logo: boolean;
    include_raw_data: boolean;
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
    screen_index: number;
    resolution: string;
    fullscreen: boolean;
}

export interface StimulusScreenConfig {
    display: StimulusDisplayConfig;
    // Add more as needed
}

export interface AppConfig {
    modules: ModulesConfig;
    general: GeneralConfig;
    vng: VNGConfig;
    stimulus_screen: StimulusScreenConfig;
}
