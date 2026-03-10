#!/usr/bin/env python3
"""
Simple helper: open the first Meshtastic interface and send a text packet.
Usage:    meshtastic_notify.py "your message here"
Optionally you may pipe a JSON object with a “message” field on stdin.
"""
import sys
import json
import meshtastic.serial_interface

def send_alert(msg):
    iface = meshtastic.serial_interface.SerialInterface()
    iface.sendText(msg)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        send_alert(" ".join(sys.argv[1:]))
    else:
        try:
            data = json.load(sys.stdin)
            send_alert(data.get("message",""))
        except Exception:
            pass