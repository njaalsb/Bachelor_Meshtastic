#!/usr/bin/env python3

import sys
import time
import struct
import base64
from pathlib import Path

import meshtastic.serial_interface
from pubsub import pub

HEADER_SIZE = 7  # [sid:1][total:2][idx:2][plen:2]


class Reassembler:
    def __init__(self):
        # msg_id -> {"total": int, "parts": {idx: bytes}}
        self.store = {}

    def add_packet(self, raw: bytes):
        if len(raw) < HEADER_SIZE:
            print(f"[rx] Packet too short ({len(raw)} bytes), ignoring.")
            return None, None, None, None

        msg_id, total, idx, plen = struct.unpack(">BHHH", raw[:HEADER_SIZE])
        payload = raw[HEADER_SIZE: HEADER_SIZE + plen]

        entry = self.store.setdefault(msg_id, {"total": total, "parts": {}})
        entry["total"] = total
        entry["parts"][idx] = payload

        have = len(entry["parts"])
        return msg_id, total, idx, have

    def try_rebuild(self, msg_id: int):
        entry = self.store.get(msg_id)
        if not entry:
            return None
        total = entry["total"]
        if len(entry["parts"]) != total:
            return None
        data = b"".join(entry["parts"][i] for i in range(total))
        del self.store[msg_id]
        return data

    def missing_chunks(self, msg_id: int):
        """Returns a sorted list of missing chunk indices, useful for debugging."""
        entry = self.store.get(msg_id)
        if not entry:
            return []
        total = entry["total"]
        have  = set(entry["parts"].keys())
        return sorted(set(range(total)) - have)


def unique_path(directory: Path, stem: str, suffix: str) -> Path:
    candidate = directory / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate
    n = 1
    while True:
        candidate = directory / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


reasm   = Reassembler()
out_dir = Path(__file__).parent / "received"
out_dir.mkdir(exist_ok=True)


def on_receive(packet, interface):
    decoded = packet.get("decoded", {})

    # Support both text and data portnum
    text = decoded.get("text") or decoded.get("data", {}).get("text")
    if not text:
        return

    # SDR alerts from sender
    if text.startswith("SDR|ALERT|"):
        power = text.split("|")[2]
        print(f"[rx] SDR alert received — signal power: {power}")
        return

    if not text.startswith("IMG|"):
        return

    try:
        parts = text.split("|", 3)
        if len(parts) != 4:
            print(f"[rx] Malformed IMG message: {text[:60]}")
            return

        _, msg_id_str, idx_str, b64 = parts
        raw = base64.b64decode(b64)

        msg_id, total, idx, have = reasm.add_packet(raw)
        if msg_id is None:
            return

        rssi = packet.get("rxRssi", "N/A")
        snr  = packet.get("rxSnr",  "N/A")
        print(f"[rx] msg_id={msg_id}  idx={idx:>3}  have={have}/{total}  "
              f"RSSI={rssi}  SNR={snr}")

        rebuilt = reasm.try_rebuild(msg_id)
        if rebuilt is not None:
            ts       = time.strftime("%Y%m%d_%H%M%S")
            stem     = f"thermal_{ts}_id{msg_id}"
            out_path = unique_path(out_dir, stem, ".webp")
            out_path.write_bytes(rebuilt)
            print(f"\n[rx] ✓ Image complete! {len(rebuilt)} bytes → {out_path}\n")
        else:
            missing = reasm.missing_chunks(msg_id)
            print(f"[rx]   Still missing: {missing}")

    except Exception as e:
        print(f"[rx] Error processing packet: {e}", file=sys.stderr)


def main():
    try:
        iface = meshtastic.serial_interface.SerialInterface()
    except Exception as e:
        print(f"[rx] Failed to open interface: {e}", file=sys.stderr)
        sys.exit(1)

    print("[rx] Listening... Ctrl+C to stop.")
    pub.subscribe(on_receive, "meshtastic.receive")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[rx] Shutting down.")
    finally:
        iface.close()


if __name__ == "__main__":
    main()