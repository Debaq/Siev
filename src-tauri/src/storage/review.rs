use std::fs;
use std::io::{BufRead, BufReader};
use std::path::Path;
use serde::{Serialize, Deserialize};
use crate::math::processor::{ProcessedEyeData, CalibrationSnapshot};
use crate::storage::bundle::{SievBundle, SessionManifest};

// ============================================
// Serializable structs for the frontend
// ============================================

/// Downsampled eye data point for charts
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChartEyeDataPoint {
    pub t: f64,
    pub lx: Option<f64>,
    pub ly: Option<f64>,
    pub rx: Option<f64>,
    pub ry: Option<f64>,
}

/// Saccade marker
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SaccadeMarker {
    pub start_time: f64,
    pub end_time: f64,
    pub amplitude: f64,
    pub peak_velocity: f64,
    pub duration_ms: f64,
    pub direction: String,
}

/// SPV time point
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SPVTimePoint {
    pub time: f64,
    pub spv: f64,
}

/// Nystagmus beat marker
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NystagmusBeatMarker {
    pub slow_start: f64,
    pub slow_end: f64,
    pub fast_end: f64,
    pub spv: f64,
    pub amplitude: f64,
}

/// Full session review payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionReviewPayload {
    pub session_id: i64,
    pub manifest: SessionManifest,
    pub calibration: Option<CalibrationSnapshot>,
    pub duration_seconds: f64,
    pub sample_rate_hz: f64,
    pub total_samples: usize,
    pub video_url: Option<String>,
    pub video_available: bool,
    pub eye_data: Vec<ChartEyeDataPoint>,
    pub saccades: Vec<SaccadeMarker>,
    pub spv_timeline: Vec<SPVTimePoint>,
    pub nystagmus_beats: Vec<NystagmusBeatMarker>,
    pub overall_spv: f64,
    pub pursuit_gain: Option<f64>,
}

// ============================================
// Data loading
// ============================================

/// Load eye data from data.bin (JSONL format)
pub fn load_eye_data(path: &Path) -> Result<Vec<ProcessedEyeData>, String> {
    let file = fs::File::open(path).map_err(|e| format!("Failed to open data file: {}", e))?;
    let reader = BufReader::new(file);
    let mut data = Vec::new();

    for line in reader.lines() {
        let line = line.map_err(|e| format!("Failed to read line: {}", e))?;
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        match serde_json::from_str::<ProcessedEyeData>(trimmed) {
            Ok(point) => data.push(point),
            Err(_) => continue, // Skip malformed lines
        }
    }

    Ok(data)
}

/// Load eye data within a time range
pub fn load_eye_data_window(
    path: &Path,
    start_time: f64,
    end_time: f64,
) -> Result<Vec<ProcessedEyeData>, String> {
    let all_data = load_eye_data(path)?;
    let base_ts = all_data.first().map(|d| d.timestamp).unwrap_or(0.0);

    Ok(all_data
        .into_iter()
        .filter(|d| {
            let t = d.timestamp - base_ts;
            t >= start_time && t <= end_time
        })
        .collect())
}

// ============================================
// LTTB Downsampling
// ============================================

/// Largest Triangle Three Buckets downsampling
/// Takes (time, value) pairs and returns downsampled version
pub fn downsample_lttb(data: &[(f64, f64)], target: usize) -> Vec<(f64, f64)> {
    let n = data.len();
    if n <= target || target < 3 {
        return data.to_vec();
    }

    let mut result = Vec::with_capacity(target);

    // Always keep first point
    result.push(data[0]);

    let bucket_size = (n - 2) as f64 / (target - 2) as f64;

    let mut prev_idx = 0usize;

    for i in 0..(target - 2) {
        // Calculate bucket range
        let bucket_start = ((i as f64 + 1.0) * bucket_size) as usize + 1;
        let bucket_end = (((i as f64 + 2.0) * bucket_size) as usize + 1).min(n - 1);

        // Calculate average point of next bucket
        let next_bucket_start = bucket_end;
        let next_bucket_end = (((i as f64 + 3.0) * bucket_size) as usize + 1).min(n);
        let mut avg_x = 0.0;
        let mut avg_y = 0.0;
        let count = (next_bucket_end - next_bucket_start).max(1);
        for j in next_bucket_start..next_bucket_end.min(n) {
            avg_x += data[j].0;
            avg_y += data[j].1;
        }
        avg_x /= count as f64;
        avg_y /= count as f64;

        // Find point in current bucket with largest triangle area
        let mut max_area = -1.0f64;
        let mut max_idx = bucket_start;

        let (px, py) = data[prev_idx];

        for j in bucket_start..bucket_end.min(n) {
            let area = ((px - avg_x) * (data[j].1 - py)
                - (px - data[j].0) * (avg_y - py))
                .abs();
            if area > max_area {
                max_area = area;
                max_idx = j;
            }
        }

        result.push(data[max_idx]);
        prev_idx = max_idx;
    }

    // Always keep last point
    result.push(data[n - 1]);

    result
}

/// Convert ProcessedEyeData to ChartEyeDataPoint with LTTB downsampling
fn to_chart_data(data: &[ProcessedEyeData], max_points: usize) -> Vec<ChartEyeDataPoint> {
    if data.is_empty() {
        return Vec::new();
    }

    let base_ts = data[0].timestamp;

    if data.len() <= max_points {
        return data
            .iter()
            .map(|d| ChartEyeDataPoint {
                t: d.timestamp - base_ts,
                lx: d.left.map(|l| l[0]),
                ly: d.left.map(|l| l[1]),
                rx: d.right.map(|r| r[0]),
                ry: d.right.map(|r| r[1]),
            })
            .collect();
    }

    // Build time series for each channel and downsample independently,
    // then merge back. For simplicity, downsample based on horizontal position
    // (most clinically relevant) of right eye, then sample all channels at those indices.

    // Build index-based LTTB on right eye X (or left if right is missing)
    let time_vals: Vec<(f64, f64)> = data
        .iter()
        .map(|d| {
            let t = d.timestamp - base_ts;
            let v = d.right.map(|r| r[0])
                .or_else(|| d.left.map(|l| l[0]))
                .unwrap_or(0.0);
            (t, v)
        })
        .collect();

    let downsampled = downsample_lttb(&time_vals, max_points);

    // Build a set of target times for lookup
    let target_times: Vec<f64> = downsampled.iter().map(|(t, _)| *t).collect();

    // For each target time, find the closest original sample
    let mut result = Vec::with_capacity(target_times.len());
    let mut search_start = 0;

    for target_t in &target_times {
        // Linear scan from last position (data is sorted by time)
        let mut best_idx = search_start;
        let mut best_diff = (data[search_start].timestamp - base_ts - target_t).abs();

        for i in (search_start + 1)..data.len() {
            let diff = (data[i].timestamp - base_ts - target_t).abs();
            if diff < best_diff {
                best_diff = diff;
                best_idx = i;
            } else if diff > best_diff {
                break; // Past the closest point
            }
        }

        search_start = best_idx;
        let d = &data[best_idx];
        result.push(ChartEyeDataPoint {
            t: d.timestamp - base_ts,
            lx: d.left.map(|l| l[0]),
            ly: d.left.map(|l| l[1]),
            rx: d.right.map(|r| r[0]),
            ry: d.right.map(|r| r[1]),
        });
    }

    result
}

// ============================================
// SPV computation
// ============================================

/// Compute Slow Phase Velocity timeline using sliding window
pub fn compute_spv_timeline(
    data: &[ProcessedEyeData],
    window_secs: f64,
    step_secs: f64,
    saccade_threshold: f64,
) -> Vec<SPVTimePoint> {
    if data.len() < 2 {
        return Vec::new();
    }

    let base_ts = data[0].timestamp;
    let total_duration = data.last().unwrap().timestamp - base_ts;

    // Compute instantaneous velocities
    let mut velocities: Vec<(f64, f64)> = Vec::with_capacity(data.len());
    for i in 1..data.len() {
        let dt = data[i].timestamp - data[i - 1].timestamp;
        if dt <= 0.0 {
            continue;
        }

        // Use horizontal component of right eye (or left)
        let pos_curr = data[i].right.map(|r| r[0])
            .or_else(|| data[i].left.map(|l| l[0]));
        let pos_prev = data[i - 1].right.map(|r| r[0])
            .or_else(|| data[i - 1].left.map(|l| l[0]));

        if let (Some(curr), Some(prev)) = (pos_curr, pos_prev) {
            let vel = (curr - prev) / dt;
            let t = data[i].timestamp - base_ts;
            velocities.push((t, vel));
        }
    }

    if velocities.is_empty() {
        return Vec::new();
    }

    // Sliding window SPV computation
    let mut spv_points = Vec::new();
    let mut t = 0.0;

    while t <= total_duration {
        let window_start = t - window_secs / 2.0;
        let window_end = t + window_secs / 2.0;

        // Collect velocities in window, excluding saccades
        let slow_vels: Vec<f64> = velocities
            .iter()
            .filter(|(vt, _)| *vt >= window_start && *vt <= window_end)
            .filter(|(_, v)| v.abs() < saccade_threshold)
            .map(|(_, v)| *v)
            .collect();

        if !slow_vels.is_empty() {
            let mean_spv = slow_vels.iter().sum::<f64>() / slow_vels.len() as f64;
            spv_points.push(SPVTimePoint {
                time: t,
                spv: mean_spv,
            });
        }

        t += step_secs;
    }

    spv_points
}

// ============================================
// Saccade detection
// ============================================

/// Simple velocity-threshold saccade detection
pub fn detect_saccades(
    data: &[ProcessedEyeData],
    velocity_threshold: f64,
    min_duration_ms: f64,
) -> Vec<SaccadeMarker> {
    if data.len() < 3 {
        return Vec::new();
    }

    let base_ts = data[0].timestamp;
    let mut saccades = Vec::new();

    // Compute velocities
    let mut velocities: Vec<(f64, f64, f64)> = Vec::new(); // (time, velocity, position)
    for i in 1..data.len() {
        let dt = data[i].timestamp - data[i - 1].timestamp;
        if dt <= 0.0 {
            continue;
        }

        let pos_curr = data[i].right.map(|r| r[0])
            .or_else(|| data[i].left.map(|l| l[0]));
        let pos_prev = data[i - 1].right.map(|r| r[0])
            .or_else(|| data[i - 1].left.map(|l| l[0]));

        if let (Some(curr), Some(prev)) = (pos_curr, pos_prev) {
            let vel = (curr - prev) / dt;
            let t = data[i].timestamp - base_ts;
            velocities.push((t, vel, curr));
        }
    }

    // Find saccade segments
    let mut in_saccade = false;
    let mut saccade_start = 0usize;
    let mut peak_vel = 0.0f64;
    let mut start_pos = 0.0f64;

    for i in 0..velocities.len() {
        let (_, vel, pos) = velocities[i];
        let abs_vel = vel.abs();

        if !in_saccade && abs_vel > velocity_threshold {
            in_saccade = true;
            saccade_start = i;
            peak_vel = abs_vel;
            start_pos = pos;
        } else if in_saccade {
            if abs_vel > peak_vel {
                peak_vel = abs_vel;
            }
            if abs_vel < velocity_threshold {
                // End of saccade
                let start_time = velocities[saccade_start].0;
                let end_time = velocities[i].0;
                let duration = (end_time - start_time) * 1000.0;
                let end_pos = pos;
                let amplitude = (end_pos - start_pos).abs();

                if duration >= min_duration_ms && amplitude > 0.5 {
                    let direction = if end_pos > start_pos {
                        "right".to_string()
                    } else {
                        "left".to_string()
                    };

                    saccades.push(SaccadeMarker {
                        start_time,
                        end_time,
                        amplitude,
                        peak_velocity: peak_vel,
                        duration_ms: duration,
                        direction,
                    });
                }

                in_saccade = false;
            }
        }
    }

    saccades
}

// ============================================
// Nystagmus beat detection
// ============================================

/// Detect nystagmus beats (slow phase + fast phase = one beat)
pub fn detect_nystagmus_beats(
    data: &[ProcessedEyeData],
    saccade_threshold: f64,
) -> Vec<NystagmusBeatMarker> {
    if data.len() < 3 {
        return Vec::new();
    }

    let base_ts = data[0].timestamp;
    let mut beats = Vec::new();

    // Compute velocities
    let mut velocities: Vec<(f64, f64, f64)> = Vec::new();
    for i in 1..data.len() {
        let dt = data[i].timestamp - data[i - 1].timestamp;
        if dt <= 0.0 {
            continue;
        }

        let pos_curr = data[i].right.map(|r| r[0])
            .or_else(|| data[i].left.map(|l| l[0]));
        let pos_prev = data[i - 1].right.map(|r| r[0])
            .or_else(|| data[i - 1].left.map(|l| l[0]));

        if let (Some(curr), Some(prev)) = (pos_curr, pos_prev) {
            let vel = (curr - prev) / dt;
            let t = data[i].timestamp - base_ts;
            velocities.push((t, vel, curr));
        }
    }

    // Segment into slow and fast phases
    let mut slow_start: Option<usize> = None;
    let mut slow_vel_sum = 0.0f64;
    let mut slow_count = 0usize;

    for i in 0..velocities.len() {
        let (_, vel, _) = velocities[i];
        let abs_vel = vel.abs();

        if abs_vel < saccade_threshold {
            // Slow phase
            if slow_start.is_none() {
                slow_start = Some(i);
                slow_vel_sum = 0.0;
                slow_count = 0;
            }
            slow_vel_sum += vel;
            slow_count += 1;
        } else if let Some(ss) = slow_start {
            // Fast phase detected - this could be end of a beat
            if slow_count > 2 {
                let spv = slow_vel_sum / slow_count as f64;
                let slow_end_idx = i - 1;

                // Find end of fast phase
                let mut fast_end_idx = i;
                for j in (i + 1)..velocities.len() {
                    if velocities[j].1.abs() < saccade_threshold {
                        fast_end_idx = j;
                        break;
                    }
                    fast_end_idx = j;
                }

                let amplitude = (velocities[fast_end_idx].2 - velocities[slow_end_idx].2).abs();

                if amplitude > 0.3 {
                    beats.push(NystagmusBeatMarker {
                        slow_start: velocities[ss].0,
                        slow_end: velocities[slow_end_idx].0,
                        fast_end: velocities[fast_end_idx].0,
                        spv,
                        amplitude,
                    });
                }
            }
            slow_start = None;
        }
    }

    beats
}

// ============================================
// Main builder
// ============================================

/// Build the complete session review payload
pub fn build_session_review(
    bundle_path: &Path,
    session_id: i64,
    max_points: usize,
) -> Result<SessionReviewPayload, String> {
    // Load manifest
    let manifest = SievBundle::load_manifest(bundle_path)
        .map_err(|e| format!("Failed to load manifest: {}", e))?;

    // Load calibration (optional)
    let calibration = SievBundle::load_calibration(bundle_path).ok();

    // Load eye data
    let data_path = bundle_path.join("data.bin");
    let raw_data = if data_path.exists() {
        load_eye_data(&data_path)?
    } else {
        Vec::new()
    };

    let total_samples = raw_data.len();

    // Compute timing
    let (duration_seconds, sample_rate_hz) = if raw_data.len() >= 2 {
        let first_ts = raw_data.first().unwrap().timestamp;
        let last_ts = raw_data.last().unwrap().timestamp;
        let dur = last_ts - first_ts;
        let rate = if dur > 0.0 {
            (raw_data.len() as f64 - 1.0) / dur
        } else {
            0.0
        };
        (dur, rate)
    } else {
        (0.0, 0.0)
    };

    // Downsample for charts
    let eye_data = to_chart_data(&raw_data, max_points);

    // Detect saccades (velocity threshold 80 deg/s, min duration 10ms)
    let saccades = detect_saccades(&raw_data, 80.0, 10.0);

    // Compute SPV timeline (2s window, 0.5s step, 80 deg/s saccade threshold)
    let spv_timeline = compute_spv_timeline(&raw_data, 2.0, 0.5, 80.0);

    // Detect nystagmus beats
    let nystagmus_beats = detect_nystagmus_beats(&raw_data, 80.0);

    // Overall SPV
    let overall_spv = if !spv_timeline.is_empty() {
        spv_timeline.iter().map(|p| p.spv.abs()).sum::<f64>() / spv_timeline.len() as f64
    } else {
        0.0
    };

    // Check video availability
    let video_path = bundle_path.join("video").join("playback.mp4");
    let raw_video_path = bundle_path.join("video").join("raw_capture.mp4");
    let video_available = video_path.exists() || raw_video_path.exists();

    Ok(SessionReviewPayload {
        session_id,
        manifest,
        calibration,
        duration_seconds,
        sample_rate_hz,
        total_samples,
        video_url: None, // Set by the command handler after asset conversion
        video_available,
        eye_data,
        saccades,
        spv_timeline,
        nystagmus_beats,
        overall_spv,
        pursuit_gain: None, // Computed if pursuit test data available
    })
}

/// Build payload with recalibrated data
pub fn build_recalibrated_review(
    bundle_path: &Path,
    session_id: i64,
    max_points: usize,
    new_calibration: &CalibrationSnapshot,
    old_calibration: &CalibrationSnapshot,
) -> Result<SessionReviewPayload, String> {
    // Load raw data
    let data_path = bundle_path.join("data.bin");
    let mut raw_data = if data_path.exists() {
        load_eye_data(&data_path)?
    } else {
        return Err("No data file found".to_string());
    };

    // Apply relative correction: new_deg = old_deg * (new_scale / old_scale)
    let scale_ratio_lx = if old_calibration.left_scale[0].abs() > 1e-9 {
        new_calibration.left_scale[0] / old_calibration.left_scale[0]
    } else { 1.0 };
    let scale_ratio_ly = if old_calibration.left_scale[1].abs() > 1e-9 {
        new_calibration.left_scale[1] / old_calibration.left_scale[1]
    } else { 1.0 };
    let scale_ratio_rx = if old_calibration.right_scale[0].abs() > 1e-9 {
        new_calibration.right_scale[0] / old_calibration.right_scale[0]
    } else { 1.0 };
    let scale_ratio_ry = if old_calibration.right_scale[1].abs() > 1e-9 {
        new_calibration.right_scale[1] / old_calibration.right_scale[1]
    } else { 1.0 };

    for sample in &mut raw_data {
        if let Some(ref mut left) = sample.left {
            left[0] *= scale_ratio_lx;
            left[1] *= scale_ratio_ly;
        }
        if let Some(ref mut right) = sample.right {
            right[0] *= scale_ratio_rx;
            right[1] *= scale_ratio_ry;
        }
    }

    // Now compute everything from corrected data
    let manifest = SievBundle::load_manifest(bundle_path)
        .map_err(|e| format!("Failed to load manifest: {}", e))?;

    let total_samples = raw_data.len();
    let (duration_seconds, sample_rate_hz) = if raw_data.len() >= 2 {
        let first_ts = raw_data.first().unwrap().timestamp;
        let last_ts = raw_data.last().unwrap().timestamp;
        let dur = last_ts - first_ts;
        let rate = if dur > 0.0 { (raw_data.len() as f64 - 1.0) / dur } else { 0.0 };
        (dur, rate)
    } else {
        (0.0, 0.0)
    };

    let eye_data = to_chart_data(&raw_data, max_points);
    let saccades = detect_saccades(&raw_data, 80.0, 10.0);
    let spv_timeline = compute_spv_timeline(&raw_data, 2.0, 0.5, 80.0);
    let nystagmus_beats = detect_nystagmus_beats(&raw_data, 80.0);
    let overall_spv = if !spv_timeline.is_empty() {
        spv_timeline.iter().map(|p| p.spv.abs()).sum::<f64>() / spv_timeline.len() as f64
    } else {
        0.0
    };

    let video_path = bundle_path.join("video").join("playback.mp4");
    let raw_video_path = bundle_path.join("video").join("raw_capture.mp4");
    let video_available = video_path.exists() || raw_video_path.exists();

    Ok(SessionReviewPayload {
        session_id,
        manifest,
        calibration: Some(new_calibration.clone()),
        duration_seconds,
        sample_rate_hz,
        total_samples,
        video_url: None,
        video_available,
        eye_data,
        saccades,
        spv_timeline,
        nystagmus_beats,
        overall_spv,
        pursuit_gain: None,
    })
}
