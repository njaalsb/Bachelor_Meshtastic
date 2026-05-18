import argparse
import csv
import os
import time
from datetime import datetime

import meshtastic.serial_interface

def ensure_csv(path, headers):
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=headers).writeheader()

def append_row(path, headers, row):
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writerow({k: row.get(k) for k in headers})

def build_payload(total_bytes: int, seq: int, send_ms: int) -> str:
    # Fast-lengde header (ASCII), så vi kan parse på RX og samtidig padde eksakt
    # Lengden på denne er konstant.
    header = f"SZ={total_bytes:03d};SEQ={seq:06d};TS={send_ms:013d};|"
    header_len = len(header.encode("utf-8"))  # ASCII => samme som len(header)

    if total_bytes < header_len:
        raise ValueError(f"total_bytes={total_bytes} er for liten, må være >= {header_len}")

    pad_len = total_bytes - header_len
    payload = header + ("A" * pad_len)

    # Sikkerhetssjekk
    if len(payload.encode("utf-8")) != total_bytes:
        raise RuntimeError("Payload ble ikke riktig størrelse")

    return payload

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default=None, help="Serial device, f.eks. COM6 eller /dev/ttyACM0 (optional)")
    ap.add_argument("--channel", type=int, default=0, help="Channel index")
    ap.add_argument("--dest", default=None, help="Optional destinationId. Hvis tom -> normal/broadcast.")
    ap.add_argument("--min", dest="min_size", type=int, default=30, help="Min payload bytes (default 30)")
    ap.add_argument("--max", dest="max_size", type=int, default=230, help="Max payload bytes (default 230)")
    ap.add_argument("--step", type=int, default=5, help="Step i bytes (default 5)")
    ap.add_argument("--per", dest="per_size", type=int, default=10, help="Antall meldinger per størrelse (default 10)")
    ap.add_argument("--delay", type=float, default=1.0, help="Sekunder mellom sendinger (default 1.0)")
    ap.add_argument("--csv", default="tx_log.csv", help="TX log CSV (default tx_log.csv)")
    args = ap.parse_args()

    headers = ["timestamp", "size_bytes", "seq", "send_ms", "channel", "dest"]
    ensure_csv(args.csv, headers)

    iface = meshtastic.serial_interface.SerialInterface(devPath=args.dev) if args.dev else meshtastic.serial_interface.SerialInterface()
    print("Koblet til Meshtastic.")

    seq = 0
    try:
        for size in range(args.min_size, args.max_size + 1, args.step):
            print(f"\n--- Size {size} bytes ---")
            for _ in range(args.per_size):
                seq += 1
                send_ms = int(time.time() * 1000)
                payload = build_payload(size, seq, send_ms)

                kwargs = {"channelIndex": args.channel}
                if args.dest:
                    kwargs["destinationId"] = args.dest

                try:
                    iface.sendText(payload, **kwargs)
                    print(f"Sendt seq={seq} size={size}")
                    append_row(args.csv, headers, {
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "size_bytes": size,
                        "seq": seq,
                        "send_ms": send_ms,
                        "channel": args.channel,
                        "dest": args.dest or "",
                    })
                except Exception as e:
                    print(f"FEIL ved sending seq={seq} size={size}: {e}")

                time.sleep(args.delay)

    finally:
        try:
            iface.close()
        except Exception:
            pass
        print("Avsluttet.")

if __name__ == "__main__":
    main()
