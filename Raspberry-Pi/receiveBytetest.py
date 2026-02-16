#!/usr/bin/env python3
import csv
import os
import time
from datetime import datetime
from threading import Lock

import meshtastic
import meshtastic.serial_interface
from pubsub import pub

CSV_FILE = "meshtastic_rx.csv"
CSV_HEADERS = [
    "timestamp",
    "from_id",
    "from_name",
    "text",
    "payload_bytes",
    "rssi_dbm",
    "snr_db",
    "hops",
    "channel",
]

lock = Lock()

def ensure_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            w.writeheader()

def append_csv_row(row: dict):
    with lock:
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            w.writerow({k: row.get(k) for k in CSV_HEADERS})

def get_best_name(interface, from_id):
    try:
        node = (interface.nodes or {}).get(from_id, {}) or {}
        user = node.get("user", {}) or {}
        return user.get("longName") or user.get("shortName") or str(from_id)
    except Exception:
        return str(from_id)

def on_receive(packet, interface):
    decoded = packet.get("decoded", {}) or {}

    # Samme logikk som din fungerende kode:
    text = decoded.get("text") or decoded.get("data", {}).get("text")
    if not text:
        return

    from_id = packet.get("from", "ukjent")
    from_name = get_best_name(interface, from_id)

    rssi = packet.get("rxRssi")
    snr = packet.get("rxSnr")
    hops = packet.get("hops")

    channel = (
        packet.get("channel")
        or decoded.get("channel")
        or decoded.get("channelIndex")
        or packet.get("channelIndex")
    )

    payload_bytes = len(str(text).encode("utf-8"))

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "from_id": from_id,
        "from_name": from_name,
        "text": text,
        "payload_bytes": payload_bytes,
        "rssi_dbm": rssi,
        "snr_db": snr,
        "hops": hops,
        "channel": channel,
    }

    append_csv_row(row)

    print(
        f"[{row['timestamp']}] Mottatt fra {from_name} ({from_id}): "
        f"bytes={payload_bytes} RSSI={rssi} SNR={snr} hops={hops} ch={channel}"
    )

def main():
    ensure_csv()
    iface = meshtastic.serial_interface.SerialInterface()
    print("Lytter etter meldinger... Ctrl+C for å avslutte")
    print(f"Logger til CSV: {CSV_FILE}")

    pub.subscribe(on_receive, "meshtastic.receive")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Avslutter...")
        iface.close()

if __name__ == "__main__":
    main()

