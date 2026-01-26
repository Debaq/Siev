use serde::{Deserialize, Serialize};

// ============================================
// Nystagmus Direction and Type
// ============================================

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum NystagmusDirection {
    Left,
    Right,
    Up,
    Down,
    RotatoryCw,
    RotatoryCcw,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum NystagmusType {
    Spontaneous,
    GazeEvoked,
    Positional,
    Positioning,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum NystagmusIntensity {
    Mild,
    Moderate,
    Severe,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum AffectedCanal {
    Posterior,
    Horizontal,
    Anterior,
}

// ============================================
// Nystagmus Data
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NystagmusData {
    pub spv: f64,                           // Slow Phase Velocity (°/s)
    pub direction: NystagmusDirection,
    pub nystagmus_type: NystagmusType,

    // Positional context
    pub head_position: Option<String>,      // 'supine', 'right_lateral', etc.
    pub gaze_position: Option<String>,      // 'center', 'right_20', etc.

    // Characteristics
    pub is_torsional: bool,
    pub beats_per_second: Option<f64>,
    pub with_fixation: bool,                // true = test with visual fixation

    // Fatigue / Habituation
    pub fatigue_present: Option<bool>,
}

// ============================================
// Dix-Hallpike Test
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DixHallpikeNystagmus {
    pub direction: NystagmusDirection,
    pub latency_seconds: f64,               // Time to onset
    pub duration_seconds: f64,              // Total duration
    pub intensity: NystagmusIntensity,
    pub fatigable: bool,                    // Decreases with repetition
    pub torsional_component: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DixHallpikeResult {
    pub side: String,                       // "left" or "right"
    pub nystagmus_present: bool,

    // Nystagmus characteristics (if present)
    pub nystagmus: Option<DixHallpikeNystagmus>,

    // Associated symptoms
    pub vertigo_reported: bool,
    pub nausea_reported: bool,

    // Interpretation
    pub bppv_suspected: bool,
    pub affected_canal: Option<AffectedCanal>,
}

// ============================================
// Gaze-Evoked Nystagmus
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GazeEvokedResults {
    pub center: Option<NystagmusData>,
    pub right: Option<NystagmusData>,
    pub left: Option<NystagmusData>,
    pub up: Option<NystagmusData>,
    pub down: Option<NystagmusData>,
}

// ============================================
// Dix-Hallpike Bilateral
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DixHallpikeBilateral {
    pub left: DixHallpikeResult,
    pub right: DixHallpikeResult,
}

// ============================================
// Positional Test Result
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PositionalTestResult {
    pub id: Option<i64>,
    pub session_id: i64,
    pub test_date: String,

    // Spontaneous nystagmus (without fixation)
    pub spontaneous_dark: Option<NystagmusData>,

    // Nystagmus with fixation
    pub spontaneous_fixation: Option<NystagmusData>,

    // Gaze-evoked nystagmus test
    pub gaze_evoked: Option<GazeEvokedResults>,

    // Positional nystagmus (different head positions)
    pub positional: Option<Vec<NystagmusData>>,

    // Dix-Hallpike
    pub dix_hallpike: Option<DixHallpikeBilateral>,

    // Visual fixation index (how much nystagmus is suppressed)
    pub fixation_index: Option<f64>,        // % suppression

    pub clinical_notes: Option<String>,
}
