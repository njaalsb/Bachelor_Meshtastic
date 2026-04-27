#!/usr/bin/env python3
import sys
import meshtastic.serial_interface

def main():
    try:
        iface = meshtastic.serial_interface.SerialInterface(devPath='/dev/ttyACM0')
    except Exception as e:
        print(f"[bridge] Failed to open Meshtastic interface: {e}", flush=True)
        sys.exit(1)

    print("[bridge] Ready.", flush=True)

    try:
        for line in sys.stdin:
            msg = line.rstrip("\n")
            if not msg:
                continue
            try:
                if msg.startswith("DATA:"):
                    _, port_str, hex_str = msg.split(":", 2)
                    payload = bytes.fromhex(hex_str)
                    iface.sendData(payload, portNum=int(port_str), wantAck=False)
                    print(f"[bridge] Sent data port={port_str} bytes={len(payload)}", flush=True)
                else:
                    iface.sendText(msg)
                    print(f"[bridge] Sent: {msg[:40]}...", flush=True)
            except Exception as e:
                print(f"[bridge] Send error: {e}", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        iface.close()
        print("[bridge] Closed.", flush=True)

if __name__ == "__main__":
    main()