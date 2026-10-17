import socket
import struct
import time
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

# Register Bayer formats into pyGigEVision
PFNC_BAYER_RG8 = 0x01080009
PFNC_BAYER_GB8 = 0x0108000A
PFNC_BAYER_GR8 = 0x01080008
PFNC_BAYER_BG8 = 0x0108000B

for fmt in [PFNC_BAYER_RG8, PFNC_BAYER_GB8, PFNC_BAYER_GR8, PFNC_BAYER_BG8]:
    gvsp.PIXEL_BPP[fmt] = 1
    gvsp.PIXEL_DTYPE[fmt] = np.uint8

CAMERA_IP = "169.254.123.85"
HOST_IP = "169.254.128.78"
REG_ACQ_START_STOP = 0x82000004  # 0 = Start, 1 = Stop
REG_ACQ_MODE = 0x82000038        # 0 = Continuous, 1 = SingleFrame
REG_PAYLOAD_SIZE = 0x88010100
REG_PIXEL_FORMAT = 0x8200002C

def ip_to_uint32(ip_str):
    return struct.unpack('>I', socket.inet_aton(ip_str))[0]

def test_capture(delay=5000, packet_size=1440):
    print("=" * 65)
    print(f"  TESTING BAUMER CAPTURE (Delay: {delay} ticks, PktSize: {packet_size})")
    print("=" * 65)
    client = gv.GVCPClient(CAMERA_IP, local_ip=HOST_IP, timeout=2.0)
    client.connect()

    try:
        receiver = gv.GVSPReceiver(
            local_ip=HOST_IP,
            camera_ip=CAMERA_IP,
            packet_size=packet_size,
            initial_packet_timeout=0.015,
            frame_retention=0.8
        )
        receiver.start()

        # Stream Channel 0 config
        client.write_reg(REG_HEARTBEAT_TIMEOUT, 3000)
        client.write_reg(REG_SC_DEST_ADDR, ip_to_uint32(HOST_IP))
        client.write_reg(REG_SC_HOST_PORT, receiver.port)
        client.write_reg(REG_SC_PACKET_SIZE, packet_size)
        client.write_reg(REG_SC_PACKET_DELAY, delay)

        # Set SingleFrame mode
        client.write_reg(REG_ACQ_MODE, 1)

        print("\nTriggering Frame Capture...")
        client.write_reg(REG_ACQ_START_STOP, 0)

        res = receiver.get_frame_with_info(timeout=4.0)

        try:
            client.write_reg(REG_ACQ_START_STOP, 1)
        except Exception:
            pass

        receiver.stop()
        receiver.close()

        if res is not None:
            raw_frame, info = res
            missing = info.get('missing_packets', 0)
            complete = info.get('complete', False)
            print(f"\n🎉 Frame Result: Missing={missing}, Complete={complete}")

            h, w = info.get("height", 1536), info.get("width", 2048)
            img = raw_frame.reshape((h, w))
            bgr = cv2.cvtColor(img, cv2.COLOR_BayerRG2BGR)

            out_file = "baumer_captured_frame.jpg"
            cv2.imwrite(out_file, bgr)
            print(f"   Saved {w}x{h} frame to {out_file}")
            return complete
        else:
            print("❌ No frame received within timeout.")
            return False

    finally:
        try:
            client.disconnect()
        except Exception:
            pass

if __name__ == "__main__":
    test_capture(delay=6000, packet_size=1440)
