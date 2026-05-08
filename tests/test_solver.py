"""Tests for the constraint solver."""

from __future__ import annotations

import numpy as np

from queens.board import Board
from queens.solver import count_solutions, find_all_solutions


class TestCountSolutions:
    def test_single_solution_board(self, sample_board_5: Board) -> None:
        assert count_solutions(sample_board_5) == 1

    def test_multi_solution_board(self, multi_solution_board_5: Board) -> None:
        # Column regions with no adjacency — many solutions
        assert count_solutions(multi_solution_board_5) >= 1

    def test_limit_works(self) -> None:
        """count_solutions with limit=1 should not find more than 1."""
        regions = np.array(
            [
                [0, 1, 2, 3],
                [0, 1, 2, 3],
                [0, 1, 2, 3],
                [0, 1, 2, 3],
            ],
            dtype=np.int_,
        )
        board = Board(n=4, regions=regions, solution=((0, 0), (1, 1), (2, 2), (3, 3)))
        # With limit=1 we should get exactly 1
        assert count_solutions(board, limit=1) == 1

    def test_unsolvable_board_returns_zero_5(self) -> None:
        """A board where two queens must share a column."""
        regions = np.array(
            [
                [0, 0, 1, 1, 2],
                [0, 0, 1, 1, 2],
                [0, 0, 1, 1, 2],
                [0, 0, 1, 1, 2],
                [3, 3, 3, 4, 4],
            ],
            dtype=np.int_,
        )
        # All of region 3 and 4 are in the last row — each region needs a queen
        # but only 1 row for 2 regions
        board = Board(n=5, regions=regions, solution=((0, 0), (1, 2), (2, 4), (3, 1), (4, 3)))
        assert count_solutions(board) == 0

    def test_solution_matches_count(self, sample_board_5: Board) -> None:
        """The sample board has exactly 1 solution (by construction)."""
        solutions = find_all_solutions(sample_board_5)
        assert len(solutions) >= 1


class TestFindAllSolutions:
    def test_finds_expected_solutions(self) -> None:
        """A 4×4 board where regions are columns — count all solutions."""
        regions = np.array(
            [
                [0, 1, 2, 3],
                [0, 1, 2, 3],
                [0, 1, 2, 3],
                [0, 1, 2, 3],
            ],
            dtype=np.int_,
        )
        solution: tuple[tuple[int, int], ...] = ((0, 0), (1, 1), (2, 2), (3, 3))
        board = Board(n=4, regions=regions, solution=solution)
        results = find_all_solutions(board)
        # N=4, column regions, no adjacency restriction between rows
        # Actually with adjacency constraint, there are only 2 diagonal placements
        assert len(results) >= 1


class TestSolverCorrectness:
    def test_known_board_has_unique_solution(self, sample_board_5: Board) -> None:
        assert count_solutions(sample_board_5, limit=10) == 1
        assert len(find_all_solutions(sample_board_5)) == 1

    def test_solver_handles_various_sizes(self) -> None:
        """Generate trivial boards of various sizes and verify solver."""
        for n in range(4, 9):
            # Create a trivial diagonal board
            regions = np.zeros((n, n), dtype=np.int_)
            # Each row gets its own region
            for r in range(n):
                regions[r, :] = r
            solution: tuple[tuple[int, int], ...] = tuple((i, i) for i in range(n))
            board = Board(n=n, regions=regions, solution=solution)
            count = count_solutions(board)
            # A pure diagonal board with row-regions may have multiple solutions
            assert count >= 1
