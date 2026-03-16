import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import threading
import time
from datetime import datetime
import csv
import os

# -------------------------
# Configuration
# -------------------------
CSV_FILE = "meshtastic_range_test.csv"

CSV_HEADERS = [
    "timestamp", "packet_type", "from_id", "from_name", "text", 
    "rssi", "snr", "hop_limit", "lat", "lon", "alt", "battery", "channel"
]

def log_to_csv(data):
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        row = {h: "" for h in CSV_HEADERS}
        row.update({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **data})
        writer.writerow(row)

def on_receive(packet, interface):
    decoded = packet.get("decoded", {})
    portnum = decoded.get("portnum")
    from_id = packet.get("from")
    
    node_info = interface.nodes.get(from_id, {})
    user_info = node_info.get("user", {})
    long_name = user_info.get("longName", str(from_id))

    stats = {
        "from_id": from_id,
        "from_name": long_name,
        "rssi": packet.get("rxRssi"),
        "snr": packet.get("rxSnr"),
        "hop_limit": packet.get("hopLimit"),
        "channel": packet.get("channel")
    }

    if portnum == "TEXT_MESSAGE_APP":
        msg_text = decoded.get("text")
        
        # Ignore our own echos to prevent an infinite loop!
        if msg_text.startswith("Echo:"):
            return

        print(f"📩 [{datetime.now().strftime('%H:%M:%S')}] Text from {long_name}: {msg_text}")
        
        stats.update({"packet_type": "TEXT", "text": msg_text})
        log_to_csv(stats)

        # BROADCAST ECHO LOGIC
        def send_broadcast_echo():
            time.sleep(2)
            print(f"📢 Broadcasting echo for {long_name} to Channel 0...")
            try:
                # Removing destinationId makes it a broadcast to the default channel
                # wantAck=False is used because broadcasts don't support ACKs
                interface.sendText(
                    f"Echo: {long_name} sent {msg_text}", 
                    wantAck=False
                )
            except Exception as e:
                print(f"❌ Failed to broadcast: {e}")
        
        threading.Thread(target=send_broadcast_echo).start()

    elif portnum == "POSITION_APP":
        pos = decoded.get("position", {})
        print(f"📍 Position update from {long_name}")
        stats.update({
            "packet_type": "POSITION",
            "lat": pos.get("latitude"),
            "lon": pos.get("longitude"),
            "alt": pos.get("altitude")
        })
        log_to_csv(stats)

    elif portnum == "TELEMETRY_APP":
        tel = decoded.get("telemetry", {}).get("deviceMetrics", {})
        print(f"🔋 Battery update from {long_name}: {tel.get('batteryLevel')}%")
        stats.update({
            "packet_type": "TELEMETRY",
            "battery": tel.get("batteryLevel")
        })
        log_to_csv(stats)

def main():
    print("--- Meshtastic Broadcast Echo & Logger Started ---")
    print(f"Logging to: {os.path.abspath(CSV_FILE)}")
    
    try:
        iface = meshtastic.serial_interface.SerialInterface()
        pub.subscribe(on_receive, "meshtastic.receive")
        print("Listening for packets... Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    main()
