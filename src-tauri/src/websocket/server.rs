use std::net::SocketAddr;
use std::sync::{Arc, Mutex};
use futures_util::{SinkExt, StreamExt};
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::{broadcast, mpsc};
use tokio_tungstenite::accept_async;
use tokio_tungstenite::tungstenite::protocol::Message as TungsteniteMessage;
use serde_json;

use crate::websocket::messages::WsMessage;

type Tx = broadcast::Sender<String>;

pub struct WebSocketServer {
    port: Arc<Mutex<u16>>,
    tx: Tx,
    cmd_tx: mpsc::Sender<WsMessage>,
}

impl WebSocketServer {
    pub fn new() -> (Self, mpsc::Receiver<WsMessage>) {
        let (tx, _rx) = broadcast::channel(100);
        let (cmd_tx, cmd_rx) = mpsc::channel(100);
        (
            Self {
                port: Arc::new(Mutex::new(0)),
                tx,
                cmd_tx,
            },
            cmd_rx
        )
    }

    pub fn get_port(&self) -> u16 {
        *self.port.lock().unwrap()
    }

    pub fn broadcast(&self, msg: &WsMessage) {
        if let Ok(json) = serde_json::to_string(msg) {
            let _ = self.tx.send(json);
        }
    }

    pub async fn start(&self, addr: &str) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let listener = TcpListener::bind(addr).await?;
        let actual_addr = listener.local_addr()?;
        let port = actual_addr.port();
        
        {
            let mut p = self.port.lock().unwrap();
            *p = port;
        }
        
        println!("WebSocket server listening on: ws://{}", actual_addr);

        let tx = self.tx.clone();
        let cmd_tx = self.cmd_tx.clone();

        while let Ok((stream, addr)) = listener.accept().await {
            let tx = tx.clone();
            let cmd_tx = cmd_tx.clone();
            tokio::spawn(async move {
                if let Err(e) = Self::handle_connection(stream, addr, tx, cmd_tx).await {
                    eprintln!("Error handling ws connection from {}: {}", addr, e);
                }
            });
        }

        Ok(())
    }

    async fn handle_connection(
        stream: TcpStream,
        addr: SocketAddr,
        broadcast_tx: Tx,
        cmd_tx: mpsc::Sender<WsMessage>,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let ws_stream = accept_async(stream).await?;
        println!("New WebSocket connection: {}", addr);

        let (mut ws_sender, mut ws_receiver) = ws_stream.split();
        let mut broadcast_rx = broadcast_tx.subscribe();

        // Task to forward broadcasts to this client
        let send_task = tokio::spawn(async move {
            while let Ok(msg) = broadcast_rx.recv().await {
                if let Err(e) = ws_sender.send(TungsteniteMessage::Text(msg.into())).await {
                    eprintln!("Error sending to ws client {}: {}", addr, e);
                    break;
                }
            }
        });

        // Loop to receive messages from this client
        while let Some(msg) = ws_receiver.next().await {
            let msg = msg?;
            if msg.is_text() {
                let text = msg.to_text()?;
                if let Ok(ws_msg) = serde_json::from_str::<WsMessage>(text) {
                    let _ = cmd_tx.send(ws_msg).await;
                }
            } else if msg.is_close() {
                break;
            }
        }

        send_task.abort();
        println!("WebSocket connection closed: {}", addr);
        Ok(())
    }
}
