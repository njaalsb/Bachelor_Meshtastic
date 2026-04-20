#!/usr/bin/env python3
"""
Meshtastic Time Broadcast Sender
Sends a broadcast message containing the current date and time every 60 seconds.
Run this script on the computer connected to Radio 2.
"""

import meshtastic
import meshtastic.serial_interface
from datetime import datetime
import time
import sys

# Configuration
SEND_INTERVAL = 30  # seconds between messages
SERIAL_PORT = None  # Set to specific port like '/dev/ttyUSB0' or 'COM3', or None for auto-detect

def get_timestamp():
    """Return current timestamp in ISO format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    print("Meshtastic Time Broadcast Sender")
    print("=" * 40)
    
    try:
        # Connect to the Meshtastic device
        if SERIAL_PORT:
            interface = meshtastic.serial_interface.SerialInterface(SERIAL_PORT)
        else:
            interface = meshtastic.serial_interface.SerialInterface()
        
        print(f"Connected to Meshtastic device")
        print(f"Sending timestamp broadcast every {SEND_INTERVAL} seconds")
        print("Press Ctrl+C to stop\n")
        
        while True:
            timestamp = get_timestamp()
            message = f"TIME:{timestamp}"
            
            # Send broadcast message (no destination = broadcast to all)
            interface.sendText(message)
            print(f"[{timestamp}] Sent: {message}")
            
            time.sleep(SEND_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nStopping sender...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'interface' in locals():
            interface.close()
            print("Connection closed.")

if __name__ == "__main__":
    main()
