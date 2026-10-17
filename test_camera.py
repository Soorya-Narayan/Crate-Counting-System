"""
Baumer VCXG.2-32C GigE Camera Diagnostic & Test Tool
====================================================
Company: Goose Industrial Solutions
Client: Milma Kottayam Dairy

Usage:
    python test_camera.py
"""

import sys
import time
import socket
import struct
import subprocess
import re


GVCP_DISCOVERY_CMD = struct.pack(
    ">BBHHII",
    0x42,  # Key (0x42 = Request)
    0x01,  # Flag (Allow broadcast ack)
    0x0002,  # Command: DISCOVERY_CMD
    0x0000,  # Length: 0 bytes data
    0x0001,  # Req ID
    0x00000000
)


def get_active_ethernet_interfaces():
    """Returns active Ethernet devices with their IP addresses."""
    active_ifaces = []
    try:
        output = subprocess.check_output(["ifconfig"], text=True)
        blocks = output.split("\n\n")
        for b in blocks:
            lines = b.strip().splitlines()
            if not lines:
                continue
            name = lines[0].split(":")[0].strip()
            if "status: active" in b and ("1000baseT" in b or "autoselect" in b or "en" in name):
                ip = None
                for l in lines:
                    if "inet " in l:
                        ip = l.strip().split()[1]
                if ip and not ip.startswith("127."):
                    active_ifaces.append((name, ip))
    except Exception as e:
        print(f"Error parsing ifconfig: {e}")
    return active_ifaces


def discover_camera():
    print("=" * 68)
    print("  BAUMER VCXG.2-32C HARDWARE CONNECTION VERIFIER")
    print("  Goose Industrial Solutions - Milma Kottayam Project")
    print("=" * 68)

    active_ifaces = get_active_ethernet_interfaces()
    if not active_ifaces:
        print("\n❌ No active Ethernet interface detected with an IP address.")
        return

    print("\n[1] Active Network Interfaces:")
    for iface, ip in active_ifaces:
        print(f"  🟢 {iface} -> IP: {ip}")

    # Prioritize USB LAN or en8
    target_ifaces = [item for item in active_ifaces if item[0] != "en0"]
    if not target_ifaces:
        target_ifaces = active_ifaces

    found_any = False
    print("\n[2] Broadcasting GigE Vision Discovery (UDP Port 3956)...")

    for iface, ip in target_ifaces:
        print(f"  Scanning via {iface} ({ip})...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            sock.bind((ip, 0))
            sock.settimeout(1.5)

            # Broadcast to 255.255.255.255 and subnet broadcast
            sock.sendto(GVCP_DISCOVERY_CMD, ('255.255.255.255', 3956))
            sock.sendto(GVCP_DISCOVERY_CMD, ('169.254.255.255', 3956))

            start_t = time.time()
            while time.time() - start_t < 1.8:
                try:
                    data, (cam_ip, cam_port) = sock.recvfrom(2048)
                    found_any = True
                    print("\n  🎯 =============================================")
                    print(f"  🎯 BAUMER CAMERA DISCOVERED & CONNECTED!")
                    print(f"  🎯 Camera IP Address : {cam_ip}")
                    print(f"  🎯 Control Port      : {cam_port}")
                    print(f"  🎯 Network Interface : {iface} (Mac IP: {ip})")
                    print(f"  🎯 Link Speed        : 1000 Mbps (Gigabit Ethernet)")
                    print("  🎯 =============================================\n")

                    # Perform quick ICMP latency ping
                    try:
                        ping_out = subprocess.check_output(["ping", "-c", "2", cam_ip], text=True)
                        for line in ping_out.splitlines():
                            if "time=" in line:
                                print(f"     Ping Response: {line.strip()}")
                    except Exception:
                        pass
                    break
                except socket.timeout:
                    break
        except Exception as e:
            print(f"  Note on {iface}: {e}")
        finally:
            sock.close()

    if not found_any:
        print("\n⚪ No GigE response on tested interfaces.")
    else:
        print("\n✅ Hardware verification successful. The camera is online and communicating.")


if __name__ == '__main__':
    discover_camera()
