"""Board generator orchestrator.

Combines placement, region building, uniqueness verification,
and difficulty analysis into a retry loop that produces
valid Queens boards.
"""

from __future__ import annotations

import random

from .board import Board
from .difficulty import DifficultyAnalyzer, layered_analyze
from .placement import PlacementStrategy, backtracking_placement
from .regions import RegionBuilder, random_bfs_build
from .solver import count_solutions


class GenerationError(RuntimeError):
    """Raised when board generation fails after max attempts."""


def generate_board(
    n: int,
    *,
    place_func: PlacementStrategy = backtracking_placement,
    region_func: RegionBuilder = random_bfs_build,
    target_difficulty: int | None = None,
    difficulty_fn: DifficultyAnalyzer = layered_analyze,
    max_attempts: int = 1000,
    seed: int | None = None,
) -> Board:
    """Generate a valid N×N Queens board with exactly one unique solution.

    The generation pipeline:
    1. Place N queens (row/col/anti-adjacency valid).
    2. Build connected regions around each queen.
    3. Count all solutions — keep only if unique.
    4. (Optional) Assess difficulty and filter by target.

    Args:
        n: Board size (N×N).
        place_func: Strategy for placing initial queens.
        region_func: Strategy for building coloured regions.
        target_difficulty: If set, only return boards at or above
            this difficulty layer (0-5).
        difficulty_fn: Function for difficulty assessment.
        max_attempts: Maximum generation attempts before raising.
        seed: Random seed for reproducibility.

    Returns:
        A valid Board with one unique solution.

    Raises:
        GenerationError: If no valid board is found within ``max_attempts``.
    """
    rng = random.Random(seed)
    for _attempt in range(max_attempts):
        placement = place_func(n, rng)
        board = region_func(n, placement, rng)

        # Verify uniqueness
        sol_count = count_solutions(board, limit=2)
        if sol_count != 1:
            continue

        # Check difficulty if requested
        if target_difficulty is not None:
            report = difficulty_fn(board)
            if report.score < target_difficulty:
                continue

        return board

    raise GenerationError(f"Failed to generate a valid {n}×{n} board after {max_attempts} attempts")
