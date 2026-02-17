#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import struct
import zlib
import base64
import meshtastic
import meshtastic.serial_interface
from meshtastic import portnums_pb2
from pubsub import pub

try:
    from PIL import Image
except ImportError:
    Image = None

PORTNUM = portnums_pb2.PortNum.PRIVATE_APP

MAX_RADIO_PAYLOAD = 230
CHUNK_OVERHEAD = (1 + 4 + 2)  # type + msg_id + idx/offset

# State for one in-flight transfer
state = {
    "active": False,
    "msg_id": None,

    "width": None,
    "height": None,
    "mn": None,
    "mx": None,

    "total_chunks": None,
    "comp_len": None,
    "pad_bits": None,
    "crc32": None,

    "meta": bytearray(256),
    "meta_received": [False] * 256,  # per-byte received
    "chunks": {},  # idx -> bytes
}


def canonical_decode(comp_bytes: bytes, pad_bits: int, lengths: bytes, expected_out_len: int) -> bytes:
    # Build canonical decode table: code->symbol by length
    items = [(lengths[s], s) for s in range(256) if lengths[s] > 0]
    items.sort()  # (len, sym)

    # Assign canonical codes
    code = 0
    prev_len = 0
    decode_by_len = {}  # length -> dict(code_int -> sym)

    for l, sym in items:
        code <<= (l - prev_len)
        decode_by_len.setdefault(l, {})[code] = sym
        code += 1
        prev_len = l

    # Bitstream reader MSB-first
    out = bytearray()
    cur = 0
    cur_len = 0

    # total bits
    total_bits = len(comp_bytes) * 8 - pad_bits
    bitpos = 0

    for b in comp_bytes:
        for shift in range(7, -1, -1):
            if bitpos >= total_bits:
                break
            bit = (b >> shift) & 1
            bitpos += 1

            cur = (cur << 1) | bit
            cur_len += 1

            if cur_len in decode_by_len:
                table = decode_by_len[cur_len]
                sym = table.get(cur)
                if sym is not None:
                    out.append(sym)
                    cur = 0
                    cur_len = 0
                    if len(out) == expected_out_len:
                        return bytes(out)

    if len(out) != expected_out_len:
        raise ValueError(f"Decoded length mismatch: got {len(out)}, expected {expected_out_len}")
    return bytes(out)


def write_received_image(u8_bytes: bytes, width: int, height: int, filename: str) -> None:
    if Image is None:
        print("Pillow mangler (pip install pillow) – kan ikke lagre PNG.")
        return
    img = Image.frombytes("L", (width, height), u8_bytes)
    img.save(filename)
    print(f"Skrev {filename}")
    img.show(title="Received IR")


def try_finish():
    if not state["active"]:
        return

    # meta complete?
    if not all(state["meta_received"]):
        return

    # chunks complete?
    if state["total_chunks"] is None:
        return
    if len(state["chunks"]) != state["total_chunks"]:
        return

    # rebuild compressed bytes in order
    comp = bytearray()
    for i in range(state["total_chunks"]):
        comp.extend(state["chunks"][i])

    # trim to comp_len (siste chunk kan være kortere/vi kan ha litt ekstra)
    comp = bytes(comp[:state["comp_len"]])

    # crc check
    crc = zlib.crc32(comp) & 0xFFFFFFFF
    if crc != state["crc32"]:
        print(f"CRC mismatch! got={crc:#010x} expected={state['crc32']:#010x}")
        return

    width = state["width"]
    height = state["height"]
    expected_u8_len = width * height

    lengths = bytes(state["meta"])
    u8 = canonical_decode(comp, state["pad_bits"], lengths, expected_u8_len)

    out_name = f"received_{state['msg_id']:#010x}.png"
    write_received_image(u8, width, height, out_name)

    print("Ferdig mottatt og rekonstruert.")
    # Nullstill for å kunne ta imot ny
    state["active"] = False


def handle_payload(payload: bytes):
    if not payload:
        return

    ptype = payload[0]

    # HEADER
    if ptype == 0:
        # >BBIHHHHHI BI B  (samme som sender)
        try:
            # vi pakker den ut manuelt litt tryggere
            if len(payload) < 26:
                print("Header for kort.")
                return
            ver = payload[1]
            if ver != 1:
                print(f"Ukjent header-versjon: {ver}")
                return

            msg_id = struct.unpack(">I", payload[2:6])[0]
            width = struct.unpack(">H", payload[6:8])[0]
            height = struct.unpack(">H", payload[8:10])[0]
            mn = struct.unpack(">H", payload[10:12])[0]
            mx = struct.unpack(">H", payload[12:14])[0]
            total_chunks = struct.unpack(">H", payload[14:16])[0]
            comp_len = struct.unpack(">I", payload[16:20])[0]
            pad_bits = payload[20]
            crc32v = struct.unpack(">I", payload[21:25])[0]
            meta_len_byte = payload[25]  # 0 betyr 256 i vår protokoll

            meta_len = 256 if meta_len_byte == 0 else meta_len_byte

            if meta_len != 256:
                print("Forventer meta_len=256.")
                return

        except Exception as e:
            print(f"Header parse-feil: {e}")
            return

        # start ny state
        state["active"] = True
        state["msg_id"] = msg_id
        state["width"] = width
        state["height"] = height
        state["mn"] = mn
        state["mx"] = mx
        state["total_chunks"] = total_chunks
        state["comp_len"] = comp_len
        state["pad_bits"] = pad_bits
        state["crc32"] = crc32v

        state["meta"] = bytearray(256)
        state["meta_received"] = [False] * 256
        state["chunks"] = {}

        print(f"HEADER mottatt: msg_id={msg_id:#010x} {width}x{height} total_chunks={total_chunks} comp_len={comp_len}")
        return

    # Ignore if we don't have active transfer
    if not state["active"]:
        return

    # META
    if ptype == 2:
        if len(payload) < 1 + 4 + 2:
            return
        msg_id = struct.unpack(">I", payload[1:5])[0]
        if msg_id != state["msg_id"]:
            return
        offset = struct.unpack(">H", payload[5:7])[0]
        data = payload[7:]

        for i, b in enumerate(data):
            pos = offset + i
            if 0 <= pos < 256:
                state["meta"][pos] = b
                state["meta_received"][pos] = True

        got = sum(1 for x in state["meta_received"] if x)
        if got in (64, 128, 192, 256):
            print(f"META progress: {got}/256 bytes")

        try_finish()
        return

    # CHUNK
    if ptype == 1:
        if len(payload) < 1 + 4 + 2:
            return
        msg_id = struct.unpack(">I", payload[1:5])[0]
        if msg_id != state["msg_id"]:
            return
        idx = struct.unpack(">H", payload[5:7])[0]
        data = payload[7:]

        if idx not in state["chunks"]:
            state["chunks"][idx] = data
            if state["total_chunks"]:
                print(f"CHUNK {len(state['chunks'])}/{state['total_chunks']} mottatt (idx={idx}, len={len(data)})")

        try_finish()
        return


def on_receive(packet, interface):  # callback signature from pubsub
    decoded = packet.get("decoded", {})
    portnum = decoded.get("portnum")

    if portnum != PORTNUM:
        return

    payload = decoded.get("payload")
    if payload is None:
        return

    # meshtastic kan gi bytes eller base64-streng – håndter begge
    if isinstance(payload, str):
        try:
            payload = base64.b64decode(payload)
        except Exception:
            return

    if not isinstance(payload, (bytes, bytearray)):
        return

    handle_payload(bytes(payload))


def main():
    iface = meshtastic.serial_interface.SerialInterface()
    pub.subscribe(on_receive, "meshtastic.receive")
    print("Receiver kjører. Venter på header ... (Ctrl+C for å stoppe)")
    try:
        while True:
            # hold process alive
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
