use serialport::SerialPort;
use std::io::{self, BufRead, BufReader, Write};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use tauri::{Emitter, Window};
use std::sync::atomic::{AtomicBool, Ordering};

pub struct HardwareManager {
    port: Arc<Mutex<Option<Box<dyn SerialPort>>>>,
    is_connected: Arc<AtomicBool>,
    reader_thread_handle: Option<thread::JoinHandle<()>>,
    should_stop: Arc<AtomicBool>,
}

#[derive(serde::Serialize, Clone)]
struct ImuData {
    yaw: f64,
    pitch: f64,
    roll: f64,
    timestamp: u128,
}

impl HardwareManager {
    pub fn new() -> Self {
        Self {
            port: Arc::new(Mutex::new(None)),
            is_connected: Arc::new(AtomicBool::new(false)),
            reader_thread_handle: None,
            should_stop: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn list_ports(&self) -> Vec<String> {
        match serialport::available_ports() {
            Ok(ports) => ports.into_iter().map(|p| p.port_name).collect(),
            Err(_) => Vec::new(),
        }
    }

    pub fn connect(&mut self, port_name: &str, baud_rate: u32, window: Window) -> Result<(), String> {
        if self.is_connected.load(Ordering::SeqCst) {
            return Err("Already connected".to_string());
        }

        let port = serialport::new(port_name, baud_rate)
            .timeout(Duration::from_millis(100))
            .open()
            .map_err(|e| e.to_string())?;

        // Clone port for reading thread
        let port_clone = port.try_clone().map_err(|e| e.to_string())?;
        
        // Store port for writing
        {
            let mut guard = self.port.lock().unwrap();
            *guard = Some(port);
        }

        self.is_connected.store(true, Ordering::SeqCst);
        self.should_stop.store(false, Ordering::SeqCst);

        // Start reader thread
        let is_connected = self.is_connected.clone();
        let should_stop = self.should_stop.clone();
        
        self.reader_thread_handle = Some(thread::spawn(move || {
            let mut reader = BufReader::new(port_clone);
            let mut buffer = String::new();

            while !should_stop.load(Ordering::SeqCst) {
                buffer.clear();
                match reader.read_line(&mut buffer) {
                    Ok(bytes) => {
                        if bytes > 0 {
                            let line = buffer.trim();
                            // Parse IMU data "yaw,pitch,roll"
                            if let Some(data) = Self::parse_imu_data(line) {
                                // Emit to frontend
                                let _ = window.emit("imu-data", data);
                            }
                        }
                    }
                    Err(ref e) if e.kind() == io::ErrorKind::TimedOut => {
                        // Timeout is fine, just continue
                        continue;
                    }
                    Err(_) => {
                        // Error reading, maybe disconnected
                        break;
                    }
                }
            }
            
            is_connected.store(false, Ordering::SeqCst);
        }));

        Ok(())
    }

    pub fn disconnect(&mut self) {
        self.should_stop.store(true, Ordering::SeqCst);
        
        // Join reader thread
        if let Some(handle) = self.reader_thread_handle.take() {
            let _ = handle.join();
        }

        let mut guard = self.port.lock().unwrap();
        *guard = None;
        self.is_connected.store(false, Ordering::SeqCst);
    }

    pub fn send_command(&self, cmd: &str) -> Result<(), String> {
        let mut guard = self.port.lock().unwrap();
        if let Some(port) = guard.as_mut() {
            let output = format!("{}\n", cmd);
            port.write_all(output.as_bytes()).map_err(|e| e.to_string())?;
            port.flush().map_err(|e| e.to_string())?;
            Ok(())
        } else {
            Err("Not connected".to_string())
        }
    }

    fn parse_imu_data(line: &str) -> Option<ImuData> {
        let parts: Vec<&str> = line.split(',').collect();
        if parts.len() >= 3 {
            let yaw = parts[0].parse::<f64>().ok()?;
            let pitch = parts[1].parse::<f64>().ok()?;
            let roll = parts[2].parse::<f64>().ok()?;
            
            use std::time::{SystemTime, UNIX_EPOCH};
            let timestamp = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_millis();

            Some(ImuData { yaw, pitch, roll, timestamp })
        } else {
            None
        }
    }
}
