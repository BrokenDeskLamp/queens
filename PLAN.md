# Queens Board Generator — Implementation Plan

## Overview

A generator that produces valid N×N Queens boards (the LinkedIn puzzle). A board is **valid** when:
1. It has exactly **one unique solution** (a single set of N queen placements satisfying all rules)
2. Every **coloured region is connected** (contiguous block of cells — 4-directional adjacency)

The generator must be **performant**, **extensible** (for game variants), and capable of producing **difficult boards** that require advanced solving techniques.

---

## Recommended Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | **Python 3.12+** | Fast to prototype, rich ecosystem, sufficient performance for N ≤ 20 |
| Package manager | **uv** | Fast, modern, PEP 621 compatible (replaces pip/venv) |
| Build backend | `uv_build` (hatchling fallback) | Pure Python package, zero C extension complexity |
| Grid ops | `numpy` | Efficient array operations for marking/elimination |
| Connectivity | `networkx` | Graph-based region connectivity checks |
| CLI | `typer` | Clean CLI with type hints, auto-completion support |
| Testing | `pytest` | Standard, fast |
| Linting | `ruff` | Fast all-in-one linter + formatter |

No database or external services needed for MVP — everything is in-memory compute.

---

## Code Style & Conventions

| Aspect | Rule |
|---|---|
| Formatter/linter | **ruff** (rules: `ALL` — no exceptions) |
| Type checker | **Pyrefly** (enable via `[tool.pyrefly]` in `pyproject.toml`) |
| Type annotations | **Always — every function signature, every public attribute.** No `Any`. |
| Inheritance | **None.** Prefer `Protocol` for structural subtyping; compose with functions instead. |
| Mutability | **Frozen `dataclass`** or typed dicts. No mutable objects passed around. |
| Side effects | **On the outside.** Pure functions core; IO in thin CLI/test harness layer. |

> **TL;DR**: Write everything as typed, pure functions over frozen data. Use `Protocol` where you need polymorphism. No `class Foo(Bar)`, no `Any`, no `None` as a default sentinel.

---

## Core Architecture

```
┌──────────────────────────────────────────────────┐
│                 BoardGenerator                    │
│  Orchestrates the full pipeline with retry logic  │
├──────────────────────────────────────────────────┤
│                                                   │
│  ┌──────────────┐   ┌──────────────┐             │
│  │ Placement    │   │ Region       │             │
│  │ Strategy     │──▶│ Builder      │             │
│  │ (queen pos)  │   │ (flood fill) │             │
│  └──────────────┘   └──────┬───────┘             │
│                             │                     │
│                             ▼                     │
│                     ┌──────────────┐              │
│                     │ Uniqueness   │              │
│                     │ Verifier     │──▶ invalid?  │
│                     │ (solver)     │    retry     │
│                     └──────┬───────┘              │
│                             │ unique              │
│                             ▼                     │
│                     ┌──────────────┐              │
│                     │ Difficulty   │              │
│                     │ Analyzer     │              │
│                     └──────────────┘              │
│                                                   │
└──────────────────────────────────────────────────┘
```

### Pipeline

```
1. Place N queens → row/col/anti-adjacency valid
2. Build connected regions around each queen
3. Count all solutions with constraint solver
4. If count ≠ 1 → goto 1 (or patch regions, see below)
5. Assess difficulty via layered human-like solver
6. If difficulty target not met → goto 1 (or adjust)
7. Output board
```

---

## Component Design

### 1. Queen Placement Strategy (`placement.py`)

**Goal**: Produce a set of N `(row, col)` positions satisfying:
- Exactly one per row, exactly one per column
- No two queens are adjacent (including diagonals)

**Algorithm**: Backtracking with random column ordering.

```
def generate_placement(n: int, rng: Random) -> list[tuple[int, int]]:
    cols = list(range(n))
    placement = [None] * n
    
    def backtrack(row):
        if row == n: return True
        rng.shuffle(cols)  # randomness in column order
        for c in cols:
            if c in used_cols: continue
            if any_adjacent(row, c, placement[:row]): continue
            placement[row] = (row, c)
            used_cols.add(c)
            if backtrack(row + 1): return True
            used_cols.discard(c)
        return False
```

For N ≤ 15 this takes < 1ms. The random shuffle ensures diverse placements.

**Extensibility**: Define a `PlacementStrategy` `Protocol` with `generate(n, rng) -> Placement`. Variants are free functions that satisfy the protocol (e.g., all queens on main diagonal, balanced spacing for harder boards, etc.).

---

### 2. Region Builder (`regions.py`)

**Goal**: Given N queen positions, partition the N×N grid into N connected regions, each containing exactly one queen.

**Algorithm**: Simultaneous BFS growth from each queen (like Voronoi on a grid with Manhattan distance, but randomised tie-breaking).

```
def build_regions(n: int, placement: Placement, rng: Random) -> Board:
    # Initialize: each queen's cell belongs to that queen's region
    region_id = [[-1] * n for _ in range(n)]
    queues = [deque([queen_pos]) for each queen]
    
    # All unclaimed cells go into a frontier set
    # At each step, randomly pick a queued cell and assign its neighbors
    while unclaimed cells remain:
        q_idx = rng.choices(range(n), weights=queue_lengths)[0]
        if queues[q_idx] is empty: skip
        cell = queues[q_idx].popleft()
        for each unclaimed neighbor of cell:
            assign neighbor to region q_idx
            queues[q_idx].append(neighbor)
    
    return Board(n, region_id, queens=placement)
```

This guarantees:
- Every region is connected (BFS from seed cell)
- Every region contains exactly one queen (the seed)
- The full grid is partitioned

**Key challenge**: Random BFS regions often allow **alternative queen placements**. The Uniqueness Verifier (step 3) catches these.

**Extensibility**: `RegionBuilder` `Protocol`. Variants:
- `random_bfs_build` — fast, high retry rate (~30-50% unique for N=8)
- `constraint_guided_build` — uses solver feedback to avoid multi-solution boards (future)
- `template_build` — grows regions from predefined templates for specific difficulty profiles

---

### 3. Uniqueness Verifier / Solver (`solver.py`)

**Goal**: Given a board (regions + dimensions), count **all** valid queen placements. Return count and optionally the solutions themselves.

This is the **performance-critical** component — it runs inside the retry loop.

**Algorithm**: Backtracking with MRV (Minimum Remaining Values) heuristic + forward checking.

```
def count_solutions(board: Board, limit: int = 2) -> int:
    """
    Count solutions up to `limit`. 
    We only care if count == 1, so limit=2 gives an early exit.
    """
```

**State representation**:
- `available[row][col]` — boolean mask of legal cells
- `region_cells[region_id]` — set of still-legal cells per region
- `row_has_queen[row]`, `col_has_queen[col]` — booleans

**MRV heuristic**: Pick the region with fewest remaining legal cells. Within that region, pick the cell that eliminates the fewest options from other regions (or just iterate in order — simpler, still fast for N ≤ 15).

**Forward checking**: When a queen is placed, immediately update:
- Mark entire row, column as unavailable
- Mark the queen's region as satisfied (0 cells remain)
- Mark all 8 neighbors as unavailable
- For each affected region, if it drops to 0 cells → backtrack immediately

**Optimisation**: Use Python's `int` bitmasks for rows/cols (since N ≤ 20, a 64-bit int suffices). This makes elimination O(1) per cell via bitwise operations.

**Extensibility**: 
- `Solver` `Protocol` with methods: `count_solutions()`, `find_all_solutions()`, `solve_stepwise()` (for difficulty analysis)
- Could swap in a Rust/PyO3 solver later for N > 20

---

### 4. Difficulty Analyzer (`difficulty.py`)

**Goal**: Determine what techniques are required to solve a board, and classify difficulty.

**Approach**: Layered solver — each layer can use a subset of the techniques from QUEENS.md:

| Layer | Techniques allowed |
|---|---|
| 0 (Trivial) | Forced singleton only |
| 1 (Easy) | + Row/col/region elimination |
| 2 (Medium) | + Region line lock |
| 3 (Hard) | + Region group lock, line group lock |
| 4 (Expert) | + Diagonal neighbor elimination |
| 5 (Master) | + Test a Queen (hypothetical chains) |

Each layer is a solver that attempts to find the solution using only those techniques (no full backtracking). If layer K succeeds, the board's difficulty is ≤ K.

**Difficulty score**: The minimum layer that can solve the board.

**API**:
```python
def assess_difficulty(board: Board) -> DifficultyReport:
    return DifficultyReport(
        score=3,            # minimum layer needed
        techniques_used=[   # which specific techniques triggered
            "forced_singleton",
            "region_line_lock", 
            "region_group_lock",
        ],
        solve_path=[...],   # step-by-step for hint system
    )
```

**Extensibility**: New techniques can be added as new layers. The layer architecture maps directly to the technique hierarchy in QUEENS.md.

---

### 5. Board Generator (`generator.py`)

A single pure function with all configuration passed explicitly as frozen dataclasses (no class with mutable state):

```python
def generate_board(
    n: int,
    *,
    place_func: PlacementStrategy,
    region_func: RegionBuilder,
    solver: Solver,
    difficulty_fn: DifficultyAnalyzer,
    target_difficulty: Difficulty | None = None,
    max_attempts: int = 1000,
    seed: int | None = None,
) -> Board:
    """Generate a valid N×N Queens board."""
    rng = Random(seed)
    for attempt in range(max_attempts):
        # 1. Place queens
        placement = place_func(n, rng)
        
        # 2. Build regions
        board = region_func(n, placement, rng)
        
        # 3. Verify uniqueness
        solutions = solver.count_solutions(board, limit=2)
        if solutions != 1:
            continue
        
        # 4. Assess difficulty
        report = difficulty_fn(board)
        
        # 5. Check difficulty target
        if target_difficulty is not None and report.score < target_difficulty:
            continue
        
        return board
    
    raise GenerationError(f"Failed after {max_attempts} attempts")
```

**Retry economics**: For N=8 with naive BFS regions, roughly 30-50% of boards are unique. So 2-3 attempts on average. With a difficulty filter, more attempts may be needed, but still well under 100 for most N.

---

### 6. Board Representation (`board.py`)

```python
@dataclass(frozen=True)  # immutable — good for caching, hashing
class Board:
    n: int
    regions: np.ndarray      # shape (n, n), int region IDs 0..n-1
    solution: tuple[tuple[int, int], ...]  # the unique queen positions
    
    def region_mask(self, region_id: int) -> np.ndarray: ...
    def is_connected(self) -> bool: ...
    def to_ascii(self) -> str: ...
    
    @classmethod
    def from_json(cls, data: dict) -> Board: ...
    def to_json(self) -> dict: ...
```

Serialisation format (for sharing boards):
```json
{
    "n": 8,
    "regions": [[0,1,1,2,...], ...],
    "solution": [[0,3],[1,6],...]
}
```

---

## File Structure

```
queens/
├── QUEENS.md                    # Game rules (existing)
├── PLAN.md                      # This file
├── pyproject.toml               # Package config (uv)
├── README.md
├── src/
│   └── queens/
│       ├── __init__.py
│       ├── board.py             # Board dataclass, serialisation
│       ├── solver.py            # Constraint solver (count + all solutions)
│       ├── placement.py         # Queen placement strategies
│       ├── regions.py           # Region building strategies
│       ├── difficulty.py        # Layered difficulty assessment
│       ├── generator.py         # Orchestrator with retry logic
│       └── cli.py               # Typer CLI
├── tests/
│   ├── __init__.py
│   ├── test_board.py
│   ├── test_solver.py
│   ├── test_generator.py
│   ├── test_regions.py
│   ├── test_difficulty.py
│   └── conftest.py              # Shared fixtures (sample boards)
└── examples/
    └── generate_boards.py       # Usage examples
```

---

## Implementation Order (MVP)

### Phase 1: Foundation (solver + board)
1. `board.py` — Board dataclass with connectivity check (via `networkx` on the region grid graph)
2. `solver.py` — Constraint solver that counts all solutions
3. Tests — verify solver on known hand-crafted boards

### Phase 2: Generation
4. `placement.py` — Backtracking queen placer
5. `regions.py` — BFS region builder
6. `generator.py` — Orchestrator with retry loop
7. Tests — generate boards for N ∈ {5, 6, 7, 8, 9, 10}, verify validity

### Phase 3: Difficulty
8. `difficulty.py` — Layered solver with technique tracking
9. Integrate into generator
10. `cli.py` — CLI with `generate --size 8 --difficulty hard`

### Phase 4: Polish
11. Board export (JSON, ASCII art, optionally SVG)
12. Performance profiling + optimisations
13. Benchmarks

---

## Extensibility Points

All major components use structural subtyping (`Protocol` — no inheritance):

| Component | Protocol | Variant examples |
|---|---|---|
| Queen placement | `PlacementStrategy` | `backtracking_placement`, `template_placement`, `adversarial_placement` |
| Region building | `RegionBuilder` | `random_bfs_build`, `constraint_guided_build`, `template_build` |
| Solving | `Solver` | `BacktrackingSolver`, `StepwiseSolver` (for difficulty), `RustSolver` (future) |
| Difficulty | `DifficultyAnalyzer` | `layered_analyze`, `custom_rule_analyze` |

Game variants (different constraints) can be supported by:
- Writing a new solver function satisfying the `Solver` Protocol with modified constraints (e.g., different adjacency rules, extra regions)
- Writing a new placement function satisfying the `PlacementStrategy` Protocol
- The `Board` dataclass can be extended with variant-specific metadata

---

## Difficulty Generation Strategy

For the MVP, difficulty is assessed post-generation and boards are filtered:

1. Generate many boards (fast retry loop)
2. Measure difficulty of each
3. Return the first that meets the target

For more reliable "hard" board generation (Phase 2+):
- **Template regions**: Hard boards often have regions that are "almost" confined to a row/column (line lock bait) or regions that intersect in specific patterns (group lock bait)
- **Constraint injection**: After generating a board, the generator could deliberately tweak region boundaries to introduce specific constraint patterns
- **Adversarial region building**: The region builder can be guided by a partial solver to avoid creating regions that make the board trivially solvable

---

## Performance Estimates

| N | Queen placement | Region build | Uniqueness check (1 sol) | Uniqueness check (2+ sols) | Avg retries | Total |
|---|---|---|---|---|---|---|
| 5 | <0.1ms | <0.1ms | ~0.1ms | ~0.5ms | ~2 | ~1ms |
| 8 | <0.1ms | ~0.5ms | ~1ms | ~5ms | ~3 | ~10ms |
| 10 | <0.1ms | ~1ms | ~5ms | ~20ms | ~3 | ~30ms |
| 12 | ~0.2ms | ~2ms | ~15ms | ~60ms | ~5 | ~100ms |
| 15 | ~0.5ms | ~5ms | ~50ms | ~200ms | ~5 | ~500ms |
| 20 | ~1ms | ~10ms | ~200ms | ~1s | ~10 | ~2-5s |

These are rough estimates. The solver with bitmask representation and MRV heuristic should be quite fast. The retry loop is the main multiplier.

**Bottleneck**: Uniqueness verification when there are 2+ solutions (the solver must explore extensively before finding the second one). This is why `limit=2` is critical — we stop as soon as we find a second solution.

---

## CLI Design (`cli.py`)

```bash
# Generate a standard 8x8 board
uv run queens generate --size 8

# Generate a hard 10x10 board with specific seed
uv run queens generate --size 10 --difficulty hard --seed 42

# Output as JSON
uv run queens generate --size 8 --format json

# Validate an existing board
uv run queens validate board.json

# Benchmark generation speed
uv run queens benchmark --size 8 --count 100
```

---

## Key Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Naive BFS regions produce too few unique boards | Measure success rate early; if <10%, implement constraint-guided building sooner |
| Solver too slow for N > 15 | Switch to bitmask representation from the start (cheap to implement, big perf win) |
| Difficulty assessment is inaccurate | Validate against a corpus of known LinkedIn daily puzzles (from archivedqueens.com) |
| Random generation doesn't reliably produce hard boards | Implement template-based region building in Phase 2 |
