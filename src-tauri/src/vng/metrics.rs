use crate::math::processor::ProcessedEyeData;

// ============================================
// Helper Functions
// ============================================

/// Extract horizontal position from eye data (prefers left eye, falls back to right)
fn get_horizontal_pos(data: &ProcessedEyeData) -> Option<f64> {
    data.left.map(|arr| arr[0])
        .or_else(|| data.right.map(|arr| arr[0]))
}

// ============================================
// Saccade Detection
// ============================================

#[derive(Debug, Clone)]
pub struct SaccadeEvent {
    pub start_time: f64,
    pub end_time: f64,
    pub start_position: f64,
    pub end_position: f64,
    pub peak_velocity: f64,
    pub amplitude: f64,
    pub duration_ms: f64,
}

/// Detect saccades by velocity threshold
/// Returns a list of detected saccade events
pub fn detect_saccades(data: &[ProcessedEyeData], threshold: f64) -> Vec<SaccadeEvent> {
    let mut saccades = Vec::new();

    if data.len() < 3 {
        return saccades;
    }

    let mut in_saccade = false;
    let mut saccade_start_idx = 0;
    let mut peak_velocity: f64 = 0.0;
    let mut prev_pos: Option<f64> = None;

    for i in 0..data.len() {
        let curr_pos = match get_horizontal_pos(&data[i]) {
            Some(p) => p,
            None => continue,
        };

        if i == 0 {
            prev_pos = Some(curr_pos);
            continue;
        }

        let dt = data[i].timestamp - data[i - 1].timestamp;
        if dt <= 0.0 {
            prev_pos = Some(curr_pos);
            continue;
        }

        let prev = prev_pos.unwrap_or(curr_pos);
        let velocity = ((curr_pos - prev) / dt).abs();

        if velocity > threshold {
            if !in_saccade {
                in_saccade = true;
                saccade_start_idx = i - 1;
                peak_velocity = velocity;
            } else {
                peak_velocity = peak_velocity.max(velocity);
            }
        } else if in_saccade {
            in_saccade = false;

            if let (Some(start_pos), Some(end_pos)) = (
                get_horizontal_pos(&data[saccade_start_idx]),
                get_horizontal_pos(&data[i])
            ) {
                let amplitude = (end_pos - start_pos).abs();
                let duration_ms = (data[i].timestamp - data[saccade_start_idx].timestamp) * 1000.0;

                if amplitude > 1.0 && duration_ms > 10.0 {
                    saccades.push(SaccadeEvent {
                        start_time: data[saccade_start_idx].timestamp,
                        end_time: data[i].timestamp,
                        start_position: start_pos,
                        end_position: end_pos,
                        peak_velocity,
                        amplitude,
                        duration_ms,
                    });
                }
            }
        }

        prev_pos = Some(curr_pos);
    }

    saccades
}

// ============================================
// SPV (Slow Phase Velocity) Calculation
// ============================================

/// Calculate Slow Phase Velocity from eye tracking data
/// Uses median of velocities during slow phases (non-saccadic)
pub fn calculate_spv(data: &[ProcessedEyeData], saccade_threshold: f64) -> f64 {
    if data.len() < 2 {
        return 0.0;
    }

    let mut slow_phase_velocities: Vec<f64> = Vec::new();
    let mut prev_pos: Option<f64> = None;

    for i in 0..data.len() {
        let curr_pos = match get_horizontal_pos(&data[i]) {
            Some(p) => p,
            None => continue,
        };

        if i == 0 {
            prev_pos = Some(curr_pos);
            continue;
        }

        let dt = data[i].timestamp - data[i - 1].timestamp;
        if dt <= 0.0 {
            prev_pos = Some(curr_pos);
            continue;
        }

        let prev = prev_pos.unwrap_or(curr_pos);
        let velocity = (curr_pos - prev) / dt;

        if velocity.abs() < saccade_threshold {
            slow_phase_velocities.push(velocity);
        }

        prev_pos = Some(curr_pos);
    }

    if slow_phase_velocities.is_empty() {
        return 0.0;
    }

    slow_phase_velocities.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let mid = slow_phase_velocities.len() / 2;

    if slow_phase_velocities.len() % 2 == 0 {
        (slow_phase_velocities[mid - 1] + slow_phase_velocities[mid]) / 2.0
    } else {
        slow_phase_velocities[mid]
    }
}

// ============================================
// Jongkees Formulas
// ============================================

/// Calculate Jongkees formulas for caloric test analysis
/// Returns (UW%, DP%) tuple
///
/// UW (Unilateral Weakness) = ((RW + RC) - (LW + LC)) / (RW + RC + LW + LC) × 100
/// DP (Directional Preponderance) = ((RW + LC) - (LW + RC)) / (RW + RC + LW + LC) × 100
///
/// Positive UW indicates right ear weakness
/// Positive DP indicates right-beating preponderance
pub fn calculate_jongkees(rw: f64, rc: f64, lw: f64, lc: f64) -> (f64, f64) {
    let total = rw + rc + lw + lc;

    if total == 0.0 {
        return (0.0, 0.0);
    }

    let uw_percent = ((rw + rc) - (lw + lc)) / total * 100.0;
    let dp_percent = ((rw + lc) - (lw + rc)) / total * 100.0;

    (uw_percent, dp_percent)
}

// ============================================
// Pursuit Gain Calculation
// ============================================

/// Calculate pursuit gain from eye and target velocities
/// Gain = eye_velocity / target_velocity
pub fn calculate_pursuit_gain(eye_vel: f64, target_vel: f64) -> f64 {
    if target_vel.abs() < 0.001 {
        return 0.0;
    }
    eye_vel / target_vel
}

/// Calculate average pursuit gain from eye tracking data and target motion
pub fn calculate_pursuit_gain_from_data(
    eye_data: &[ProcessedEyeData],
    target_positions: &[(f64, f64)], // (time, position)
    saccade_threshold: f64,
) -> f64 {
    if eye_data.len() < 2 || target_positions.len() < 2 {
        return 0.0;
    }

    let mut gains: Vec<f64> = Vec::new();
    let mut prev_eye_pos: Option<f64> = None;

    for i in 1..eye_data.len().min(target_positions.len()) {
        let curr_eye_pos = match get_horizontal_pos(&eye_data[i]) {
            Some(p) => p,
            None => continue,
        };

        if prev_eye_pos.is_none() {
            prev_eye_pos = get_horizontal_pos(&eye_data[i - 1]);
            if prev_eye_pos.is_none() {
                continue;
            }
        }

        let dt_eye = eye_data[i].timestamp - eye_data[i - 1].timestamp;
        let dt_target = target_positions[i].0 - target_positions[i - 1].0;

        if dt_eye <= 0.0 || dt_target <= 0.0 {
            prev_eye_pos = Some(curr_eye_pos);
            continue;
        }

        let prev = prev_eye_pos.unwrap();
        let eye_vel = (curr_eye_pos - prev) / dt_eye;
        let target_vel = (target_positions[i].1 - target_positions[i - 1].1) / dt_target;

        if eye_vel.abs() < saccade_threshold && target_vel.abs() > 1.0 {
            let gain = calculate_pursuit_gain(eye_vel, target_vel);
            if gain > 0.0 && gain < 2.0 {
                gains.push(gain);
            }
        }

        prev_eye_pos = Some(curr_eye_pos);
    }

    if gains.is_empty() {
        return 0.0;
    }

    gains.iter().sum::<f64>() / gains.len() as f64
}

// ============================================
// Fixation Index
// ============================================

/// Calculate fixation index (suppression of nystagmus with fixation)
/// FI = (SPV_dark - SPV_fixation) / SPV_dark × 100
/// Normal: > 60%
pub fn calculate_fixation_index(spv_dark: f64, spv_fixation: f64) -> f64 {
    if spv_dark.abs() < 0.1 {
        return 100.0;
    }

    ((spv_dark.abs() - spv_fixation.abs()) / spv_dark.abs()) * 100.0
}

// ============================================
// Nystagmus Beat Analysis
// ============================================

#[derive(Debug, Clone)]
pub struct NystagmusBeat {
    pub slow_phase_start: f64,
    pub slow_phase_end: f64,
    pub fast_phase_end: f64,
    pub slow_phase_velocity: f64,
    pub amplitude: f64,
}

/// Analyze nystagmus beats from eye tracking data
pub fn analyze_nystagmus_beats(
    data: &[ProcessedEyeData],
    slow_threshold: f64,
    fast_threshold: f64,
) -> Vec<NystagmusBeat> {
    let mut beats = Vec::new();

    if data.len() < 3 {
        return beats;
    }

    let mut in_slow_phase = false;
    let mut slow_start_idx = 0;
    let mut slow_velocities: Vec<f64> = Vec::new();
    let mut prev_pos: Option<f64> = None;

    for i in 0..data.len() {
        let curr_pos = match get_horizontal_pos(&data[i]) {
            Some(p) => p,
            None => continue,
        };

        if i == 0 {
            prev_pos = Some(curr_pos);
            continue;
        }

        let dt = data[i].timestamp - data[i - 1].timestamp;
        if dt <= 0.0 {
            prev_pos = Some(curr_pos);
            continue;
        }

        let prev = prev_pos.unwrap_or(curr_pos);
        let velocity = (curr_pos - prev) / dt;
        let abs_vel = velocity.abs();

        if abs_vel < slow_threshold {
            if !in_slow_phase {
                in_slow_phase = true;
                slow_start_idx = i - 1;
                slow_velocities.clear();
            }
            slow_velocities.push(velocity);
        } else if abs_vel > fast_threshold && in_slow_phase {
            in_slow_phase = false;

            if !slow_velocities.is_empty() {
                let avg_slow_vel =
                    slow_velocities.iter().sum::<f64>() / slow_velocities.len() as f64;

                if let (Some(start_pos), Some(end_pos)) = (
                    get_horizontal_pos(&data[slow_start_idx]),
                    get_horizontal_pos(&data[i - 1])
                ) {
                    let amplitude = (end_pos - start_pos).abs();

                    if amplitude > 0.5 {
                        beats.push(NystagmusBeat {
                            slow_phase_start: data[slow_start_idx].timestamp,
                            slow_phase_end: data[i - 1].timestamp,
                            fast_phase_end: data[i].timestamp,
                            slow_phase_velocity: avg_slow_vel,
                            amplitude,
                        });
                    }
                }
            }
        }

        prev_pos = Some(curr_pos);
    }

    beats
}

// ============================================
// Reference Values
// ============================================

#[derive(Debug, Clone)]
pub struct ReferenceValue {
    pub test_type: String,
    pub metric_name: String,
    pub min_normal: f64,
    pub max_normal: f64,
    pub unit: String,
    pub age_group: Option<String>,
}

/// Get default reference values for VNG tests
pub fn get_default_reference_values() -> Vec<ReferenceValue> {
    vec![
        ReferenceValue {
            test_type: "saccade".into(),
            metric_name: "latency".into(),
            min_normal: 150.0,
            max_normal: 250.0,
            unit: "ms".into(),
            age_group: None,
        },
        ReferenceValue {
            test_type: "saccade".into(),
            metric_name: "peak_velocity".into(),
            min_normal: 300.0,
            max_normal: 600.0,
            unit: "°/s".into(),
            age_group: None,
        },
        ReferenceValue {
            test_type: "saccade".into(),
            metric_name: "accuracy".into(),
            min_normal: 80.0,
            max_normal: 100.0,
            unit: "%".into(),
            age_group: None,
        },
        ReferenceValue {
            test_type: "pursuit".into(),
            metric_name: "gain".into(),
            min_normal: 0.8,
            max_normal: 1.0,
            unit: "".into(),
            age_group: None,
        },
        ReferenceValue {
            test_type: "caloric".into(),
            metric_name: "spv_max".into(),
            min_normal: 6.0,
            max_normal: 80.0,
            unit: "°/s".into(),
            age_group: None,
        },
        ReferenceValue {
            test_type: "caloric".into(),
            metric_name: "unilateral_weakness".into(),
            min_normal: -22.0,
            max_normal: 22.0,
            unit: "%".into(),
            age_group: None,
        },
        ReferenceValue {
            test_type: "caloric".into(),
            metric_name: "directional_preponderance".into(),
            min_normal: -28.0,
            max_normal: 28.0,
            unit: "%".into(),
            age_group: None,
        },
        ReferenceValue {
            test_type: "caloric".into(),
            metric_name: "fixation_index".into(),
            min_normal: 60.0,
            max_normal: 100.0,
            unit: "%".into(),
            age_group: None,
        },
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_jongkees_normal() {
        let (uw, dp) = calculate_jongkees(20.0, 15.0, 18.0, 17.0);
        assert!(uw.abs() < 25.0);
        assert!(dp.abs() < 30.0);
    }

    #[test]
    fn test_jongkees_unilateral_weakness() {
        let (uw, _dp) = calculate_jongkees(5.0, 5.0, 20.0, 20.0);
        assert!(uw < -30.0);
    }

    #[test]
    fn test_pursuit_gain() {
        let gain = calculate_pursuit_gain(45.0, 50.0);
        assert!((gain - 0.9).abs() < 0.01);
    }

    #[test]
    fn test_fixation_index() {
        let fi = calculate_fixation_index(10.0, 3.0);
        assert!((fi - 70.0).abs() < 0.1);
    }
}
