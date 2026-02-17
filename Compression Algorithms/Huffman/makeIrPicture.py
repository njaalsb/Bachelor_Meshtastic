#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
IR sensor TXT -> image -> Huffman compress -> Huffman decompress -> image

Forventer en tekstfil med blokker som:
===================VOSPI PACKET===========================
0 0 250 116
<masse tall...>
END OF VOSPI PACKET

Vi antar (typisk Lepton/VoSPI):
- Etter header-linja kommer 160 bytes payload = 80 pixels * 2 bytes
- 240 packets = 120 rader * 2 halvrader (80+80) = 160x120

Output:
- ir_preview.png
- decompressed_ir_preview.png
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
import heapq
import os

# Pillow er enklest for å lagre PNG
try:
    from PIL import Image
except ImportError:
    Image = None


# -----------------------------
# Huffman (byte-wise, lossless)
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


def build_codes(root: Node) -> Dict[int, str]:
    codes: Dict[int, str] = {}

    def dfs(n: Node, path: str) -> None:
        if n.symbol is not None:
            codes[n.symbol] = path if path else "0"
            return
        if n.left is not None:
            dfs(n.left, path + "0")
        if n.right is not None:
            dfs(n.right, path + "1")

    dfs(root, "")
    return codes


def bits_to_bytes(bitstr: str) -> Tuple[bytes, int]:
    pad = (8 - (len(bitstr) % 8)) % 8
    if pad:
        bitstr += "0" * pad
    out = bytearray()
    for i in range(0, len(bitstr), 8):
        out.append(int(bitstr[i:i + 8], 2))
    return bytes(out), pad


def bytes_to_bits(data: bytes) -> str:
    return "".join(f"{b:08b}" for b in data)


def compress_bytes(data: bytes) -> Tuple[bytes, int, List[int]]:
    freq = build_frequency_table(data)
    tree = build_huffman_tree(freq)
    codes = build_codes(tree)
    encoded_bits = "".join(codes[b] for b in data)
    compressed, pad_bits = bits_to_bytes(encoded_bits)
    return compressed, pad_bits, freq


def decompress_bytes(compressed: bytes, pad_bits: int, freq: List[int]) -> bytes:
    tree = build_huffman_tree(freq)
    bitstr = bytes_to_bits(compressed)
    if pad_bits:
        bitstr = bitstr[:-pad_bits]

    out = bytearray()
    node = tree
    for bit in bitstr:
        node = node.left if bit == "0" else node.right
        if node is None:
            raise ValueError("Decoding error (korrupt data / feil tre).")
        if node.symbol is not None:
            out.append(node.symbol)
            node = tree
    return bytes(out)


# -----------------------------
# Parse IR txt (VOSPI blocks)
# -----------------------------
def parse_vospi_packets_txt(path: str) -> List[List[int]]:
    """
    Returnerer liste av pakker.
    Hver pakke er en liste av ints (rå bytes 0..255) fra payloaden (ikke header).
    """
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
                # ferdig pakke
                packets.append(payload)
                in_packet = False
                expecting_header_line = False
                payload = []
                continue

            if expecting_header_line:
                # Headeren ser ut som "0 12 250 116" osv.
                # Vi trenger ikke header for “første 240 pakker”-metoden.
                expecting_header_line = False
                continue

            # Payload-linjer: masse tall
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
    """
    Bygger ett 160x120 frame fra de første 240 pakkene.
    Antar: 1 packet = 80 pixels = 160 bytes.
    Frame layout: 2 packets per row (venstre + høyre).
    Returnerer flatt array av uint16-verdier (len = width*height).
    """
    needed_packets = height * 2  # 240
    if len(packets) < needed_packets:
        raise ValueError(f"For få pakker: har {len(packets)}, trenger minst {needed_packets}.")

    frame = [0] * (width * height)

    for i in range(needed_packets):
        payload = packets[i]

        # Vi forventer 160 bytes. Hvis mer/mindre: trim/pad.
        if len(payload) < 160:
            payload = payload + [0] * (160 - len(payload))
        elif len(payload) > 160:
            payload = payload[:160]

        # parse 80 uint16 (big-endian: hi,lo)
        pixels = []
        for j in range(0, 160, 2):
            hi = payload[j]
            lo = payload[j + 1]
            pixels.append((hi << 8) | lo)

        row = i // 2
        half = i % 2  # 0=left, 1=right
        col0 = half * 80

        for x in range(80):
            frame[row * width + (col0 + x)] = pixels[x]

    return frame


def u16_to_png(frame_u16: List[int], width: int, height: int, out_path: str) -> None:
    """
    Skalerer 16-bit verdier til 8-bit gråskala (min-max) og lagrer PNG.
    """
    if Image is None:
        raise ImportError("Pillow (PIL) er ikke installert. Installer med: pip install pillow")

    mn = min(frame_u16)
    mx = max(frame_u16)
    if mx == mn:
        mx = mn + 1

    # min-max til 0..255
    data8 = bytearray()
    for v in frame_u16:
        data8.append(int((v - mn) * 255 / (mx - mn)))

    img = Image.frombytes("L", (width, height), bytes(data8))
    img.save(out_path)


def main() -> None:
    txt_name = "ir_sensor_image.txt"
    txt_path = os.path.join(os.getcwd(), txt_name)

    if not os.path.isfile(txt_path):
        raise FileNotFoundError(f"Fant ikke '{txt_name}' i mappen: {os.getcwd()}")

    packets = parse_vospi_packets_txt(txt_path)
    print(f"Fant {len(packets)} VOSPI-pakker i {txt_name}")

    width, height = 160, 120
    frame_u16 = packets_to_frame_u16(packets, width=width, height=height)

    # Lag preview-bilde
    u16_to_png(frame_u16, width, height, "ir_preview.png")
    print("Skrev ir_preview.png")

    # Gjør om frame til bytes (big-endian uint16)
    original_bytes = bytearray()
    for v in frame_u16:
        original_bytes.append((v >> 8) & 0xFF)
        original_bytes.append(v & 0xFF)
    original_bytes = bytes(original_bytes)

    compressed, pad_bits, freq = compress_bytes(original_bytes)
    recovered = decompress_bytes(compressed, pad_bits, freq)

    print(f"Original raw bytes:   {len(original_bytes)}")
    print(f"Compressed bytes:     {len(compressed)} (pad_bits={pad_bits})")
    print(f"Lossless match:       {recovered == original_bytes}")

    # Bygg dekomprimert frame og lag bilde
    rec_u16 = []
    for i in range(0, len(recovered), 2):
        hi = recovered[i]
        lo = recovered[i + 1]
        rec_u16.append((hi << 8) | lo)

    u16_to_png(rec_u16, width, height, "decompressed_ir_preview.png")
    print("Skrev decompressed_ir_preview.png")

    # Ekstra: sjekk at bildedata er identisk
    print(f"Pixel-array identisk: {rec_u16 == frame_u16}")


if __name__ == "__main__":
    main()
