import time
import struct
import random
from pathlib import Path
import cv2
import meshtastic.serial_interface

HEADER_SIZE = 7  # >BHHH
QUALITY = 10

def encode_webp_bytes(image_path: Path, quality: int = 10) -> bytes:
    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Kunne ikke lese: {image_path.resolve()}")
    ok, buf = cv2.imencode(".webp", img, [cv2.IMWRITE_WEBP_QUALITY, int(quality)])
    if not ok:
        raise RuntimeError("WebP encoding feilet")
    return buf.tobytes()

def probe_max_payload(iface, channel_index: int = 0, low: int = 20, high: int = 255) -> int:
    """
    Finn største payload-lengde som sendData godtar ved å binærsøke.
    (Vi sender dummy-bytes; mottaker kan ignorere.)
    """
    # Først sjekk at low faktisk funker
    try:
        iface.sendData(b"\x00" * low, channelIndex=channel_index)
    except Exception as e:
        raise RuntimeError(f"Til og med {low} bytes feiler: {e}")

    lo, hi = low, high
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        try:
            iface.sendData(b"\x00" * mid, channelIndex=channel_index)
            best = mid
            lo = mid + 1
        except Exception:
            hi = mid - 1

        time.sleep(0.15)  # ikke spam radioen

    return best

def chunkify(data: bytes, msg_id: int, max_packet_size: int) -> list[bytes]:
    max_payload = max_packet_size - HEADER_SIZE
    if max_payload <= 0:
        raise ValueError("max_packet_size for liten til header")

    total_chunks = (len(data) + max_payload - 1) // max_payload
    packets = []
    for idx in range(total_chunks):
        payload = data[idx*max_payload:(idx+1)*max_payload]
        header = struct.pack(">BHHH", msg_id, total_chunks, idx, len(payload))
        packets.append(header + payload)
    return packets

if __name__ == "__main__":
    base = Path(__file__).parent
    image_path = base / "My mom is kinda homeless.jpg"

    iface = meshtastic.serial_interface.SerialInterface()
    channel_index = 0

    # 1) Komprimer
    webp = encode_webp_bytes(image_path, quality=QUALITY)

    # 2) Finn maks payload Meshtastic godtar akkurat nå
    max_packet = probe_max_payload(iface, channel_index=channel_index, low=20, high=255)
    print(f"Maks sendData payload (bytes) på denne linken: {max_packet}")

    # 3) Chunk med den grensa
    msg_id = random.randint(0, 255)
    packets = chunkify(webp, msg_id=msg_id, max_packet_size=max_packet)

    print(f"Skal sende {len(packets)} pakker, totalt {len(webp)} bytes (msg_id={msg_id})")
    print(f"Per pakke: header={HEADER_SIZE} + payload<={max_packet-HEADER_SIZE} bytes")

    delay_s = 2
    for i, p in enumerate(packets):
        iface.sendData(p, channelIndex=channel_index)
        print(f"Sendt {i+1}/{len(packets)} ({len(p)} bytes)")
        time.sleep(delay_s)

    print("Ferdig.")
