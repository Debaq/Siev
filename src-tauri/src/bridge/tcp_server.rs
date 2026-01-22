use bytes::BytesMut;
use std::io;
use std::sync::Arc;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::{broadcast, mpsc, Mutex};

use super::protocol::{FrameCodec, Message, MessageType};

/// Default port for TCP server
pub const DEFAULT_PORT: u16 = 9999;
/// Buffer size for reading from socket
const READ_BUFFER_SIZE: usize = 64 * 1024;

/// Connection state
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConnectionState {
    Disconnected,
    Connected,
}

/// Events emitted by the TCP server
#[derive(Debug, Clone)]
pub enum ServerEvent {
    ClientConnected,
    ClientDisconnected,
    Message(Message),
}

/// Handle to send messages to the connected client
#[derive(Clone)]
pub struct ClientSender {
    tx: mpsc::Sender<Message>,
}

impl ClientSender {
    pub async fn send(&self, msg: Message) -> Result<(), io::Error> {
        self.tx.send(msg).await.map_err(|_| {
            io::Error::new(io::ErrorKind::NotConnected, "Client not connected")
        })
    }
}

/// TCP Server that accepts a single Python client connection
pub struct TcpServer {
    port: u16,
    state: Arc<Mutex<ConnectionState>>,
    event_tx: broadcast::Sender<ServerEvent>,
    client_tx: Arc<Mutex<Option<mpsc::Sender<Message>>>>,
}

impl TcpServer {
    pub fn new(port: u16) -> Self {
        let (event_tx, _) = broadcast::channel(256);
        Self {
            port,
            state: Arc::new(Mutex::new(ConnectionState::Disconnected)),
            event_tx,
            client_tx: Arc::new(Mutex::new(None)),
        }
    }

    pub fn with_default_port() -> Self {
        Self::new(DEFAULT_PORT)
    }

    /// Subscribe to server events
    pub fn subscribe(&self) -> broadcast::Receiver<ServerEvent> {
        self.event_tx.subscribe()
    }

    /// Get current connection state
    pub async fn state(&self) -> ConnectionState {
        *self.state.lock().await
    }

    /// Check if a client is connected
    pub async fn is_connected(&self) -> bool {
        *self.state.lock().await == ConnectionState::Connected
    }

    /// Get a sender to send messages to the client
    pub fn get_sender(&self) -> ClientSender {
        ClientSender {
            tx: self.create_client_channel(),
        }
    }

    fn create_client_channel(&self) -> mpsc::Sender<Message> {
        // This creates a new channel; the actual sender will be set when client connects
        let (tx, _) = mpsc::channel(256);
        tx
    }

    /// Send a message to the connected client
    pub async fn send(&self, msg: Message) -> Result<(), io::Error> {
        let guard = self.client_tx.lock().await;
        if let Some(tx) = guard.as_ref() {
            tx.send(msg).await.map_err(|_| {
                io::Error::new(io::ErrorKind::NotConnected, "Client channel closed")
            })
        } else {
            Err(io::Error::new(
                io::ErrorKind::NotConnected,
                "No client connected",
            ))
        }
    }

    /// Start the TCP server (runs forever)
    pub async fn run(&self) -> io::Result<()> {
        let addr = format!("127.0.0.1:{}", self.port);
        let listener = TcpListener::bind(&addr).await?;
        println!("[TCP] Server listening on {}", addr);

        loop {
            match listener.accept().await {
                Ok((stream, peer_addr)) => {
                    println!("[TCP] Client connected from {}", peer_addr);

                    // Update state
                    *self.state.lock().await = ConnectionState::Connected;

                    // Notify subscribers
                    let _ = self.event_tx.send(ServerEvent::ClientConnected);

                    // Handle the connection
                    self.handle_connection(stream).await;

                    // Update state after disconnect
                    *self.state.lock().await = ConnectionState::Disconnected;
                    let _ = self.event_tx.send(ServerEvent::ClientDisconnected);

                    println!("[TCP] Client disconnected");
                }
                Err(e) => {
                    eprintln!("[TCP] Accept error: {}", e);
                }
            }
        }
    }

    async fn handle_connection(&self, stream: TcpStream) {
        let (mut reader, mut writer) = stream.into_split();

        // Create channel for outgoing messages
        let (tx, mut rx) = mpsc::channel::<Message>(256);
        *self.client_tx.lock().await = Some(tx);

        // Read buffer
        let read_buffer = Arc::new(Mutex::new(BytesMut::with_capacity(READ_BUFFER_SIZE)));
        let event_tx = self.event_tx.clone();

        // Spawn writer task
        let writer_handle = tokio::spawn(async move {
            let mut write_buf = BytesMut::new();
            while let Some(msg) = rx.recv().await {
                write_buf.clear();
                FrameCodec::encode(&msg, &mut write_buf);
                if let Err(e) = writer.write_all(&write_buf).await {
                    eprintln!("[TCP] Write error: {}", e);
                    break;
                }
            }
        });

        // Reader loop
        let mut temp_buf = [0u8; READ_BUFFER_SIZE];
        loop {
            match reader.read(&mut temp_buf).await {
                Ok(0) => {
                    // EOF - client disconnected
                    break;
                }
                Ok(n) => {
                    let mut buf = read_buffer.lock().await;
                    buf.extend_from_slice(&temp_buf[..n]);

                    // Try to decode messages
                    loop {
                        match FrameCodec::decode(&mut buf) {
                            Ok(Some(msg)) => {
                                // Emit the message event
                                let _ = event_tx.send(ServerEvent::Message(msg));
                            }
                            Ok(None) => {
                                // Need more data
                                break;
                            }
                            Err(e) => {
                                eprintln!("[TCP] Decode error: {}", e);
                                break;
                            }
                        }
                    }
                }
                Err(e) => {
                    eprintln!("[TCP] Read error: {}", e);
                    break;
                }
            }
        }

        // Cleanup
        *self.client_tx.lock().await = None;
        writer_handle.abort();
    }
}

/// Typed message handlers for convenience
impl Message {
    /// Parse payload as JSON command
    pub fn as_command(&self) -> Option<super::protocol::Command> {
        if self.msg_type != MessageType::Cmd && self.msg_type != MessageType::CmdAck {
            return None;
        }
        serde_json::from_slice(&self.payload).ok()
    }

    /// Parse payload as eye data
    pub fn as_eye_data(&self) -> Option<super::protocol::EyeDataPayload> {
        if self.msg_type != MessageType::EyeData {
            return None;
        }
        serde_json::from_slice(&self.payload).ok()
    }

    /// Parse payload as command ack
    pub fn as_cmd_ack(&self) -> Option<super::protocol::CommandAck> {
        if self.msg_type != MessageType::CmdAck {
            return None;
        }
        serde_json::from_slice(&self.payload).ok()
    }

    /// Get video frame bytes (JPEG)
    pub fn as_video_frame(&self) -> Option<&[u8]> {
        if self.msg_type != MessageType::VideoFrame {
            return None;
        }
        Some(&self.payload)
    }

    /// Parse error message
    pub fn as_error(&self) -> Option<String> {
        if self.msg_type != MessageType::Error {
            return None;
        }
        String::from_utf8(self.payload.clone()).ok()
    }
}
