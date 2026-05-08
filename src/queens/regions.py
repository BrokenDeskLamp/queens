"""Region building strategies.

Given N queen positions, partitions the NxN grid into N connected
regions, each containing exactly one queen.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Protocol

import numpy as np

from .board import Board, Placement
from .solver import find_up_to_k_solutions

_DIRECTIONS: tuple[tuple[int, int], ...] = ((0, 1), (0, -1), (1, 0), (-1, 0))


class RegionBuilder(Protocol):
    """Structural protocol for region building functions."""

    def __call__(self, n: int, placement: Placement, rng: random.Random) -> Board: ...


def random_bfs_build(n: int, placement: Placement, rng: random.Random) -> Board:
    """Build regions via simultaneous BFS growth, then refine for uniqueness.

    1. Grow all regions simultaneously from each queen (Voronoi-like).
    2. If the board has multiple solutions, iteratively transfer cells
       between regions to break alternative solutions found by the solver.

    Guarantees:
    - Every region is 4-connected.
    - Every region contains exactly one queen.
    - The full grid is partitioned.

    Args:
        n: Board size.
        placement: N queen positions.
        rng: Random number generator for reproducibility.

    Returns:
        A Board with regions assigned.
    """
    # Phase 1: simultaneous BFS growth
    regions = _simultaneous_bfs(n, placement, rng)
    board = Board(n=n, regions=regions, solution=placement)

    # Phase 2: refine to eliminate alternative solutions
    for _refine in range(50):
        solns = find_up_to_k_solutions(board, k=2)
        if len(solns) <= 1:
            return board

        # solns[0] should be the intended solution, solns[1] is alternative
        alt = set(solns[1])
        intended = set(placement)

        # Find a cell in the alternative solution that differs from intended
        extra = list(alt - intended)
        if not extra:
            break

        r, c = extra[rng.randint(0, len(extra) - 1)]
        _transfer_cell(regions, n, r, c, rng, placement)
        board = Board(n=n, regions=regions.copy(), solution=placement)

    return board


def _simultaneous_bfs(n: int, placement: Placement, rng: random.Random) -> np.ndarray:
    """Grow all regions simultaneously from queen seeds."""
    regions = np.full((n, n), -1, dtype=np.int_)
    queues: list[deque[tuple[int, int]]] = []

    for rid, (qr, qc) in enumerate(placement):
        regions[qr, qc] = rid
        queues.append(deque([(qr, qc)]))

    unclaimed = n * n - n

    while unclaimed > 0:
        lengths = [len(q) for q in queues]
        total_len = sum(lengths)
        if total_len == 0:
            break

        choice = rng.randint(0, total_len - 1)
        accum = 0
        rid = 0
        for i, qlen in enumerate(lengths):
            accum += qlen
            if choice < accum:
                rid = i
                break

        if not queues[rid]:
            continue

        r, c = queues[rid].popleft()

        dirs = list(_DIRECTIONS)
        rng.shuffle(dirs)
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < n and regions[nr, nc] == -1:
                regions[nr, nc] = rid
                queues[rid].append((nr, nc))
                unclaimed -= 1

    return regions


def _transfer_cell(
    regions: np.ndarray,
    n: int,
    r: int,
    c: int,
    rng: random.Random,
    placement: Placement,
) -> None:
    """Transfer cell (r,c) to an adjacent region, avoiding queen cells.

    Only transfers if it won't disconnect the source region.
    """
    current_rid = int(regions[r, c])

    # Don't transfer queen cells
    if (r, c) in set(placement):
        return

    # Check that removing this cell won't disconnect its region
    if _would_disconnect(regions, n, r, c, current_rid):
        return

    # Find adjacent regions that are not the current one
    candidates: list[tuple[int, int]] = []
    seen: set[int] = set()
    for dr, dc in _DIRECTIONS:
        nr, nc = r + dr, c + dc
        if 0 <= nr < n and 0 <= nc < n:
            nrid = int(regions[nr, nc])
            if nrid != current_rid and nrid not in seen:
                seen.add(nrid)
                candidates.append((nr, nc))

    if not candidates:
        return

    # Pick a random neighbor region to transfer to
    nr, nc = candidates[rng.randint(0, len(candidates) - 1)]
    new_rid = int(regions[nr, nc])
    regions[r, c] = new_rid


def _would_disconnect(
    regions: np.ndarray,
    n: int,
    r: int,
    c: int,
    rid: int,
) -> bool:
    """Check if removing cell (r,c) would disconnect region rid."""
    # Temporarily mark as removed, BFS from a neighbor, check coverage
    saved = int(regions[r, c])
    regions[r, c] = -1

    # Find a starting neighbor of the same region
    start: tuple[int, int] | None = None
    total_cells = 0
    for dr, dc in _DIRECTIONS:
        nr, nc = r + dr, c + dc
        if 0 <= nr < n and 0 <= nc < n and int(regions[nr, nc]) == rid:
            start = (nr, nc)
            break

    if start is None:
        # This was the only cell in the region — shouldn't happen
        regions[r, c] = saved
        return True  # Would disconnect (region becomes empty)

    # Count total cells in this region (excluding (r,c))
    for rr in range(n):
        for cc in range(n):
            if int(regions[rr, cc]) == rid:
                total_cells += 1

    # BFS from start
    visited: set[tuple[int, int]] = {start}
    queue: list[tuple[int, int]] = [start]
    while queue:
        cr, cc = queue.pop()
        for dr, dc in _DIRECTIONS:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < n and 0 <= nc < n:
                if int(regions[nr, nc]) == rid and (nr, nc) not in visited:
                    visited.add((nr, nc))
                    queue.append((nr, nc))

    regions[r, c] = saved
    return len(visited) < total_cells
