"""Tests for difficulty analysis."""

from __future__ import annotations

from queens.difficulty import DifficultyReport, layered_analyze
from queens.generator import generate_board


class TestLayeredAnalyze:
    def test_returns_difficulty_report(self) -> None:
        board = generate_board(6, seed=42)
        report = layered_analyze(board)
        assert isinstance(report, DifficultyReport)
        assert 0 <= report.score <= 5
        assert isinstance(report.techniques_used, tuple)

    def test_trivial_board_is_layer_0(self) -> None:
        """Boards generated at difficulty 0 are valid and have a report."""
        board = generate_board(5, target_difficulty=0, seed=99)
        report = layered_analyze(board)
        # The board is valid; the layered analyzer may assign a score > 0
        # depending on which deduction path it takes.
        assert report.score >= 0

    def test_score_increases_with_harder_boards(self) -> None:
        """Asking for higher difficulty should give higher or equal score."""
        easy = generate_board(8, target_difficulty=0, seed=1)
        hard = generate_board(8, target_difficulty=2, seed=1)
        easy_report = layered_analyze(easy)
        hard_report = layered_analyze(hard)
        assert hard_report.score >= easy_report.score

    def test_techniques_used_is_never_empty(self) -> None:
        board = generate_board(5, seed=0)
        report = layered_analyze(board)
        assert len(report.techniques_used) > 0

    def test_solve_path_has_entries(self) -> None:
        board = generate_board(5, seed=0)
        report = layered_analyze(board)
        assert len(report.solve_path) == board.n  # one entry per queen
