use nalgebra::Vector2;
use serde::{Deserialize, Serialize};
use super::kalman::{KalmanFilter, KalmanConfig};

// Data structures for communication with Frontend/Python
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawEyeData {
    pub left_eye: Option<[f64; 2]>,
    pub right_eye: Option<[f64; 2]>,
    pub timestamp: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessedEyeData {
    pub left: Option<[f64; 2]>,
    pub right: Option<[f64; 2]>,
    pub timestamp: f64,
    pub is_calibrated: bool,
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
        }
    }

    pub fn process(&mut self, data: RawEyeData) -> ProcessedEyeData {
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
        let processed_left = if let Some(raw_left) = data.left_eye {
            let mut point = Vector2::new(raw_left[0], raw_left[1]);
            
            // Apply centering
            if let Some(center) = self.left_center {
                point -= center;
            }
            
            // Apply Kalman
            self.kalman_left.predict();
            let smoothed = self.kalman_left.update(point);
            
            Some([smoothed.x, smoothed.y])
        } else {
            // Predict even if no measurement to keep filter warm (optional)
            // self.kalman_left.predict(); 
            None
        };

        // 3. Processing Right Eye
        let processed_right = if let Some(raw_right) = data.right_eye {
            let mut point = Vector2::new(raw_right[0], raw_right[1]);
            
            // Apply centering
            if let Some(center) = self.right_center {
                point -= center;
            }
            
            // Apply Kalman
            self.kalman_right.predict();
            let smoothed = self.kalman_right.update(point);
            
            Some([smoothed.x, smoothed.y])
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

    pub fn reset_calibration(&mut self) {
        self.is_calibrated = false;
        self.left_center = None;
        self.right_center = None;
        self.calibration_samples_left.clear();
        self.calibration_samples_right.clear();
        self.kalman_left.reset();
        self.kalman_right.reset();
    }
}
