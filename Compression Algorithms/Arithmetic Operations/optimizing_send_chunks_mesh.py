import time
import struct
import base64
import random
from pathlib import Path
import cv2
import meshtastic.serial_interface

QUALITY = 8
MAX_PAYLOAD = 80
DELAY = 0.35
CHANNEL_INDEX = 0

HEADER_SIZE = 8  # >HHHH

def encode_webp_bytes(image_path: Path) -> bytes:
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)

    max_width = 320
    h, w = img.shape[:2]
    if w > max_width:
        new_h = int(h * max_width / w)
        img = cv2.resize(img, (max_width, new_h))

    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    ok, buf = cv2.imencode(".webp", img, [
        cv2.IMWRITE_WEBP_QUALITY, QUALITY
    ])

    return buf.tobytes()

def chunkify(data: bytes, sid: int):
    total = (len(data) + MAX_PAYLOAD - 1) // MAX_PAYLOAD
    packets = []

    for idx in range(total):
        payload = data[idx*MAX_PAYLOAD:(idx+1)*MAX_PAYLOAD]
        header = struct.pack(">HHHH", sid, total, idx, len(payload))
        packets.append(header + payload)

    return packets

if __name__ == "__main__":
    base = Path(__file__).parent
    image_path = base / "My mom is kinda homeless.jpg"

    iface = meshtastic.serial_interface.SerialInterface()

    webp = encode_webp_bytes(image_path)

    sid = random.randint(1, 65535)
    packets = chunkify(webp, sid)

    print(f"session={sid} | chunks={len(packets)} | bytes={len(webp)}")
    print("Starter kontinuerlig sending... Ctrl+C for å stoppe")

    try:
        while True:
            for idx, p in enumerate(packets):
                b64 = base64.b64encode(p).decode()
                iface.sendText(f"IMG|{sid}|{idx}|{b64}", channelIndex=CHANNEL_INDEX)
                print(f"Sendt idx={idx}")
                time.sleep(DELAY)

    except KeyboardInterrupt:
        print("Stoppet.")
