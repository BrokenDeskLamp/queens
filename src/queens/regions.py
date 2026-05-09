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

_MAX_ALT_SOLUTIONS = 20
_MAX_REFINE_ITERS = 30


class RegionBuilder(Protocol):
    """Structural protocol for region building functions."""

    def __call__(self, n: int, placement: Placement, rng: random.Random) -> Board: ...


# ── Original BFS + hot-spot builder ─────────────────────────────────────


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

        intended = set(placement)
        heat: Counter[tuple[int, int]] = Counter()
        for sol in alt_solutions:
            for pos in sol:
                if pos not in intended:
                    heat[pos] += 1

        if not heat:
            return board

        hot_spots = [pos for pos, _ in heat.most_common()]
        rng.shuffle(hot_spots)

        transferred = 0
        for r, c in hot_spots:
            if transferred >= 3:
                break
            if (r, c) in intended:
                continue
            count = _transfer_patch(regions, n, r, c, rng, placement)
            if count > 0:
                transferred += count

        if transferred == 0:
            break

        board = Board(n=n, regions=regions.copy(), solution=placement)

    return board


# ── N-Queens-aware builder (harder boards) ──────────────────────────────


def nqueens_aware_build(n: int, placement: Placement, rng: random.Random) -> Board:
    """Build regions by blocking all known N-Queens alternatives.

    Unlike BFS-based growth which produces deduction-friendly blobs,
    this builder:

    1. Enumerates ALL modified N-Queens solutions for size N.
    2. Grows initial regions via BFS.
    3. For each alternative solution, moves cells between regions so that
       at least two of the alternative's queen positions land in the same
       region — guaranteeing the alternative is invalid.
    4. Then runs aggressive anti-deduction refinement to break
       forced singletons, line locks, and group locks.

    Because this knows about EVERY alternative upfront (not just those
    found by a solver), regions are shaped to be globally deduction-resistant.

    Args:
        n: Board size.
        placement: N queen positions (the unique solution).
        rng: Random number generator for reproducibility.

    Returns:
        A Board with regions assigned.
    """
    # Phase 1: BFS growth for initial connected regions
    regions = _simultaneous_bfs(n, placement, rng)

    # Phase 2: Enumerate all N-Queens alternatives
    all_alts = _all_nqueens_solutions(n)
    target_bits = _placement_to_bits(n, placement)
    alternatives = [bits for bits in all_alts if bits != target_bits]
    rng.shuffle(alternatives)

    # Phase 3: Block alternatives by cell transfers
    _block_alternatives(regions, n, placement, alternatives, rng)

    # Phase 4: Aggressive anti-deduction refinement
    _anti_deduction_refine(regions, n, placement, rng)

    # Verify regions are all connected
    _ensure_all_connected(regions, n, placement, rng)

    return Board(n=n, regions=regions, solution=placement)


# ── N-Queens enumeration (bitwise, modified rules) ──────────────────────


def _all_nqueens_solutions(n: int) -> list[int]:
    """Return all modified N-Queens solutions as bitmasks (one int per row).

    Modified rules: one queen per row/col, NO two queens are adjacent
    (including diagonals). Standard N-Queens uses full diagonal attack;
    this uses only immediate-neighbour adjacency.
    """
    solutions: list[int] = []
    # representation: tuple of N ints, each int = 1 << col
    stack: list[tuple[int, int, int, int]] = [(0, 0, 0, 0)]

    all_cols = (1 << n) - 1

    while stack:
        row, cols, diag, packed = stack.pop()

        if row == n:
            solutions.append(packed)
            continue

        # Legal cols: not in same col, not adjacent to prev queen
        # diag tracks columns blocked by adjacency to queen in row-1
        mask = (~(cols | diag)) & all_cols
        bit = mask & -mask

        while bit != 0:
            # Adjacency constraint for next row: the bit's neighbours
            # (bit<<1 for NW-SE, bit>>1 for NE-SW)
            new_diag = (bit << 1) | (bit >> 1)
            # Pack the bit into the solution: shift by row*n bits
            col_idx = (bit.bit_length() - 1)
            new_packed = packed | (col_idx << (row * 4))  # max N=15 fits in 4 bits

            stack.append((row + 1, cols | bit, new_diag, new_packed))

            mask ^= bit
            bit = mask & -mask

    return solutions


def _placement_to_bits(n: int, placement: Placement) -> int:  # noqa: ARG001
    """Convert placement [(r,c),...] to packed bits representation."""
    result = 0
    for r, c in placement:
        result |= c << (r * 4)
    return result


def _unpack_solution(n: int, packed: int) -> list[tuple[int, int]]:
    """Unpack bits to list of (row, col) positions."""
    return [(r, (packed >> (r * 4)) & 0xF) for r in range(n)]


# ── Alternative blocking ────────────────────────────────────────────────


def _block_alternatives(
    regions: np.ndarray,
    n: int,
    placement: Placement,
    alternatives: list[int],
    rng: random.Random,
    max_to_block: int = 500,
) -> None:
    """Transfer cells to block as many alternatives as possible.

    For each alternative, try to put two of its queen cells in the same
    region. Uses connectivity-preserving transfers only.
    """
    intended = set(placement)

    blocked = 0
    for alt_bits in alternatives:
        if blocked >= max_to_block:
            break

        alt_queens = _unpack_solution(n, alt_bits)

        # Collect region assignments for this alternative's queens
        # (only cells that aren't the target queen cells)
        alt_regions: dict[int, list[tuple[int, int]]] = {}
        for qr, qc in alt_queens:
            if (qr, qc) in intended:
                continue
            rid = int(regions[qr, qc])
            alt_regions.setdefault(rid, []).append((qr, qc))

        # Find region with 2+ cells from this alternative
        # If none exists, try to create one by transfer
        has_duplicate = any(len(cells) >= 2 for cells in alt_regions.values())
        if has_duplicate:
            blocked += 1
            continue

        # Need to move a cell to create a duplicate region
        # Pick two cells from different regions and try to merge them
        region_list = list(alt_regions.items())
        if len(region_list) < 2:
            continue  # can't block — only 1 non-queen cell or all in same region

        rng.shuffle(region_list)
        for i in range(len(region_list)):
            for j in range(i + 1, len(region_list)):
                rid_i, cells_i = region_list[i]
                rid_j, cells_j = region_list[j]

                for ci in cells_i:
                    if _transfer_cell_to_region(regions, n, ci[0], ci[1], rid_j):
                        blocked += 1
                        break
                else:
                    for cj in cells_j:
                        if _transfer_cell_to_region(regions, n, cj[0], cj[1], rid_i):
                            blocked += 1
                            break
                    else:
                        continue
                break
            else:
                continue
            break


def _transfer_cell_to_region(
    regions: np.ndarray,
    n: int,
    r: int,
    c: int,
    target_rid: int,
) -> bool:
    """Transfer cell (r,c) to target_rid, preserving connectivity.

    Returns True if transfer succeeded.
    """
    current_rid = int(regions[r, c])
    if current_rid == target_rid:
        return True

    # Don't disconnect current region
    if _would_disconnect(regions, n, r, c, current_rid):
        return False

    # Target region must be adjacent
    for dr, dc in _DIRECTIONS:
        nr, nc = r + dr, c + dc
        if 0 <= nr < n and 0 <= nc < n and int(regions[nr, nc]) == target_rid:
            regions[r, c] = target_rid
            return True

    return False


# ── Anti-deduction refinement ───────────────────────────────────────────


def _anti_deduction_refine(
    regions: np.ndarray,
    n: int,
    placement: Placement,
    rng: random.Random,
    max_iterations: int = 20,
) -> None:
    """Break deduction patterns: line locks, group locks, forced singletons.

    After alternative blocking, regions may still have structural patterns
    that deduction exploits. This phase explicitly breaks them.
    """
    intended = set(placement)

    for _iteration in range(max_iterations):
        changed = False

        # 1. Break line locks: if a region's cells all share a row or col,
        #    transfer one cell to an adjacent different region
        for rid in range(n):
            cells = [
                (r, c)
                for r in range(n)
                for c in range(n)
                if int(regions[r, c]) == rid and (r, c) not in intended
            ]
            if not cells:
                continue

            rows = {r for r, _ in cells}
            cols = {c for _, c in cells}

            if len(rows) == 1 and len(cells) >= 2:
                # All cells in one row — try to move one to a different row
                cell = cells[rng.randint(0, len(cells) - 1)]
                for dr, dc in _DIRECTIONS:
                    nr, nc = cell[0] + dr, cell[1] + dc
                    if 0 <= nr < n and 0 <= nc < n and nr != cell[0]:
                        target_rid = int(regions[nr, nc])
                        if target_rid != rid:
                            if _transfer_cell_to_region(regions, n, cell[0], cell[1], target_rid):
                                changed = True
                                break
                if changed:
                    break

            if len(cols) == 1 and len(cells) >= 2:
                # All cells in one column — try to move one
                cell = cells[rng.randint(0, len(cells) - 1)]
                for dr, dc in _DIRECTIONS:
                    nr, nc = cell[0] + dr, cell[1] + dc
                    if 0 <= nr < n and 0 <= nc < n and nc != cell[1]:
                        target_rid = int(regions[nr, nc])
                        if target_rid != rid:
                            if _transfer_cell_to_region(regions, n, cell[0], cell[1], target_rid):
                                changed = True
                                break
                if changed:
                    break

        if changed:
            continue

        # 2. Scatter cells: for each region, try to move a non-queen cell
        #    to a neighbor to increase row/col diversity
        for rid in range(n):
            cells = [
                (r, c)
                for r in range(n)
                for c in range(n)
                if int(regions[r, c]) == rid and (r, c) not in intended
            ]
            if len(cells) <= 1:
                continue

            cell = cells[rng.randint(0, len(cells) - 1)]
            for dr, dc in _DIRECTIONS:
                nr, nc = cell[0] + dr, cell[1] + dc
                if 0 <= nr < n and 0 <= nc < n:
                    target_rid = int(regions[nr, nc])
                    if target_rid != rid:
                        if _transfer_cell_to_region(regions, n, cell[0], cell[1], target_rid):
                            changed = True
                            break
            if changed:
                break

        if not changed:
            break


# ── Connectivity helpers ────────────────────────────────────────────────


def _ensure_all_connected(
    regions: np.ndarray,
    n: int,
    placement: Placement,  # noqa: ARG001
    rng: random.Random,
) -> None:
    """Ensure every region is 4-connected by growing BFS seeds into gaps."""
    for rid in range(n):
        cells = [
            (r, c)
            for r in range(n)
            for c in range(n)
            if int(regions[r, c]) == rid
        ]
        if not cells:
            continue

        # Find connected components
        components = _find_components(regions, n, rid, cells)
        if len(components) <= 1:
            continue

        # Grow the main component by converting nearby -1 or adjacent cells
        main = max(components, key=len)
        for comp in components:
            if comp is main:
                continue
            for r, c in comp:
                regions[r, c] = -1  # unassign isolated fragment

        # Let BFS fill reconnect them
        queue = deque(main)
        while queue:
            r, c = queue.popleft()
            dirs = list(_DIRECTIONS)
            rng.shuffle(dirs)
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n and int(regions[nr, nc]) == -1:
                    regions[nr, nc] = rid
                    queue.append((nr, nc))


def _find_components(
    regions: np.ndarray,
    n: int,
    rid: int,
    cells: list[tuple[int, int]],
) -> list[list[tuple[int, int]]]:
    """Find 4-connected components of region rid."""
    unvisited = set(cells)
    components: list[list[tuple[int, int]]] = []

    while unvisited:
        start = unvisited.pop()
        comp: list[tuple[int, int]] = [start]
        queue = [start]
        while queue:
            r, c = queue.pop()
            for dr, dc in _DIRECTIONS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n:
                    if int(regions[nr, nc]) == rid and (nr, nc) in unvisited:
                        unvisited.discard((nr, nc))
                        comp.append((nr, nc))
                        queue.append((nr, nc))
        components.append(comp)

    return components


# ── Shared helpers ──────────────────────────────────────────────────────


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
    """Transfer a hot-spot cell and its transferable same-region neighbours."""
    intended = set(placement)
    source_rid = int(regions[seed_r, seed_c])

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
    """Transfer a single cell to an adjacent region."""
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
