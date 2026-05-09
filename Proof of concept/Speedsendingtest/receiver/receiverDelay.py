import meshtastic
import meshtastic.serial_interface
import csv
import re
import signal
import sys
from pubsub import pub
import time

# Configuration
CSV_FILE = 'longfast_meshtastic_test_results_1seconds_231bytes.csv'

# State tracking
received_count = 0
last_seq = 0
results = []

def on_receive(packet, interface):
    global received_count, last_seq
    try:
        if 'decoded' in packet and packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
            message = packet['decoded']['text']
            # Calculate actual received size
            msg_size = len(message.encode('utf-8')) 
            
            match = re.search(r'Packet (\d+)/', message)
            if match:
                current_seq = int(match.group(1))
                received_count += 1
                

                # Updated print to show byte size
                print(f"Received: {current_seq} | Size: {msg_size} bytes | RSSI: {packet.get('rxRssi', 'N/A')}")
                
                # Save as before
                results.append([current_seq, "SUCCESS", packet.get('rxRssi', 'N/A')])
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
pub.subscribe(on_receive, "meshtastic.receive")
interface = meshtastic.serial_interface.SerialInterface()

print(f"Listening for packets")

# Keep the script running
while True:
    time.sleep(1)