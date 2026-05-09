import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import csv
import os
import time
from datetime import datetime

CSV_FILE = "direct_packets.csv"
FIELDNAMES = ["timestamp", "from_node", "portnum", "snr", "rssi", "hops"]

def ensure_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()

def on_receive(packet, interface):
    try:
        hop_start = packet.get("hopStart", 0)
        hop_limit = packet.get("hopLimit", 0)
        hops = hop_start - hop_limit

        if hops != 0:
            return  # Ignore anything that was relayed

        snr  = packet.get("rxSnr")
        rssi = packet.get("rxRssi")
        portnum = packet.get("decoded", {}).get("portnum", "UNKNOWN")

        row = {
            "timestamp": datetime.now().isoformat(),
            "from_node": hex(packet.get("from", 0)),
            "portnum":   portnum,
            "snr":       snr if snr is not None else "N/A",
            "rssi":      rssi if rssi is not None else "N/A",
            "hops":      hops,
        }

        with open(CSV_FILE, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writerow(row)

        print(f"[{row['timestamp']}] FROM={row['from_node']} | PORT={portnum} | SNR={row['snr']} | RSSI={row['rssi']}")

    except Exception as e:
        print(f"Error processing packet: {e}")

def main():
    ensure_csv()
    print(f"Logging direct (0-hop) packets to {CSV_FILE} ...")
    print("Ctrl+C to stop.\n")

    iface = meshtastic.serial_interface.SerialInterface()
    pub.subscribe(on_receive, "meshtastic.receive")
    print(f"Connected to: {iface.getMyNodeInfo()['user']['longName']}\n")

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        iface.close()

if __name__ == "__main__":
    main()