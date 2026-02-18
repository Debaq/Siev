use nalgebra::Vector2;
use serde::{Deserialize, Serialize};
use super::kalman::{KalmanFilter, KalmanConfig};

// Data structures for communication with Frontend
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawEyeData {
    pub left_eye: Option<[f64; 2]>,
    pub right_eye: Option<[f64; 2]>,
    pub processed: Option<ProcessedFromBackend>,
    pub timestamp: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessedFromBackend {
    pub left_eye: Option<[f64; 2]>,
    pub right_eye: Option<[f64; 2]>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessedEyeData {
    pub left: Option<[f64; 2]>,
    pub right: Option<[f64; 2]>,
    pub timestamp: f64,
    pub is_calibrated: bool,
}

// --- Manual Calibration Data (from Frontend) ---

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PixelCoord {
    pub x: f64,
    pub y: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ManualCalibrationPoint {
    pub id: String,
    pub angle_x: f64,      // degrees
    pub angle_y: f64,      // degrees
    pub pixel_right: PixelCoord,
    pub pixel_left: PixelCoord,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManualCalibrationData {
    pub points: Vec<ManualCalibrationPoint>,
    pub patient_distance: f64,
}

/// Snapshot of the full calibration state for persistence
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibrationSnapshot {
    pub points: Vec<ManualCalibrationPoint>,
    pub patient_distance: f64,
    pub left_center: [f64; 2],
    pub right_center: [f64; 2],
    pub left_scale: [f64; 2],
    pub right_scale: [f64; 2],
    pub timestamp: String,
}

/// Linear mapping from centered pixels to degrees for one eye
#[derive(Debug, Clone)]
struct EyeCalibrationMapping {
    scale: Vector2<f64>,            // degrees per pixel (x, y)
}

pub struct EyeProcessor {
    kalman_left: KalmanFilter,
    kalman_right: KalmanFilter,

    // Calibration
    left_center: Option<Vector2<f64>>,
    right_center: Option<Vector2<f64>>,
    calibration_samples_left: Vec<Vector2<f64>>,
    calibration_samples_right: Vec<Vector2<f64>>,
    is_calibrated: bool,
    calibration_target_samples: usize,

    // Manual calibration: pixel -> degrees mapping
    manual_cal_right: Option<EyeCalibrationMapping>,
    manual_cal_left: Option<EyeCalibrationMapping>,

    // Controls
    pub filtering_enabled: bool,
    last_timestamp: Option<f64>,
}

impl EyeProcessor {
    pub fn new() -> Self {
        let config = KalmanConfig::default();
        Self {
            kalman_left: KalmanFilter::new(config.clone()),
            kalman_right: KalmanFilter::new(config),
            left_center: None,
            right_center: None,
            calibration_samples_left: Vec::with_capacity(30),
            calibration_samples_right: Vec::with_capacity(30),
            is_calibrated: false,
            calibration_target_samples: 30,
            manual_cal_right: None,
            manual_cal_left: None,
            filtering_enabled: true,
            last_timestamp: None,
        }
    }

    pub fn process(&mut self, data: RawEyeData) -> ProcessedEyeData {
        self.process_internal(data)
    }

    fn process_internal(&mut self, data: RawEyeData) -> ProcessedEyeData {
        // Calculate dynamic dt
        let current_time = data.timestamp;
        let dt = match self.last_timestamp {
            Some(last) => (current_time - last).max(0.001), // Min 1ms to avoid infinity
            None => 0.005, // Default for 200 FPS
        };
        self.last_timestamp = Some(current_time);

        if !self.filtering_enabled {
            // Return raw or pre-processed data directly
            let (l, r) = if let Some(p) = data.processed {
                (p.left_eye, p.right_eye)
            } else {
                (data.left_eye, data.right_eye)
            };

            return ProcessedEyeData {
                left: l,
                right: r,
                timestamp: data.timestamp,
                is_calibrated: true, // Mark as "calibrated" to show it's ready
            };
        }

        // 1. Calibration Collection
        if !self.is_calibrated && self.left_center.is_none() {
            if let Some(left) = data.left_eye {
                if self.calibration_samples_left.len() < self.calibration_target_samples {
                    self.calibration_samples_left.push(Vector2::new(left[0], left[1]));
                }
            }
            if let Some(right) = data.right_eye {
                if self.calibration_samples_right.len() < self.calibration_target_samples {
                    self.calibration_samples_right.push(Vector2::new(right[0], right[1]));
                }
            }
            
            // Check if ready to calibrate
            if self.calibration_samples_left.len() >= self.calibration_target_samples &&
               self.calibration_samples_right.len() >= self.calibration_target_samples {
                self.finalize_calibration();
            }
        }

        // 2. Processing Left Eye
        // Always predict to keep uncertainty growing and maintain inertia
        self.kalman_left.predict(dt);
        let processed_left = if let Some(raw_left) = data.left_eye {
            let mut point = Vector2::new(raw_left[0], raw_left[1]);

            // Apply centering
            if let Some(center) = self.left_center {
                point -= center;
            }

            let smoothed = self.kalman_left.update(point);

            // Convert to degrees if manual calibration is available
            if let Some(ref cal) = self.manual_cal_left {
                Some([smoothed.x * cal.scale.x, smoothed.y * cal.scale.y])
            } else {
                Some([smoothed.x, smoothed.y])
            }
        } else {
            None
        };

        // 3. Processing Right Eye
        self.kalman_right.predict(dt);
        let processed_right = if let Some(raw_right) = data.right_eye {
            let mut point = Vector2::new(raw_right[0], raw_right[1]);

            // Apply centering
            if let Some(center) = self.right_center {
                point -= center;
            }

            let smoothed = self.kalman_right.update(point);

            // Convert to degrees if manual calibration is available
            if let Some(ref cal) = self.manual_cal_right {
                Some([smoothed.x * cal.scale.x, smoothed.y * cal.scale.y])
            } else {
                Some([smoothed.x, smoothed.y])
            }
        } else {
            None
        };

        ProcessedEyeData {
            left: processed_left,
            right: processed_right,
            timestamp: data.timestamp,
            is_calibrated: self.is_calibrated,
        }
    }

    pub fn process_batch(&mut self, batch: Vec<RawEyeData>) -> Vec<ProcessedEyeData> {
        batch.into_iter()
             .map(|data| self.process_internal(data))
             .collect()
    }

    fn finalize_calibration(&mut self) {
        // Calculate average for left
        if !self.calibration_samples_left.is_empty() {
            let sum: Vector2<f64> = self.calibration_samples_left.iter().sum();
            self.left_center = Some(sum / self.calibration_samples_left.len() as f64);
        }

        // Calculate average for right
        if !self.calibration_samples_right.is_empty() {
            let sum: Vector2<f64> = self.calibration_samples_right.iter().sum();
            self.right_center = Some(sum / self.calibration_samples_right.len() as f64);
        }

        self.is_calibrated = true;
        
        // Reset Kalman filters to adapt to new centered coordinates (0,0)
        self.kalman_left.reset();
        self.kalman_right.reset();
    }

    /// Apply manual calibration from multi-point data captured by the frontend.
    /// Computes a linear mapping: degrees = (pixel - center_pixel) * scale
    /// where scale = degrees_per_pixel, computed via least-squares from all calibration points.
    pub fn apply_manual_calibration(&mut self, data: ManualCalibrationData) {
        // Find center point (angle 0,0)
        let center_point = data.points.iter()
            .find(|p| p.id == "C" || (p.angle_x == 0.0 && p.angle_y == 0.0));

        let center_point = match center_point {
            Some(p) => p,
            None => {
                eprintln!("[EyeProcessor] No center point found in calibration data");
                return;
            }
        };

        let center_right = Vector2::new(center_point.pixel_right.x, center_point.pixel_right.y);
        let center_left = Vector2::new(center_point.pixel_left.x, center_point.pixel_left.y);

        // Compute degrees_per_pixel using least-squares regression through origin:
        //   angle = scale * (pixel - center_pixel)
        //   scale = sum(angle * delta_pixel) / sum(delta_pixel^2)
        // Computed separately for X and Y axes, and for each eye.

        let mut sum_ax_dpx_r = 0.0_f64;  // sum(angleX * delta_pixel_x) for right eye
        let mut sum_dpx2_r = 0.0_f64;    // sum(delta_pixel_x^2) for right eye
        let mut sum_ay_dpy_r = 0.0_f64;
        let mut sum_dpy2_r = 0.0_f64;

        let mut sum_ax_dpx_l = 0.0_f64;
        let mut sum_dpx2_l = 0.0_f64;
        let mut sum_ay_dpy_l = 0.0_f64;
        let mut sum_dpy2_l = 0.0_f64;

        for point in &data.points {
            // Skip center point (delta would be 0)
            if point.id == "C" || (point.angle_x == 0.0 && point.angle_y == 0.0) {
                continue;
            }

            // Right eye
            let dpx_r = point.pixel_right.x - center_right.x;
            let dpy_r = point.pixel_right.y - center_right.y;

            if dpx_r.abs() > 1e-6 {
                sum_ax_dpx_r += point.angle_x * dpx_r;
                sum_dpx2_r += dpx_r * dpx_r;
            }
            if dpy_r.abs() > 1e-6 {
                sum_ay_dpy_r += point.angle_y * dpy_r;
                sum_dpy2_r += dpy_r * dpy_r;
            }

            // Left eye
            let dpx_l = point.pixel_left.x - center_left.x;
            let dpy_l = point.pixel_left.y - center_left.y;

            if dpx_l.abs() > 1e-6 {
                sum_ax_dpx_l += point.angle_x * dpx_l;
                sum_dpx2_l += dpx_l * dpx_l;
            }
            if dpy_l.abs() > 1e-6 {
                sum_ay_dpy_l += point.angle_y * dpy_l;
                sum_dpy2_l += dpy_l * dpy_l;
            }
        }

        // Compute scale factors (degrees per pixel)
        // Fallback to a reasonable default if no data for an axis (e.g., 3-point horizontal only)
        let scale_x_r = if sum_dpx2_r > 1e-6 { sum_ax_dpx_r / sum_dpx2_r } else { 1.0 };
        let scale_y_r = if sum_dpy2_r > 1e-6 { sum_ay_dpy_r / sum_dpy2_r } else { 1.0 };
        let scale_x_l = if sum_dpx2_l > 1e-6 { sum_ax_dpx_l / sum_dpx2_l } else { 1.0 };
        let scale_y_l = if sum_dpy2_l > 1e-6 { sum_ay_dpy_l / sum_dpy2_l } else { 1.0 };

        println!("[EyeProcessor] Manual calibration applied:");
        println!("  Right eye - center: ({:.1}, {:.1}), scale: ({:.4}, {:.4}) deg/px",
            center_right.x, center_right.y, scale_x_r, scale_y_r);
        println!("  Left eye  - center: ({:.1}, {:.1}), scale: ({:.4}, {:.4}) deg/px",
            center_left.x, center_left.y, scale_x_l, scale_y_l);

        self.manual_cal_right = Some(EyeCalibrationMapping {
            scale: Vector2::new(scale_x_r, scale_y_r),
        });
        self.manual_cal_left = Some(EyeCalibrationMapping {
            scale: Vector2::new(scale_x_l, scale_y_l),
        });

        // Set center positions for the existing centering logic
        self.left_center = Some(center_left);
        self.right_center = Some(center_right);
        self.is_calibrated = true;

        // Reset Kalman filters to adapt to new coordinate system
        self.kalman_left.reset();
        self.kalman_right.reset();

        // Clear auto-calibration samples (no longer needed)
        self.calibration_samples_left.clear();
        self.calibration_samples_right.clear();
    }

    /// Export the current calibration state as a serializable snapshot
    pub fn export_calibration_snapshot(&self) -> Option<CalibrationSnapshot> {
        if !self.is_calibrated {
            return None;
        }
        let left_center = self.left_center.map(|c| [c.x, c.y]).unwrap_or([0.0, 0.0]);
        let right_center = self.right_center.map(|c| [c.x, c.y]).unwrap_or([0.0, 0.0]);
        let left_scale = self.manual_cal_left.as_ref()
            .map(|c| [c.scale.x, c.scale.y])
            .unwrap_or([1.0, 1.0]);
        let right_scale = self.manual_cal_right.as_ref()
            .map(|c| [c.scale.x, c.scale.y])
            .unwrap_or([1.0, 1.0]);

        Some(CalibrationSnapshot {
            points: Vec::new(), // filled by caller
            patient_distance: 0.0, // filled by caller
            left_center,
            right_center,
            left_scale,
            right_scale,
            timestamp: chrono::Local::now().to_rfc3339(),
        })
    }

    /// Restore calibration from a previously saved snapshot
    pub fn restore_calibration(&mut self, snapshot: CalibrationSnapshot) {
        self.left_center = Some(Vector2::new(snapshot.left_center[0], snapshot.left_center[1]));
        self.right_center = Some(Vector2::new(snapshot.right_center[0], snapshot.right_center[1]));
        self.manual_cal_left = Some(EyeCalibrationMapping {
            scale: Vector2::new(snapshot.left_scale[0], snapshot.left_scale[1]),
        });
        self.manual_cal_right = Some(EyeCalibrationMapping {
            scale: Vector2::new(snapshot.right_scale[0], snapshot.right_scale[1]),
        });
        self.is_calibrated = true;
        self.kalman_left.reset();
        self.kalman_right.reset();
        self.calibration_samples_left.clear();
        self.calibration_samples_right.clear();
    }

    pub fn reset_calibration(&mut self) {
        self.is_calibrated = false;
        self.left_center = None;
        self.right_center = None;
        self.manual_cal_right = None;
        self.manual_cal_left = None;
        self.calibration_samples_left.clear();
        self.calibration_samples_right.clear();
        self.kalman_left.reset();
        self.kalman_right.reset();
    }
}
