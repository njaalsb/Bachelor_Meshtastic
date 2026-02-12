import struct
from pathlib import Path
import meshtastic.serial_interface
from pubsub import pub

MAX_CHUNK_SIZE = 255
HEADER_SIZE = 7

class Reassembler:
    def __init__(self):
        self.store = {}  # msg_id -> {total:int, parts:{idx:bytes}}

    def add_packet(self, packet: bytes) -> bytes | None:
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
    data = decoded.get("payload")  # bytes når sendData brukes

    if not data:
        return

    # Meshtastic kan gi payload som bytes eller bytearray
    if isinstance(data, bytearray):
        data = bytes(data)

    rebuilt = reasm.add_packet(data)
    if rebuilt is not None:
        out_path = out_dir / "received.webp"
        out_path.write_bytes(rebuilt)
        print(f"✅ Ferdig bilde! Skrev: {out_path.resolve()} ({len(rebuilt)} bytes)")

if __name__ == "__main__":
    iface = meshtastic.serial_interface.SerialInterface()
    pub.subscribe(on_receive, "meshtastic.receive")
    print("Lytter… Ctrl+C for å avslutte")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
