"""Queens — a board generator for the LinkedIn Queens puzzle."""

from .board import Board, Placement
from .generator import GenerationError, generate_board
from .solver import count_solutions, find_all_solutions, find_up_to_k_solutions

__all__ = [
    "Board",
    "GenerationError",
    "Placement",
    "count_solutions",
    "find_all_solutions",
    "find_up_to_k_solutions",
    "generate_board",
]
