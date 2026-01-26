// ============================================
// VNG Test Result Types
// ============================================

// --- Direction Types ---
export type HorizontalDirection = 'left' | 'right';
export type VerticalDirection = 'up' | 'down';
export type NystagmusDirection = 'left' | 'right' | 'up' | 'down' | 'rotatory_cw' | 'rotatory_ccw';

// --- Oculomotor Tests ---

export interface SaccadeMetrics {
    latency_ms: number;           // Tiempo de reacción (ms)
    peak_velocity: number;        // Velocidad máxima (°/s)
    accuracy_percent: number;     // Precisión (%)
    duration_ms: number;          // Duración de la sacada (ms)
}

export interface SaccadeTestResult {
    id?: number;
    session_id: number;
    test_date: string;

    // Métricas por dirección
    left: SaccadeMetrics;
    right: SaccadeMetrics;
    up?: SaccadeMetrics;
    down?: SaccadeMetrics;

    // Parámetros del test
    target_amplitude: number;     // Amplitud del estímulo (°)
    target_velocity?: number;     // Velocidad del estímulo si es predictivo

    // Interpretación
    is_normal: boolean;
    abnormality_notes?: string;
    clinical_notes?: string;
}

export type PursuitPattern = 'I' | 'II' | 'III' | 'IV';

export interface SmoothPursuitMetrics {
    gain: number;                 // Ganancia (eye_vel / target_vel)
    phase_lag: number;            // Desfase en grados
    asymmetry_percent?: number;   // Asimetría L/R
}

export interface SmoothPursuitTestResult {
    id?: number;
    session_id: number;
    test_date: string;

    // Métricas por dirección
    horizontal: {
        left: SmoothPursuitMetrics;
        right: SmoothPursuitMetrics;
    };
    vertical?: {
        up: SmoothPursuitMetrics;
        down: SmoothPursuitMetrics;
    };

    // Patrón visual
    pattern: PursuitPattern;      // I = normal, IV = muy afectado

    // Parámetros del test
    target_frequency: number;     // Hz (típico: 0.2-0.5)
    target_amplitude: number;     // Grados

    is_normal: boolean;
    clinical_notes?: string;
}

export interface OKNMetrics {
    gain: number;                 // Ganancia del nistagmo
    spv: number;                  // Slow Phase Velocity promedio (°/s)
    beat_frequency: number;       // Frecuencia de batido (Hz)
}

export interface OKNTestResult {
    id?: number;
    session_id: number;
    test_date: string;

    // Métricas por velocidad y dirección
    velocities: {
        stimulus_velocity: number;  // °/s (20, 40, 60)
        left: OKNMetrics;
        right: OKNMetrics;
    }[];

    // Asimetría total
    directional_preponderance: number;  // % (+ = derecha)

    is_normal: boolean;
    clinical_notes?: string;
}

// --- Positional Tests ---

export type NystagmusType = 'spontaneous' | 'gaze_evoked' | 'positional' | 'positioning';

export interface NystagmusData {
    spv: number;                  // Slow Phase Velocity (°/s)
    direction: NystagmusDirection;
    type: NystagmusType;

    // Contexto posicional
    head_position?: string;       // 'supine', 'right_lateral', 'left_lateral', 'head_hanging'
    gaze_position?: string;       // 'center', 'right_20', 'left_20', 'up_20', 'down_20'

    // Características
    is_torsional: boolean;
    beats_per_second?: number;
    with_fixation: boolean;       // true = prueba con fijación visual

    // Fatigue / Habituation
    fatigue_present?: boolean;    // Disminuye con el tiempo
}

export interface DixHallpikeResult {
    side: 'left' | 'right';
    nystagmus_present: boolean;

    // Características del nistagmo (si presente)
    nystagmus?: {
        direction: NystagmusDirection;
        latency_seconds: number;    // Tiempo hasta aparición
        duration_seconds: number;   // Duración total
        intensity: 'mild' | 'moderate' | 'severe';
        fatigable: boolean;         // Disminuye con repetición
        torsional_component: boolean;
    };

    // Síntomas asociados
    vertigo_reported: boolean;
    nausea_reported: boolean;

    // Interpretación
    bppv_suspected: boolean;
    affected_canal?: 'posterior' | 'horizontal' | 'anterior';
}

export interface PositionalTestResult {
    id?: number;
    session_id: number;
    test_date: string;

    // Nistagmo espontáneo (sin fijación)
    spontaneous_dark?: NystagmusData;

    // Nistagmo con fijación
    spontaneous_fixation?: NystagmusData;

    // Test de mirada excéntrica
    gaze_evoked?: {
        center: NystagmusData | null;
        right: NystagmusData | null;
        left: NystagmusData | null;
        up?: NystagmusData | null;
        down?: NystagmusData | null;
    };

    // Nistagmo posicional (diferentes posiciones de cabeza)
    positional?: NystagmusData[];

    // Dix-Hallpike
    dix_hallpike?: {
        left: DixHallpikeResult;
        right: DixHallpikeResult;
    };

    // Índice de fijación visual (cuánto suprime el nistagmo)
    fixation_index?: number;      // % de supresión

    clinical_notes?: string;
}

// --- Caloric Tests ---

export type IrrigationType = 'warm' | 'cool';
export type IrrigationSide = 'left' | 'right';

export interface SPVTimePoint {
    time_seconds: number;
    spv: number;                  // °/s (positivo = derecha, negativo = izquierda)
}

export interface CaloricIrrigation {
    side: IrrigationSide;
    type: IrrigationType;
    temperature_celsius: number;  // Típico: 30°C (cool), 44°C (warm)
    volume_ml?: number;           // Típico: 250ml agua o 5ml aire
    duration_seconds: number;     // Típico: 30-40s

    // Resultados
    spv_max: number;              // SPV máximo (°/s)
    spv_timeline: SPVTimePoint[]; // Evolución temporal
    latency_seconds: number;      // Tiempo hasta respuesta máxima
    duration_response: number;    // Duración de la respuesta

    // Índice de fijación
    spv_with_fixation?: number;
    fixation_index?: number;      // % de supresión
}

export interface JongkeesFormula {
    // Fórmula: UW = ((RW + RC) - (LW + LC)) / (RW + RC + LW + LC) × 100
    unilateral_weakness_percent: number;  // UW% (+ = derecha débil)

    // Fórmula: DP = ((RW + LC) - (LW + RC)) / (RW + RC + LW + LC) × 100
    directional_preponderance_percent: number;  // DP% (+ = preponderancia derecha)

    // Interpretación
    uw_significant: boolean;      // |UW| > 20-25% típicamente
    dp_significant: boolean;      // |DP| > 25-30% típicamente

    // Valores usados
    rw: number;  // Right Warm
    rc: number;  // Right Cool
    lw: number;  // Left Warm
    lc: number;  // Left Cool
}

export interface CaloricTestResult {
    id?: number;
    session_id: number;
    test_date: string;

    // 4 irrigaciones estándar (RCLW order: Right Cool, Left Warm, Right Warm, Left Cool)
    irrigations: {
        right_warm: CaloricIrrigation;
        right_cool: CaloricIrrigation;
        left_warm: CaloricIrrigation;
        left_cool: CaloricIrrigation;
    };

    // Análisis Jongkees
    jongkees: JongkeesFormula;

    // Interpretación clínica
    interpretation: {
        vestibular_function: 'normal' | 'unilateral_weakness' | 'bilateral_weakness' | 'hyperactive';
        affected_side?: 'left' | 'right' | 'bilateral';
        central_signs?: string[];
    };

    clinical_notes?: string;
}

// ============================================
// Report Configuration Types
// ============================================

export interface ReportSection {
    id: string;
    label: string;
    enabled: boolean;
    order: number;
}

export const DEFAULT_REPORT_SECTIONS: ReportSection[] = [
    { id: 'header', label: 'Encabezado', enabled: true, order: 0 },
    { id: 'patient', label: 'Datos del Paciente', enabled: true, order: 1 },
    { id: 'saccades', label: 'Sacadas', enabled: true, order: 2 },
    { id: 'pursuit', label: 'Rastreo', enabled: true, order: 3 },
    { id: 'okn', label: 'OKN', enabled: false, order: 4 },
    { id: 'positional', label: 'Posicional', enabled: true, order: 5 },
    { id: 'caloric', label: 'Calóricas', enabled: true, order: 6 },
    { id: 'summary', label: 'Resumen Clínico', enabled: true, order: 7 },
    { id: 'signature', label: 'Firma', enabled: true, order: 8 },
];

export type DiagramStyle = 'claussen' | 'freyss' | 'butterfly';
export type ReportTemplate = 'standard' | 'detailed' | 'minimal' | 'custom';

// ============================================
// Report Data DTOs (from Rust backend)
// ============================================

export interface PatientReportData {
    id: number;
    full_name: string;
    dni?: string;
    birth_date?: string;
    age?: number;
    gender?: string;
}

export interface SessionReportData {
    id: number;
    date: string;
    specialist_name?: string;
    description?: string;
}

export interface VNGReportData {
    patient: PatientReportData;
    session: SessionReportData;

    // Test results (null if not performed)
    saccades?: SaccadeTestResult;
    pursuit?: SmoothPursuitTestResult;
    okn?: OKNTestResult;
    positional?: PositionalTestResult;
    caloric?: CaloricTestResult;

    // Historical comparison (optional)
    previous_session?: {
        session: SessionReportData;
        caloric?: CaloricTestResult;
    };

    // Reference values for comparison
    reference_values?: ReferenceValueSet;
}

export interface ReferenceValue {
    test_type: string;
    metric_name: string;
    min_normal: number;
    max_normal: number;
    unit: string;
    age_group?: string;
}

export interface ReferenceValueSet {
    saccade_latency: ReferenceValue;
    saccade_velocity: ReferenceValue;
    pursuit_gain: ReferenceValue;
    caloric_spv: ReferenceValue;
    uw_threshold: ReferenceValue;
    dp_threshold: ReferenceValue;
}

// ============================================
// Diagram Data Types
// ============================================

export interface ClaussenDiagramData {
    // Cuadrantes del diagrama de Claussen
    right_warm: number;   // SPV máximo
    right_cool: number;
    left_warm: number;
    left_cool: number;

    // Líneas calculadas
    uw_line?: { x1: number; y1: number; x2: number; y2: number };
    dp_line?: { x1: number; y1: number; x2: number; y2: number };
}

export interface FreyssDiagramData {
    // Vectores del diagrama de Freyss
    vectors: {
        label: string;
        magnitude: number;
        angle: number;
    }[];
}

export interface ButterflyDiagramData {
    // Datos para diagrama de mariposa
    spv_timelines: {
        irrigation: string;  // 'RW', 'RC', 'LW', 'LC'
        data: SPVTimePoint[];
    }[];
}
