"""Minimal RFB/VNC server that serves the mock monitor renderer output.

Implements just enough of the RFB 3.3 protocol for vncdotool to connect:
- Protocol version handshake
- No authentication
- ServerInit with framebuffer dimensions
- FramebufferUpdate responses
- PointerEvent / KeyEvent reception
"""

import socket
import struct
import threading
import time
from typing import Optional

import numpy as np

from monitor_eye.mock.renderer import MonitorRenderer


class MockVNCServer:
    """A minimal VNC server that serves rendered monitor frames."""

    RFB_VERSION = b"RFB 003.003\n"
    SECURITY_NONE = 1

    def __init__(self, port: int = 5900, renderer: Optional[MonitorRenderer] = None):
        self.port = port
        self.renderer = renderer or MonitorRenderer()
        self._server_socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the VNC server in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the VNC server and close all connections."""
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=2)

    def _serve(self) -> None:
        """Main server loop: accept connections and spawn handler threads."""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.settimeout(1.0)
        self._server_socket.bind(("0.0.0.0", self.port))
        self._server_socket.listen(5)

        while self._running:
            try:
                client, addr = self._server_socket.accept()
                threading.Thread(
                    target=self._handle_client, args=(client,), daemon=True
                ).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle_client(self, client: socket.socket) -> None:
        """Handle a single VNC client connection through the full RFB lifecycle."""
        try:
            self._handshake(client)
            self._server_init(client)
            self._message_loop(client)
        except (ConnectionResetError, BrokenPipeError, OSError, ConnectionError):
            pass
        finally:
            try:
                client.close()
            except OSError:
                pass

    def _recv_exact(self, client: socket.socket, n: int) -> bytes:
        """Receive exactly n bytes from a socket, handling partial reads."""
        data = b""
        while len(data) < n:
            chunk = client.recv(n - len(data))
            if not chunk:
                raise ConnectionError(
                    f"Connection closed, received {len(data)}/{n} bytes"
                )
            data += chunk
        return data

    def _handshake(self, client: socket.socket) -> None:
        """Perform the RFB 3.3 protocol version and security handshake."""
        # Send protocol version
        client.sendall(self.RFB_VERSION)
        # Receive client version (12 bytes)
        self._recv_exact(client, 12)
        # RFB 3.3: server decides security type, send as U32
        client.sendall(struct.pack("!I", self.SECURITY_NONE))

    def _server_init(self, client: socket.socket) -> None:
        """Send ServerInit message with framebuffer dimensions and pixel format."""
        # Receive ClientInit (1 byte: shared flag)
        self._recv_exact(client, 1)

        w = self.renderer.width
        h = self.renderer.height

        # Pixel format: 32bpp, depth 24, little-endian, true-colour
        # RGB max values 255 each, shifts: R=16, G=8, B=0
        pixel_format = struct.pack(
            "!BBBBHHHBBBxxx",
            32,             # bits-per-pixel
            24,             # depth
            0,              # big-endian flag (0 = little-endian)
            1,              # true-colour flag
            255, 255, 255,  # red-max, green-max, blue-max
            16, 8, 0,       # red-shift, green-shift, blue-shift
        )

        name = b"MonitorEye Mock"
        # ServerInit: width(U16) + height(U16) + pixel_format(16 bytes) + name_len(U32) + name
        header = struct.pack("!HH", w, h) + pixel_format
        header += struct.pack("!I", len(name)) + name
        client.sendall(header)

    def _message_loop(self, client: socket.socket) -> None:
        """Process incoming client messages and respond to framebuffer requests."""
        client.settimeout(1.0)
        while self._running:
            try:
                msg_type_data = client.recv(1)
                if not msg_type_data:
                    break
                msg_type = msg_type_data[0]

                if msg_type == 0:  # SetPixelFormat
                    self._recv_exact(client, 19)  # 3 padding + 16 pixel format
                elif msg_type == 2:  # SetEncodings
                    padding_and_count = self._recv_exact(client, 3)
                    n_enc = struct.unpack("!xH", padding_and_count)[0]
                    self._recv_exact(client, n_enc * 4)
                elif msg_type == 3:  # FramebufferUpdateRequest
                    self._recv_exact(client, 9)
                    self._send_framebuffer_update(client)
                elif msg_type == 4:  # KeyEvent
                    self._recv_exact(client, 7)
                elif msg_type == 5:  # PointerEvent
                    data = self._recv_exact(client, 5)
                    button_mask, x, y = struct.unpack("!BHH", data)
                    self._handle_pointer(button_mask, x, y)
                elif msg_type == 6:  # ClientCutText
                    self._recv_exact(client, 3)  # padding
                    length_data = self._recv_exact(client, 4)
                    text_len = struct.unpack("!I", length_data)[0]
                    self._recv_exact(client, text_len)
                else:
                    # Unknown message type, skip
                    break
            except socket.timeout:
                self.renderer.tick()
                continue

    def _send_framebuffer_update(self, client: socket.socket) -> None:
        """Render and send a full framebuffer update to the client."""
        frame = self.renderer.render()
        h, w = frame.shape[:2]

        # Convert BGR (from renderer) to BGRA for 32bpp pixel format
        # The pixel format has R-shift=16, G-shift=8, B-shift=0
        # In memory order (little-endian 32-bit): B, G, R, A
        bgra = np.zeros((h, w, 4), dtype=np.uint8)
        bgra[:, :, 0] = frame[:, :, 0]  # B
        bgra[:, :, 1] = frame[:, :, 1]  # G
        bgra[:, :, 2] = frame[:, :, 2]  # R
        bgra[:, :, 3] = 255             # A (unused padding)
        raw_pixels = bgra.tobytes()

        # FramebufferUpdate: type(U8=0) + padding(U8) + nRects(U16=1)
        fb_header = struct.pack("!BxH", 0, 1)
        # Rectangle: x(U16) + y(U16) + w(U16) + h(U16) + encoding(I32=0 raw)
        rect_header = struct.pack("!HHHHi", 0, 0, w, h, 0)
        client.sendall(fb_header + rect_header + raw_pixels)

    def _handle_pointer(self, button_mask: int, x: int, y: int) -> None:
        """Handle pointer/mouse events from the client."""
        if button_mask & 1:  # left click
            # Check if click is on the SILENCE button area
            if 650 <= x <= 780 and 550 <= y <= 590:
                self.renderer.silence_alarm()
