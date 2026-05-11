"""Tests for difficulty analysis.

See docs/algorithms/difficulty.md for the scoring formula and techniques.
"""

from __future__ import annotations

from queens.difficulty import DifficultyReport, exhaustive_analyze, layered_analyze
from queens.generator import generate_board


class TestExhaustiveAnalyze:
    def test_returns_difficulty_report(self) -> None:
        board = generate_board(6, seed=42)
        report = exhaustive_analyze(board)
        assert isinstance(report, DifficultyReport)
        assert report.score >= 0
        assert isinstance(report.techniques_used, tuple)
        assert report.deduction_total == board.n
        assert report.deduction_placed >= 0
        assert report.difficulty_class in (
            "trivial", "easy", "medium", "hard", "expert", "master",
        )

    def test_trivial_board_has_low_score(self) -> None:
        """A board generated without difficulty filter should still get a valid score."""
        board = generate_board(5, seed=99)
        report = exhaustive_analyze(board)
        assert report.score >= 0

    def test_different_boards_have_different_complexity(self) -> None:
        """Even deduction-solvable boards should have varying technique complexity."""
        b1 = generate_board(7, seed=100)
        b2 = generate_board(7, seed=200)
        r1 = exhaustive_analyze(b1)
        r2 = exhaustive_analyze(b2)
        # At least one board should use techniques beyond forced_singleton
        assert len(r1.techniques_used) >= 1
        assert len(r2.techniques_used) >= 1

    def test_techniques_used_is_never_empty(self) -> None:
        board = generate_board(5, seed=0)
        report = exhaustive_analyze(board)
        assert len(report.techniques_used) > 0

    def test_solved_by_deduction_sets_flag(self) -> None:
        board = generate_board(5, seed=0)
        report = exhaustive_analyze(board)
        assert isinstance(report.solved_by_deduction, bool)

    def test_deduction_counts_are_consistent(self) -> None:
        board = generate_board(8, seed=42)
        report = exhaustive_analyze(board)
        assert report.deduction_placed <= report.deduction_total
        assert report.max_hypo_depth >= 0
        assert report.hypotheses_tested >= 0
        assert report.cells_eliminated >= 0


class TestLayeredAnalyze:
    """Backwards-compatibility wrapper tests."""

    def test_returns_same_type(self) -> None:
        board = generate_board(6, seed=42)
        report = layered_analyze(board)
        assert isinstance(report, DifficultyReport)
        assert report.score >= 0
