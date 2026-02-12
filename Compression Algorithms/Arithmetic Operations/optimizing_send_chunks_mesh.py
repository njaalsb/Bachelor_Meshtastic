import time
import struct
import random
import base64
from pathlib import Path
import cv2
import meshtastic.serial_interface
from pubsub import pub

# ===== SETTINGS =====
QUALITY = 8 
MAX_PAYLOAD = 80          # trygg verdi for sendText (base64 overhead)
WINDOW_SIZE = 5
DELAY = 0.35
TIMEOUT = 3

HEADER_SIZE = 7

acked = set()

def encode_webp_bytes(image_path: Path) -> bytes:
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)

    # Resize til maks 320px bredde
    max_width = 320
    h, w = img.shape[:2]
    if w > max_width:
        new_h = int(h * max_width / w)
        img = cv2.resize(img, (max_width, new_h))

    # Grayscale for mindre data
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    ok, buf = cv2.imencode(".webp", img, [
        cv2.IMWRITE_WEBP_QUALITY, QUALITY
    ])

    return buf.tobytes()

def chunkify(data: bytes, msg_id: int):
    total = (len(data) + MAX_PAYLOAD - 1) // MAX_PAYLOAD
    chunks = []

    for idx in range(total):
        payload = data[idx*MAX_PAYLOAD:(idx+1)*MAX_PAYLOAD]
        header = struct.pack(">BHHH", msg_id, total, idx, len(payload))
        chunks.append(header + payload)

    return chunks

def on_receive(packet, interface):
    global acked
    decoded = packet.get("decoded", {})
    text = decoded.get("text") or decoded.get("data", {}).get("text")
    if not text:
        return

    if text.startswith("ACK|"):
        _, m_id, idx = text.split("|")
        if int(m_id) == msg_id:
            acked.add(int(idx))

if __name__ == "__main__":
    base = Path(__file__).parent
    image_path = base / "My mom is kinda homeless.jpg"

    iface = meshtastic.serial_interface.SerialInterface()
    pub.subscribe(on_receive, "meshtastic.receive")

    msg_id = random.randint(0, 255)

    webp = encode_webp_bytes(image_path)
    packets = chunkify(webp, msg_id)

    print(f"Sender {len(packets)} chunks | {len(webp)} bytes")

    i = 0
    while i < len(packets):

        window_end = min(i + WINDOW_SIZE, len(packets))

        # Send window
        for j in range(i, window_end):
            if j not in acked:
                b64 = base64.b64encode(packets[j]).decode()
                iface.sendText(f"IMG|{msg_id}|{j}|{b64}")
                print(f"Sendt {j+1}/{len(packets)}")
                time.sleep(DELAY)

        # Vent på ACK
        start = time.time()
        while time.time() - start < TIMEOUT:
            if all(k in acked for k in range(i, window_end)):
                break
            time.sleep(0.1)

        # Hvis alt ACKet → gå videre
        if all(k in acked for k in range(i, window_end)):
            i = window_end
        else:
            print("Resender manglende chunks...")

    print("Ferdig sendt!")
