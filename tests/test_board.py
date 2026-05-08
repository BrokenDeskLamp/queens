"""Tests for board representation and validation."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from queens.board import Board


class TestBoardConstruction:
    def test_valid_board(self) -> None:
        regions = np.array([[0, 1], [1, 0]], dtype=np.int_)
        solution: tuple[tuple[int, int], ...] = ((0, 0), (1, 1))
        board = Board(n=2, regions=regions, solution=solution)
        assert board.n == 2
        assert board.solution == ((0, 0), (1, 1))

    def test_wrong_shape_raises(self) -> None:
        regions = np.array([[0, 1, 2], [1, 2, 3]], dtype=np.int_)
        solution: tuple[tuple[int, int], ...] = ((0, 0), (1, 1))
        with pytest.raises(ValueError, match="regions shape"):
            Board(n=2, regions=regions, solution=solution)

    def test_wrong_solution_length_raises(self) -> None:
        regions = np.array([[0, 1], [1, 0]], dtype=np.int_)
        solution: tuple[tuple[int, int], ...] = ((0, 0),)
        with pytest.raises(ValueError, match="solution length"):
            Board(n=2, regions=regions, solution=solution)


class TestRegionMask:
    def test_region_mask(self) -> None:
        regions = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=np.int_)
        board = Board(n=3, regions=regions, solution=((0, 0), (1, 1), (2, 2)))
        mask = board.region_mask(0)
        expected = np.array([[True, False, True], [False, True, False], [True, False, True]])
        assert np.array_equal(mask, expected)


class TestIsConnected:
    def test_connected_board(self, sample_board_5: Board) -> None:
        assert sample_board_5.is_connected()

    def test_disconnected_board(self, disconnected_board_5: Board) -> None:
        assert not disconnected_board_5.is_connected()

    def test_all_single_cell_regions(self, multi_solution_board_5: Board) -> None:
        # Each region is a column of 5 cells — should be connected
        assert multi_solution_board_5.is_connected()


class TestSerialization:
    def test_roundtrip(self, sample_board_5: Board) -> None:
        data = sample_board_5.to_json()
        restored = Board.from_json(data)
        assert restored.n == sample_board_5.n
        assert np.array_equal(restored.regions, sample_board_5.regions)
        assert restored.solution == sample_board_5.solution

    def test_save_load(self, sample_board_5: Board) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            sample_board_5.save(path)
            loaded = Board.load(path)
            assert loaded.n == sample_board_5.n
            assert np.array_equal(loaded.regions, sample_board_5.regions)
            assert loaded.solution == sample_board_5.solution
        finally:
            path.unlink()

    def test_to_json_structure(self, sample_board_5: Board) -> None:
        data = sample_board_5.to_json()
        assert "n" in data
        assert "regions" in data
        assert "solution" in data
        assert isinstance(data["regions"], list)
        assert isinstance(data["solution"], list)


class TestToAscii:
    def test_to_ascii_contains_queen(self, sample_board_5: Board) -> None:
        ascii_str = sample_board_5.to_ascii()
        assert "♛" in ascii_str

    def test_to_ascii_has_header(self, sample_board_5: Board) -> None:
        ascii_str = sample_board_5.to_ascii()
        lines = ascii_str.split("\n")
        assert len(lines) == sample_board_5.n + 1  # header + n rows
