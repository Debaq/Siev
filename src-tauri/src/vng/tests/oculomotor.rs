use serde::{Deserialize, Serialize};

// ============================================
// Saccade Test Types
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SaccadeMetrics {
    pub latency_ms: f64,        // Reaction time (ms)
    pub peak_velocity: f64,     // Peak velocity (°/s)
    pub accuracy_percent: f64,  // Accuracy (%)
    pub duration_ms: f64,       // Saccade duration (ms)
}

impl Default for SaccadeMetrics {
    fn default() -> Self {
        Self {
            latency_ms: 0.0,
            peak_velocity: 0.0,
            accuracy_percent: 100.0,
            duration_ms: 0.0,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SaccadeTestResult {
    pub id: Option<i64>,
    pub session_id: i64,
    pub test_date: String,

    // Metrics by direction
    pub left: SaccadeMetrics,
    pub right: SaccadeMetrics,
    pub up: Option<SaccadeMetrics>,
    pub down: Option<SaccadeMetrics>,

    // Test parameters
    pub target_amplitude: f64,      // Stimulus amplitude (°)
    pub target_velocity: Option<f64>, // Stimulus velocity if predictive

    // Interpretation
    pub is_normal: bool,
    pub abnormality_notes: Option<String>,
    pub clinical_notes: Option<String>,
}

// ============================================
// Smooth Pursuit Test Types
// ============================================

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum PursuitPattern {
    I,   // Normal
    II,  // Mildly affected
    III, // Moderately affected
    IV,  // Severely affected
}

impl Default for PursuitPattern {
    fn default() -> Self {
        Self::I
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SmoothPursuitMetrics {
    pub gain: f64,                  // Gain (eye_vel / target_vel)
    pub phase_lag: f64,             // Phase lag in degrees
    pub asymmetry_percent: Option<f64>, // L/R asymmetry
}

impl Default for SmoothPursuitMetrics {
    fn default() -> Self {
        Self {
            gain: 1.0,
            phase_lag: 0.0,
            asymmetry_percent: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DirectionalPursuitMetrics {
    pub left: SmoothPursuitMetrics,
    pub right: SmoothPursuitMetrics,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerticalPursuitMetrics {
    pub up: SmoothPursuitMetrics,
    pub down: SmoothPursuitMetrics,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SmoothPursuitTestResult {
    pub id: Option<i64>,
    pub session_id: i64,
    pub test_date: String,

    // Metrics by direction
    pub horizontal: DirectionalPursuitMetrics,
    pub vertical: Option<VerticalPursuitMetrics>,

    // Visual pattern
    pub pattern: PursuitPattern,

    // Test parameters
    pub target_frequency: f64,  // Hz (typical: 0.2-0.5)
    pub target_amplitude: f64,  // Degrees

    pub is_normal: bool,
    pub clinical_notes: Option<String>,
}

// ============================================
// OKN (Optokinetic Nystagmus) Test Types
// ============================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OKNMetrics {
    pub gain: f64,           // Nystagmus gain
    pub spv: f64,            // Average Slow Phase Velocity (°/s)
    pub beat_frequency: f64, // Beat frequency (Hz)
}

impl Default for OKNMetrics {
    fn default() -> Self {
        Self {
            gain: 1.0,
            spv: 0.0,
            beat_frequency: 0.0,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OKNVelocityResult {
    pub stimulus_velocity: f64, // °/s (20, 40, 60)
    pub left: OKNMetrics,
    pub right: OKNMetrics,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OKNTestResult {
    pub id: Option<i64>,
    pub session_id: i64,
    pub test_date: String,

    // Metrics by velocity and direction
    pub velocities: Vec<OKNVelocityResult>,

    // Total asymmetry
    pub directional_preponderance: f64, // % (+ = right)

    pub is_normal: bool,
    pub clinical_notes: Option<String>,
}
