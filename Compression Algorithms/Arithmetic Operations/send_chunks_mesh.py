import time
from pathlib import Path
import cv2
import struct
import random
import meshtastic.serial_interface

MAX_CHUNK_SIZE = 255
HEADER_SIZE = 7
MAX_PAYLOAD = MAX_CHUNK_SIZE - HEADER_SIZE
QUALITY = 10

def encode_webp_bytes(image_path: Path, quality: int = 10) -> bytes:
    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Kunne ikke lese: {image_path.resolve()}")
    ok, buf = cv2.imencode(".webp", img, [cv2.IMWRITE_WEBP_QUALITY, int(quality)])
    if not ok:
        raise RuntimeError("WebP encoding feilet")
    return buf.tobytes()

def chunkify(data: bytes, msg_id: int | None = None) -> list[bytes]:
    if msg_id is None:
        msg_id = random.randint(0, 255)
    total_chunks = (len(data) + MAX_PAYLOAD - 1) // MAX_PAYLOAD
    packets = []
    for idx in range(total_chunks):
        payload = data[idx*MAX_PAYLOAD:(idx+1)*MAX_PAYLOAD]
        header = struct.pack(">BHHH", msg_id, total_chunks, idx, len(payload))
        packet = header + payload
        assert len(packet) <= MAX_CHUNK_SIZE
        packets.append(packet)
    return packets

if __name__ == "__main__":
    base = Path(__file__).parent
    image_path = base / "My mom is kinda homeless.jpg"

    webp_bytes = encode_webp_bytes(image_path, quality=QUALITY)
    packets = chunkify(webp_bytes)
    print(f"Skal sende {len(packets)} pakker, totalt {len(webp_bytes)} bytes")

    iface = meshtastic.serial_interface.SerialInterface()  # USB-tilkoblet node

    # Kanal: 0 = primary. Endre om du bruker en annen.
    channel_index = 0

    # Litt pause mellom pakker for å ikke overkjøre radio/mesh
    delay_s = 0.6  # start her; øk hvis du mister pakker

    for i, p in enumerate(packets):
        iface.sendData(p, channelIndex=channel_index)
        print(f"Sendt {i+1}/{len(packets)} ({len(p)} bytes)")
        time.sleep(delay_s)

    print("Ferdig.")
