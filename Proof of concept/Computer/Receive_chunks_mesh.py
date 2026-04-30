#!/usr/bin/env python3

import sys
import time
import struct
from pathlib import Path

import meshtastic.serial_interface
from pubsub import pub

# Header layout: [0x02][sid:1][total:2][idx:2][plen:2]
HEADER_SIZE = 8
TRANSFER_TYPE_IMAGE = 0x02
ATAK_FORWARDER_PORTNUM = 257


class Reassembler:
    def __init__(self):
        # msg_id -> {"total": int, "parts": {idx: bytes}}
        self.store = {}

    def add_packet(self, raw: bytes):
        if len(raw) < HEADER_SIZE:
            print(f" Packet too short ({len(raw)} bytes), ignoring.")
            return None, None, None, None

        type_byte, msg_id, total, idx, plen = struct.unpack(">BBHHH", raw[:HEADER_SIZE])
        if type_byte != TRANSFER_TYPE_IMAGE:
            return None, None, None, None

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
        entry = self.store.get(msg_id)
        if not entry:
            return []
        total = entry["total"]
        have = set(entry["parts"].keys())
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


reasm = Reassembler()
out_dir = Path(__file__).parent / "received"
out_dir.mkdir(exist_ok=True)


def on_receive(packet, interface):
    decoded = packet.get("decoded", {})
    portnum = decoded.get("portnum")

    # Binary image chunks arrive on ATAK_FORWARDER port (257)
    if portnum not in ("ATAK_FORWARDER", ATAK_FORWARDER_PORTNUM):
        return

    raw = decoded.get("payload")
    if not raw or len(raw) < HEADER_SIZE:
        return
    if raw[0] != TRANSFER_TYPE_IMAGE:
        return

    try:
        msg_id, total, idx, have = reasm.add_packet(raw)
        if msg_id is None:
            return

        rssi = packet.get("rxRssi", "N/A")
        snr  = packet.get("rxSnr",  "N/A")
        print(f"msg_id={msg_id}  idx={idx:>3}  have={have}/{total}  RSSI={rssi}  SNR={snr}")

        rebuilt = reasm.try_rebuild(msg_id)
        if rebuilt is not None:
            ts       = time.strftime("%Y%m%d_%H%M%S")
            stem     = f"thermal_{ts}_id{msg_id}"
            out_path = unique_path(out_dir, stem, ".webp")
            out_path.write_bytes(rebuilt)
            print(f"\n Image complete! {len(rebuilt)} bytes → {out_path}\n")
        else:
            missing = reasm.missing_chunks(msg_id)
            print(f"Still missing: {missing}")

    except Exception as e:
        print(f"Error processing packet: {e}", file=sys.stderr)


def main():
    try:
        iface = meshtastic.serial_interface.SerialInterface()
    except Exception as e:
        print(f"[rx] Failed to open interface: {e}", file=sys.stderr)
        sys.exit(1)

    print("Listening for binary image chunks on ATAK_FORWARDER port (257)... Ctrl+C to stop.")
    pub.subscribe(on_receive, "meshtastic.receive")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n Shutting down.")
    finally:
        iface.close()


if __name__ == "__main__":
    main()
