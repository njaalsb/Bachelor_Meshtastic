import time
import struct
import random
import base64
from pathlib import Path
import cv2
import meshtastic.serial_interface

HEADER_SIZE = 7
QUALITY = 10

def encode_webp_bytes(image_path: Path, quality: int = 10) -> bytes:
    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Kunne ikke lese: {image_path.resolve()}")
    ok, buf = cv2.imencode(".webp", img, [cv2.IMWRITE_WEBP_QUALITY, int(quality)])
    if not ok:
        raise RuntimeError("WebP encoding feilet")
    return buf.tobytes()

def chunkify(data: bytes, msg_id: int, max_payload: int):
    total_chunks = (len(data) + max_payload - 1) // max_payload
    chunks = []

    for idx in range(total_chunks):
        payload = data[idx*max_payload:(idx+1)*max_payload]
        header = struct.pack(">BHHH", msg_id, total_chunks, idx, len(payload))
        full_packet = header + payload
        chunks.append(full_packet)

    return chunks

if __name__ == "__main__":
    base = Path(__file__).parent
    image_path = base / "onMyMama.jpg"

    iface = meshtastic.serial_interface.SerialInterface()

    webp = encode_webp_bytes(image_path, quality=QUALITY)

    # TEXT_MESSAGE tåler mindre → vi bruker trygg verdi
    max_payload = 120   # konservativ pga base64 overhead

    msg_id = random.randint(0, 255)
    packets = chunkify(webp, msg_id=msg_id, max_payload=max_payload)

    print(f"Sender {len(packets)} chunks (msg_id={msg_id})")

    for i, p in enumerate(packets):
        b64 = base64.b64encode(p).decode()

        # Tekstformat:
        # IMG|msgid|chunkindex|base64data
        text_packet = f"IMG|{msg_id}|{i}|{b64}"

        iface.sendText(text_packet)
        print(f"Sendt {i+1}/{len(packets)}")

        time.sleep(15)  # viktig på LoRa

    print("Ferdig.")
