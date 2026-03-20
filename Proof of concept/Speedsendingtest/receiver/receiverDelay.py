import meshtastic
import meshtastic.serial_interface
import csv
import re
import signal
import sys
from pubsub import pub
import time

# Configuration
DEV_PATH = '/dev/ttyACM0'  # Change if your receiver is on a different port
CSV_FILE = 'meshtastic_test_results.csv'

# State tracking
received_count = 0
last_seq = 0
results = []

def on_receive(packet, interface):
    global received_count, last_seq
    
    try:
        if 'decoded' in packet and packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
            message = packet['decoded']['text']
            
            # Use regex to find the number in "Test Packet X/100"
            match = re.search(r'Packet (\d+)/', message)
            if match:
                current_seq = int(match.group(1))
                received_count += 1
                
                # Check for gaps (Missing Packets)
                # If current_seq is more than 1 higher than last_seq, we missed some
                if last_seq != 0 and current_seq > last_seq + 1:
                    for missing in range(last_seq + 1, current_seq):
                        print(f"--- Packet {missing} MISSING ---")
                        results.append([missing, "NA", "LOST"])
                
                print(f"Received: {message} (RSSI: {packet.get('rxRssi', 'N/A')} dBm)")
                results.append([current_seq, message, packet.get('rxRssi', 'N/A')])
                last_seq = current_seq

    except Exception as e:
        print(f"Error processing packet: {e}")

def signal_handler(sig, frame):
    """Handles Ctrl+C to save data and exit"""
    print(f"\n\nTest Stopped.")
    print(f"Total packets successfully received: {received_count}")
    
    # Save to CSV
    keys = ['Sequence', 'Message', 'RSSI']
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(keys)
        writer.writerows(results)
    
    print(f"Data saved to {CSV_FILE}. Exiting...")
    sys.exit(0)

# Setup Listener
signal.signal(signal.SIGINT, signal_handler)
interface = meshtastic.serial_interface.SerialInterface(devPath=DEV_PATH)
pub.subscribe(on_receive, "meshtastic.receive")

print(f"Listening for packets on {DEV_PATH}... Press Ctrl+C to stop.")

# Keep the script running
while True:
    time.sleep(1)