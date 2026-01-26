use serde::{Deserialize, Serialize};
use crate::vng::tests::{
    SaccadeTestResult, SmoothPursuitTestResult, OKNTestResult,
    PositionalTestResult, CaloricTestResult,
};

// ============================================
// Patient Data for Reports
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PatientReportData {
    pub id: i64,
    pub full_name: String,
    pub dni: Option<String>,
    pub birth_date: Option<String>,
    pub age: Option<i32>,
    pub gender: Option<String>,
}

// ============================================
// Session Data for Reports
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionReportData {
    pub id: i64,
    pub date: String,
    pub specialist_name: Option<String>,
    pub description: Option<String>,
}

// ============================================
// Reference Values for Reports
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReferenceValue {
    pub test_type: String,
    pub metric_name: String,
    pub min_normal: f64,
    pub max_normal: f64,
    pub unit: String,
    pub age_group: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReferenceValueSet {
    pub saccade_latency: ReferenceValue,
    pub saccade_velocity: ReferenceValue,
    pub pursuit_gain: ReferenceValue,
    pub caloric_spv: ReferenceValue,
    pub uw_threshold: ReferenceValue,
    pub dp_threshold: ReferenceValue,
}

impl Default for ReferenceValueSet {
    fn default() -> Self {
        Self {
            saccade_latency: ReferenceValue {
                test_type: "saccade".into(),
                metric_name: "latency".into(),
                min_normal: 150.0,
                max_normal: 250.0,
                unit: "ms".into(),
                age_group: None,
            },
            saccade_velocity: ReferenceValue {
                test_type: "saccade".into(),
                metric_name: "peak_velocity".into(),
                min_normal: 300.0,
                max_normal: 600.0,
                unit: "°/s".into(),
                age_group: None,
            },
            pursuit_gain: ReferenceValue {
                test_type: "pursuit".into(),
                metric_name: "gain".into(),
                min_normal: 0.8,
                max_normal: 1.0,
                unit: "".into(),
                age_group: None,
            },
            caloric_spv: ReferenceValue {
                test_type: "caloric".into(),
                metric_name: "spv_max".into(),
                min_normal: 6.0,
                max_normal: 80.0,
                unit: "°/s".into(),
                age_group: None,
            },
            uw_threshold: ReferenceValue {
                test_type: "caloric".into(),
                metric_name: "unilateral_weakness".into(),
                min_normal: -22.0,
                max_normal: 22.0,
                unit: "%".into(),
                age_group: None,
            },
            dp_threshold: ReferenceValue {
                test_type: "caloric".into(),
                metric_name: "directional_preponderance".into(),
                min_normal: -28.0,
                max_normal: 28.0,
                unit: "%".into(),
                age_group: None,
            },
        }
    }
}

// ============================================
// Historical Comparison
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PreviousSessionData {
    pub session: SessionReportData,
    pub caloric: Option<CaloricTestResult>,
}

// ============================================
// Main VNG Report Data DTO
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VNGReportData {
    pub patient: PatientReportData,
    pub session: SessionReportData,

    // Test results (null if not performed)
    pub saccades: Option<SaccadeTestResult>,
    pub pursuit: Option<SmoothPursuitTestResult>,
    pub okn: Option<OKNTestResult>,
    pub positional: Option<PositionalTestResult>,
    pub caloric: Option<CaloricTestResult>,

    // Historical comparison (optional)
    pub previous_session: Option<PreviousSessionData>,

    // Reference values for comparison
    pub reference_values: Option<ReferenceValueSet>,
}

impl VNGReportData {
    pub fn new(patient: PatientReportData, session: SessionReportData) -> Self {
        Self {
            patient,
            session,
            saccades: None,
            pursuit: None,
            okn: None,
            positional: None,
            caloric: None,
            previous_session: None,
            reference_values: Some(ReferenceValueSet::default()),
        }
    }
}

// ============================================
// Report Section Configuration
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReportSection {
    pub id: String,
    pub label: String,
    pub enabled: bool,
    pub order: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VNGReportConfig {
    pub template: String,
    pub sections: Vec<ReportSection>,
    pub export_format: String,
    pub include_logo: bool,
    pub include_raw_data: bool,
    pub include_graphs: bool,
    pub compare_with_previous: bool,
    pub diagram_style: String,
}

impl Default for VNGReportConfig {
    fn default() -> Self {
        Self {
            template: "standard".into(),
            sections: vec![
                ReportSection { id: "header".into(), label: "Encabezado".into(), enabled: true, order: 0 },
                ReportSection { id: "patient".into(), label: "Datos del Paciente".into(), enabled: true, order: 1 },
                ReportSection { id: "saccades".into(), label: "Sacadas".into(), enabled: true, order: 2 },
                ReportSection { id: "pursuit".into(), label: "Rastreo".into(), enabled: true, order: 3 },
                ReportSection { id: "okn".into(), label: "OKN".into(), enabled: false, order: 4 },
                ReportSection { id: "positional".into(), label: "Posicional".into(), enabled: true, order: 5 },
                ReportSection { id: "caloric".into(), label: "Calóricas".into(), enabled: true, order: 6 },
                ReportSection { id: "summary".into(), label: "Resumen Clínico".into(), enabled: true, order: 7 },
                ReportSection { id: "signature".into(), label: "Firma".into(), enabled: true, order: 8 },
            ],
            export_format: "pdf".into(),
            include_logo: true,
            include_raw_data: false,
            include_graphs: true,
            compare_with_previous: false,
            diagram_style: "claussen".into(),
        }
    }
}

// ============================================
// VNG Report Record (stored in DB)
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VNGReportRecord {
    pub id: Option<i64>,
    pub session_id: i64,
    pub pdf_path: Option<String>,
    pub config_json: String,
    pub created_at: String,
}

// ============================================
// VNG Test Result Record (generic, stored as JSON)
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VNGTestResultRecord {
    pub id: Option<i64>,
    pub session_id: i64,
    pub test_type: String,
    pub results_json: String,
    pub clinical_notes: Option<String>,
    pub created_at: Option<String>,
}
