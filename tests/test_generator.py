"""Tests for the board generator."""

from __future__ import annotations

import pytest

from queens.generator import GenerationError, generate_board
from queens.solver import count_solutions


class TestGenerateBoard:
    @pytest.mark.parametrize("n", [5, 6, 7, 8, 9, 10])
    def test_generates_valid_board(self, n: int) -> None:
        board = generate_board(n, seed=0)
        assert board.n == n
        assert board.is_connected()
        assert count_solutions(board, limit=2) == 1

    def test_seed_reproducibility(self) -> None:
        b1 = generate_board(8, seed=42)
        b2 = generate_board(8, seed=42)
        assert b1.solution == b2.solution

    def test_max_attempts_raises(self) -> None:
        with pytest.raises(GenerationError):
            # Very small max_attempts on large N — likely to fail
            generate_board(20, max_attempts=1)

    def test_difficulty_filter(self) -> None:
        """At difficulty 0 (trivial), should find boards quickly."""
        board = generate_board(5, target_difficulty=0, seed=123)
        assert count_solutions(board, limit=2) == 1

    def test_each_region_has_queen(self) -> None:
        board = generate_board(8, seed=7)
        # Map solution positions to region IDs
        q_regions = set()
        for r, c in board.solution:
            q_regions.add(int(board.regions[r, c]))
        assert q_regions == set(range(board.n))
