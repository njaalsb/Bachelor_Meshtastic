import struct
import base64
from pathlib import Path
import meshtastic.serial_interface
from pubsub import pub
import time

HEADER_SIZE = 7

class Reassembler:
    def __init__(self):
        self.store = {}

    def add_packet(self, packet: bytes):
        if len(packet) < HEADER_SIZE:
            return None, None

        msg_id, total, idx, plen = struct.unpack(">BHHH", packet[:HEADER_SIZE])
        payload = packet[HEADER_SIZE:HEADER_SIZE + plen]

        s = self.store.setdefault(msg_id, {"total": total, "parts": {}})
        s["total"] = total
        s["parts"][idx] = payload

        print(f"Har {len(s['parts'])}/{total} chunks")

        if len(s["parts"]) == total:
            data = b"".join(s["parts"][i] for i in range(total))
            del self.store[msg_id]
            return data, msg_id

        return None, None

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

    if text.startswith("IMG|"):
        try:
            _, msg_id_str, idx_str, b64 = text.split("|", 3)
            raw = base64.b64decode(b64)

            msg_id, total, idx, plen = struct.unpack(">BHHH", raw[:HEADER_SIZE])

            rebuilt, finished_id = reasm.add_packet(raw)

            # Send ACK
            interface.sendText(f"ACK|{msg_id}|{idx}")

            if rebuilt is not None:
                ts = time.strftime("%Y%m%d_%H%M%S")
                stem = f"received_{ts}_msg{finished_id}"
                out_path = unique_path(out_dir, stem, ".webp")
                out_path.write_bytes(rebuilt)

                print(f"\n Ferdig bilde! {out_path.resolve()} ({len(rebuilt)} bytes)\n")

        except Exception as e:
            print("Feil:", e)

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
