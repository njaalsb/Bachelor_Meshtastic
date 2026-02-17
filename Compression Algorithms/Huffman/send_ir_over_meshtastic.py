#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import random
import struct
import zlib
import heapq
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple

import meshtastic
import meshtastic.serial_interface
from meshtastic import portnums_pb2

try:
    from PIL import Image
except ImportError:
    Image = None


# -----------------------------
# CONFIG
# -----------------------------
TXT_FILE = "ir_sensor_image.txt"
DESTINATION_ID = None  # f.eks. "!abcd1234" eller None for broadcast
SEND_DELAY_S = 10

# Du sa 230 bytes per sending. Vi må ha litt header i hver melding.
MAX_RADIO_PAYLOAD = 230
CHUNK_PAYLOAD = MAX_RADIO_PAYLOAD - (1 + 4 + 2)  # type(1) + msg_id(4) + idx(2) = 223
META_PAYLOAD = MAX_RADIO_PAYLOAD - (1 + 4 + 2)   # type(1) + msg_id(4) + offset(2) = 223

PORTNUM = portnums_pb2.PortNum.PRIVATE_APP  # binær data


# -----------------------------
# IR parsing (samme logikk som før)
# -----------------------------
def parse_vospi_packets_txt(path: str) -> List[List[int]]:
    packets: List[List[int]] = []
    in_packet = False
    expecting_header_line = False
    payload: List[int] = []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            if line.startswith("===================VOSPI PACKET"):
                in_packet = True
                expecting_header_line = True
                payload = []
                continue

            if not in_packet:
                continue

            if line.startswith("END OF VOSPI PACKET"):
                packets.append(payload)
                in_packet = False
                expecting_header_line = False
                payload = []
                continue

            if expecting_header_line:
                expecting_header_line = False
                continue

            parts = line.split()
            for p in parts:
                try:
                    v = int(p)
                except ValueError:
                    continue
                if 0 <= v <= 255:
                    payload.append(v)

    return packets


def packets_to_frame_u16(packets: List[List[int]], width: int = 160, height: int = 120) -> List[int]:
    needed_packets = height * 2  # 240
    if len(packets) < needed_packets:
        raise ValueError(f"For få pakker: har {len(packets)}, trenger minst {needed_packets}.")

    frame = [0] * (width * height)

    for i in range(needed_packets):
        payload = packets[i]
        if len(payload) < 160:
            payload = payload + [0] * (160 - len(payload))
        elif len(payload) > 160:
            payload = payload[:160]

        pixels = []
        for j in range(0, 160, 2):
            hi = payload[j]
            lo = payload[j + 1]
            pixels.append((hi << 8) | lo)

        row = i // 2
        half = i % 2
        col0 = half * 80

        for x in range(80):
            frame[row * width + (col0 + x)] = pixels[x]

    return frame


def u16_to_u8_minmax(frame_u16: List[int]) -> Tuple[bytes, int, int]:
    mn = min(frame_u16)
    mx = max(frame_u16)
    if mx == mn:
        mx = mn + 1
    out = bytearray()
    for v in frame_u16:
        out.append(int((v - mn) * 255 / (mx - mn)))
    return bytes(out), mn, mx


def show_u8_preview(frame_u8: bytes, width: int, height: int, title: str = "Preview") -> None:
    if Image is None:
        print("Pillow mangler (pip install pillow) – kan ikke vise bilde.")
        return
    img = Image.frombytes("L", (width, height), frame_u8)
    img.show(title=title)


# -----------------------------
# Huffman med CANONICAL codes (så vi bare trenger code-lengths)
# -----------------------------
@dataclass
class Node:
    freq: int
    symbol: Optional[int] = None
    left: Optional["Node"] = None
    right: Optional["Node"] = None

    def __lt__(self, other: "Node") -> bool:
        return self.freq < other.freq


def build_frequency_table(data: bytes) -> List[int]:
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    return freq


def build_huffman_tree(freq: List[int]) -> Node:
    heap: List[Node] = []
    for sym, f in enumerate(freq):
        if f > 0:
            heapq.heappush(heap, Node(freq=f, symbol=sym))

    if not heap:
        return Node(freq=0, symbol=0)

    if len(heap) == 1:
        only = heapq.heappop(heap)
        dummy = Node(freq=0, symbol=None)
        return Node(freq=only.freq, symbol=None, left=only, right=dummy)

    while len(heap) > 1:
        a = heapq.heappop(heap)
        b = heapq.heappop(heap)
        heapq.heappush(heap, Node(freq=a.freq + b.freq, symbol=None, left=a, right=b))

    return heap[0]


def get_code_lengths(root: Node) -> List[int]:
    lengths = [0] * 256

    def dfs(n: Node, depth: int) -> None:
        if n.symbol is not None:
            lengths[n.symbol] = max(depth, 1)  # minimum 1 bit
            return
        if n.left is not None:
            dfs(n.left, depth + 1)
        if n.right is not None:
            dfs(n.right, depth + 1)

    dfs(root, 0)
    return lengths


def build_canonical_codes_from_lengths(lengths: List[int]) -> Dict[int, Tuple[int, int]]:
    """
    Returnerer: symbol -> (code_int, code_len)
    Canonical Huffman:
      - sorter (length, symbol)
      - tildel codes økende
    """
    items = [(l, s) for s, l in enumerate(lengths) if l > 0]
    items.sort()  # (len, sym)

    codes: Dict[int, Tuple[int, int]] = {}
    code = 0
    prev_len = 0

    for length, sym in items:
        code <<= (length - prev_len)
        codes[sym] = (code, length)
        code += 1
        prev_len = length

    return codes


def pack_bits_from_codes(data: bytes, codes: Dict[int, Tuple[int, int]]) -> Tuple[bytes, int]:
    """
    Pakker bitstream (MSB-first) til bytes.
    Return: (packed_bytes, pad_bits)
    """
    out = bytearray()
    bitbuf = 0
    bitcount = 0

    for b in data:
        c, clen = codes[b]
        bitbuf = (bitbuf << clen) | c
        bitcount += clen

        while bitcount >= 8:
            shift = bitcount - 8
            out.append((bitbuf >> shift) & 0xFF)
            bitbuf &= (1 << shift) - 1
            bitcount -= 8

    pad_bits = (8 - bitcount) % 8
    if bitcount > 0:
        out.append((bitbuf << pad_bits) & 0xFF)

    return bytes(out), pad_bits


# -----------------------------
# Meshtastic packet format
# -----------------------------
# Header (type=0):
#   [0]type=0
#   [1]ver=1
#   [2:6] msg_id (uint32)
#   [6:8] width (uint16)
#   [8:10] height (uint16)
#   [10:12] mn (uint16)
#   [12:14] mx (uint16)
#   [14:16] total_chunks (uint16)
#   [16:20] comp_len (uint32)
#   [20] pad_bits (uint8)
#   [21:25] crc32(comp_bytes) (uint32)
#   [25] meta_len (uint8)  # alltid 256 -> passer i uint8 som 0 betyr 256? Vi sender 255+1? Vi bruker 0x00 for 256.
#
# Meta (type=2):
#   [0]type=2
#   [1:5] msg_id
#   [5:7] offset (uint16)
#   [7:]  data
#
# Chunk (type=1):
#   [0]type=1
#   [1:5] msg_id
#   [5:7] idx (uint16)
#   [7:]  data


def make_header(msg_id: int, width: int, height: int, mn: int, mx: int,
                total_chunks: int, comp_len: int, pad_bits: int, crc32: int) -> bytes:
    ver = 1
    meta_len_byte = 0  # betyr 256
    return struct.pack(">BBIHHHHHI BI B",
                       0, ver, msg_id,
                       width, height, mn & 0xFFFF, mx & 0xFFFF,
                       total_chunks & 0xFFFF,
                       comp_len & 0xFFFFFFFF,
                       pad_bits & 0xFF,
                       crc32 & 0xFFFFFFFF,
                       meta_len_byte)


def make_meta(msg_id: int, offset: int, payload: bytes) -> bytes:
    return bytes([2]) + struct.pack(">IH", msg_id, offset) + payload


def make_chunk(msg_id: int, idx: int, payload: bytes) -> bytes:
    return bytes([1]) + struct.pack(">IH", msg_id, idx) + payload


# -----------------------------
# MAIN
# -----------------------------
def main() -> None:
    if not os.path.isfile(TXT_FILE):
        raise FileNotFoundError(f"Fant ikke {TXT_FILE} i denne mappen: {os.getcwd()}")

    width, height = 160, 120

    packets = parse_vospi_packets_txt(TXT_FILE)
    if len(packets) < 240:
        raise RuntimeError(f"For få VOSPI-pakker: {len(packets)} (trenger minst 240)")

    frame_u16 = packets_to_frame_u16(packets, width, height)
    frame_u8, mn, mx = u16_to_u8_minmax(frame_u16)

    # Preview før sending
    print("Viser preview-bilde før sending ...")
    show_u8_preview(frame_u8, width, height, title="IR Preview (u8)")

    # Huffman canonical
    freq = build_frequency_table(frame_u8)
    tree = build_huffman_tree(freq)
    lengths = get_code_lengths(tree)  # 256 bytes meta
    canonical_codes = build_canonical_codes_from_lengths(lengths)
    comp_bytes, pad_bits = pack_bits_from_codes(frame_u8, canonical_codes)
    crc = zlib.crc32(comp_bytes) & 0xFFFFFFFF

    # Chunking
    chunks = []
    for i in range(0, len(comp_bytes), CHUNK_PAYLOAD):
        chunks.append(comp_bytes[i:i + CHUNK_PAYLOAD])
    total_chunks = len(chunks)

    msg_id = random.getrandbits(32)

    print(f"u8 bytes: {len(frame_u8)}")
    print(f"compressed bytes: {len(comp_bytes)} (pad_bits={pad_bits})")
    print(f"chunk payload: {CHUNK_PAYLOAD} bytes")
    print(f"total chunks: {total_chunks}")

    iface = meshtastic.serial_interface.SerialInterface()

    # Send header
    header = make_header(msg_id, width, height, mn, mx, total_chunks, len(comp_bytes), pad_bits, crc)
    iface.sendData(header, destinationId=DESTINATION_ID, portNum=PORTNUM, wantAck=False)
    print(f"Sendt HEADER (msg_id={msg_id:#010x})")
    time.sleep(SEND_DELAY_S)

    # Send meta: 256 bytes code lengths
    meta_bytes = bytes([l & 0xFF for l in lengths])  # 256 bytes
    offset = 0
    while offset < len(meta_bytes):
        part = meta_bytes[offset:offset + META_PAYLOAD]
        pkt = make_meta(msg_id, offset, part)
        iface.sendData(pkt, destinationId=DESTINATION_ID, portNum=PORTNUM, wantAck=False)
        print(f"Sendt META offset={offset} len={len(part)}")
        offset += len(part)
        time.sleep(SEND_DELAY_S)

    # Send chunks
    for idx, payload in enumerate(chunks):
        pkt = make_chunk(msg_id, idx, payload)
        iface.sendData(pkt, destinationId=DESTINATION_ID, portNum=PORTNUM, wantAck=False)
        print(f"Sendt CHUNK {idx+1}/{total_chunks} (len={len(payload)})")
        time.sleep(SEND_DELAY_S)

    print("Ferdig sendt.")


if __name__ == "__main__":
    main()
