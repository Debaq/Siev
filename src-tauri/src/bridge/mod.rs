//! Bridge module for TCP communication with Python worker
//!
//! This module provides the infrastructure for Rust to act as the orchestrator,
//! communicating with Python via TCP on localhost.

pub mod protocol;
pub mod python_bridge;
pub mod tcp_server;

// Re-export commonly used types
pub use protocol::{Command, CommandAck, EyeDataPayload, EyePoint, Message, MessageType};
pub use python_bridge::{BridgeEvent, PythonBridge};
pub use tcp_server::{ConnectionState, TcpServer, DEFAULT_PORT};
