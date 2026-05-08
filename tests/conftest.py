"""Shared test fixtures for Queens tests."""

from __future__ import annotations

import numpy as np
import pytest

from queens.board import Board


@pytest.fixture
def sample_board_5() -> Board:
    """A known-valid 5×5 board with exactly one solution."""
    regions = np.array(
        [
            [0, 0, 1, 1, 1],
            [0, 0, 0, 1, 1],
            [2, 0, 0, 1, 1],
            [2, 2, 3, 4, 1],
            [2, 2, 3, 4, 4],
        ],
        dtype=np.int_,
    )
    solution: tuple[tuple[int, int], ...] = ((0, 0), (1, 3), (2, 1), (3, 4), (4, 2))
    return Board(n=5, regions=regions, solution=solution)


@pytest.fixture
def multi_solution_board_5() -> Board:
    """A 5×5 board with multiple solutions (all regions are single cells)."""
    regions = np.array(
        [
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
        ],
        dtype=np.int_,
    )
    solution: tuple[tuple[int, int], ...] = ((0, 0), (1, 1), (2, 2), (3, 3), (4, 4))
    return Board(n=5, regions=regions, solution=solution)


@pytest.fixture
def disconnected_board_5() -> Board:
    """A 5×5 board where region 0 has a disconnected cell."""
    regions = np.array(
        [
            [0, 0, 1, 1, 1],
            [0, 0, 0, 1, 1],
            [2, 0, 1, 1, 1],  # region 1 is connected but split? Actually 1 is fine
            [2, 2, 3, 4, 1],
            [2, 0, 3, 4, 4],  # This cell [4,1] is region 0, disconnected from the main blob
        ],
        dtype=np.int_,
    )
    solution: tuple[tuple[int, int], ...] = ((0, 0), (1, 3), (2, 1), (3, 4), (4, 2))
    return Board(n=5, regions=regions, solution=solution)
