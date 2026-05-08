"""Difficulty analysis for Queens boards.

Uses a layered logic-only solver. Each layer has access to
more advanced deduction techniques. The board's difficulty
is the minimum layer that can solve it without backtracking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .board import Board

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


@dataclass(frozen=True)
class DifficultyReport:
    """Result of difficulty analysis.

    Attributes:
        score: Minimum technique layer needed (0-5).
        techniques_used: Specific deduction techniques that triggered.
        solve_path: Step-by-step description of the solve.
    """

    score: int
    techniques_used: tuple[str, ...]
    solve_path: tuple[str, ...]


class DifficultyAnalyzer(Protocol):
    """Structural protocol for difficulty analysis functions."""

    def __call__(self, board: Board) -> DifficultyReport: ...


def layered_analyze(board: Board) -> DifficultyReport:
    """Analyze board difficulty by running layered logic solvers.

    Tries each layer in order (0 → 5). Returns the first layer
    that can solve the board without backtracking.

    Layers:
        0: Forced singleton only
        1: + Row/col/region elimination
        2: + Region line lock
        3: + Region group lock, line group lock
        4: + Diagonal neighbor elimination
        5: + Test a Queen (hypothetical chains)

    Args:
        board: The board to analyze.

    Returns:
        DifficultyReport with score and techniques used.
    """
    for layer in range(6):
        solved, techniques, path = _try_solve_at_layer(board, layer)
        if solved:
            return DifficultyReport(
                score=layer,
                techniques_used=tuple(techniques),
                solve_path=tuple(path),
            )
    return DifficultyReport(score=5, techniques_used=(), solve_path=())


def _try_solve_at_layer(board: Board, layer: int) -> tuple[bool, list[str], list[str]]:
    """Attempt to solve using techniques up to the given layer.

    Returns:
        (solved, techniques_used, solve_path)
    """
    n = board.n
    regions = board.regions

    # State
    available: list[list[bool]] = [[True] * n for _ in range(n)]
    queens: list[tuple[int, int]] = []
    row_has = [False] * n
    col_has = [False] * n
    region_has = [False] * n

    # Precompute region cells
    region_cells: list[set[tuple[int, int]]] = [set() for _ in range(n)]
    for r in range(n):
        for c in range(n):
            region_cells[int(regions[r, c])].add((r, c))

    techniques: list[str] = []
    path: list[str] = []

    # ---- helpers ----

    def _region_avail(rid: int) -> list[tuple[int, int]]:
        return [(r, c) for r, c in region_cells[rid] if available[r][c]]

    def _row_avail(r: int) -> list[int]:
        return [c for c in range(n) if available[r][c]]

    def _col_avail(c: int) -> list[int]:
        return [r for r in range(n) if available[r][c]]

    def _place_queen(r: int, c: int) -> None:
        rid = int(regions[r, c])
        # Full elimination
        for cc in range(n):
            available[r][cc] = False
        for rr in range(n):
            available[rr][c] = False
        for dr, dc in _NEIGHBORS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < n:
                available[nr][nc] = False
        row_has[r] = True
        col_has[c] = True
        region_has[rid] = True
        queens.append((r, c))
        path.append(f"Queen at ({r},{c}) in region {rid}")

    def _dead_region_exists() -> bool:
        for rid in range(n):
            if region_has[rid]:
                continue
            if not _region_avail(rid):
                return True
        return False

    # ---- technique: forced singleton ----

    def _try_forced_singleton() -> bool:
        """If a region/row/col has exactly one legal cell, place a queen there."""
        # Regions
        for rid in range(n):
            if region_has[rid]:
                continue
            cells = _region_avail(rid)
            if len(cells) == 1:
                r, c = cells[0]
                techniques.append("forced_singleton")
                _place_queen(r, c)
                return True

        # Rows
        for r in range(n):
            if row_has[r]:
                continue
            ac = _row_avail(r)
            if len(ac) == 1:
                c = ac[0]
                rid = int(regions[r, c])
                if not region_has[rid]:
                    techniques.append("forced_singleton")
                    _place_queen(r, c)
                    return True

        # Cols
        for c in range(n):
            if col_has[c]:
                continue
            ar = _col_avail(c)
            if len(ar) == 1:
                r = ar[0]
                rid = int(regions[r, c])
                if not region_has[rid]:
                    techniques.append("forced_singleton")
                    _place_queen(r, c)
                    return True

        return False

    # ---- technique: region line lock (layer 2+) ----

    def _try_region_line_lock() -> bool:
        """Eliminate other regions' cells from a locked row or col.

        If all of a region's remaining cells share a row or col,
        mark cells of other regions in that row/col as unavailable.
        """
        for rid in range(n):
            if region_has[rid]:
                continue
            cells = _region_avail(rid)
            if not cells:
                continue

            # All in same row?
            rows = {r for r, _ in cells}
            if len(rows) == 1:
                row = rows.pop()
                changed = False
                for c in range(n):
                    if available[row][c]:
                        other_rid = int(regions[row, c])
                        if other_rid != rid and not region_has[other_rid]:
                            available[row][c] = False
                            changed = True
                if changed:
                    techniques.append("region_line_lock")
                    path.append(f"Region {rid} line-locked to row {row}")
                    return True

            # All in same column?
            cols = {c for _, c in cells}
            if len(cols) == 1:
                col = cols.pop()
                changed = False
                for r in range(n):
                    if available[r][col]:
                        other_rid = int(regions[r, col])
                        if other_rid != rid and not region_has[other_rid]:
                            available[r][col] = False
                            changed = True
                if changed:
                    techniques.append("region_line_lock")
                    path.append(f"Region {rid} line-locked to col {col}")
                    return True

        return False

    # ---- technique: region group lock (layer 3+) ----

    def _try_region_group_lock() -> bool:
        """Eliminate cells via region group locks.

        If K regions' cells are contained within K rows or cols,
        eliminate other regions' cells from those rows/cols,
        and eliminate those regions' cells outside the locked set.
        """
        unsolved = [rid for rid in range(n) if not region_has[rid]]
        if len(unsolved) < 2:
            return False

        # Row group lock
        # For each subset size K ≥ 2, check if K regions fit in ≤ K rows
        for k in range(2, len(unsolved) + 1):
            for subset in _choose_k(unsolved, k):
                rows_used: set[int] = set()
                for rid in subset:
                    for r, _ in _region_avail(rid):
                        rows_used.add(r)
                if len(rows_used) <= k:
                    # These K regions occupy at most K rows —
                    # eliminate cells of these regions outside those rows,
                    # and eliminate other regions' cells inside those rows.
                    changed = False
                    for rid in subset:
                        for r, c in _region_avail(rid):
                            if r not in rows_used:
                                available[r][c] = False
                                changed = True
                    for other_rid in unsolved:
                        if other_rid in subset:
                            continue
                        for r, c in _region_avail(other_rid):
                            if r in rows_used:
                                available[r][c] = False
                                changed = True
                    if changed:
                        techniques.append("region_group_lock")
                        path.append(f"Group lock: {len(subset)} regions in {len(rows_used)} rows")
                        return True

        # Column group lock
        for k in range(2, len(unsolved) + 1):
            for subset in _choose_k(unsolved, k):
                cols_used: set[int] = set()
                for rid in subset:
                    for _, c in _region_avail(rid):
                        cols_used.add(c)
                if len(cols_used) <= k:
                    changed = False
                    for rid in subset:
                        for r, c in _region_avail(rid):
                            if c not in cols_used:
                                available[r][c] = False
                                changed = True
                    for other_rid in unsolved:
                        if other_rid in subset:
                            continue
                        for r, c in _region_avail(other_rid):
                            if c in cols_used:
                                available[r][c] = False
                                changed = True
                    if changed:
                        techniques.append("region_group_lock")
                        path.append(f"Group lock: {len(subset)} regions in {len(cols_used)} cols")
                        return True

        return False

    # ---- technique: diagonal neighbor elimination (layer 4+) ----

    def _try_diagonal_neighbor_elim() -> bool:
        """Eliminate cells via diagonal neighbor analysis.

        If every placement in a region touches the same outside cell
        diagonally, that outside cell cannot hold a queen.
        """
        for rid in range(n):
            if region_has[rid]:
                continue
            cells = _region_avail(rid)
            if not cells or len(cells) > 3:
                continue

            # Collect all diagonal neighbours of every cell in this region
            common_diag: set[tuple[int, int]] | None = None
            for r, c in cells:
                diag_neighbors: set[tuple[int, int]] = set()
                for dr, dc in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < n and 0 <= nc < n:
                        other_rid = int(regions[nr, nc])
                        if other_rid != rid and available[nr][nc]:
                            diag_neighbors.add((nr, nc))
                if common_diag is None:
                    common_diag = diag_neighbors
                else:
                    common_diag &= diag_neighbors

            if common_diag:
                changed = False
                for nr, nc in common_diag:
                    if available[nr][nc]:
                        available[nr][nc] = False
                        changed = True
                if changed:
                    techniques.append("diagonal_neighbor_elimination")
                    path.append(f"Diagonal elimination from region {rid}")
                    return True

        return False

    # ---- technique: test a queen (layer 5+) ----

    def _try_test_queen() -> bool:
        """For each region with 2 legal cells, test-placing a queen.

        If the test forces any region to have 0 cells,
        the tested cell is eliminated.
        """
        for rid in range(n):
            if region_has[rid]:
                continue
            cells = _region_avail(rid)
            if len(cells) != 2:
                continue

            for test_r, test_c in cells:
                # Simulate placing a queen at (test_r, test_c)
                saved = _snapshot()
                _place_queen(test_r, test_c)

                # Run forced deduction chain
                while True:
                    if _dead_region_exists():
                        # Contradiction! The test queen kills a region.
                        _restore(saved)
                        # Eliminate this cell (it can't be a queen)
                        available[test_r][test_c] = False
                        techniques.append("test_a_queen")
                        path.append(
                            f"Test Queen at ({test_r},{test_c}) eliminated — creates dead region"
                        )
                        return True
                    # Apply forced singletons to propagate
                    progress = False
                    while _try_forced_singleton():
                        progress = True
                    if layer >= 2:
                        while _try_region_line_lock():
                            progress = True
                    if not progress:
                        break

                _restore(saved)

        return False

    # ---- snapshot/restore for test-a-queen backtracking ----

    def _snapshot() -> tuple:
        return (
            [row[:] for row in available],
            list(queens),
            list(row_has),
            list(col_has),
            list(region_has),
        )

    def _restore(snap: tuple) -> None:
        nonlocal available, queens, row_has, col_has, region_has
        saved_avail, saved_queens, saved_rows, saved_cols, saved_regions = snap
        available = saved_avail
        queens.clear()
        queens.extend(saved_queens)
        for i in range(n):
            row_has[i] = saved_rows[i]
            col_has[i] = saved_cols[i]
            region_has[i] = saved_regions[i]

    # ---- main deduction loop ----

    while len(queens) < n:
        progress = False

        # Forced singletons (all layers)
        while _try_forced_singleton():
            if _dead_region_exists():
                return False, techniques, path
            progress = True

        if len(queens) == n:
            break

        # Region line lock (layer 2+)
        if layer >= 2 and _try_region_line_lock():
            progress = True
            continue

        # Region group lock (layer 3+)
        if layer >= 3 and _try_region_group_lock():
            progress = True
            continue

        # Diagonal neighbour elimination (layer 4+)
        if layer >= 4 and _try_diagonal_neighbor_elim():
            progress = True
            continue

        # Test a Queen (layer 5+)
        if layer >= 5 and _try_test_queen():
            progress = True
            continue

        if not progress:
            break

    solved = len(queens) == n
    return solved, techniques, path


def _choose_k(items: list[int], k: int) -> list[list[int]]:
    """Generate all k-element subsets of items."""
    result: list[list[int]] = []

    def _combine(start: int, current: list[int]) -> None:
        if len(current) == k:
            result.append(list(current))
            return
        for i in range(start, len(items)):
            current.append(items[i])
            _combine(i + 1, current)
            current.pop()

    _combine(0, [])
    return result
