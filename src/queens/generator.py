"""Board generator orchestrator.

Combines placement, region building, uniqueness verification,
and difficulty analysis into a retry loop that produces
valid Queens boards.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from .board import Board, Placement
from .difficulty import DifficultyAnalyzer, layered_analyze
from .placement import PlacementStrategy, backtracking_placement
from .regions import RegionBuilder, nqueens_aware_build, random_bfs_build  # noqa: F401
from .solver import count_solutions

if TYPE_CHECKING:
    import numpy as np


class GenerationError(RuntimeError):
    """Raised when board generation fails after max attempts."""


_DIRECTIONS: tuple[tuple[int, int], ...] = ((0, 1), (0, -1), (1, 0), (-1, 0))


def generate_board(
    n: int,
    *,
    place_func: PlacementStrategy = backtracking_placement,
    region_func: RegionBuilder = random_bfs_build,
    target_difficulty: float | None = None,
    difficulty_fn: DifficultyAnalyzer = layered_analyze,
    max_attempts: int = 1000,
    seed: int | None = None,
    harden_deduction: bool = True,
) -> Board:
    """Generate a valid N×N Queens board with exactly one unique solution.

    The generation pipeline:
    1. Place N queens (row/col/anti-adjacency valid).
    2. Build connected regions around each queen.
    3. Count all solutions — keep only if unique.
    4. If harden_deduction, iteratively transfer cells to break deduction
       patterns (forced singletons, line locks) while preserving uniqueness.
    5. (Optional) Assess difficulty and filter by target.

    Args:
        n: Board size (N×N).
        place_func: Strategy for placing initial queens.
        region_func: Strategy for building coloured regions.
        target_difficulty: If set, only return boards at or above
            this difficulty score (float, 0–10+).
        difficulty_fn: Function for difficulty assessment.
        max_attempts: Maximum generation attempts before raising.
        seed: Random seed for reproducibility.
        harden_deduction: If True, apply deduction-breaking refinement.

    Returns:
        A valid Board with one unique solution.

    Raises:
        GenerationError: If no valid board is found within ``max_attempts``.
    """
    rng = random.Random(seed)
    for _attempt in range(max_attempts):
        placement = place_func(n, rng)
        board = region_func(n, placement, rng)

        # Verify uniqueness
        sol_count = count_solutions(board, limit=2)
        if sol_count != 1:
            continue

        # Deduction hardening
        if harden_deduction:
            board = _harden_deduction_resistance(board, n, placement, rng)
            sol_count = count_solutions(board, limit=2)
            if sol_count != 1:
                continue

        # Check difficulty if requested
        if target_difficulty is not None:
            report = difficulty_fn(board)
            if report.score < target_difficulty:
                continue

        return board

    raise GenerationError(f"Failed to generate a valid {n}×{n} board after {max_attempts} attempts")


def _harden_deduction_resistance(
    board: Board,
    n: int,
    placement: Placement,
    _rng: random.Random,
) -> Board:
    """Iteratively transfer cells to break deduction patterns.

    Each candidate transfer is verified for uniqueness preservation.
    Only transfers that keep the board valid (exactly 1 solution) are kept.
    """
    from .difficulty import _DeductionState  # noqa: PLC0415

    regions = board.regions.copy()
    intended = set(placement)

    for _iteration in range(25):
        state = _DeductionState(n, regions)
        state.run_full_deduction()

        if state.queens_count == n:
            # Deduction solved it — find pattern and try to break it
            changed = _break_deduction_step(regions, n, intended, state)
            if not changed:
                break

            # Verify uniqueness after transfer
            test_board = Board(n=n, regions=regions.copy(), solution=placement)
            if count_solutions(test_board, limit=2) != 1:
                break
        else:
            break  # Already not deduction-solvable

    return Board(n=n, regions=regions, solution=placement)


def _would_disconnect_local(
    regions: np.ndarray,
    n: int,
    r: int,
    c: int,
    rid: int,
) -> bool:
    """Check if removing (r,c) would disconnect region rid."""
    saved = int(regions[r, c])
    regions[r, c] = -1

    start: tuple[int, int] | None = None
    for dr, dc in _DIRECTIONS:
        nr, nc = r + dr, c + dc
        if 0 <= nr < n and 0 <= nc < n and int(regions[nr, nc]) == rid:
            start = (nr, nc)
            break

    if start is None:
        regions[r, c] = saved
        return True

    total = sum(1 for rr in range(n) for cc in range(n) if int(regions[rr, cc]) == rid)
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
    return len(visited) < total


def _break_deduction_step(
    regions: np.ndarray,
    n: int,
    intended: set[tuple[int, int]],
    state: object,  # _DeductionState
) -> bool:
    """Try to break the first deduction step by transferring a cell."""
    for rid in range(n):
        if state.region_has[rid]:  # type: ignore[union-attr]
            continue
        avail = state._region_avail(rid)  # type: ignore[union-attr]  # noqa: SLF001
        if len(avail) == 1:
            target_cell = avail[0]

            for dr, dc in _DIRECTIONS:
                nr, nc = target_cell[0] + dr, target_cell[1] + dc
                if (
                    0 <= nr < n
                    and 0 <= nc < n
                    and int(regions[nr, nc]) != rid
                    and (nr, nc) not in intended
                ):
                    if not _would_disconnect_local(regions, n, nr, nc, int(regions[nr, nc])):
                        regions[nr, nc] = rid
                        return True

        # Also try line-locked regions
        if len(avail) >= 2:
            rows = {r for r, _ in avail}
            cols = {c for _, c in avail}
            if len(rows) == 1:
                locked_row = rows.pop()
                for other_rid in range(n):
                    if other_rid == rid or state.region_has[other_rid]:  # type: ignore[union-attr]
                        continue
                    other_avail = state._region_avail(other_rid)  # type: ignore[union-attr]  # noqa: SLF001
                    for or_, oc in other_avail:
                        if or_ != locked_row and (or_, oc) not in intended:
                            if not _would_disconnect_local(regions, n, or_, oc, other_rid):
                                regions[or_, oc] = rid
                                return True
            if len(cols) == 1:
                locked_col = cols.pop()
                for other_rid in range(n):
                    if other_rid == rid or state.region_has[other_rid]:  # type: ignore[union-attr]
                        continue
                    other_avail = state._region_avail(other_rid)  # type: ignore[union-attr]  # noqa: SLF001
                    for or_, oc in other_avail:
                        if oc != locked_col and (or_, oc) not in intended:
                            if not _would_disconnect_local(regions, n, or_, oc, other_rid):
                                regions[or_, oc] = rid
                                return True

    return False
