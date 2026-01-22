"""
TCP Protocol for communication between Rust orchestrator and Python worker.
Must match the protocol defined in src-tauri/src/bridge/protocol.rs
"""
import struct
import json
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, Dict, Any, Union

# Message types - must match Rust MessageType enum
class MessageType(IntEnum):
    CMD = 0x01       # Command from Rust to Python
    CMD_ACK = 0x02   # Command acknowledgment from Python to Rust
    EYE_DATA = 0x03  # Eye tracking data from Python to Rust
    VIDEO_FRAME = 0x04  # Video frame (JPEG) from Python to Rust
    ERROR = 0x05     # Error message (bidirectional)
    HEARTBEAT = 0x06 # Heartbeat (bidirectional)


@dataclass
class Message:
    """A framed message with type and payload"""
    msg_type: MessageType
    payload: bytes

    @classmethod
    def cmd(cls, payload: bytes) -> 'Message':
        return cls(MessageType.CMD, payload)

    @classmethod
    def cmd_ack(cls, success: bool, data: Any = None, error: Optional[str] = None) -> 'Message':
        payload = {
            "success": success,
            "data": data if data is not None else {},
            "error": error
        }
        return cls(MessageType.CMD_ACK, json.dumps(payload).encode('utf-8'))

    @classmethod
    def eye_data(cls, timestamp: int, left: Optional[Dict] = None, right: Optional[Dict] = None) -> 'Message':
        payload = {
            "timestamp": timestamp,
            "left": left,
            "right": right
        }
        return cls(MessageType.EYE_DATA, json.dumps(payload).encode('utf-8'))

    @classmethod
    def video_frame(cls, jpeg_bytes: bytes) -> 'Message':
        return cls(MessageType.VIDEO_FRAME, jpeg_bytes)

    @classmethod
    def error(cls, message: str) -> 'Message':
        return cls(MessageType.ERROR, message.encode('utf-8'))

    @classmethod
    def heartbeat(cls) -> 'Message':
        return cls(MessageType.HEARTBEAT, b'')

    def as_command(self) -> Optional[Dict]:
        """Parse payload as JSON command"""
        if self.msg_type not in (MessageType.CMD, MessageType.CMD_ACK):
            return None
        try:
            return json.loads(self.payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None


class FrameCodec:
    """
    Codec for encoding/decoding length-prefixed messages.
    Frame format: [length: u32 BE][type: u8][payload: bytes]
    """
    HEADER_SIZE = 5  # 4 bytes length + 1 byte type
    MAX_PAYLOAD_SIZE = 16 * 1024 * 1024  # 16MB

    @staticmethod
    def encode(msg: Message) -> bytes:
        """Encode a message into bytes"""
        payload_len = len(msg.payload)
        frame_len = 1 + payload_len  # type byte + payload

        # Pack: length (4 bytes BE) + type (1 byte) + payload
        header = struct.pack('>IB', frame_len, msg.msg_type)
        return header + msg.payload

    @staticmethod
    def decode(buffer: bytearray) -> tuple[Optional[Message], int]:
        """
        Try to decode a message from the buffer.

        Returns:
            tuple: (Message or None, bytes consumed)
        """
        if len(buffer) < FrameCodec.HEADER_SIZE:
            return None, 0

        # Read length (big endian u32)
        frame_len = struct.unpack('>I', buffer[:4])[0]

        if frame_len == 0:
            raise ValueError("Frame length cannot be zero")
        if frame_len > FrameCodec.MAX_PAYLOAD_SIZE:
            raise ValueError(f"Frame too large: {frame_len} bytes")

        total_len = 4 + frame_len
        if len(buffer) < total_len:
            return None, 0

        # Read type
        msg_type = MessageType(buffer[4])

        # Read payload
        payload = bytes(buffer[5:total_len])

        return Message(msg_type, payload), total_len


@dataclass
class EyePoint:
    """Eye tracking point data"""
    x: float
    y: float
    radius: float
    confidence: float = 1.0

    def to_dict(self) -> Dict:
        return {
            "x": self.x,
            "y": self.y,
            "radius": self.radius,
            "confidence": self.confidence
        }


@dataclass
class Command:
    """Command structure"""
    cmd: str
    params: Dict[str, Any]

    @classmethod
    def from_message(cls, msg: Message) -> Optional['Command']:
        """Parse a Command from a Message"""
        data = msg.as_command()
        if data is None:
            return None
        return cls(
            cmd=data.get('cmd', ''),
            params=data.get('params', {})
        )
