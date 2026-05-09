"""Difficulty analysis for Queens boards.

Uses exhaustive deduction followed by recursive hypothetical search
to measure the true objective solving difficulty.
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

_DIAGONALS: tuple[tuple[int, int], ...] = (
    (1, 1),
    (1, -1),
    (-1, 1),
    (-1, -1),
)


@dataclass(frozen=True)
class DifficultyReport:
    """Result of objective difficulty analysis.

    Attributes:
        score: Continuous difficulty score (0–10+). Higher = harder.
        difficulty_class: Human-readable class (trivial/easy/medium/hard/expert/master).
        deduction_placed: Queens placed by pure deduction (no guessing).
        deduction_total: Board size N.
        max_hypo_depth: Deepest nested hypothesis level that made progress (0 = none).
        hypotheses_tested: Total cells tested in hypothetical analysis.
        cells_eliminated: Cells proven impossible by hypotheticals.
        solved_by_deduction: Whether deduction alone solves the board.
        techniques_used: Deduction techniques that contributed.
    """

    score: float
    difficulty_class: str
    deduction_placed: int
    deduction_total: int
    max_hypo_depth: int
    hypotheses_tested: int
    cells_eliminated: int
    solved_by_deduction: bool
    techniques_used: tuple[str, ...]


def _compute_class(score: float) -> str:
    if score < 1:
        return "trivial"
    if score < 2:
        return "easy"
    if score < 4:
        return "medium"
    if score < 7:
        return "hard"
    if score < 10:
        return "expert"
    return "master"


def _compute_score(
    n: int,
    phase1_placed: int,
    max_hypo_depth: int,
    hypotheses_tested: int,
    cells_eliminated: int,
    technique_counts: dict[str, int],
) -> float:
    """Compute continuous difficulty score from analysis results."""
    if phase1_placed == n:
        # Pure deduction solved it — score based on technique complexity.
        weights = {
            "forced_singleton": 0.1,
            "region_line_lock": 0.3,
            "region_group_lock": 0.6,
            "diagonal_elimination": 0.5,
        }
        complexity = sum(weights.get(t, 0.1) * c for t, c in technique_counts.items())
        return round(min(complexity / n, 0.99), 2)

    # Board required hypotheticals to make progress
    deduction_gap = 1.0 - phase1_placed / n
    elimination_yield = cells_eliminated / max(hypotheses_tested, 1)

    score = deduction_gap * 10

    if max_hypo_depth == 0:
        score *= 0.5
    elif max_hypo_depth == 1:
        score *= 1.0
    elif max_hypo_depth == 2:
        score *= 1.5
    else:
        score *= 2.0

    score *= 2.0 - elimination_yield

    return round(score, 2)


class DifficultyAnalyzer(Protocol):
    """Structural protocol for difficulty analysis functions."""

    def __call__(self, board: Board) -> DifficultyReport: ...


# ── Deduction state ────────────────────────────────────────────────────


class _DeductionState:
    """Mutable state for running deduction on a board."""

    def __init__(self, n: int, regions: "numpy.ndarray") -> None:  # noqa: F821, UP037
        self.n = n
        self.regions = regions
        self.available: list[list[bool]] = [[True] * n for _ in range(n)]
        self.queens: list[tuple[int, int]] = []
        self.row_has: list[bool] = [False] * n
        self.col_has: list[bool] = [False] * n
        self.region_has: list[bool] = [False] * n

        self.region_cells: list[set[tuple[int, int]]] = [set() for _ in range(n)]
        for r in range(n):
            for c in range(n):
                self.region_cells[int(regions[r, c])].add((r, c))

        self.techniques: list[str] = []
        self.technique_counts: dict[str, int] = {}
        self.steps: list[str] = []

    # ── helpers ─────────────────────────────────────────────────

    @property
    def queens_count(self) -> int:
        return len(self.queens)

    def _region_avail(self, rid: int) -> list[tuple[int, int]]:
        return [(r, c) for r, c in self.region_cells[rid] if self.available[r][c]]

    def _row_avail(self, r: int) -> list[int]:
        return [c for c in range(self.n) if self.available[r][c]]

    def _col_avail(self, c: int) -> list[int]:
        return [r for r in range(self.n) if self.available[r][c]]

    def _unsolved_regions(self) -> list[int]:
        return [rid for rid in range(self.n) if not self.region_has[rid]]

    def _dead_region_exists(self) -> bool:
        for rid in range(self.n):
            if self.region_has[rid]:
                continue
            if not self._region_avail(rid):
                return True
        return False

    def _place_queen(self, r: int, c: int) -> None:
        rid = int(self.regions[r, c])
        for cc in range(self.n):
            self.available[r][cc] = False
        for rr in range(self.n):
            self.available[rr][c] = False
        for dr, dc in _NEIGHBORS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.n and 0 <= nc < self.n:
                self.available[nr][nc] = False
        self.row_has[r] = True
        self.col_has[c] = True
        self.region_has[rid] = True
        self.queens.append((r, c))

    def _record_technique(self, name: str) -> None:
        self.techniques.append(name)
        self.technique_counts[name] = self.technique_counts.get(name, 0) + 1

    # ── snapshot / restore ──────────────────────────────────────

    def snapshot(self) -> _Snapshot:
        return _Snapshot(
            available=[row[:] for row in self.available],
            queens=self.queens.copy(),
            row_has=self.row_has.copy(),
            col_has=self.col_has.copy(),
            region_has=self.region_has.copy(),
        )

    def restore(self, snap: _Snapshot) -> None:
        self.available = [row[:] for row in snap.available]
        self.queens = snap.queens.copy()
        self.row_has = snap.row_has.copy()
        self.col_has = snap.col_has.copy()
        self.region_has = snap.region_has.copy()

    # ── deduction techniques ─────────────────────────────────────

    def try_forced_singleton(self) -> bool:
        """If a region/row/col has exactly one legal cell, place queen there."""
        # Regions
        for rid in range(self.n):
            if self.region_has[rid]:
                continue
            cells = self._region_avail(rid)
            if len(cells) == 1:
                r, c = cells[0]
                self._record_technique("forced_singleton")
                self.steps.append(f"Queen at ({r},{c}) — forced singleton in region {rid}")
                self._place_queen(r, c)
                return True

        # Rows
        for r in range(self.n):
            if self.row_has[r]:
                continue
            ac = self._row_avail(r)
            if len(ac) == 1:
                c = ac[0]
                rid = int(self.regions[r, c])
                if not self.region_has[rid]:
                    self._record_technique("forced_singleton")
                    self.steps.append(f"Queen at ({r},{c}) — forced singleton in row {r}")
                    self._place_queen(r, c)
                    return True

        # Columns
        for c in range(self.n):
            if self.col_has[c]:
                continue
            ar = self._col_avail(c)
            if len(ar) == 1:
                r = ar[0]
                rid = int(self.regions[r, c])
                if not self.region_has[rid]:
                    self._record_technique("forced_singleton")
                    self.steps.append(f"Queen at ({r},{c}) — forced singleton in col {c}")
                    self._place_queen(r, c)
                    return True

        return False

    def try_region_line_lock(self) -> bool:
        """Eliminate other regions' cells from a locked row or col."""
        for rid in range(self.n):
            if self.region_has[rid]:
                continue
            cells = self._region_avail(rid)
            if not cells:
                continue

            # All in same row?
            rows = {r for r, _ in cells}
            if len(rows) == 1:
                row = rows.pop()
                changed = False
                for c in range(self.n):
                    if self.available[row][c]:
                        other_rid = int(self.regions[row, c])
                        if other_rid != rid and not self.region_has[other_rid]:
                            self.available[row][c] = False
                            changed = True
                if changed:
                    self._record_technique("region_line_lock")
                    self.steps.append(f"Region {rid} line-locked to row {row}")
                    return True

            # All in same column?
            cols = {c for _, c in cells}
            if len(cols) == 1:
                col = cols.pop()
                changed = False
                for r in range(self.n):
                    if self.available[r][col]:
                        other_rid = int(self.regions[r, col])
                        if other_rid != rid and not self.region_has[other_rid]:
                            self.available[r][col] = False
                            changed = True
                if changed:
                    self._record_technique("region_line_lock")
                    self.steps.append(f"Region {rid} line-locked to col {col}")
                    return True

        return False

    def try_region_group_lock(self) -> bool:
        """If K regions span ≤K rows/cols, eliminate other regions there."""
        unsolved = self._unsolved_regions()
        if len(unsolved) < 2:
            return False

        # Row group lock
        for k in range(2, len(unsolved) + 1):
            for subset in _choose_k(unsolved, k):
                rows_used: set[int] = set()
                for rid in subset:
                    for r, _ in self._region_avail(rid):
                        rows_used.add(r)
                if len(rows_used) <= k:
                    changed = False
                    for rid in subset:
                        for r, c in self._region_avail(rid):
                            if r not in rows_used:
                                self.available[r][c] = False
                                changed = True
                    for other_rid in unsolved:
                        if other_rid in subset:
                            continue
                        for r, c in self._region_avail(other_rid):
                            if r in rows_used:
                                self.available[r][c] = False
                                changed = True
                    if changed:
                        self._record_technique("region_group_lock")
                        self.steps.append(
                            f"Group lock: {len(subset)} regions in {len(rows_used)} rows"
                        )
                        return True

        # Column group lock
        for k in range(2, len(unsolved) + 1):
            for subset in _choose_k(unsolved, k):
                cols_used: set[int] = set()
                for rid in subset:
                    for _, c in self._region_avail(rid):
                        cols_used.add(c)
                if len(cols_used) <= k:
                    changed = False
                    for rid in subset:
                        for r, c in self._region_avail(rid):
                            if c not in cols_used:
                                self.available[r][c] = False
                                changed = True
                    for other_rid in unsolved:
                        if other_rid in subset:
                            continue
                        for r, c in self._region_avail(other_rid):
                            if c in cols_used:
                                self.available[r][c] = False
                                changed = True
                    if changed:
                        self._record_technique("region_group_lock")
                        self.steps.append(
                            f"Group lock: {len(subset)} regions in {len(cols_used)} cols"
                        )
                        return True

        return False

    def try_diagonal_elim(self) -> bool:
        """Eliminate cells via diagonal neighbor analysis."""
        for rid in range(self.n):
            if self.region_has[rid]:
                continue
            cells = self._region_avail(rid)
            if not cells or len(cells) > 3:
                continue

            common_diag: set[tuple[int, int]] | None = None
            for r, c in cells:
                diag_neighbors: set[tuple[int, int]] = set()
                for dr, dc in _DIAGONALS:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.n and 0 <= nc < self.n:
                        other_rid = int(self.regions[nr, nc])
                        if other_rid != rid and self.available[nr][nc]:
                            diag_neighbors.add((nr, nc))
                if common_diag is None:
                    common_diag = diag_neighbors
                else:
                    common_diag &= diag_neighbors

            if common_diag:
                changed = False
                for nr, nc in common_diag:
                    if self.available[nr][nc]:
                        self.available[nr][nc] = False
                        changed = True
                if changed:
                    self._record_technique("diagonal_elimination")
                    self.steps.append(f"Diagonal elimination from region {rid}")
                    return True

        return False

    def run_full_deduction(self) -> bool:
        """Run all deduction techniques to a fixed point. Returns True if any queen was placed."""
        start_count = self.queens_count
        while True:
            progress = False
            while self.try_forced_singleton():
                progress = True
            if self.try_region_line_lock():
                progress = True
                continue
            if self.try_region_group_lock():
                progress = True
                continue
            if self.try_diagonal_elim():
                progress = True
                continue
            if not progress:
                break
        return self.queens_count > start_count

    # ── hypothetical analysis ────────────────────────────────────

    def run_hypotheticals(
        self, max_depth: int, depth: int = 1
    ) -> tuple[list[tuple[int, int]], int]:
        """Try placing queens hypothetically.

        Returns (list of cells proven impossible, number of hypotheses tested).
        """
        eliminated: list[tuple[int, int]] = []
        tested = 0
        processed: set[tuple[int, int]] = set()

        for rid in self._unsolved_regions():
            for r, c in self._region_avail(rid):
                if (r, c) in processed:
                    continue
                processed.add((r, c))

                snap = self.snapshot()
                self._place_queen(r, c)
                tested += 1

                # Run deduction within the hypothetical
                self.run_full_deduction()

                if self._dead_region_exists():
                    # Contradiction — this cell cannot hold a queen
                    eliminated.append((r, c))
                    self.restore(snap)
                    continue

                if depth < max_depth and self.queens_count < self.n:
                    # Try deeper hypotheticals within this hypothesis
                    sub_eliminated, sub_tested = self.run_hypotheticals(max_depth, depth + 1)
                    tested += sub_tested
                    # If ALL remaining paths from deeper analysis lead to contradiction,
                    # then this cell is impossible too
                    if sub_eliminated:
                        # Check if the deeper analysis proved contradiction
                        # by seeing if any unsolved region is dead after applying eliminations
                        restorable = self.snapshot()
                        dead = False
                        for sr, sc in sub_eliminated:
                            self.available[sr][sc] = False
                        if self._dead_region_exists():
                            dead = True
                        self.restore(restorable)
                        if dead:
                            eliminated.append((r, c))

                self.restore(snap)

        return eliminated, tested


class _Snapshot:
    """Immutable snapshot of deduction state."""

    __slots__ = ("available", "col_has", "queens", "region_has", "row_has")

    def __init__(
        self,
        available: list[list[bool]],
        queens: list[tuple[int, int]],
        row_has: list[bool],
        col_has: list[bool],
        region_has: list[bool],
    ) -> None:
        self.available = available
        self.queens = queens
        self.row_has = row_has
        self.col_has = col_has
        self.region_has = region_has


# ── Main analyzer ──────────────────────────────────────────────────────


def exhaustive_analyze(board: Board, max_hypo_depth: int = 3) -> DifficultyReport:
    """Analyze board difficulty by measuring deduction gap and hypothetical depth.

    Phase 1: Run all deduction techniques (forced singleton, line lock, group lock,
    diagonal elimination) to exhaustion. Record how many queens are placed.

    Phase 2: For each remaining available cell, hypothetically place a queen and
    run deduction within the hypothetical. If a contradiction is found, the cell
    is eliminated. Re-run deduction with new eliminations.

    Phase 3: If still unsolved, recurse into deeper hypothetical chains (hypothesis
    within hypothesis) up to ``max_hypo_depth``.

    The difficulty score combines: deduction gap, hypothetical depth needed,
    and elimination yield (fraction of hypotheses that produce contradictions).

    Args:
        board: The board to analyze.
        max_hypo_depth: Maximum nesting depth for hypothetical chains.

    Returns:
        DifficultyReport with continuous score and detailed metrics.
    """
    n = board.n
    state = _DeductionState(n, board.regions)

    # Phase 1: deduction to exhaustion
    state.run_full_deduction()
    phase1_placed = state.queens_count

    if phase1_placed == n:
        score = _compute_score(n, phase1_placed, 0, 0, 0, state.technique_counts)
        return DifficultyReport(
            score=score,
            difficulty_class=_compute_class(score),
            deduction_placed=phase1_placed,
            deduction_total=n,
            max_hypo_depth=0,
            hypotheses_tested=0,
            cells_eliminated=0,
            solved_by_deduction=True,
            techniques_used=tuple(sorted(set(state.techniques))),
        )

    # Phase 2-3: hypothetical analysis
    total_tested = 0
    total_eliminated = 0
    effective_depth = 0

    for depth in range(1, max_hypo_depth + 1):
        eliminated, tested = state.run_hypotheticals(max_depth=depth)
        total_tested += tested
        total_eliminated += len(eliminated)

        if eliminated:
            effective_depth = depth
            for r, c in eliminated:
                state.available[r][c] = False

        # Re-run deduction with any new eliminations
        state.run_full_deduction()

        if state.queens_count == n:
            break

        if not eliminated:
            # No progress at this depth — try deeper
            continue

    score = _compute_score(
        n,
        phase1_placed,
        effective_depth,
        total_tested,
        total_eliminated,
        state.technique_counts,
    )

    return DifficultyReport(
        score=round(score, 2),
        difficulty_class=_compute_class(score),
        deduction_placed=phase1_placed,
        deduction_total=n,
        max_hypo_depth=effective_depth,
        hypotheses_tested=total_tested,
        cells_eliminated=total_eliminated,
        solved_by_deduction=False,
        techniques_used=tuple(sorted(set(state.techniques))),
    )


# ── Backwards compatibility ────────────────────────────────────────────


def layered_analyze(board: Board) -> DifficultyReport:
    """Legacy wrapper — delegates to exhaustive_analyze.

    Kept for backwards compatibility. The returned ``score`` is
    now continuous (0–10+), not a discrete layer (0–5).
    """
    return exhaustive_analyze(board)


# ── Helpers ────────────────────────────────────────────────────────────


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
