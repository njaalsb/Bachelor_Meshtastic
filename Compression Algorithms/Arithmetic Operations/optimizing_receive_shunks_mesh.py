import time
import struct
import base64
from pathlib import Path
import meshtastic.serial_interface
from pubsub import pub

HEADER_SIZE = 7

# Litt ACK-delay for half-duplex på LongFast
ACK_DELAY_S = 0.15

class Reassembler:
    def __init__(self):
        self.store = {}  # msg_id -> {"total": int, "parts": {idx: bytes}}

    def add_packet(self, packet: bytes):
        if len(packet) < HEADER_SIZE:
            return None, None, None, None

        msg_id, total, idx, plen = struct.unpack(">BHHH", packet[:HEADER_SIZE])
        payload = packet[HEADER_SIZE:HEADER_SIZE + plen]

        s = self.store.setdefault(msg_id, {"total": total, "parts": {}})
        s["total"] = total
        s["parts"][idx] = payload

        have = len(s["parts"])
        return msg_id, total, idx, have

    def try_rebuild(self, msg_id: int):
        s = self.store.get(msg_id)
        if not s:
            return None
        total = s["total"]
        parts = s["parts"]
        if len(parts) != total:
            return None
        data = b"".join(parts[i] for i in range(total))
        del self.store[msg_id]
        return data

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

reasm = Reassembler()
out_dir = Path(__file__).parent / "received"
out_dir.mkdir(exist_ok=True)

def on_receive(packet, interface):
    decoded = packet.get("decoded", {})
    text = decoded.get("text") or decoded.get("data", {}).get("text")
    if not text:
        return

    # Ignorer ACK som kommer tilbake
    if text.startswith("ACK|"):
        return

    if not text.startswith("IMG|"):
        # Optional debug:
        # print("Tekst:", text)
        return

    try:
        _, msg_id_str, idx_str, b64 = text.split("|", 3)
        raw = base64.b64decode(b64)

        msg_id, total, idx, have = reasm.add_packet(raw)
        if msg_id is None:
            return

        print(f"msg_id={msg_id}  mottatt idx={idx}  have={have}/{total}")

        # Send ACK (liten delay for å unngå kollisjon)
        time.sleep(ACK_DELAY_S)
        interface.sendText(f"ACK|{msg_id}|{idx}")

        rebuilt = reasm.try_rebuild(msg_id)
        if rebuilt is not None:
            ts = time.strftime("%Y%m%d_%H%M%S")
            stem = f"received_{ts}_msg{msg_id}"
            out_path = unique_path(out_dir, stem, ".webp")
            out_path.write_bytes(rebuilt)
            print(f"\n✅ Ferdig bilde! Lagret: {out_path.resolve()} ({len(rebuilt)} bytes)\n")

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
