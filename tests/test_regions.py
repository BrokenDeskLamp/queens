"""Tests for region building."""

from __future__ import annotations

import random

import numpy as np
import pytest

from queens.regions import random_bfs_build


class TestRandomBfsBuild:
    @pytest.mark.parametrize("n", [5, 6, 7, 8])
    def test_all_cells_assigned(self, n: int) -> None:
        placement: tuple[tuple[int, int], ...] = tuple((i, (i * 2) % n) for i in range(n))
        board = random_bfs_build(n, placement, random.Random(42))
        # Every cell should have a region ID in 0..n-1
        assert board.regions.shape == (n, n)
        for rid in range(n):
            assert np.any(board.regions == rid)

    @pytest.mark.parametrize("n", [5, 6, 7, 8])
    def test_every_region_has_exactly_one_queen(self, n: int) -> None:
        placement: tuple[tuple[int, int], ...] = tuple((i, (i * 3) % n) for i in range(n))
        board = random_bfs_build(n, placement, random.Random(7))
        for rid, (qr, qc) in enumerate(placement):
            assert board.regions[qr, qc] == rid

    @pytest.mark.parametrize("n", [5, 6, 7, 8])
    def test_all_regions_connected(self, n: int) -> None:
        placement: tuple[tuple[int, int], ...] = tuple((i, (i * 2) % n) for i in range(n))
        board = random_bfs_build(n, placement, random.Random(99))
        assert board.is_connected()

    def test_deterministic_with_seed(self) -> None:
        placement: tuple[tuple[int, int], ...] = ((0, 0), (1, 1), (2, 2), (3, 3), (4, 4))
        b1 = random_bfs_build(5, placement, random.Random(42))
        b2 = random_bfs_build(5, placement, random.Random(42))
        assert np.array_equal(b1.regions, b2.regions)
