"""Constraint solver for Queens puzzles.

Counts all valid queen placements for a given Board.
Uses backtracking with MRV (Minimum Remaining Values) heuristic
and forward checking for efficient pruning.
"""

from __future__ import annotations

from .board import Board, Placement

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


def count_solutions(board: Board, limit: int = 2) -> int:
    """Count valid queen placements up to `limit`.

    Uses MRV heuristic: always places in the region with fewest
    remaining legal cells. Forward-checking prunes branches where
    any unsolved region has zero legal cells.

    Args:
        board: The board to solve.
        limit: Stop counting once this many solutions are found.

    Returns:
        Number of valid queen placements (capped at `limit`).
    """
    n = board.n
    regions = board.regions
    count = 0

    # Precompute per-region cell sets for O(1) region lookup
    region_cells: list[set[tuple[int, int]]] = [set() for _ in range(n)]
    for r in range(n):
        for c in range(n):
            region_cells[int(regions[r, c])].add((r, c))

    # State
    available: list[list[bool]] = [[True] * n for _ in range(n)]
    row_has: list[bool] = [False] * n
    col_has: list[bool] = [False] * n
    region_has: list[bool] = [False] * n
    placed: set[tuple[int, int]] = set()

    def _adjacent(r: int, c: int) -> bool:
        for dr, dc in _NEIGHBORS:
            if (r + dr, c + dc) in placed:
                return True
        return False

    def _region_avail(rid: int) -> int:
        n_avail = 0
        for cr, cc in region_cells[rid]:
            if available[cr][cc]:
                n_avail += 1
        return n_avail

    def _region_avail_cells(rid: int) -> list[tuple[int, int]]:
        return [(cr, cc) for cr, cc in region_cells[rid] if available[cr][cc]]

    def _any_region_dead() -> bool:
        for rid in range(n):
            if region_has[rid]:
                continue
            if _region_avail(rid) == 0:
                return True
        return False

    def _place(r: int, c: int) -> tuple[list[tuple[int, int]], int]:
        affected: list[tuple[int, int]] = []
        for cc in range(n):
            if available[r][cc]:
                available[r][cc] = False
                affected.append((r, cc))
        for rr in range(n):
            if available[rr][c]:
                available[rr][c] = False
                affected.append((rr, c))
        for dr, dc in _NEIGHBORS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < n and available[nr][nc]:
                available[nr][nc] = False
                affected.append((nr, nc))
        rid = int(regions[r, c])
        row_has[r] = True
        col_has[c] = True
        region_has[rid] = True
        placed.add((r, c))
        return affected, rid

    def _unplace(affected: list[tuple[int, int]], rid: int, r: int, c: int) -> None:
        for cr, cc in affected:
            available[cr][cc] = True
        row_has[r] = False
        col_has[c] = False
        region_has[rid] = False
        placed.discard((r, c))

    def _solve() -> bool:
        nonlocal count
        if count >= limit:
            return True

        # MRV: region with fewest available cells
        best_rid = -1
        best_cnt = n * n + 1
        for rid in range(n):
            if region_has[rid]:
                continue
            cnt = _region_avail(rid)
            if cnt == 0:
                return False
            if cnt < best_cnt:
                best_cnt = cnt
                best_rid = rid

        if best_rid == -1:
            # All regions satisfied — found a solution
            count += 1
            return False

        for r, c in _region_avail_cells(best_rid):
            if not available[r][c]:
                continue
            if row_has[r] or col_has[c]:
                continue
            if _adjacent(r, c):
                continue

            affected, rid = _place(r, c)

            if not _any_region_dead():
                if _solve():
                    _unplace(affected, rid, r, c)
                    return True

            _unplace(affected, rid, r, c)

        return False

    _solve()
    return count


def find_up_to_k_solutions(board: Board, k: int = 2) -> list[Placement]:
    """Find up to k valid queen placements.

    Stops early once k solutions are found. Much faster than
    :func:`find_all_solutions` for boards with many solutions.

    Args:
        board: The board to solve.
        k: Maximum number of solutions to return.

    Returns:
        Up to k valid queen placement tuples.
    """
    n = board.n
    regions = board.regions
    solutions: list[Placement] = []

    region_cells: list[set[tuple[int, int]]] = [set() for _ in range(n)]
    for r in range(n):
        for c in range(n):
            region_cells[int(regions[r, c])].add((r, c))

    available: list[list[bool]] = [[True] * n for _ in range(n)]
    row_has: list[bool] = [False] * n
    col_has: list[bool] = [False] * n
    region_has: list[bool] = [False] * n
    placed: set[tuple[int, int]] = set()
    current: list[tuple[int, int]] = []

    def _adjacent(r: int, c: int) -> bool:
        for dr, dc in _NEIGHBORS:
            if (r + dr, c + dc) in placed:
                return True
        return False

    def _region_avail(rid: int) -> int:
        n_avail = 0
        for cr, cc in region_cells[rid]:
            if available[cr][cc]:
                n_avail += 1
        return n_avail

    def _region_avail_cells(rid: int) -> list[tuple[int, int]]:
        return [(cr, cc) for cr, cc in region_cells[rid] if available[cr][cc]]

    def _any_region_dead() -> bool:
        for rid in range(n):
            if region_has[rid]:
                continue
            if _region_avail(rid) == 0:
                return True
        return False

    def _place(r: int, c: int) -> tuple[list[tuple[int, int]], int]:
        affected: list[tuple[int, int]] = []
        for cc in range(n):
            if available[r][cc]:
                available[r][cc] = False
                affected.append((r, cc))
        for rr in range(n):
            if available[rr][c]:
                available[rr][c] = False
                affected.append((rr, c))
        for dr, dc in _NEIGHBORS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < n and available[nr][nc]:
                available[nr][nc] = False
                affected.append((nr, nc))
        rid = int(regions[r, c])
        row_has[r] = True
        col_has[c] = True
        region_has[rid] = True
        placed.add((r, c))
        current.append((r, c))
        return affected, rid

    def _unplace(affected: list[tuple[int, int]], rid: int, r: int, c: int) -> None:
        for cr, cc in affected:
            available[cr][cc] = True
        row_has[r] = False
        col_has[c] = False
        region_has[rid] = False
        placed.discard((r, c))
        current.pop()

    def _solve() -> bool:
        if len(solutions) >= k:
            return True

        best_rid = -1
        best_cnt = n * n + 1
        for rid in range(n):
            if region_has[rid]:
                continue
            cnt = _region_avail(rid)
            if cnt == 0:
                return False
            if cnt < best_cnt:
                best_cnt = cnt
                best_rid = rid

        if best_rid == -1:
            solutions.append(tuple(current))
            return False

        for r, c in _region_avail_cells(best_rid):
            if not available[r][c]:
                continue
            if row_has[r] or col_has[c]:
                continue
            if _adjacent(r, c):
                continue

            affected, rid = _place(r, c)

            if not _any_region_dead():
                if _solve():
                    _unplace(affected, rid, r, c)
                    return True

            _unplace(affected, rid, r, c)

        return False

    _solve()
    return solutions


def find_all_solutions(board: Board) -> list[Placement]:
    """Find every valid queen placement for a board.

    Useful for debugging and verification. For normal use,
    prefer :func:`count_solutions` with a limit=2.

    Args:
        board: The board to solve.

    Returns:
        All valid queen placement tuples.
    """
    n = board.n
    regions = board.regions
    solutions: list[Placement] = []

    region_cells: list[set[tuple[int, int]]] = [set() for _ in range(n)]
    for r in range(n):
        for c in range(n):
            region_cells[int(regions[r, c])].add((r, c))

    available: list[list[bool]] = [[True] * n for _ in range(n)]
    row_has: list[bool] = [False] * n
    col_has: list[bool] = [False] * n
    region_has: list[bool] = [False] * n
    placed: set[tuple[int, int]] = set()
    current: list[tuple[int, int]] = []

    def _adjacent(r: int, c: int) -> bool:
        for dr, dc in _NEIGHBORS:
            if (r + dr, c + dc) in placed:
                return True
        return False

    def _region_avail(rid: int) -> int:
        n_avail = 0
        for cr, cc in region_cells[rid]:
            if available[cr][cc]:
                n_avail += 1
        return n_avail

    def _region_avail_cells(rid: int) -> list[tuple[int, int]]:
        return [(cr, cc) for cr, cc in region_cells[rid] if available[cr][cc]]

    def _any_region_dead() -> bool:
        for rid in range(n):
            if region_has[rid]:
                continue
            if _region_avail(rid) == 0:
                return True
        return False

    def _place(r: int, c: int) -> tuple[list[tuple[int, int]], int]:
        affected: list[tuple[int, int]] = []
        for cc in range(n):
            if available[r][cc]:
                available[r][cc] = False
                affected.append((r, cc))
        for rr in range(n):
            if available[rr][c]:
                available[rr][c] = False
                affected.append((rr, c))
        for dr, dc in _NEIGHBORS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < n and available[nr][nc]:
                available[nr][nc] = False
                affected.append((nr, nc))
        rid = int(regions[r, c])
        row_has[r] = True
        col_has[c] = True
        region_has[rid] = True
        placed.add((r, c))
        current.append((r, c))
        return affected, rid

    def _unplace(affected: list[tuple[int, int]], rid: int, r: int, c: int) -> None:
        for cr, cc in affected:
            available[cr][cc] = True
        row_has[r] = False
        col_has[c] = False
        region_has[rid] = False
        placed.discard((r, c))
        current.pop()

    def _solve() -> None:
        best_rid = -1
        best_cnt = n * n + 1
        for rid in range(n):
            if region_has[rid]:
                continue
            cnt = _region_avail(rid)
            if cnt == 0:
                return
            if cnt < best_cnt:
                best_cnt = cnt
                best_rid = rid

        if best_rid == -1:
            solutions.append(tuple(current))
            return

        for r, c in _region_avail_cells(best_rid):
            if not available[r][c]:
                continue
            if row_has[r] or col_has[c]:
                continue
            if _adjacent(r, c):
                continue

            affected, rid = _place(r, c)

            if not _any_region_dead():
                _solve()

            _unplace(affected, rid, r, c)

    _solve()
    return solutions
