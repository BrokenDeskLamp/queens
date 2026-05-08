"""Queen placement strategies.

Generates sets of N queen positions satisfying:
- Exactly one per row, exactly one per column.
- No two queens are adjacent (including diagonals).
"""

from __future__ import annotations

import random
from typing import Protocol

from .board import Placement

_NEIGHBORS: tuple[tuple[int, int], ...] = (
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
)


class PlacementStrategy(Protocol):
    """Structural protocol for queen placement functions."""

    def __call__(self, n: int, rng: random.Random) -> Placement: ...


def backtracking_placement(n: int, rng: random.Random) -> Placement:
    """Generate N queen positions via row-by-row backtracking.

    Randomises column order for diverse output. Guarantees row/col
    uniqueness and no-adjacency constraints. The region constraint
    is not considered here — that's handled by the region builder.

    Args:
        n: Board size.
        rng: Random number generator for reproducibility.

    Returns:
        Tuple of (row, col) positions, one per row.
    """
    cols = list(range(n))
    placement: list[tuple[int, int] | None] = [None] * n
    used_cols: set[int] = set()
    queen_set: set[tuple[int, int]] = set()

    def _is_adjacent(row: int, col: int) -> bool:
        for dr, dc in _NEIGHBORS:
            if (row + dr, col + dc) in queen_set:
                return True
        return False

    def _backtrack(row: int) -> bool:
        if row == n:
            return True
        rng.shuffle(cols)
        for c in cols:
            if c in used_cols:
                continue
            if _is_adjacent(row, c):
                continue
            placement[row] = (row, c)
            used_cols.add(c)
            queen_set.add((row, c))
            if _backtrack(row + 1):
                return True
            used_cols.discard(c)
            queen_set.discard((row, c))
        return False

    _backtrack(0)
    assert all(p is not None for p in placement), "backtracking failed"
    return tuple(placement)  # type: ignore[arg-type,return-value]
