#!/usr/bin/env python3
import sys
import meshtastic.serial_interface

def main():
    print("Starting Meshtastic Bridge...", file=sys.stderr)
    try:
        # Initialize the radio connection ONCE
        interface = meshtastic.serial_interface.SerialInterface(devPath='/dev/ttyACM0')
        print("Connected to Radio. Ready for messages.", file=sys.stderr)
    except Exception as e:
        print(f"FATAL: Could not connect to radio: {e}", file=sys.stderr)
        sys.exit(1)

    # Listen to stdin (fed by the C++ QProcess)
    try:
        for line in sys.stdin:
            msg = line.strip()
            if msg:
                try:
                    # Send to channel 0
                    interface.sendText(msg, wantAck=True)
                    print(f"Sent: {msg[:30]}...", file=sys.stderr)
                    sys.stderr.flush()
                except Exception as e:
                    print(f"Error sending message: {e}", file=sys.stderr)
    except KeyboardInterrupt:
        pass
    finally:
        interface.close()

if __name__ == "__main__":
    main()