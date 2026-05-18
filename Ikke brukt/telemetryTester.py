import csv, time
from datetime import datetime, timezone
import meshtastic.serial_interface
from pubsub import pub

CSV_PATH = "battery_log.csv"

def on_receive(packet, interface):
    decoded = packet.get("decoded", {})
    dm = decoded.get("deviceMetrics") or decoded.get("device_metrics")
    if not dm:
        return

    batt = dm.get("batteryLevel") or dm.get("battery_level")
    volt = dm.get("voltage")

    if batt is None and volt is None:
        return

    ts = datetime.now(timezone.utc).isoformat()
    from_id = packet.get("fromId") or packet.get("from") or ""

    with open(CSV_PATH, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([ts, from_id, batt, volt])

    print(ts, from_id, batt, volt)

def main():
    # write header if file doesn't exist
    try:
        open(CSV_PATH, "r").close()
    except FileNotFoundError:
        with open(CSV_PATH, "w", newline="") as f:
            csv.writer(f).writerow(["timestamp_iso", "from_id", "battery_percent", "voltage_v"])

    iface = meshtastic.serial_interface.SerialInterface(devPath="/dev/ttyACM0", timeout=60)
    pub.subscribe(on_receive, "meshtastic.receive")

    print("Logging battery to", CSV_PATH)
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
