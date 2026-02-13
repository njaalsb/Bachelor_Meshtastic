import time
import struct
import random
import base64
from pathlib import Path

import numpy as np
import cv2
import meshtastic.serial_interface

HEADER_SIZE = 7

W, H = 160, 120          # Lepton 3.1R
MAX_PAYLOAD = 120        # samme konservative som du bruker
SLEEP_S = 15             # LoRa pause

# ---------- Chunking (samme stil som din) ----------
def chunkify(data: bytes, msg_id: int, max_payload: int):
    total_chunks = (len(data) + max_payload - 1) // max_payload
    chunks = []
    for idx in range(total_chunks):
        payload = data[idx*max_payload:(idx+1)*max_payload]
        header = struct.pack(">BHHH", msg_id, total_chunks, idx, len(payload))
        chunks.append(header + payload)
    return chunks

# ---------- TXT -> 16-bit words ----------
def parse_vospi_packets_words(txt: str):
    """
    Leser blocks som:
      ===================VOSPI PACKET===========================
      0 0 250 116
      131 236 129 138
      ...
      END OF VOSPI PACKET

    Returnerer liste med (header4, words16_list).
    """
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    packets = []
    i = 0
    while i < len(lines):
        if "VOSPI PACKET" in lines[i]:
            i += 1
            if i >= len(lines):
                break

            # header line: 4 ints
            try:
                hdr = [int(x) for x in lines[i].split()]
            except Exception:
                i += 1
                continue
            if len(hdr) < 4:
                i += 1
                continue

            i += 1
            words = []
            while i < len(lines) and "END OF VOSPI PACKET" not in lines[i]:
                parts = lines[i].split()
                ints = []
                for p in parts:
                    try:
                        ints.append(int(p))
                    except Exception:
                        pass

                # combine (hi, lo) pairs into 16-bit words
                for k in range(0, len(ints) - 1, 2):
                    hi = ints[k] & 0xFF
                    lo = ints[k + 1] & 0xFF
                    words.append((hi << 8) | lo)

                i += 1

            # skip END line
            if i < len(lines) and "END OF VOSPI PACKET" in lines[i]:
                i += 1

            packets.append((hdr[:4], words))
        else:
            i += 1

    return packets

def build_frame_8bit_from_packets(packets, width=W, height=H):
    """
    Robust "just make a picture":
    - Tar words i den rekkefølgen de kommer i txt.
    - Leser 80 pixels per packet (Lepton VoSPI payload = 160 bytes = 80 words).
    - For 160 bredde => 2 packets per rad.
    - Fyller frame row-major: 160*120 pixels.
    - Normaliserer til 8-bit.
    """
    pixels16 = []

    for _hdr, words in packets:
        if len(words) < 80:
            continue
        # ta første 80 pixels fra pakken (typisk payload-lengde)
        pixels16.extend(words[:80])

    needed_packets = (width // 80) * height  # 2*120 = 240
    needed_pixels = width * height           # 19200

    if len(pixels16) < needed_pixels:
        raise RuntimeError(
            f"For lite data i txt: fikk {len(pixels16)} pixels, trenger {needed_pixels}. "
            f"(Har du bare dumpet noen få VOSPI PACKETs?)"
        )

    pixels16 = np.array(pixels16[:needed_pixels], dtype=np.uint16).reshape((height, width))

    # enkel normalisering til 8-bit
    vmin = int(pixels16.min())
    vmax = int(pixels16.max())
    if vmax <= vmin:
        img8 = np.zeros((height, width), dtype=np.uint8)
    else:
        img8 = ((pixels16.astype(np.float32) - vmin) * (255.0 / (vmax - vmin))).clip(0, 255).astype(np.uint8)

    return img8

def pack_ir8_payload(img8: np.ndarray) -> bytes:
    """
    BINARY payload:
      b'IR8' + uint16 width + uint16 height + raw img bytes (W*H)
    """
    h, w = img8.shape[:2]
    header = b"IR8" + struct.pack(">HH", w, h)
    return header + img8.tobytes()

if __name__ == "__main__":
    base = Path(__file__).parent
    txt_path = base / "ir_sensor_image.txt"

    txt = txt_path.read_text(encoding="utf-8", errors="ignore")
    packets = parse_vospi_packets_words(txt)

    img8 = build_frame_8bit_from_packets(packets, width=W, height=H)

    # lokal preview (så du ser at parsing gir noe)
    preview = base / "ir_preview.png"
    cv2.imwrite(str(preview), img8)
    print(f"Preview lagret: {preview.resolve()}  shape={img8.shape}")

    # bygg rå payload og send
    payload = pack_ir8_payload(img8)

    iface = meshtastic.serial_interface.SerialInterface()

    msg_id = random.randint(0, 255)
    chunks = chunkify(payload, msg_id=msg_id, max_payload=MAX_PAYLOAD)

    print(f"Sender IR8: {len(chunks)} chunks (msg_id={msg_id}) bytes={len(payload)}")

    for i, ch in enumerate(chunks):
        b64 = base64.b64encode(ch).decode()
        # IR8|msgid|chunkindex|base64
        iface.sendText(f"IR8|{msg_id}|{i}|{b64}")
        print(f"Sendt {i+1}/{len(chunks)}")
        time.sleep(SLEEP_S)

    print("Ferdig.")
