use serde::{Deserialize, Serialize};

// ============================================
// Irrigation Types
// ============================================

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum IrrigationType {
    Warm,
    Cool,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum IrrigationSide {
    Left,
    Right,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum VestibularFunction {
    Normal,
    UnilateralWeakness,
    BilateralWeakness,
    Hyperactive,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum CaloricCalculationMethod {
    Spv,           // VCL máxima (default)
    BeatCount,     // Conteo de nistagmos
    TotalDuration, // Duración total de respuesta
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum CaloricProtocolType {
    Bithermal,
    MonothermalWarm,
    MonothermalCool,
}

// ============================================
// SPV Timeline Data
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SPVTimePoint {
    pub time_seconds: f64,
    pub spv: f64, // °/s (positive = right, negative = left)
}

// ============================================
// Caloric Irrigation
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CaloricIrrigation {
    pub side: IrrigationSide,
    pub irrigation_type: IrrigationType,
    pub temperature_celsius: f64,           // Typical: 30°C (cool), 44°C (warm)
    pub volume_ml: Option<f64>,             // Typical: 250ml water or 5ml air
    pub duration_seconds: f64,              // Typical: 30-40s

    // Results
    pub spv_max: f64,                       // Maximum SPV (°/s)
    pub spv_timeline: Vec<SPVTimePoint>,    // Temporal evolution
    pub latency_seconds: f64,               // Time to maximum response
    pub duration_response: f64,             // Response duration

    // Fixation index
    pub spv_with_fixation: Option<f64>,
    pub fixation_index: Option<f64>,        // % suppression

    // Beat metrics
    pub beat_count: Option<u32>,            // Conteo total de nistagmos detectados
    pub nystagmus_frequency: Option<f64>,   // Frecuencia (beats/s) en ventana de culminación
}

impl CaloricIrrigation {
    pub fn new(side: IrrigationSide, irrigation_type: IrrigationType) -> Self {
        let temp = match irrigation_type {
            IrrigationType::Warm => 44.0,
            IrrigationType::Cool => 30.0,
        };

        Self {
            side,
            irrigation_type,
            temperature_celsius: temp,
            volume_ml: Some(250.0),
            duration_seconds: 30.0,
            spv_max: 0.0,
            spv_timeline: Vec::new(),
            latency_seconds: 0.0,
            duration_response: 0.0,
            spv_with_fixation: None,
            fixation_index: None,
            beat_count: None,
            nystagmus_frequency: None,
        }
    }
}

// ============================================
// Jongkees Formula
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JongkeesFormula {
    // Formula: UW = ((RW + RC) - (LW + LC)) / (RW + RC + LW + LC) × 100
    pub unilateral_weakness_percent: f64,  // UW% (+ = right weak)

    // Formula: DP = ((RW + LC) - (LW + RC)) / (RW + RC + LW + LC) × 100
    pub directional_preponderance_percent: f64, // DP% (+ = right preponderance)

    // Interpretation
    pub uw_significant: bool,               // |UW| > 20-25% typically
    pub dp_significant: bool,               // |DP| > 25-30% typically

    // Values used
    pub rw: f64, // Right Warm
    pub rc: f64, // Right Cool
    pub lw: f64, // Left Warm
    pub lc: f64, // Left Cool

    // Calculation method
    #[serde(default = "default_calculation_method")]
    pub calculation_method: CaloricCalculationMethod,
}

fn default_calculation_method() -> CaloricCalculationMethod {
    CaloricCalculationMethod::Spv
}

impl JongkeesFormula {
    pub fn calculate(rw: f64, rc: f64, lw: f64, lc: f64, method: CaloricCalculationMethod) -> Self {
        let total = rw + rc + lw + lc;

        let (uw_percent, dp_percent) = if total > 0.0 {
            let uw = ((rw + rc) - (lw + lc)) / total * 100.0;
            let dp = ((rw + lc) - (lw + rc)) / total * 100.0;
            (uw, dp)
        } else {
            (0.0, 0.0)
        };

        Self {
            unilateral_weakness_percent: uw_percent,
            directional_preponderance_percent: dp_percent,
            uw_significant: uw_percent.abs() > 22.0,
            dp_significant: dp_percent.abs() > 28.0,
            rw,
            rc,
            lw,
            lc,
            calculation_method: method,
        }
    }
}

// ============================================
// Caloric Irrigations Set
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CaloricIrrigations {
    pub right_warm: CaloricIrrigation,
    pub right_cool: CaloricIrrigation,
    pub left_warm: CaloricIrrigation,
    pub left_cool: CaloricIrrigation,
}

impl Default for CaloricIrrigations {
    fn default() -> Self {
        Self {
            right_warm: CaloricIrrigation::new(IrrigationSide::Right, IrrigationType::Warm),
            right_cool: CaloricIrrigation::new(IrrigationSide::Right, IrrigationType::Cool),
            left_warm: CaloricIrrigation::new(IrrigationSide::Left, IrrigationType::Warm),
            left_cool: CaloricIrrigation::new(IrrigationSide::Left, IrrigationType::Cool),
        }
    }
}

// ============================================
// Clinical Interpretation
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CaloricInterpretation {
    pub vestibular_function: VestibularFunction,
    pub affected_side: Option<IrrigationSide>,
    pub bilateral: bool,
    pub central_signs: Option<Vec<String>>,
}

// ============================================
// Caloric Test Result
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CaloricTestResult {
    pub id: Option<i64>,
    pub session_id: i64,
    pub test_date: String,

    // 4 standard irrigations (RCLW order)
    pub irrigations: CaloricIrrigations,

    // Jongkees analysis
    pub jongkees: JongkeesFormula,

    // Clinical interpretation
    pub interpretation: CaloricInterpretation,

    // Protocol type
    #[serde(default = "default_protocol_type")]
    pub protocol_type: CaloricProtocolType,

    pub clinical_notes: Option<String>,
}

fn default_protocol_type() -> CaloricProtocolType {
    CaloricProtocolType::Bithermal
}

impl CaloricTestResult {
    pub fn new(session_id: i64) -> Self {
        let irrigations = CaloricIrrigations::default();
        let jongkees = JongkeesFormula::calculate(0.0, 0.0, 0.0, 0.0, CaloricCalculationMethod::Spv);

        Self {
            id: None,
            session_id,
            test_date: chrono::Local::now().to_rfc3339(),
            irrigations,
            jongkees,
            interpretation: CaloricInterpretation {
                vestibular_function: VestibularFunction::Normal,
                affected_side: None,
                bilateral: false,
                central_signs: None,
            },
            protocol_type: CaloricProtocolType::Bithermal,
            clinical_notes: None,
        }
    }

    pub fn recalculate_jongkees(&mut self, method: CaloricCalculationMethod) {
        let extract = |irr: &CaloricIrrigation| -> f64 {
            match method {
                CaloricCalculationMethod::Spv => irr.spv_max,
                CaloricCalculationMethod::BeatCount => irr.beat_count.unwrap_or(0) as f64,
                CaloricCalculationMethod::TotalDuration => irr.duration_response,
            }
        };
        self.jongkees = JongkeesFormula::calculate(
            extract(&self.irrigations.right_warm),
            extract(&self.irrigations.right_cool),
            extract(&self.irrigations.left_warm),
            extract(&self.irrigations.left_cool),
            method,
        );
    }
}
