import struct
import random
from pathlib import Path
import cv2


MAX_CHUNK_SIZE = 255
HEADER_SIZE = 7
MAX_PAYLOAD = MAX_CHUNK_SIZE - HEADER_SIZE  
QUALITY = 10


def encode_webp_bytes(image_path: Path, quality: int = 10) -> bytes:
    """Les bilde og returner WebP-komprimerte bytes."""
    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Kunne ikke lese: {image_path.resolve()}")

    ok, buf = cv2.imencode(".webp", img, [cv2.IMWRITE_WEBP_QUALITY, int(quality)])
    if not ok:
        raise RuntimeError("WebP encoding feilet")

    return buf.tobytes()


def chunkify(data: bytes, msg_id: int | None = None) -> list[bytes]:
    """Splitter data til pakker på maks 255 bytes (inkl header)."""
    if msg_id is None:
        msg_id = random.randint(0, 255)

    total_chunks = (len(data) + MAX_PAYLOAD - 1) // MAX_PAYLOAD
    packets = []

    for idx in range(total_chunks):
        start = idx * MAX_PAYLOAD
        payload = data[start:start + MAX_PAYLOAD]

        # Header:
        # msg_id (1 byte)
        # total_chunks (2 bytes)
        # chunk_index (2 bytes)
        # payload_length (2 bytes)
        header = struct.pack(">BHHH", msg_id, total_chunks, idx, len(payload))

        packet = header + payload
        assert len(packet) <= MAX_CHUNK_SIZE

        packets.append(packet)

    return packets


class Reassembler:
    """Samler pakker tilbake til original byte-strøm."""
    def __init__(self):
        self.store = {}

    def add_packet(self, packet: bytes) -> bytes | None:
        if len(packet) < HEADER_SIZE:
            return None

        msg_id, total, idx, plen = struct.unpack(">BHHH", packet[:HEADER_SIZE])
        payload = packet[HEADER_SIZE:HEADER_SIZE + plen]

        if msg_id not in self.store:
            self.store[msg_id] = {"total": total, "parts": {}}

        self.store[msg_id]["parts"][idx] = payload

        if len(self.store[msg_id]["parts"]) == total:
            data = b"".join(self.store[msg_id]["parts"][i] for i in range(total))
            del self.store[msg_id]
            return data

        return None


def save_webp_bytes(webp_bytes: bytes, out_path: Path):
    out_path.write_bytes(webp_bytes)



if __name__ == "__main__":

    BASE_DIR = Path(__file__).parent

    image_path = BASE_DIR / "My mom is kinda homeless.jpg"
    output_path = BASE_DIR / "rebuilt_q10.webp"

    print(f"Laster bilde fra: {image_path}")

    # 1️⃣ Komprimer
    webp_bytes = encode_webp_bytes(image_path, quality=QUALITY)
    print(f"WebP størrelse: {len(webp_bytes)} bytes")

    # 2️⃣ Chunk
    packets = chunkify(webp_bytes)
    print(f"Antall pakker: {len(packets)}")
    print(f"Første pakke størrelse: {len(packets[0])} bytes (<=255)")

    # 3️⃣ Simuler mottaker
    reassembler = Reassembler()
    rebuilt = None

    for packet in packets:
        result = reassembler.add_packet(packet)
        if result is not None:
            rebuilt = result

    if rebuilt is None:
        raise RuntimeError("Reassembly feilet")

    # 4️⃣ Lagre i samme mappe som scriptet
    save_webp_bytes(rebuilt, output_path)

    print(f"Ferdig! Lagret til: {output_path}")
