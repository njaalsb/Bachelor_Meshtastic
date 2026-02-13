import struct
import base64
import time
from pathlib import Path

import numpy as np
import cv2
import meshtastic.serial_interface
from pubsub import pub

HEADER_SIZE = 7

class Reassembler:
    def __init__(self):
        self.store = {}

    def add_packet(self, packet: bytes):
        if len(packet) < HEADER_SIZE:
            return None

        msg_id, total, idx, plen = struct.unpack(">BHHH", packet[:HEADER_SIZE])
        payload = packet[HEADER_SIZE:HEADER_SIZE + plen]

        s = self.store.setdefault(msg_id, {"total": total, "parts": {}})
        s["total"] = total
        s["parts"][idx] = payload

        if len(s["parts"]) == total:
            data = b"".join(s["parts"][i] for i in range(total))
            del self.store[msg_id]
            return data

        return None

def unique_path(dirpath: Path, stem: str, suffix: str) -> Path:
    p = dirpath / f"{stem}{suffix}"
    if not p.exists():
        return p
    n = 1
    while True:
        p2 = dirpath / f"{stem}_{n}{suffix}"
        if not p2.exists():
            return p2
        n += 1

def unpack_ir8_payload(data: bytes):
    """
    Expect:
      b'IR8' + uint16 w + uint16 h + w*h bytes
    """
    if len(data) < 3 + 4:
        raise ValueError("For kort IR8 payload")
    if data[:3] != b"IR8":
        raise ValueError("Feil magic, ikke IR8")
    w, h = struct.unpack(">HH", data[3:7])
    img_bytes = data[7:]
    if len(img_bytes) < w * h:
        raise ValueError(f"For lite bilde-data: fikk {len(img_bytes)} bytes, forventet {w*h}")
    img = np.frombuffer(img_bytes[: w * h], dtype=np.uint8).reshape((h, w))
    return img

reasm = Reassembler()
out_dir = Path(__file__).parent / "received"
out_dir.mkdir(exist_ok=True)

def on_receive(packet, interface):
    decoded = packet.get("decoded", {})
    text = decoded.get("text") or decoded.get("data", {}).get("text")
    if not text:
        return

    if not text.startswith("IR8|"):
        # valgfritt: print annen tekst
        # print("Vanlig tekst:", text)
        return

    try:
        _, msg_id_str, idx_str, b64 = text.split("|", 3)
        raw = base64.b64decode(b64)

        msg_id, total, idx, plen = struct.unpack(">BHHH", raw[:HEADER_SIZE])
        print(f"Mottatt IR8 chunk {idx} / {total-1} (msg_id={msg_id})")

        rebuilt = reasm.add_packet(raw)
        if rebuilt is None:
            return

        # rebuilt == full IR8 payload
        img = unpack_ir8_payload(rebuilt)

        ts = time.strftime("%Y%m%d_%H%M%S")
        stem = f"ir_{ts}_msg{msg_id}"
        out_path = unique_path(out_dir, stem, ".png")
        cv2.imwrite(str(out_path), img)

        print(f"\nFerdig IR-bilde! Lagret: {out_path.resolve()}  shape={img.shape}\n")

    except Exception as e:
        print("Feil ved parsing:", e)

def main():
    iface = meshtastic.serial_interface.SerialInterface()
    print("Lytter... Ctrl+C")
    pub.subscribe(on_receive, "meshtastic.receive")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        iface.close()

if __name__ == "__main__":
    main()
