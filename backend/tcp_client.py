"""
TCP Client for connecting to the Rust orchestrator.
Handles connection, reconnection with backoff, and message framing.
"""
import asyncio
import logging
from typing import Optional, AsyncIterator, Callable, Awaitable

from protocol import Message, FrameCodec, MessageType

logger = logging.getLogger(__name__)

# TCP connection settings for Rust orchestrator
# Must match the values in src-tauri/src/bridge/tcp_server.rs
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9999  # Rust TCP server listens on this port
READ_BUFFER_SIZE = 64 * 1024


class TcpClient:
    """Async TCP client for communication with Rust orchestrator"""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._read_buffer = bytearray()
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 30.0
        self._should_reconnect = True

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """
        Connect to the Rust TCP server.

        Returns:
            bool: True if connection successful
        """
        try:
            logger.info(f"Connecting to {self.host}:{self.port}...")
            self._reader, self._writer = await asyncio.open_connection(
                self.host, self.port
            )
            self._connected = True
            self._reconnect_delay = 1.0  # Reset backoff on successful connection
            logger.info(f"Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._connected = False
            return False

    async def connect_with_retry(self, max_attempts: int = 0) -> bool:
        """
        Connect with automatic retry and exponential backoff.

        Args:
            max_attempts: Maximum number of attempts (0 = infinite)

        Returns:
            bool: True if connection successful
        """
        attempts = 0
        while self._should_reconnect:
            if await self.connect():
                return True

            attempts += 1
            if max_attempts > 0 and attempts >= max_attempts:
                logger.error(f"Max reconnection attempts ({max_attempts}) reached")
                return False

            logger.info(f"Retrying in {self._reconnect_delay:.1f}s...")
            await asyncio.sleep(self._reconnect_delay)

            # Exponential backoff
            self._reconnect_delay = min(
                self._reconnect_delay * 2, self._max_reconnect_delay
            )

        return False

    async def send(self, msg: Message) -> bool:
        """
        Send a message to the server.

        Args:
            msg: Message to send

        Returns:
            bool: True if send successful
        """
        if not self._connected or self._writer is None:
            logger.warning("Cannot send: not connected")
            return False

        try:
            data = FrameCodec.encode(msg)
            self._writer.write(data)
            await self._writer.drain()
            return True
        except Exception as e:
            logger.error(f"Send error: {e}")
            await self._handle_disconnect()
            return False

    async def send_eye_data(
        self, timestamp: int, left: Optional[dict] = None, right: Optional[dict] = None
    ) -> bool:
        """Send eye tracking data"""
        msg = Message.eye_data(timestamp, left, right)
        return await self.send(msg)

    async def send_frame(self, jpeg_bytes: bytes) -> bool:
        """Send video frame (JPEG bytes)"""
        msg = Message.video_frame(jpeg_bytes)
        return await self.send(msg)

    async def send_ack(
        self, success: bool, data: any = None, error: Optional[str] = None
    ) -> bool:
        """Send command acknowledgment"""
        msg = Message.cmd_ack(success, data, error)
        return await self.send(msg)

    async def send_error(self, message: str) -> bool:
        """Send error message"""
        msg = Message.error(message)
        return await self.send(msg)

    async def send_heartbeat(self) -> bool:
        """Send heartbeat"""
        msg = Message.heartbeat()
        return await self.send(msg)

    async def recv(self) -> Optional[Message]:
        """
        Receive a single message.

        Returns:
            Message or None if disconnected
        """
        if not self._connected or self._reader is None:
            return None

        try:
            # Try to decode from existing buffer first
            msg, consumed = FrameCodec.decode(self._read_buffer)
            if msg is not None:
                del self._read_buffer[:consumed]
                return msg

            # Need more data
            while True:
                data = await self._reader.read(READ_BUFFER_SIZE)
                if not data:
                    # EOF - server closed connection
                    await self._handle_disconnect()
                    return None

                self._read_buffer.extend(data)

                msg, consumed = FrameCodec.decode(self._read_buffer)
                if msg is not None:
                    del self._read_buffer[:consumed]
                    return msg

        except Exception as e:
            logger.error(f"Receive error: {e}")
            await self._handle_disconnect()
            return None

    async def messages(self) -> AsyncIterator[Message]:
        """
        Async iterator for receiving messages.

        Yields:
            Message objects as they arrive
        """
        while self._connected:
            msg = await self.recv()
            if msg is None:
                break
            yield msg

    async def close(self):
        """Close the connection"""
        self._should_reconnect = False
        self._connected = False

        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass

        self._reader = None
        self._writer = None
        self._read_buffer.clear()
        logger.info("Connection closed")

    async def _handle_disconnect(self):
        """Handle disconnection"""
        was_connected = self._connected
        self._connected = False

        if self._writer is not None:
            try:
                self._writer.close()
            except Exception:
                pass

        self._reader = None
        self._writer = None
        self._read_buffer.clear()

        if was_connected:
            logger.warning("Disconnected from server")


class ReconnectingTcpClient(TcpClient):
    """
    TCP client with automatic reconnection.
    Wraps TcpClient and handles reconnection transparently.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        on_connect: Optional[Callable[[], Awaitable[None]]] = None,
        on_disconnect: Optional[Callable[[], Awaitable[None]]] = None,
    ):
        super().__init__(host, port)
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._reconnect_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the client with auto-reconnection"""
        self._should_reconnect = True
        await self._connection_loop()

    async def _connection_loop(self):
        """Main connection loop with auto-reconnection"""
        while self._should_reconnect:
            if not self._connected:
                if await self.connect():
                    if self._on_connect:
                        await self._on_connect()
                else:
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(
                        self._reconnect_delay * 2, self._max_reconnect_delay
                    )
                    continue

            # Wait for disconnect
            while self._connected and self._should_reconnect:
                await asyncio.sleep(0.1)

            # Handle disconnect
            if self._on_disconnect and self._should_reconnect:
                await self._on_disconnect()

            self._reconnect_delay = 1.0

    async def _handle_disconnect(self):
        """Override to trigger reconnection"""
        await super()._handle_disconnect()
        # Connection loop will handle reconnection

    async def stop(self):
        """Stop the client and close connection"""
        await self.close()
