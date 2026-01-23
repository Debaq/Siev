use std::collections::HashMap;
use std::io;
use std::sync::Arc;
use tokio::sync::{broadcast, mpsc, oneshot, Mutex};

use super::protocol::{Command, CommandAck, EyeDataPayload, Message, MessageType};
use super::tcp_server::{ConnectionState, ServerEvent, TcpServer};

/// Events emitted by PythonBridge for consumers
#[derive(Debug, Clone)]
pub enum BridgeEvent {
    /// Python worker connected
    Connected,
    /// Python worker disconnected
    Disconnected,
    /// Eye tracking data received
    EyeData(EyeDataPayload),
    /// Video frame received (JPEG bytes)
    VideoFrame(Vec<u8>),
    /// Error from Python
    Error(String),
    /// Command acknowledgment from Python
    CmdAck(CommandAck),
}

/// High-level API for communicating with Python worker
pub struct PythonBridge {
    server: Arc<TcpServer>,
    event_tx: broadcast::Sender<BridgeEvent>,
    pending_commands: Arc<Mutex<HashMap<u64, oneshot::Sender<CommandAck>>>>,
}

impl PythonBridge {
    pub fn new() -> Self {
        Self::with_port(super::tcp_server::DEFAULT_PORT)
    }

    pub fn with_port(port: u16) -> Self {
        let (event_tx, _) = broadcast::channel(512);
        Self {
            server: Arc::new(TcpServer::new(port)),
            event_tx,
            pending_commands: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Subscribe to bridge events
    pub fn subscribe(&self) -> broadcast::Receiver<BridgeEvent> {
        self.event_tx.subscribe()
    }

    /// Check if Python is connected
    pub async fn is_connected(&self) -> bool {
        self.server.is_connected().await
    }

    /// Get connection state
    pub async fn state(&self) -> ConnectionState {
        self.server.state().await
    }

    /// Start the bridge (spawns TCP server task)
    pub fn start(&self) -> mpsc::Receiver<()> {
        let server = Arc::clone(&self.server);
        let event_tx = self.event_tx.clone();
        let pending = Arc::clone(&self.pending_commands);

        let (shutdown_tx, shutdown_rx) = mpsc::channel::<()>(1);

        // Spawn the main event processing loop
        tokio::spawn(async move {
            let mut server_events = server.subscribe();

            // Spawn the TCP server
            let server_clone = Arc::clone(&server);
            tokio::spawn(async move {
                if let Err(e) = server_clone.run().await {
                    eprintln!("[Bridge] TCP server error: {}", e);
                }
            });

            // Process events
            loop {
                match server_events.recv().await {
                    Ok(ServerEvent::ClientConnected) => {
                        let _ = event_tx.send(BridgeEvent::Connected);
                    }
                    Ok(ServerEvent::ClientDisconnected) => {
                        // Clear pending commands on disconnect
                        pending.lock().await.clear();
                        let _ = event_tx.send(BridgeEvent::Disconnected);
                    }
                    Ok(ServerEvent::Message(msg)) => {
                        Self::handle_message(&event_tx, &pending, msg).await;
                    }
                    Err(broadcast::error::RecvError::Lagged(n)) => {
                        eprintln!("[Bridge] Dropped {} events", n);
                    }
                    Err(broadcast::error::RecvError::Closed) => {
                        break;
                    }
                }
            }

            drop(shutdown_tx);
        });

        shutdown_rx
    }

    async fn handle_message(
        event_tx: &broadcast::Sender<BridgeEvent>,
        _pending: &Arc<Mutex<HashMap<u64, oneshot::Sender<CommandAck>>>>,
        msg: Message,
    ) {
        match msg.msg_type {
            MessageType::CmdAck => {
                if let Some(ack) = msg.as_cmd_ack() {
                    let _ = event_tx.send(BridgeEvent::CmdAck(ack.clone()));
                    // For now, we don't track command IDs - just log
                    if !ack.success {
                        if let Some(err) = &ack.error {
                            eprintln!("[Bridge] Command failed: {}", err);
                        }
                    }
                }
            }
            MessageType::EyeData => {
                if let Some(data) = msg.as_eye_data() {
                    let _ = event_tx.send(BridgeEvent::EyeData(data));
                }
            }
            MessageType::VideoFrame => {
                let _ = event_tx.send(BridgeEvent::VideoFrame(msg.payload));
            }
            MessageType::Error => {
                if let Some(err) = msg.as_error() {
                    let _ = event_tx.send(BridgeEvent::Error(err));
                }
            }
            MessageType::Heartbeat => {
                // Respond with heartbeat
                // Note: This is handled at protocol level
            }
            _ => {}
        }
    }

    /// Send a command to Python
    pub async fn send_command(&self, cmd: &str) -> io::Result<()> {
        self.send_command_with_params(cmd, serde_json::Value::Object(serde_json::Map::new()))
            .await
    }

    /// Send a command with parameters to Python
    pub async fn send_command_with_params(
        &self,
        cmd: &str,
        params: serde_json::Value,
    ) -> io::Result<()> {
        let command = Command::with_params(cmd, params);
        let payload = serde_json::to_vec(&command).map_err(|e| {
            io::Error::new(io::ErrorKind::InvalidData, format!("JSON error: {}", e))
        })?;

        let msg = Message::new(MessageType::Cmd, payload);
        self.server.send(msg).await
    }

    // --- Convenience methods for common commands ---

    /// Start video capture
    pub async fn start_capture(
        &self,
        camera_id: i32,
        width: u32,
        height: u32,
    ) -> io::Result<()> {
        let params = serde_json::json!({
            "camera_id": camera_id,
            "width": width,
            "height": height
        });
        self.send_command_with_params("start_capture", params).await
    }

    /// Stop video capture
    pub async fn stop_capture(&self) -> io::Result<()> {
        self.send_command("stop_capture").await
    }

    /// List available cameras
    pub async fn list_cameras(&self) -> io::Result<()> {
        self.send_command("list_cameras").await
    }

    /// Set generic configuration
    pub async fn set_config(&self, key: &str, value: serde_json::Value) -> io::Result<()> {
        let params = serde_json::json!({
            "key": key,
            "value": value
        });
        self.send_command_with_params("set_config", params).await
    }

    /// Set camera configuration (Legacy - kept for compatibility)
    pub async fn set_camera_config(&self, key: &str, value: i32) -> io::Result<()> {
        self.set_config(key, serde_json::Value::from(value)).await
    }

    /// Set pupil detection configuration
    pub async fn set_pupil_config(&self, threshold: i32, mode: &str) -> io::Result<()> {
        let params = serde_json::json!({
            "threshold": threshold,
            "mode": mode
        });
        self.send_command_with_params("set_pupil_config", params).await
    }

    /// Send heartbeat
    pub async fn heartbeat(&self) -> io::Result<()> {
        self.server.send(Message::heartbeat()).await
    }
}

impl Default for PythonBridge {
    fn default() -> Self {
        Self::new()
    }
}
