#!/usr/bin/env python3
"""
Meshtastic Time Broadcast Receiver
Receives timestamp messages and logs timing data to CSV.
Run this script on the Raspberry Pi connected to Radio 1.
"""

import meshtastic
import meshtastic.serial_interface
from pubsub import pub
from datetime import datetime
import csv
import os
import sys
import time

# =============================================================================
# CONFIGURATION - Edit these settings as needed
# =============================================================================

# Serial port: Set to specific port like '/dev/ttyUSB0' or '/dev/ttyACM0'
# Set to None for auto-detect
SERIAL_PORT = "/dev/ttyACM0"

# CSV file to log timing data
CSV_FILE = "02sek_congestion.csv"

# Node filter: Add node IDs to only listen to specific nodes
# Use node ID format like '!9eeff3a4' (from your debug: 'fromId': '!9eeff3a4')
# Leave empty [] to listen to all nodes
ALLOWED_NODES = [
    '!9eeff3a4',  # Example: Your Radio 2 node ID
    # ''
]

# =============================================================================
# END OF CONFIGURATION
# =============================================================================

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_timestamp(payload):
    """Extract timestamp from payload in format 'TIME:YYYY-MM-DD HH:MM:SS'."""
    # Handle both string and bytes payload
    if isinstance(payload, bytes):
        payload = payload.decode('utf-8', errors='ignore')
    
    payload = str(payload).strip()
    
    if payload.startswith("TIME:"):
        timestamp_str = payload[5:]  # Remove 'TIME:' prefix
        try:
            return datetime.strptime(timestamp_str, TIME_FORMAT)
        except ValueError as e:
            print(f"  Error parsing timestamp '{timestamp_str}': {e}")
            return None
    return None


def log_to_csv(send_time, receive_time, transmission_time, sender_id):
    """Append the timing data to the CSV file."""
    file_exists = os.path.isfile(CSV_FILE)
    
    with open(CSV_FILE, 'a', newline='') as csvfile:
        fieldnames = ['send_time', 'receive_time', 'transmission_time_seconds', 'sender_node']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            'send_time': send_time.strftime(TIME_FORMAT),
            'receive_time': receive_time.strftime(TIME_FORMAT),
            'transmission_time_seconds': f"{transmission_time:.3f}",
            'sender_node': sender_id
        })


def is_allowed_node(from_id):
    """Check if the sender is in the allowed nodes list."""
    if not ALLOWED_NODES:
        return True
    return from_id in ALLOWED_NODES


def on_receive(packet, interface):
    """Callback for all received packets."""
    receive_time = datetime.now()
    
    try:
        from_id = packet.get('fromId', 'unknown')
        
        # Check node filter
        if not is_allowed_node(from_id):
            return
        
        decoded = packet.get('decoded', {})
        portnum = decoded.get('portnum', '')
        
        if portnum != 'TEXT_MESSAGE_APP':
            return
        
        # Try to get the text - check both 'text' and 'payload'
        payload = decoded.get('text') or decoded.get('payload', b'')
        
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8', errors='ignore')
        
        if not payload:
            return
        
        send_time = parse_timestamp(payload)
        
        if send_time:
            transmission_time = (receive_time - send_time).total_seconds()
            log_to_csv(send_time, receive_time, transmission_time, from_id)
            
            print(f"\n{'=' * 50}")
            print(f"Timestamp message received from {from_id}")
            print(f"  Send time:         {send_time.strftime(TIME_FORMAT)}")
            print(f"  Receive time:      {receive_time.strftime(TIME_FORMAT)}")
            print(f"  Transmission time: {transmission_time:.3f} seconds")
            print(f"  Logged to: {CSV_FILE}")
            print(f"{'=' * 50}")
        else:
            print(f"[{receive_time.strftime(TIME_FORMAT)}] From {from_id}: {payload}")
            
    except Exception as e:
        print(f"Error in on_receive: {e}")
        import traceback
        traceback.print_exc()


def on_text_receive(packet, interface):
    """Callback specifically for text messages."""
    # This is triggered by meshtastic.receive.text
    on_receive(packet, interface)


def on_connection(interface, topic=pub.AUTO_TOPIC):
    """Called when we connect to the radio."""
    print("Connected to radio!")


def main():
    print("Meshtastic Time Broadcast Receiver")
    print("=" * 50)
    print(f"Serial port: {SERIAL_PORT or 'Auto-detect'}")
    print(f"Logging to:  {CSV_FILE}")
    if ALLOWED_NODES:
        print(f"Filtering:   Only nodes: {ALLOWED_NODES}")
    else:
        print("Filtering:   Listening to ALL nodes")
    print("=" * 50)
    
    # Subscribe to multiple topics to catch messages
    pub.subscribe(on_receive, "meshtastic.receive")
    pub.subscribe(on_text_receive, "meshtastic.receive.text")
    pub.subscribe(on_connection, "meshtastic.connection.established")
    
    print("\nConnecting to Meshtastic device...")
    
    interface = None
    
    try:
        if SERIAL_PORT:
            interface = meshtastic.serial_interface.SerialInterface(SERIAL_PORT)
        else:
            interface = meshtastic.serial_interface.SerialInterface()
        
        print("Listening for messages... (Press Ctrl+C to stop)\n")
        
        # Keep running
        while True:
            sys.stdout.flush()
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nStopping receiver...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if interface:
            interface.close()
            print("Connection closed.")


if __name__ == "__main__":
    main()
