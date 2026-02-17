use std::collections::VecDeque;
use serde::{Serialize, Deserialize};

/// A single nystagmus beat: one slow phase + one fast phase
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NystagmusBeat {
    pub slow_start_time: f64,
    pub slow_end_time: f64,
    /// Slow Phase Velocity (°/s) — THE clinically important number
    pub slow_velocity: f64,
    /// +1.0 = rightward/upward, -1.0 = leftward/downward
    pub slow_direction: f64,

    pub fast_start_time: f64,
    pub fast_end_time: f64,
    pub fast_velocity: f64,

    /// Total amplitude of the beat (degrees)
    pub amplitude: f64,
    /// Direction of the fast phase: "right", "left", "up", "down"
    pub direction: String,

    /// Deflection points (time, position) that bound this beat
    pub deflection_points: Vec<(f64, f64)>,
}

/// Result from batch analysis
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NystagmusResult {
    pub beats: Vec<NystagmusBeat>,
    pub deflection_points: Vec<(f64, f64)>,
    pub average_spv: f64,
    pub beat_count: usize,
}

/// A detected local extremum (peak or valley)
#[derive(Debug, Clone)]
struct Extremum {
    time: f64,
    position: f64,
}

/// A segment between two consecutive deflection points
#[derive(Debug, Clone)]
struct Segment {
    start_time: f64,
    start_pos: f64,
    end_time: f64,
    end_pos: f64,
    amplitude: f64,
    velocity: f64,   // signed: positive = rightward/upward
}

/// Stateful nystagmus analyzer supporting both real-time and batch processing.
///
/// The algorithm:
/// 1. Smooth the position signal (moving average)
/// 2. Detect local extrema (peaks and valleys)
/// 3. Filter by minimum prominence (min_amplitude)
/// 4. Between consecutive extrema, compute segments
/// 5. Pair consecutive opposite-direction segments: slower = slow phase, faster = fast phase
pub struct NystagmusAnalyzer {
    min_amplitude: f64,
    smooth_window: usize,

    // Buffer for incremental detection
    position_buffer: VecDeque<(f64, f64)>,
    smoothed_buffer: VecDeque<(f64, f64)>,
    deflection_points: Vec<(f64, f64)>,
    last_emitted_deflection: usize,

    // Accumulated stats
    beat_count: usize,
    spv_sum: f64,
}

impl NystagmusAnalyzer {
    pub fn new(min_amplitude: f64) -> Self {
        Self {
            min_amplitude,
            smooth_window: 5,
            position_buffer: VecDeque::new(),
            smoothed_buffer: VecDeque::new(),
            deflection_points: Vec::new(),
            last_emitted_deflection: 0,
            beat_count: 0,
            spv_sum: 0.0,
        }
    }

    /// Feed a single sample (real-time). Returns a beat if one was just completed.
    pub fn push_sample(&mut self, time: f64, position: f64) -> Option<NystagmusBeat> {
        self.position_buffer.push_back((time, position));

        // Need at least smooth_window samples to produce a smoothed value
        if self.position_buffer.len() < self.smooth_window {
            return None;
        }

        // Compute smoothed value for the center of the window
        let half = self.smooth_window / 2;
        let center_idx = self.position_buffer.len() - 1 - half;
        let start = if center_idx >= half { center_idx - half } else { 0 };
        let end = (center_idx + half + 1).min(self.position_buffer.len());
        let count = end - start;
        let sum_pos: f64 = (start..end).map(|i| self.position_buffer[i].1).sum();
        let smoothed_pos = sum_pos / count as f64;
        let smoothed_time = self.position_buffer[center_idx].0;

        self.smoothed_buffer.push_back((smoothed_time, smoothed_pos));

        // Need at least 3 smoothed points to detect an extremum
        if self.smoothed_buffer.len() < 3 {
            return None;
        }

        let n = self.smoothed_buffer.len();
        let prev = self.smoothed_buffer[n - 3];
        let curr = self.smoothed_buffer[n - 2];
        let next = self.smoothed_buffer[n - 1];

        // Check if curr is a local extremum
        let is_peak = curr.1 > prev.1 && curr.1 > next.1;
        let is_valley = curr.1 < prev.1 && curr.1 < next.1;

        if !is_peak && !is_valley {
            return None;
        }

        // Check prominence against last deflection
        if let Some(last_defl) = self.deflection_points.last() {
            let prominence = (curr.1 - last_defl.1).abs();
            if prominence < self.min_amplitude {
                return None;
            }
        }

        self.deflection_points.push((curr.0, curr.1));

        // Try to form a beat from the last 3 deflection points
        self.try_emit_beat()
    }

    /// Try to emit a beat from recent deflection points
    fn try_emit_beat(&mut self) -> Option<NystagmusBeat> {
        let n = self.deflection_points.len();
        if n < 3 {
            return None;
        }

        // We need 3 points to form 2 segments
        let p0 = self.deflection_points[n - 3];
        let p1 = self.deflection_points[n - 2];
        let p2 = self.deflection_points[n - 1];

        let seg1 = make_segment(p0, p1)?;
        let seg2 = make_segment(p1, p2)?;

        // Segments must go in opposite directions
        if seg1.velocity.signum() == seg2.velocity.signum() {
            return None;
        }

        let beat = classify_beat(&seg1, &seg2, &[p0, p1, p2]);
        self.beat_count += 1;
        self.spv_sum += beat.slow_velocity.abs();

        Some(beat)
    }

    /// Analyze a complete dataset in batch mode
    pub fn analyze_batch(data: &[(f64, f64)], min_amplitude: f64) -> NystagmusResult {
        if data.len() < 5 {
            return NystagmusResult {
                beats: Vec::new(),
                deflection_points: Vec::new(),
                average_spv: 0.0,
                beat_count: 0,
            };
        }

        let smooth_window = 5;

        // 1. Smooth
        let smoothed = smooth_signal(data, smooth_window);

        // 2. Detect all local extrema
        let raw_extrema = detect_extrema(&smoothed);

        // 3. Filter by prominence
        let extrema = filter_by_prominence(&raw_extrema, min_amplitude);

        let deflection_points: Vec<(f64, f64)> = extrema.iter()
            .map(|e| (e.time, e.position))
            .collect();

        // 4. Build segments between consecutive deflection points
        if extrema.len() < 3 {
            return NystagmusResult {
                beats: Vec::new(),
                deflection_points,
                average_spv: 0.0,
                beat_count: 0,
            };
        }

        let mut segments: Vec<Segment> = Vec::new();
        for i in 0..extrema.len() - 1 {
            let p0 = (extrema[i].time, extrema[i].position);
            let p1 = (extrema[i + 1].time, extrema[i + 1].position);
            if let Some(seg) = make_segment(p0, p1) {
                segments.push(seg);
            }
        }

        // 5. Pair consecutive opposite-direction segments into beats
        let mut beats = Vec::new();
        let mut i = 0;
        while i + 1 < segments.len() {
            let seg1 = &segments[i];
            let seg2 = &segments[i + 1];

            // Must be opposite directions
            if seg1.velocity.signum() != seg2.velocity.signum() {
                let p0 = (seg1.start_time, seg1.start_pos);
                let p1 = (seg1.end_time, seg1.end_pos);
                let p2 = (seg2.end_time, seg2.end_pos);
                let beat = classify_beat(seg1, seg2, &[p0, p1, p2]);
                beats.push(beat);
                i += 2; // Skip both segments
            } else {
                i += 1;
            }
        }

        let beat_count = beats.len();
        let spv_sum: f64 = beats.iter().map(|b| b.slow_velocity.abs()).sum();
        let average_spv = if beat_count > 0 {
            spv_sum / beat_count as f64
        } else {
            0.0
        };

        NystagmusResult {
            beats,
            deflection_points,
            average_spv,
            beat_count,
        }
    }

    pub fn get_deflection_points(&self) -> &[(f64, f64)] {
        &self.deflection_points
    }

    pub fn get_beat_count(&self) -> usize {
        self.beat_count
    }

    pub fn get_average_spv(&self) -> f64 {
        if self.beat_count > 0 {
            self.spv_sum / self.beat_count as f64
        } else {
            0.0
        }
    }

    pub fn reset(&mut self) {
        self.position_buffer.clear();
        self.smoothed_buffer.clear();
        self.deflection_points.clear();
        self.last_emitted_deflection = 0;
        self.beat_count = 0;
        self.spv_sum = 0.0;
    }
}

// ============================================
// Helper functions
// ============================================

fn smooth_signal(data: &[(f64, f64)], window: usize) -> Vec<(f64, f64)> {
    let half = window / 2;
    let n = data.len();
    let mut result = Vec::with_capacity(n);

    for i in 0..n {
        let start = if i >= half { i - half } else { 0 };
        let end = (i + half + 1).min(n);
        let count = end - start;
        let sum: f64 = data[start..end].iter().map(|(_, v)| v).sum();
        result.push((data[i].0, sum / count as f64));
    }

    result
}

fn detect_extrema(data: &[(f64, f64)]) -> Vec<Extremum> {
    let mut extrema = Vec::new();

    for i in 1..data.len().saturating_sub(1) {
        let prev = data[i - 1].1;
        let curr = data[i].1;
        let next = data[i + 1].1;

        let is_peak = curr > prev && curr > next;
        let is_valley = curr < prev && curr < next;

        if is_peak || is_valley {
            extrema.push(Extremum {
                time: data[i].0,
                position: data[i].1,
            });
        }
    }

    extrema
}

/// Filter extrema by minimum prominence: consecutive peak-valley must differ by >= min_amplitude
fn filter_by_prominence(extrema: &[Extremum], min_amplitude: f64) -> Vec<Extremum> {
    if extrema.is_empty() {
        return Vec::new();
    }

    let mut filtered = vec![extrema[0].clone()];

    for i in 1..extrema.len() {
        let last = filtered.last().unwrap();
        let diff = (extrema[i].position - last.position).abs();

        if diff >= min_amplitude {
            filtered.push(extrema[i].clone());
        } else {
            // If this extremum is of the same type as the last one (both peaks or both valleys),
            // keep the more extreme one
            let last_is_peak = if filtered.len() >= 2 {
                filtered[filtered.len() - 1].position > filtered[filtered.len() - 2].position
            } else {
                true // assume first is a peak
            };

            let curr_higher = extrema[i].position > last.position;
            if (last_is_peak && curr_higher) || (!last_is_peak && !curr_higher) {
                // Replace the last with this more extreme one
                *filtered.last_mut().unwrap() = extrema[i].clone();
            }
        }
    }

    filtered
}

fn make_segment(p0: (f64, f64), p1: (f64, f64)) -> Option<Segment> {
    let duration = p1.0 - p0.0;
    if duration <= 0.001 {
        return None; // Too short, avoid division by zero
    }
    let amplitude = p1.1 - p0.1; // signed
    let velocity = amplitude / duration;

    Some(Segment {
        start_time: p0.0,
        start_pos: p0.1,
        end_time: p1.0,
        end_pos: p1.1,
        amplitude,
        velocity,
    })
}

/// Given two consecutive opposite-direction segments, classify which is slow and which is fast
fn classify_beat(seg1: &Segment, seg2: &Segment, points: &[(f64, f64)]) -> NystagmusBeat {
    let abs_vel1 = seg1.velocity.abs();
    let abs_vel2 = seg2.velocity.abs();

    let (slow, fast) = if abs_vel1 <= abs_vel2 {
        (seg1, seg2)
    } else {
        (seg2, seg1)
    };

    // Direction is named by the fast phase direction
    let direction = if fast.velocity > 0.0 {
        "right".to_string()
    } else {
        "left".to_string()
    };

    let slow_direction = if slow.velocity > 0.0 { 1.0 } else { -1.0 };
    let total_amplitude = slow.amplitude.abs().max(fast.amplitude.abs());

    NystagmusBeat {
        slow_start_time: slow.start_time,
        slow_end_time: slow.end_time,
        slow_velocity: slow.velocity,
        slow_direction,
        fast_start_time: fast.start_time,
        fast_end_time: fast.end_time,
        fast_velocity: fast.velocity,
        amplitude: total_amplitude,
        direction,
        deflection_points: points.to_vec(),
    }
}

// ============================================
// Tests
// ============================================

#[cfg(test)]
mod tests {
    use super::*;

    /// Generate synthetic nystagmus data: sawtooth pattern
    /// Slow rightward drift followed by fast leftward saccade
    fn generate_sawtooth(
        n_beats: usize,
        slow_vel: f64,       // deg/s (positive = rightward)
        fast_vel: f64,       // deg/s (negative = leftward)
        slow_duration: f64,  // seconds
        fast_duration: f64,  // seconds
        sample_rate: f64,    // Hz
    ) -> Vec<(f64, f64)> {
        let mut data = Vec::new();
        let mut t = 0.0;
        let mut pos = 0.0;
        let dt = 1.0 / sample_rate;

        for _ in 0..n_beats {
            // Slow phase
            let slow_samples = (slow_duration * sample_rate) as usize;
            for _ in 0..slow_samples {
                data.push((t, pos));
                pos += slow_vel * dt;
                t += dt;
            }
            // Fast phase
            let fast_samples = (fast_duration * sample_rate) as usize;
            for _ in 0..fast_samples {
                data.push((t, pos));
                pos += fast_vel * dt;
                t += dt;
            }
        }

        data
    }

    #[test]
    fn test_batch_detects_beats() {
        // 10 beats: slow rightward at 5°/s for 1s, fast leftward at -100°/s for 0.05s
        let data = generate_sawtooth(10, 5.0, -100.0, 1.0, 0.05, 200.0);
        let result = NystagmusAnalyzer::analyze_batch(&data, 0.5);

        assert!(result.beat_count > 0, "Should detect at least some beats");
        assert!(result.beat_count >= 5, "Should detect most of the 10 beats, got {}", result.beat_count);

        // SPV should be close to 5°/s
        for beat in &result.beats {
            let spv = beat.slow_velocity.abs();
            assert!(spv > 1.0 && spv < 15.0,
                "SPV should be roughly 5°/s, got {:.1}", spv);
        }

        assert!(result.average_spv > 1.0 && result.average_spv < 15.0,
            "Average SPV should be roughly 5°/s, got {:.1}", result.average_spv);
    }

    #[test]
    fn test_batch_leftward_nystagmus() {
        // Slow leftward, fast rightward
        let data = generate_sawtooth(8, -8.0, 150.0, 0.8, 0.04, 200.0);
        let result = NystagmusAnalyzer::analyze_batch(&data, 0.5);

        assert!(result.beat_count > 0, "Should detect beats");

        // Direction should be "right" (fast phase is rightward)
        for beat in &result.beats {
            assert_eq!(beat.direction, "right", "Fast phase should be rightward");
            assert!(beat.slow_velocity < 0.0, "Slow velocity should be negative (leftward)");
        }
    }

    #[test]
    fn test_no_nystagmus_in_flat_signal() {
        let data: Vec<(f64, f64)> = (0..1000)
            .map(|i| {
                let t = i as f64 / 200.0;
                (t, 0.0) // Flat signal
            })
            .collect();

        let result = NystagmusAnalyzer::analyze_batch(&data, 0.5);
        assert_eq!(result.beat_count, 0, "Flat signal should have no beats");
    }

    #[test]
    fn test_noise_filtered_out() {
        // Small noise (amplitude < min_amplitude of 0.5°)
        let data: Vec<(f64, f64)> = (0..1000)
            .map(|i| {
                let t = i as f64 / 200.0;
                let noise = (i as f64 * 0.3).sin() * 0.2; // 0.2° amplitude
                (t, noise)
            })
            .collect();

        let result = NystagmusAnalyzer::analyze_batch(&data, 0.5);
        assert_eq!(result.beat_count, 0, "Sub-threshold noise should not produce beats");
    }

    #[test]
    fn test_realtime_push_sample() {
        let data = generate_sawtooth(5, 5.0, -100.0, 1.0, 0.05, 200.0);
        let mut analyzer = NystagmusAnalyzer::new(0.5);
        let mut beats = Vec::new();

        for (t, pos) in &data {
            if let Some(beat) = analyzer.push_sample(*t, *pos) {
                beats.push(beat);
            }
        }

        assert!(beats.len() > 0, "Real-time should detect at least some beats");
        assert!(analyzer.get_beat_count() > 0);
        assert!(analyzer.get_average_spv() > 1.0);
    }

    #[test]
    fn test_deflection_points_detected() {
        let data = generate_sawtooth(5, 5.0, -100.0, 1.0, 0.05, 200.0);
        let result = NystagmusAnalyzer::analyze_batch(&data, 0.5);

        assert!(result.deflection_points.len() >= 5,
            "Should detect deflection points, got {}", result.deflection_points.len());
    }

    #[test]
    fn test_amplitude_correct() {
        // Slow phase: 5°/s * 1s = 5° amplitude per beat
        let data = generate_sawtooth(5, 5.0, -100.0, 1.0, 0.05, 200.0);
        let result = NystagmusAnalyzer::analyze_batch(&data, 0.5);

        for beat in &result.beats {
            assert!(beat.amplitude > 2.0 && beat.amplitude < 10.0,
                "Beat amplitude should be ~5°, got {:.1}", beat.amplitude);
        }
    }
}
