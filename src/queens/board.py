"""Board representation for Queens puzzles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

type Placement = tuple[tuple[int, int], ...]

_DIRECTIONS: tuple[tuple[int, int], ...] = ((0, 1), (0, -1), (1, 0), (-1, 0))


@dataclass(frozen=True)
class Board:
    """Immutable representation of a Queens puzzle board.

    Attributes:
        n: Board dimension (N×N grid).
        regions: Integer array of shape (n, n), each cell assigned a region ID 0..n-1.
        solution: The unique queen positions that solve this board.
    """

    n: int
    regions: NDArray[np.int_]
    solution: Placement

    def __post_init__(self) -> None:
        if self.regions.shape != (self.n, self.n):
            raise ValueError(f"regions shape {self.regions.shape} != ({self.n}, {self.n})")
        if len(self.solution) != self.n:
            raise ValueError(f"solution length {len(self.solution)} != n ({self.n})")

    def region_mask(self, region_id: int) -> NDArray[np.bool_]:
        """Boolean mask of cells belonging to the given region."""
        return self.regions == region_id

    def is_connected(self) -> bool:
        """Check that every region forms a single 4-connected component."""
        n = self.n
        for rid in range(n):
            # Find starting cell and count total cells for this region
            start: tuple[int, int] | None = None
            cell_count = 0
            for r in range(n):
                for c in range(n):
                    if int(self.regions[r, c]) == rid:
                        cell_count += 1
                        if start is None:
                            start = (r, c)
            if start is None:
                return False

            # BFS to count reachable cells
            visited: set[tuple[int, int]] = {start}
            queue: list[tuple[int, int]] = [start]
            while queue:
                r, c = queue.pop()
                for dr, dc in _DIRECTIONS:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < n and 0 <= nc < n:
                        if int(self.regions[nr, nc]) == rid and (nr, nc) not in visited:
                            visited.add((nr, nc))
                            queue.append((nr, nc))

            if len(visited) != cell_count:
                return False
        return True

    def to_ascii(self) -> str:
        """Render board as ASCII art with region IDs and queen markers."""
        n = self.n
        lines: list[str] = []
        # Column header
        header = "   " + " ".join(str(i % 10) for i in range(n))
        lines.append(header)
        qset = set(self.solution)
        for r in range(n):
            chars: list[str] = [f"{r:2d} "]
            for c in range(n):
                if (r, c) in qset:
                    chars.append("♛ ")
                else:
                    rid = int(self.regions[r, c])
                    ch = str(rid) if rid < 10 else chr(ord("a") + rid - 10)
                    chars.append(f"{ch} ")
            lines.append("".join(chars))
        return "\n".join(lines)

    def to_json(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dict."""
        return {
            "n": self.n,
            "regions": self.regions.tolist(),
            "solution": [list(pos) for pos in self.solution],
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> Board:
        """Deserialize from a JSON-compatible dict."""
        return cls(
            n=int(data["n"]),
            regions=np.array(data["regions"], dtype=np.int_),
            solution=tuple(
                tuple(pos)  # type: ignore[arg-type]
                for pos in data["solution"]
            ),
        )

    def save(self, path: Path) -> None:
        """Save board to a JSON file."""
        path.write_text(json.dumps(self.to_json(), indent=2))

    @classmethod
    def load(cls, path: Path) -> Board:
        """Load board from a JSON file."""
        return cls.from_json(json.loads(path.read_text()))
