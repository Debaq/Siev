use bytes::{Buf, BufMut, BytesMut};
use serde::{Deserialize, Serialize};
use std::io;

/// Message types for TCP protocol between Rust and Python
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MessageType {
    /// Command from Rust to Python
    Cmd = 0x01,
    /// Command acknowledgment from Python to Rust
    CmdAck = 0x02,
    /// Eye tracking data from Python to Rust
    EyeData = 0x03,
    /// Video frame (JPEG binary) from Python to Rust
    VideoFrame = 0x04,
    /// Error message (bidirectional)
    Error = 0x05,
    /// Heartbeat (bidirectional)
    Heartbeat = 0x06,
}

impl TryFrom<u8> for MessageType {
    type Error = io::Error;

    fn try_from(value: u8) -> Result<Self, io::Error> {
        match value {
            0x01 => Ok(MessageType::Cmd),
            0x02 => Ok(MessageType::CmdAck),
            0x03 => Ok(MessageType::EyeData),
            0x04 => Ok(MessageType::VideoFrame),
            0x05 => Ok(MessageType::Error),
            0x06 => Ok(MessageType::Heartbeat),
            _ => Err(io::Error::new(
                io::ErrorKind::InvalidData,
                format!("Unknown message type: {}", value),
            )),
        }
    }
}

/// A framed message with type and payload
#[derive(Debug, Clone)]
pub struct Message {
    pub msg_type: MessageType,
    pub payload: Vec<u8>,
}

impl Message {
    pub fn new(msg_type: MessageType, payload: Vec<u8>) -> Self {
        Self { msg_type, payload }
    }

    pub fn cmd(payload: Vec<u8>) -> Self {
        Self::new(MessageType::Cmd, payload)
    }

    pub fn heartbeat() -> Self {
        Self::new(MessageType::Heartbeat, Vec::new())
    }

    pub fn error(msg: &str) -> Self {
        Self::new(MessageType::Error, msg.as_bytes().to_vec())
    }
}

// --- Command payloads ---

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Command {
    pub cmd: String,
    #[serde(default)]
    pub params: serde_json::Value,
}

impl Command {
    pub fn new(cmd: &str) -> Self {
        Self {
            cmd: cmd.to_string(),
            params: serde_json::Value::Object(serde_json::Map::new()),
        }
    }

    pub fn with_params(cmd: &str, params: serde_json::Value) -> Self {
        Self {
            cmd: cmd.to_string(),
            params,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandAck {
    pub success: bool,
    #[serde(default)]
    pub data: serde_json::Value,
    #[serde(default)]
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EyePoint {
    pub x: f64,
    pub y: f64,
    pub radius: f64,
    pub confidence: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EyeDataPayload {
    pub timestamp: u64,
    #[serde(default)]
    pub left: Option<EyePoint>,
    #[serde(default)]
    pub right: Option<EyePoint>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorPayload {
    pub message: String,
    #[serde(default)]
    pub code: Option<String>,
}

// --- Frame codec ---

/// Minimum header size: 4 bytes length + 1 byte type
const HEADER_SIZE: usize = 5;
/// Maximum payload size (16MB)
const MAX_PAYLOAD_SIZE: usize = 16 * 1024 * 1024;

/// Codec for encoding/decoding length-prefixed messages
pub struct FrameCodec;

impl FrameCodec {
    /// Encode a message into bytes
    /// Format: [length: u32 BE][type: u8][payload: bytes]
    pub fn encode(msg: &Message, buf: &mut BytesMut) {
        let payload_len = msg.payload.len();
        // Length includes type byte + payload
        let frame_len = 1 + payload_len;

        buf.reserve(4 + frame_len);
        buf.put_u32(frame_len as u32);
        buf.put_u8(msg.msg_type as u8);
        buf.extend_from_slice(&msg.payload);
    }

    /// Try to decode a message from the buffer
    /// Returns None if not enough data, Some(Message) if complete
    pub fn decode(buf: &mut BytesMut) -> io::Result<Option<Message>> {
        // Need at least header
        if buf.len() < HEADER_SIZE {
            return Ok(None);
        }

        // Peek at length (don't consume yet)
        let frame_len = u32::from_be_bytes([buf[0], buf[1], buf[2], buf[3]]) as usize;

        // Sanity check
        if frame_len == 0 {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "Frame length cannot be zero",
            ));
        }
        if frame_len > MAX_PAYLOAD_SIZE {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                format!("Frame too large: {} bytes", frame_len),
            ));
        }

        // Check if we have the full frame
        let total_len = 4 + frame_len;
        if buf.len() < total_len {
            return Ok(None);
        }

        // Consume the frame
        buf.advance(4); // length field
        let msg_type = MessageType::try_from(buf[0])?;
        buf.advance(1); // type field

        let payload_len = frame_len - 1;
        let payload = buf.split_to(payload_len).to_vec();

        Ok(Some(Message::new(msg_type, payload)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encode_decode_roundtrip() {
        let msg = Message::cmd(b"hello".to_vec());
        let mut buf = BytesMut::new();

        FrameCodec::encode(&msg, &mut buf);

        let decoded = FrameCodec::decode(&mut buf).unwrap().unwrap();
        assert_eq!(decoded.msg_type, MessageType::Cmd);
        assert_eq!(decoded.payload, b"hello");
    }

    #[test]
    fn test_decode_partial() {
        let msg = Message::cmd(b"hello".to_vec());
        let mut buf = BytesMut::new();
        FrameCodec::encode(&msg, &mut buf);

        // Split buffer to simulate partial read
        let mut partial = buf.split_to(5);

        // Should return None (not enough data)
        assert!(FrameCodec::decode(&mut partial).unwrap().is_none());
    }

    #[test]
    fn test_heartbeat() {
        let msg = Message::heartbeat();
        let mut buf = BytesMut::new();

        FrameCodec::encode(&msg, &mut buf);

        let decoded = FrameCodec::decode(&mut buf).unwrap().unwrap();
        assert_eq!(decoded.msg_type, MessageType::Heartbeat);
        assert!(decoded.payload.is_empty());
    }
}
