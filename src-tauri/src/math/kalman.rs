use nalgebra::{Matrix2, Matrix2x6, Matrix6, Vector2, Vector6};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KalmanConfig {
    pub process_noise: f64,
    pub measurement_noise: f64,
    pub stability_factor: f64,
}

impl Default for KalmanConfig {
    fn default() -> Self {
        Self {
            process_noise: 0.01,
            measurement_noise: 0.1,
            stability_factor: 0.01,
        }
    }
}

pub struct KalmanFilter {
    // State: [x, y, vx, vy, ax, ay]
    state: Vector6<f64>,
    // Covariance matrix
    p: Matrix6<f64>,
    // Process noise covariance
    q: Matrix6<f64>,
    // Measurement noise covariance
    r: Matrix2<f64>,
    // Measurement matrix
    h: Matrix2x6<f64>,
    // Stability factor for acceleration
    sf: f64,
    
    initialized: bool,
}

impl KalmanFilter {
    pub fn new(config: KalmanConfig) -> Self {
        let sf = config.stability_factor;

        // Measurement Matrix (We measure x and y)
        let h = Matrix2x6::new(
            1.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0, 0.0, 0.0,
        );

        // Process Noise
        let mut q = Matrix6::identity() * config.process_noise;
        // Fine tune noise (less noise in pos, more in acc)
        q[(0, 0)] *= 0.1;
        q[(1, 1)] *= 0.1;
        q[(4, 4)] *= 10.0;
        q[(5, 5)] *= 10.0;

        // Measurement Noise
        let r = Matrix2::identity() * config.measurement_noise;

        Self {
            state: Vector6::zeros(),
            p: Matrix6::identity(),
            q,
            r,
            h,
            sf,
            initialized: false,
        }
    }

    pub fn reset(&mut self) {
        self.state = Vector6::zeros();
        self.p = Matrix6::identity();
        self.initialized = false;
    }

    pub fn predict(&mut self, dt: f64) {
        if !self.initialized {
            return;
        }

        // Dynamic Transition Matrix (Physics model: pos + vel + acc)
        // x = x + vx*dt + 0.5*ax*dt^2
        // v = v + ax*dt
        // a = a * stability_factor
        let a = Matrix6::new(
            1.0, 0.0, dt,  0.0, 0.5*dt*dt, 0.0,
            0.0, 1.0, 0.0, dt,  0.0,       0.5*dt*dt,
            0.0, 0.0, 1.0, 0.0, dt,        0.0,
            0.0, 0.0, 0.0, 1.0, 0.0,       dt,
            0.0, 0.0, 0.0, 0.0, self.sf,   0.0,
            0.0, 0.0, 0.0, 0.0, 0.0,       self.sf,
        );
        
        // x = A * x
        self.state = a * self.state;
        
        // P = A * P * A^T + Q
        self.p = a * self.p * a.transpose() + self.q;
    }

    pub fn update(&mut self, measurement: Vector2<f64>) -> Vector2<f64> {
        if !self.initialized {
            self.state[0] = measurement[0];
            self.state[1] = measurement[1];
            // Initialize velocity and acceleration to 0
            self.initialized = true;
            return measurement;
        }

        // y = z - H * x (Innovation)
        let z = measurement;
        let y = z - (self.h * self.state);

        // S = H * P * H^T + R (Innovation covariance)
        let s = self.h * self.p * self.h.transpose() + self.r;

        // K = P * H^T * S^-1 (Kalman gain)
        // Try invert S, if fails (rare), return current prediction
        let s_inv = match s.try_inverse() {
            Some(inv) => inv,
            None => return Vector2::new(self.state[0], self.state[1]),
        };
        
        let k = self.p * self.h.transpose() * s_inv;

        // x = x + K * y
        self.state = self.state + k * y;

        // P = (I - K * H) * P
        let i = Matrix6::identity();
        self.p = (i - k * self.h) * self.p;

        // Return position [x, y]
        Vector2::new(self.state[0], self.state[1])
    }
}
