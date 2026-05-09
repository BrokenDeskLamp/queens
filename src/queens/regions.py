"""Region building strategies.

Given N queen positions, partitions the NxN grid into N connected
regions, each containing exactly one queen.
"""

from __future__ import annotations

import random
from collections import Counter, deque
from typing import Protocol

import numpy as np

from .board import Board, Placement
from .solver import find_up_to_k_solutions

_DIRECTIONS: tuple[tuple[int, int], ...] = ((0, 1), (0, -1), (1, 0), (-1, 0))

# How many alternative solutions to examine during refinement.
# More alternatives → better targeting of multi-solution "hot spots".
_MAX_ALT_SOLUTIONS = 20

# Maximum refinement iterations before giving up and letting the retry loop
# handle it. Each iteration examines all alternatives and transfers multiple
# cells, so fewer iterations are needed than before.
_MAX_REFINE_ITERS = 30


class RegionBuilder(Protocol):
    """Structural protocol for region building functions."""

    def __call__(self, n: int, placement: Placement, rng: random.Random) -> Board: ...


def random_bfs_build(n: int, placement: Placement, rng: random.Random) -> Board:
    """Build regions via simultaneous BFS growth, then refine for uniqueness.

    1. Grow all regions simultaneously from each queen (Voronoi-like).
    2. Find up to 20 alternative solutions and build a "heat map" of cells
       that appear as queens in many alternatives.
    3. Transfer hot-spot cells (and their same-region neighbours) to
       adjacent regions, blocking many alternatives at once.

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
    regions = _simultaneous_bfs(n, placement, rng)
    board = Board(n=n, regions=regions, solution=placement)

    for _iteration in range(_MAX_REFINE_ITERS):
        alt_solutions = find_up_to_k_solutions(board, k=_MAX_ALT_SOLUTIONS + 1)
        if len(alt_solutions) <= 1:
            return board

        # Build heat map: cell → how many alternative solutions place a queen there
        intended = set(placement)
        heat: Counter[tuple[int, int]] = Counter()
        for sol in alt_solutions:
            for pos in sol:
                if pos not in intended:
                    heat[pos] += 1

        if not heat:
            return board

        # Sort hot-spots by frequency (most common alternatives first)
        hot_spots = [pos for pos, _ in heat.most_common()]
        rng.shuffle(hot_spots)  # shuffle equally-hot cells for variety

        # Transfer top hot-spots (up to 3 per iteration for meaningful reshaping)
        transferred = 0
        for r, c in hot_spots:
            if transferred >= 3:
                break
            if (r, c) in intended:
                continue
            # Transfer this cell and its transferable same-region neighbours
            count = _transfer_patch(regions, n, r, c, rng, placement)
            if count > 0:
                transferred += count

        if transferred == 0:
            break  # No transferable cells left — give up

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


def _transfer_patch(
    regions: np.ndarray,
    n: int,
    seed_r: int,
    seed_c: int,
    rng: random.Random,
    placement: Placement,
) -> int:
    """Transfer a hot-spot cell and its transferable same-region neighbours.

    Returns the number of cells actually transferred.
    """
    intended = set(placement)
    source_rid = int(regions[seed_r, seed_c])

    # Collect cells to attempt: the seed plus up to 3 same-region neighbours
    candidates: list[tuple[int, int]] = [(seed_r, seed_c)]
    dirs = list(_DIRECTIONS)
    rng.shuffle(dirs)
    for dr, dc in dirs:
        nr, nc = seed_r + dr, seed_c + dc
        if (
            0 <= nr < n
            and 0 <= nc < n
            and int(regions[nr, nc]) == source_rid
            and (nr, nc) not in intended
        ):
            candidates.append((nr, nc))
            if len(candidates) >= 4:
                break

    # Transfer each candidate, stopping at the first one that would disconnect
    transferred = 0
    for r, c in candidates:
        if _transfer_cell(regions, n, r, c, rng, placement):
            transferred += 1

    return transferred


def _transfer_cell(
    regions: np.ndarray,
    n: int,
    r: int,
    c: int,
    rng: random.Random,
    placement: Placement,
) -> bool:
    """Transfer a single cell to an adjacent region.

    Returns True if the transfer succeeded, False if it was blocked.
    """
    current_rid = int(regions[r, c])

    if (r, c) in set(placement):
        return False

    if _would_disconnect(regions, n, r, c, current_rid):
        return False

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
        return False

    nr, nc = candidates[rng.randint(0, len(candidates) - 1)]
    new_rid = int(regions[nr, nc])
    regions[r, c] = new_rid
    return True


def _would_disconnect(
    regions: np.ndarray,
    n: int,
    r: int,
    c: int,
    rid: int,
) -> bool:
    """Check if removing cell (r,c) would disconnect region rid."""
    saved = int(regions[r, c])
    regions[r, c] = -1

    start: tuple[int, int] | None = None
    total_cells = 0
    for dr, dc in _DIRECTIONS:
        nr, nc = r + dr, c + dc
        if 0 <= nr < n and 0 <= nc < n and int(regions[nr, nc]) == rid:
            start = (nr, nc)
            break

    if start is None:
        regions[r, c] = saved
        return True

    for rr in range(n):
        for cc in range(n):
            if int(regions[rr, cc]) == rid:
                total_cells += 1

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
