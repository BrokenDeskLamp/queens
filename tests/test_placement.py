"""Tests for queen placement strategies."""

from __future__ import annotations

import random

import pytest

from queens.placement import backtracking_placement


class TestBacktrackingPlacement:
    @pytest.mark.parametrize("n", [4, 5, 6, 8, 10, 12, 15])
    def test_returns_n_queens(self, n: int) -> None:
        placement = backtracking_placement(n, random.Random(42))
        assert len(placement) == n

    @pytest.mark.parametrize("n", [4, 5, 6, 8, 10, 12, 15])
    def test_unique_rows_and_cols(self, n: int) -> None:
        placement = backtracking_placement(n, random.Random(7))
        rows = {r for r, _ in placement}
        cols = {c for _, c in placement}
        assert rows == set(range(n))
        assert cols == set(range(n))

    @pytest.mark.parametrize("n", [4, 5, 6, 8, 10])
    def test_no_adjacent_queens(self, n: int) -> None:
        placement = backtracking_placement(n, random.Random(13))
        qset = set(placement)
        neighbors = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ]
        for r, c in placement:
            for dr, dc in neighbors:
                assert (r + dr, c + dc) not in qset

    def test_deterministic_with_seed(self) -> None:
        p1 = backtracking_placement(8, random.Random(42))
        p2 = backtracking_placement(8, random.Random(42))
        assert p1 == p2

    def test_different_seeds_produce_different_results(self) -> None:
        rng = random.Random(0)
        placements = {backtracking_placement(10, rng) for _ in range(10)}
        # At least some should differ (may not always be the case for N=10)
        # This is probabilistic — if all 10 are the same, that's a bug
        assert len(placements) > 1
