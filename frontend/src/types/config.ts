export interface ModulesConfig {
    [key: string]: boolean;
    vng: boolean;
    stimulus_screen: boolean;
    vhit: boolean;
    static_posturography: boolean;
    imu_posturography: boolean;
    vemp: boolean;
    point_projector: boolean;
    audiometria: boolean;
    otoscopia: boolean;
    impedanciometria: boolean;
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
}

export interface VNGAlgorithmConfig {
    primary: 'yolo26' | 'hough' | 'threshold';
    yolo_frequency?: number;
    yolo_confidence?: number;
    yolo_pupil_confidence?: number;
}

export interface VNGHardwareConfig {
    serial_port: string;
    baudrate: number;
    ir_led_intensity: 0 | 1 | 2 | 3 | 4;
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
    analysis_method: 'saccades' | 'spv' | 'both';
}

export interface CaloricIrrigation {
    label: string;
    temperature: number;
    ear: 'od' | 'oi';
}

export interface CaloricProtocolTiming {
    delay: number;
    irrigation_duration: number;
    rest_time: number;
    total_duration: number;
    torok: {
        start_time: number;
        duration: number;
    };
    ofi: {
        start_time: number;
        duration: number;
        fixation_led: 'right' | 'left' | 'both';
    };
}

export interface CaloricProtocol {
    id: string;
    name: string;
    comment: string;
    is_base: boolean;
    irrigations: CaloricIrrigation[];
    timing: CaloricProtocolTiming;
}

export interface VNGCaloricTestConfig {
    protocols: CaloricProtocol[];
}

export interface VNGTestsConfig {
    caloric: VNGCaloricTestConfig;
}

export interface VNGConfig {
    camera: VNGCameraConfig;
    algorithm: VNGAlgorithmConfig;
    hardware: VNGHardwareConfig;
    calibration: VNGCalibrationConfig;
    report: VNGReportConfig;
    tests: VNGTestsConfig;
}

export interface StimulusDisplayConfig {
    monitor_name: string;
    monitor_index: number;
    scale_factor: number;
    resolution_width: number;
    resolution_height: number;
    physical_width_mm: number;
    physical_height_mm: number;
    distance_cm: number;
    is_calibrated: boolean;
    pixel_density: number;
}

export interface StimulusDefaultParams {
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

// --- Audiometría ---

export interface AudiometriaReportConfig {
    template: 'standard' | 'detailed' | 'minimal' | 'custom';
    sections: ReportSection[];
    export_format: 'pdf' | 'docx';
    include_logo: boolean;
    include_audiogram: boolean;
    include_speech_curve: boolean;
}

export interface AudiometriaTestConfig {
    tonal_liminar: boolean;
    vocal: boolean;
    supraliminar: boolean;
    altas_frecuencias: boolean;
}

export interface AudiometriaReferencesConfig {
    normative: 'iso_7029' | 'ansi_s3_6';
    normal_threshold_db: number;
}

export interface AudiometriaFrequenciesConfig {
    standard: number[];
    extended: number[];
    high_frequency: number[];
    default_range: 'standard' | 'extended' | 'high_frequency';
}

export interface AudiometriaConfig {
    report: AudiometriaReportConfig;
    tests: AudiometriaTestConfig;
    references: AudiometriaReferencesConfig;
    frequencies: AudiometriaFrequenciesConfig;
}

// --- Otoscopia ---

export interface OtoscopiaReportConfig {
    template: 'standard' | 'detailed' | 'minimal' | 'custom';
    sections: ReportSection[];
    export_format: 'pdf' | 'docx';
    include_logo: boolean;
    include_images: boolean;
}

export interface OtoscopiaFinding {
    id: string;
    label: string;
    category: 'normal' | 'patologico';
    enabled: boolean;
}

export interface OtoscopiaFindingsConfig {
    findings: OtoscopiaFinding[];
}

export interface OtoscopiaRegion {
    id: string;
    label: string;
    enabled: boolean;
}

export interface OtoscopiaRegionsConfig {
    regions: OtoscopiaRegion[];
}

export interface OtoscopiaImagesConfig {
    capture_enabled: boolean;
    reference_images_enabled: boolean;
}

export interface OtoscopiaConfig {
    report: OtoscopiaReportConfig;
    findings: OtoscopiaFindingsConfig;
    regions: OtoscopiaRegionsConfig;
    images: OtoscopiaImagesConfig;
}

// --- Impedanciometría ---

export interface ImpedanciometriaReportConfig {
    template: 'standard' | 'detailed' | 'minimal' | 'custom';
    sections: ReportSection[];
    export_format: 'pdf' | 'docx';
    include_logo: boolean;
    include_tympanogram: boolean;
    include_reflex_table: boolean;
}

export interface ImpedanciometriaTestsConfig {
    timpanograma: boolean;
    reflejo_ipsilateral: boolean;
    reflejo_contralateral: boolean;
    decay: boolean;
    funcion_tubarica: boolean;
}

export interface ImpedanciometriaReferencesConfig {
    normative: 'asha_1997' | 'jerger_1970';
}

export interface JergerTypeConfig {
    id: string;
    label: string;
    description: string;
    compliance_min: number;
    compliance_max: number;
    pressure_min: number;
    pressure_max: number;
    enabled: boolean;
}

export interface ImpedanciometriaClassificationConfig {
    jerger_types: JergerTypeConfig[];
}

export interface ImpedanciometriaConfig {
    report: ImpedanciometriaReportConfig;
    tests: ImpedanciometriaTestsConfig;
    references: ImpedanciometriaReferencesConfig;
    classification: ImpedanciometriaClassificationConfig;
}

// --- Postural / VPPB ---

export type BodyPosition = 'seated' | 'supine' | 'side_right' | 'side_left' | 'prone'

export interface PosturalPosition {
    id: string
    label: string
    description: string
    default_duration_seconds: number
    body_position?: BodyPosition
    target_head_orientation?: { yaw?: number; pitch?: number; roll?: number }
}

export interface PosturalTestDefinition {
    id: string
    name: string
    category: 'provocation' | 'liberation' | 'repositioning'
    canal: 'posterior' | 'lateral' | 'anterior'
    side?: 'right' | 'left'
    positions: PosturalPosition[]
}

export interface PosturalTimingConfig {
    auto_advance: boolean
    countdown_sound: boolean
}

export interface PosturalVisualizationConfig {
    show_3d_head: boolean
    show_target_orientation: boolean
    head_model: 'ellipsoid' | 'capsule'
}

export interface SubjectiveSymptomDefinition {
    id: string
    label: string
    enabled: boolean
}

export interface SubjectiveSymptomScaleConfig {
    type: 'vas_0_10' | 'likert_0_4'
}

export interface SubjectiveSymptomRecord {
    symptom_id: string
    value: number
}

export interface PosturalSymptomsConfig {
    scale: SubjectiveSymptomScaleConfig
    symptoms: SubjectiveSymptomDefinition[]
}

export interface PosturalConfig {
    timing: PosturalTimingConfig
    visualization: PosturalVisualizationConfig
    symptoms: PosturalSymptomsConfig
    enabled_tests: string[]
    custom_tests: PosturalTestDefinition[]
}

export interface AppConfig {
    modules: ModulesConfig;
    general: GeneralConfig;
    vng: VNGConfig;
    stimulus_screen: StimulusScreenConfig;
    audiometria: AudiometriaConfig;
    otoscopia: OtoscopiaConfig;
    impedanciometria: ImpedanciometriaConfig;
    postural: PosturalConfig;
}
