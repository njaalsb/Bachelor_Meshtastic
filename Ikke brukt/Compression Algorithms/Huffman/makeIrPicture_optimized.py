#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
IR TXT -> frame -> (A) raw16 Huffman
                -> (B) u8 + Huffman
                -> (C) delta16 + RLE + Huffman
Decompress all, verify lossless (for A and C), and write preview images.

Input file expected in same folder:
  ir_sensor_image.txt

Outputs:
  ir_preview_u16.png                     (original frame scaled to 8-bit for viewing)
  decompressed_raw16.png                 (A decoded)
  decompressed_u8.png                    (B decoded u8)
  decompressed_delta16.png               (C decoded)
Also prints byte savings.

Notes:
- (B) u8 pipeline is lossless *for the u8 representation* (but lossy vs original u16).
- (C) is fully lossless vs original u16 (we decode back to exact u16).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
import heapq
import os

# Pillow for PNG
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


# -----------------------------
# Image helpers
# -----------------------------
def u16_to_png_scaled(frame_u16: List[int], width: int, height: int, out_path: str) -> None:
    if Image is None:
        raise ImportError("Installer Pillow: pip install pillow")
    mn = min(frame_u16)
    mx = max(frame_u16)
    if mx == mn:
        mx = mn + 1

    data8 = bytearray()
    for v in frame_u16:
        data8.append(int((v - mn) * 255 / (mx - mn)))
    img = Image.frombytes("L", (width, height), bytes(data8))
    img.save(out_path)


def u8_to_png(frame_u8: bytes, width: int, height: int, out_path: str) -> None:
    if Image is None:
        raise ImportError("Installer Pillow: pip install pillow")
    if len(frame_u8) != width * height:
        raise ValueError("u8 length mismatch")
    img = Image.frombytes("L", (width, height), frame_u8)
    img.save(out_path)


# -----------------------------
# Representations
# -----------------------------
def u16_frame_to_bytes_be(frame_u16: List[int]) -> bytes:
    out = bytearray()
    for v in frame_u16:
        out.append((v >> 8) & 0xFF)
        out.append(v & 0xFF)
    return bytes(out)


def bytes_be_to_u16_frame(data: bytes) -> List[int]:
    if len(data) % 2 != 0:
        raise ValueError("u16 byte length must be even")
    out = []
    for i in range(0, len(data), 2):
        out.append((data[i] << 8) | data[i + 1])
    return out


def u16_to_u8_minmax(frame_u16: List[int]) -> Tuple[bytes, int, int]:
    """
    Lossy vs original u16, but very useful for transmission.
    We return u8 bytes plus (min,max) so you can map back to pseudo-u16 if needed.
    """
    mn = min(frame_u16)
    mx = max(frame_u16)
    if mx == mn:
        mx = mn + 1
    out = bytearray()
    for v in frame_u16:
        out.append(int((v - mn) * 255 / (mx - mn)))
    return bytes(out), mn, mx


def u8_to_u16_from_minmax(frame_u8: bytes, mn: int, mx: int) -> List[int]:
    if mx == mn:
        mx = mn + 1
    out = []
    for b in frame_u8:
        out.append(int(mn + (b / 255.0) * (mx - mn)))
    return out


# -----------------------------
# Delta16 + RLE (lossless)
# -----------------------------
def zigzag16(x: int) -> int:
    # x is signed int, output non-negative
    return (x << 1) ^ (x >> 31)


def unzigzag16(u: int) -> int:
    return (u >> 1) ^ -(u & 1)


def encode_varint(u: int) -> bytes:
    """Unsigned LEB128-ish."""
    out = bytearray()
    while True:
        b = u & 0x7F
        u >>= 7
        if u:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def decode_varint(data: bytes, idx: int) -> Tuple[int, int]:
    shift = 0
    u = 0
    while True:
        if idx >= len(data):
            raise ValueError("Varint truncated")
        b = data[idx]
        idx += 1
        u |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
        if shift > 35:
            raise ValueError("Varint too large")
    return u, idx


def delta_rle_encode_u16(frame_u16: List[int]) -> bytes:
    """
    Lossless encoding:
    - First sample stored as uint16 BE
    - Then deltas (current - prev) in scan order
    - We RLE runs of delta==0
    Format:
      [first_hi first_lo] then tokens:
        0x00 <varint run_len>            for run of zero-deltas
        0x01 <varint zigzag(delta)>      for one nonzero delta
    """
    if not frame_u16:
        return b""

    out = bytearray()
    first = frame_u16[0] & 0xFFFF
    out.append((first >> 8) & 0xFF)
    out.append(first & 0xFF)

    zero_run = 0
    prev = first
    for v in frame_u16[1:]:
        v &= 0xFFFF
        # signed delta in range -65535..65535 (but practically smaller)
        d = int(v) - int(prev)
        prev = v
        if d == 0:
            zero_run += 1
            continue

        # flush zero run if any
        if zero_run:
            out.append(0x00)
            out.extend(encode_varint(zero_run))
            zero_run = 0

        out.append(0x01)
        out.extend(encode_varint(zigzag16(d)))

    # flush trailing zeros
    if zero_run:
        out.append(0x00)
        out.extend(encode_varint(zero_run))

    return bytes(out)


def delta_rle_decode_u16(data: bytes, expected_len: int) -> List[int]:
    if expected_len == 0:
        return []
    if len(data) < 2:
        raise ValueError("delta_rle data too short")

    first = (data[0] << 8) | data[1]
    out = [first]
    idx = 2
    prev = first

    while idx < len(data) and len(out) < expected_len:
        tag = data[idx]
        idx += 1

        if tag == 0x00:
            run, idx = decode_varint(data, idx)
            # run is number of additional samples with delta==0
            out.extend([prev] * run)

        elif tag == 0x01:
            u, idx = decode_varint(data, idx)
            d = unzigzag16(u)
            prev = (prev + d) & 0xFFFF
            out.append(prev)

        else:
            raise ValueError(f"Unknown tag {tag}")

        if out:
            prev = out[-1]

    if len(out) != expected_len:
        raise ValueError(f"Decoded length mismatch: got {len(out)}, expected {expected_len}")
    return out


# -----------------------------
# Utility
# -----------------------------
def fmt_bytes(n: int) -> str:
    return f"{n} bytes"


def print_savings(label: str, original: int, compressed: int) -> None:
    saved = original - compressed
    pct = (saved / original * 100.0) if original else 0.0
    print(f"{label}: {fmt_bytes(original)} -> {fmt_bytes(compressed)} | spart {fmt_bytes(saved)} ({pct:.1f}%)")


# -----------------------------
# Main
# -----------------------------
def main() -> None:
    txt_name = "ir_sensor_image.txt"
    txt_path = os.path.join(os.getcwd(), txt_name)
    if not os.path.isfile(txt_path):
        raise FileNotFoundError(f"Fant ikke '{txt_name}' i mappen: {os.getcwd()}")

    width, height = 160, 120
    n_pixels = width * height

    packets = parse_vospi_packets_txt(txt_path)
    print(f"Fant {len(packets)} VOSPI-pakker i {txt_name}")

    frame_u16 = packets_to_frame_u16(packets, width=width, height=height)

    # Preview of original u16 (scaled)
    u16_to_png_scaled(frame_u16, width, height, "ir_preview_u16.png")
    print("Skrev ir_preview_u16.png")

    # ---------------------------------------------------------
    # (A) RAW16 bytes + Huffman (lossless vs original u16)
    # ---------------------------------------------------------
    raw16_bytes = u16_frame_to_bytes_be(frame_u16)
    A_comp, A_pad, A_freq = compress_bytes(raw16_bytes)
    A_rec = decompress_bytes(A_comp, A_pad, A_freq)
    A_ok = (A_rec == raw16_bytes)
    print_savings("(A) RAW16 + Huffman", len(raw16_bytes), len(A_comp))
    print(f"(A) Lossless match: {A_ok}")

    A_rec_u16 = bytes_be_to_u16_frame(A_rec)
    u16_to_png_scaled(A_rec_u16, width, height, "decompressed_raw16.png")
    print("Skrev decompressed_raw16.png")

    # ---------------------------------------------------------
    # (B) U8 (min-max) + Huffman (lossless vs u8, lossy vs u16)
    # ---------------------------------------------------------
    u8_bytes, mn, mx = u16_to_u8_minmax(frame_u16)
    B_comp, B_pad, B_freq = compress_bytes(u8_bytes)
    B_rec_u8 = decompress_bytes(B_comp, B_pad, B_freq)
    B_ok = (B_rec_u8 == u8_bytes)

    print_savings("(B) U8(minmax) + Huffman", len(u8_bytes), len(B_comp))
    print(f"(B) Lossless match (u8): {B_ok} | min={mn} max={mx}")

    u8_to_png(B_rec_u8, width, height, "decompressed_u8.png")
    print("Skrev decompressed_u8.png")

    # (valgfritt) rekonstruer pseudo-u16 for sammenligning (ikke identisk med original)
    B_rec_u16 = u8_to_u16_from_minmax(B_rec_u8, mn, mx)

    # ---------------------------------------------------------
    # (C) Delta16 + RLE + Huffman (lossless vs original u16)
    # ---------------------------------------------------------
    delta_rle = delta_rle_encode_u16(frame_u16)
    C_comp, C_pad, C_freq = compress_bytes(delta_rle)
    C_rec_delta_rle = decompress_bytes(C_comp, C_pad, C_freq)

    # decode delta+rle back to u16
    C_rec_u16 = delta_rle_decode_u16(C_rec_delta_rle, expected_len=n_pixels)
    C_ok = (C_rec_u16 == frame_u16)

    print_savings("(C) Delta16+RLE + Huffman", len(raw16_bytes), len(C_comp))
    print(f"(C) Lossless match (u16): {C_ok} | delta_rle_bytes={len(delta_rle)}")

    u16_to_png_scaled(C_rec_u16, width, height, "decompressed_delta16.png")
    print("Skrev decompressed_delta16.png")

    # ---------------------------------------------------------
    # Summary (what matters for Meshtastic)
    # ---------------------------------------------------------
    print("\n--- Oppsummert ---")
    print(f"Original RAW16: {len(raw16_bytes)} bytes (160x120x16-bit)")
    print(f"A comp bytes:   {len(A_comp)}")
    print(f"B u8 bytes:     {len(u8_bytes)}  (allerede 50% kutt før komprimering)")
    print(f"B comp bytes:   {len(B_comp)}")
    print(f"C comp bytes:   {len(C_comp)}  (lossless u16)")

    # Quick guidance:
    if len(B_comp) < len(C_comp):
        print("\nTips: Hvis du tåler litt tap, er (B) ofte best for Meshtastic (mye mindre å sende).")
    else:
        print("\nTips: Hvis du må være tapsfri, er (C) ofte bedre enn bare Huffman på rå u16.")


if __name__ == "__main__":
    main()
