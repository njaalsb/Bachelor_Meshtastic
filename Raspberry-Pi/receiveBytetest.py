#!/usr/bin/env python3
import csv
import os
import time
from datetime import datetime

import meshtastic.serial_interface
from pubsub import pub

CSV_FILE = "rx_all.csv"
CSV_HEADERS = [
    "rx_timestamp",
    "from_id",
    "portnum",
    "payload_bytes",
    "rssi_dbm",
    "snr_db",
    "has_text",
    "text",
]

def ensure_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_HEADERS).writeheader()

def append_row(row: dict):
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        w.writerow({k: row.get(k) for k in CSV_HEADERS})

def on_receive(packet, interface):
    try:
        decoded = packet.get("decoded", {}) or {}
        port = decoded.get("portnum")

        # tekst der den faktisk ligger hos deg
        text = decoded.get("text") or (decoded.get("data") or {}).get("text")
        has_text = 1 if text is not None else 0
        text_str = str(text) if text is not None else ""

        # payload_bytes: bruk tekst hvis mulig, ellers raw payload
        payload_bytes = None
        if text is not None:
            payload_bytes = len(text_str.encode("utf-8"))
        else:
            raw = decoded.get("payload")
            if isinstance(raw, (bytes, bytearray)):
                payload_bytes = len(raw)

        row = {
            "rx_timestamp": datetime.now().isoformat(timespec="seconds"),
            "from_id": packet.get("from"),
            "portnum": port,
            "payload_bytes": payload_bytes,
            "rssi_dbm": packet.get("rxRssi"),
            "snr_db": packet.get("rxSnr"),
            "has_text": has_text,
            "text": text_str,
        }

        append_row(row)

        # print ALWAYS + flush
        print(
            f"[{row['rx_timestamp']}] port={port} from={row['from_id']} "
            f"bytes={payload_bytes} RSSI={row['rssi_dbm']} SNR={row['snr_db']} text={has_text}",
            flush=True
        )

    except Exception as e:
        # Hvis noe går galt i callbacken, så SER du det
        print("ERROR in on_receive:", repr(e), flush=True)

def main():
    ensure_csv()
    iface = meshtastic.serial_interface.SerialInterface()
    print("Receiver koblet. Lytter... Logger til", CSV_FILE, flush=True)

    pub.subscribe(on_receive, "meshtastic.receive")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            iface.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
