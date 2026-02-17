#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
import heapq
import os


# -----------------------------
# Huffman tree
# -----------------------------
@dataclass
class Node:
    freq: int
    symbol: Optional[int] = None  # 0..255 for leaf, None for internal
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

    # Edge case: empty file
    if not heap:
        return Node(freq=0, symbol=0)

    # Edge case: only one unique byte -> make a 2-node tree
    if len(heap) == 1:
        only = heapq.heappop(heap)
        dummy = Node(freq=0, symbol=None)
        root = Node(freq=only.freq, symbol=None, left=only, right=dummy)
        return root

    while len(heap) > 1:
        a = heapq.heappop(heap)
        b = heapq.heappop(heap)
        heapq.heappush(heap, Node(freq=a.freq + b.freq, symbol=None, left=a, right=b))

    return heap[0]


def build_codes(root: Node) -> Dict[int, str]:
    codes: Dict[int, str] = {}

    def dfs(n: Node, path: str) -> None:
        if n.symbol is not None:
            # Leaf
            codes[n.symbol] = path if path else "0"  # handle degenerate
            return
        if n.left is not None:
            dfs(n.left, path + "0")
        if n.right is not None:
            dfs(n.right, path + "1")

    dfs(root, "")
    return codes


# -----------------------------
# Bit packing helpers
# -----------------------------
def bits_to_bytes(bitstr: str) -> Tuple[bytes, int]:
    """
    Pack a '0'/'1' string into bytes.
    Returns (packed_bytes, padding_bits_added_at_end)
    """
    pad = (8 - (len(bitstr) % 8)) % 8
    if pad:
        bitstr += "0" * pad
    out = bytearray()
    for i in range(0, len(bitstr), 8):
        out.append(int(bitstr[i:i + 8], 2))
    return bytes(out), pad


def bytes_to_bits(data: bytes) -> str:
    return "".join(f"{b:08b}" for b in data)


# -----------------------------
# Compress / Decompress
# -----------------------------
def compress_bytes(data: bytes) -> Tuple[bytes, int, List[int]]:
    """
    Returns:
      compressed_bytes, padding_bits, frequency_table
    (freq_table lets us rebuild the same tree during decompression)
    """
    freq = build_frequency_table(data)
    tree = build_huffman_tree(freq)
    codes = build_codes(tree)

    # Encode into a bit string
    encoded_bits = "".join(codes[b] for b in data)

    # Pack bits into bytes
    compressed, pad = bits_to_bytes(encoded_bits)
    return compressed, pad, freq


def decompress_bytes(compressed: bytes, pad_bits: int, freq: List[int]) -> bytes:
    tree = build_huffman_tree(freq)

    bitstr = bytes_to_bits(compressed)
    if pad_bits:
        bitstr = bitstr[:-pad_bits]  # remove padding we added

    out = bytearray()
    node = tree
    for bit in bitstr:
        node = node.left if bit == "0" else node.right
        if node is None:
            raise ValueError("Decoding error: reached a null node (corrupt data/tree).")
        if node.symbol is not None:
            out.append(node.symbol)
            node = tree

    return bytes(out)


# -----------------------------
# Main
# -----------------------------
def main() -> None:
    image_name = "AirsoftNerd.jpg"
    in_path = os.path.join(os.getcwd(), image_name)

    if not os.path.isfile(in_path):
        raise FileNotFoundError(f"Fant ikke '{image_name}' i mappen: {os.getcwd()}")

    with open(in_path, "rb") as f:
        original = f.read()

    compressed, pad_bits, freq = compress_bytes(original)
    recovered = decompress_bytes(compressed, pad_bits, freq)

    base, ext = os.path.splitext(image_name)
    out_name = f"decompressed_{base}{ext}"
    out_path = os.path.join(os.getcwd(), out_name)

    with open(out_path, "wb") as f:
        f.write(recovered)

    # Simple verification + stats
    ok = (original == recovered)
    original_bits = len(original) * 8
    compressed_bits = len(compressed) * 8 - pad_bits

    print(f"Input:  {image_name} ({len(original)} bytes)")
    print(f"Output: {out_name} ({len(recovered)} bytes)")
    print(f"Lossless match: {ok}")
    if compressed_bits > 0:
        print(f"Compression ratio (original_bits / compressed_bits): {original_bits / compressed_bits:.3f}")
        print(f"Original bits: {original_bits}")
        print(f"Compressed bits (minus padding): {compressed_bits}")
        print(f"Padding bits added: {pad_bits}")
    else:
        print("Compressed bit-length is 0 (empty input).")


if __name__ == "__main__":
    main()
