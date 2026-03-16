#!/usr/bin/env python3
"""
Simple helper: use Meshtastic CLI to send a text packet.
Usage:    meshtastic_notify.py "your message here"
"""
import sys
import subprocess

def send_alert(msg):
    result = subprocess.run(["/home/meshtastic/meshtastic-venv/bin/meshtastic", "--sendtext", msg, "--channel", "0"], capture_output=True, text=True, timeout=10)
    print(f"Return code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
    else:
        print(f"Sent: {msg}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        send_alert(" ".join(sys.argv[1:]))