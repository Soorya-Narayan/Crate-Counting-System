"""
Baumer VCXG.2-32C GigE Camera Driver for macOS
==============================================
Client: Milma Kottayam Dairy
Company: Goose Industrial Solutions

Handles GigE Vision 2.0 communication, control channel privilege,
stream configuration, Bayer demosaicing, and packet pacing on macOS.
"""

import time
import socket
import struct
import threading
import logging
import cv2
import numpy as np
import pyGigEVision as gv
import pyGigEVision.gvsp as gvsp
from pyGigEVision.standard import (
    REG_CCP,
    REG_HEARTBEAT_TIMEOUT,
    REG_SC_HOST_PORT,
    REG_SC_PACKET_SIZE,
    REG_SC_DEST_ADDR,
    REG_SC_PACKET_DELAY,
)

logger = logging.getLogger("BaumerCamera")

# Ensure Bayer formats are registered into pyGigEVision
PFNC_BAYER_RG8 = 0x01080009
PFNC_BAYER_GB8 = 0x0108000A
PFNC_BAYER_GR8 = 0x01080008
PFNC_BAYER_BG8 = 0x0108000B

for fmt in [PFNC_BAYER_RG8, PFNC_BAYER_GB8, PFNC_BAYER_GR8, PFNC_BAYER_BG8]:
    gvsp.PIXEL_BPP[fmt] = 1
    gvsp.PIXEL_DTYPE[fmt] = np.uint8

# Standard Baumer registers
REG_ACQ_START_STOP = 0x82000004   # 0 = Start, 1 = Stop
REG_ACQ_MODE = 0x82000038         # 0 = Continuous, 1 = SingleFrame
REG_PAYLOAD_SIZE = 0x88010100     # 3145728 bytes
REG_PIXEL_FORMAT = 0x8200002C     # 0x01080009 (BayerRG8)
REG_EXPOSURE_TIME = 0x82000008    # In microseconds (us)


def ip_to_uint32(ip_str: str) -> int:
    return struct.unpack('>I', socket.inet_aton(ip_str))[0]


class BaumerCamera:
    def __init__(self, camera_ip="169.254.123.85", host_ip="169.254.128.78", packet_size=1440, packet_delay=42000):
        self.camera_ip = camera_ip
        self.host_ip = host_ip
        self.packet_size = packet_size
        self.packet_delay = packet_delay
        self.client = None
        self.receiver = None
        self.is_streaming = False
        self.width = 2048
        self.height = 1536
        self.current_exposure_us = 25000  # Default 25 ms
        self._lock = threading.Lock()

    def connect(self):
        """Connect to camera via GVCP and claim control privilege."""
        with self._lock:
            if self.client is not None:
                return True
            print(f"Connecting to Baumer VCXG.2-32C at {self.camera_ip}...")
            self.client = gv.GVCPClient(self.camera_ip, local_ip=self.host_ip, timeout=2.0)
            self.client.connect()
            print("✓ Connected. Acquired CCP control.")

            # Read current settings
            try:
                self.current_exposure_us = self.client.read_reg(REG_EXPOSURE_TIME)
                if self.current_exposure_us < 10000:
                    self.set_exposure_time(25000)
            except Exception:
                pass
            return True

    def set_exposure_time(self, exposure_us: int):
        """Set exposure time in microseconds (e.g. 20000 = 20ms)."""
        with self._lock:
            if self.client:
                exposure_us = max(500, min(100000, exposure_us))
                self.client.write_reg(REG_EXPOSURE_TIME, int(exposure_us))
                self.current_exposure_us = exposure_us
                print(f"Exposure set to {exposure_us / 1000.0:.1f} ms ({exposure_us} µs)")

    def start_stream(self):
        """Configure stream channel and start continuous acquisition."""
        with self._lock:
            if not self.client:
                raise RuntimeError("Camera not connected. Call connect() first.")
            if self.is_streaming:
                return

            print("Configuring Stream Channel 0 and starting receiver...")
            self.receiver = gv.GVSPReceiver(
                local_ip=self.host_ip,
                camera_ip=self.camera_ip,
                packet_size=self.packet_size,
                initial_packet_timeout=0.015,
                frame_retention=0.4
            )
            self.receiver.start()

            # Stream Channel 0 config
            self.client.write_reg(REG_HEARTBEAT_TIMEOUT, 3000)
            self.client.write_reg(REG_SC_DEST_ADDR, ip_to_uint32(self.host_ip))
            self.client.write_reg(REG_SC_HOST_PORT, self.receiver.port)
            self.client.write_reg(REG_SC_PACKET_SIZE, self.packet_size)
            self.client.write_reg(REG_SC_PACKET_DELAY, self.packet_delay)

            # Continuous Acquisition mode
            self.client.write_reg(REG_ACQ_MODE, 0)
            # Acquisition Start
            self.client.write_reg(REG_ACQ_START_STOP, 0)
            self.is_streaming = True
            print("✓ Continuous video acquisition active.")

    def get_frame(self, timeout=2.0):
        """
        Retrieve next frame from the camera.
        Returns: (bgr_image, metadata_dict) or (None, None)
        """
        if not self.is_streaming or not self.receiver:
            return None, None

        res = self.receiver.get_frame_with_info(timeout=timeout)
        if res is None:
            return None, None

        raw_frame, info = res
        h = info.get("height", self.height)
        w = info.get("width", self.width)
        self.height, self.width = h, w

        try:
            # Reshape raw 1D array to 2D Bayer
            bayer_img = raw_frame.reshape((h, w))
            # Demosaic BayerRG8 to BGR color for OpenCV
            bgr_img = cv2.cvtColor(bayer_img, cv2.COLOR_BayerRG2BGR)
            return bgr_img, info
        except Exception as e:
            logger.warning(f"Error processing frame: {e}")
            return None, None

    def stop_stream(self):
        """Stop video acquisition and release stream receiver."""
        with self._lock:
            if not self.is_streaming:
                return
            self.is_streaming = False
            try:
                if self.client:
                    self.client.write_reg(REG_ACQ_START_STOP, 1)
            except Exception:
                pass

            if self.receiver:
                try:
                    self.receiver.stop()
                    self.receiver.close()
                except Exception:
                    pass
                self.receiver = None
            print("✓ Camera stream stopped.")

    def disconnect(self):
        """Stop stream and release camera control."""
        self.stop_stream()
        with self._lock:
            if self.client:
                try:
                    self.client.disconnect()
                except Exception:
                    pass
                self.client = None
            print("✓ Disconnected from Baumer camera.")
