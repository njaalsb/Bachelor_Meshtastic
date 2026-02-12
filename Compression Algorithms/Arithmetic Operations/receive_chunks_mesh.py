import struct
import base64
from pathlib import Path
import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import time

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


reasm = Reassembler()
out_dir = Path(__file__).parent / "received"
out_dir.mkdir(exist_ok=True)


def on_receive(packet, interface):
    decoded = packet.get("decoded", {})
    text = decoded.get("text") or decoded.get("data", {}).get("text")

    if not text:
        return

    if not text.startswith("IMG|"):
        print("Vanlig tekst:", text)
        return

    try:
        _, msg_id_str, idx_str, b64 = text.split("|", 3)
        raw = base64.b64decode(b64)

        rebuilt = reasm.add_packet(raw)

        print(f"Mottatt chunk {idx_str}")

        if rebuilt is not None:
            out_path = out_dir / "received.webp"
            out_path.write_bytes(rebuilt)
            print(f"\n✅ Ferdig bilde! {out_path.resolve()}\n")

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
