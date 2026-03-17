import meshtastic
import threading
import meshtastic.serial_interface
from pubsub import pub
import csv
import os
from datetime import datetime

# --- CONFIGURATION ---
# Set this to the Node ID you want to IGNORE (e.g., "!abcdef12")
# Set to None if you want to log every single node seen.
EXCLUDED_NODE_ID = "!720472da" 
CSV_FILE = "battery_log.csv"

def on_receive(packet, interface):
    try:
        # Check if the packet contains telemetry/device metrics
        if 'decoded' in packet and packet['decoded'].get('portnum') == 'TELEMETRY_APP':
            telemetry = packet['decoded'].get('telemetry')
            
            # Check if it contains device metrics (battery info)
            if telemetry and 'deviceMetrics' in telemetry:
                node_id = packet.get('fromId')
                metrics = telemetry['deviceMetrics']
                
                # --- EXCLUSION LOGIC ---
                # If the current packet is from our excluded ID, stop here.
                if EXCLUDED_NODE_ID and node_id == EXCLUDED_NODE_ID:
                    return

                battery_level = metrics.get('batteryLevel')
                voltage = metrics.get('voltage')
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Save to CSV
                file_exists = os.path.isfile(CSV_FILE)
                with open(CSV_FILE, mode='a', newline='') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(['Timestamp', 'NodeID', 'Battery%', 'Voltage(V)'])
                    
                    writer.writerow([timestamp, node_id, battery_level, voltage])
                
                print(f"Logged: Node {node_id} at {battery_level}% ({voltage}V)")

    except Exception as e:
        print(f"Error processing packet: {e}")

# Initialize the radio interface
interface = meshtastic.serial_interface.SerialInterface()

# Subscribe to all incoming messages
pub.subscribe(on_receive, "meshtastic.receive")

print(f"Listening for battery data...")
if EXCLUDED_NODE_ID:
    print(f"Ignoring data from: {EXCLUDED_NODE_ID}")
else:
    print("Logging data from ALL nodes.")
print("Press Ctrl+C to stop.")

# Keep the script running
stop_event = threading.Event()

try:
    while True:
        print("Listening for battery data... Press Ctrl+C to stop")
        stop_event.wait()
except KeyboardInterrupt:
    print("\nClosing connection...")
    interface.close()
