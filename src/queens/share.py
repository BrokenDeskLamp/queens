"""Compact URL-safe board encoding for shareable puzzles.

Encodes the region grid as a short string suitable for a URL hash fragment:
- 1 character: board size N (base36)
- remainder: bit-packed region IDs, base64url-encoded

Decoding is implemented in play.html in JavaScript so no Python
server is needed to serve puzzles.
"""

from __future__ import annotations

import base64


def encode_board(n: int, regions: list[list[int]]) -> str:
    """Encode board regions as a compact URL hash fragment.

    For N ≤ 8: 3 bits per cell → 24 bytes for N=8 → 32 chars base64.
    For 8 < N ≤ 15: 4 bits per cell.

    Args:
        n: Board size.
        regions: N×N list of region IDs (0..n-1).

    Returns:
        URL-safe encoded string like ``8;LgLw9Wm2TxYv...``
    """
    bits_per_cell = 3 if n <= 8 else 4
    total_bits = n * n * bits_per_cell

    # Pack region IDs into a bitstream
    bitstream = 0
    for r in range(n):
        for c in range(n):
            rid = regions[r][c]
            bitstream = (bitstream << bits_per_cell) | rid

    # Pad to full bytes
    byte_count = (total_bits + 7) // 8
    shift = byte_count * 8 - total_bits
    bitstream <<= shift

    data = bitstream.to_bytes(byte_count, "big")
    encoded = base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    # First char: N in base36
    n_char = "0123456789abcdefghijklmnopqrstuvwxyz"[n]

    return f"{n_char}{encoded}"
