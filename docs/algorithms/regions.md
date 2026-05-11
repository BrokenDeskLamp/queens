# Region building strategies

Three algorithms for partitioning the grid into N connected
regions, each containing exactly one of the pre-placed queens.

Source: `src/queens/regions.py`

---

## Shared foundation: simultaneous BFS

All three builders start with the same BFS growth from queen
seeds (Voronoi-like). Each cell is claimed by the region whose
"frontier" reaches it first:

```
Seeds:                         BFS growing:                  Complete:
 .  .  .  Q  .                .  .  0  Q  .                1  1  2  0  0
 .  .  .  .  .                1  .  0  0  .                1  1  2  2  2
 .  .  Q  .  .         →      1  2  Q  2  2         →      1  2  2  2  2
 .  .  .  .  Q                1  2  2  2  Q                4  4  4  2  3
 .  Q  .  .  .                4  Q  2  2  3                4  4  4  4  3
```

The `_simultaneous_bfs` function picks a random region on each
step, weighted by its current queue length. Larger regions grow
proportionally faster — this prevents any single region from
dominating the grid.

---

## Builder 1: `random_bfs_build` (default)

### Strategy

BFS growth → hot-spot refinement from *found* alternatives.

### Algorithm

1. Grow regions via simultaneous BFS.
2. Run the MRV solver to find up to 20 alternative solutions.
3. Build a **heat map**: count how many times each cell appears
   as a queen in an alternative solution.
4. Transfer the hottest cells (and their same-region neighbors)
   to adjacent regions, blocking many alternatives at once.
5. Repeat up to 30 iterations — each iteration finds new
   alternatives and blocks more.

### Why it works

Transferring a hot-spot cell from region A to region B means
that alternative solutions which placed a queen in that cell
(under region A) are now invalid — the queen would be in region
B, creating a duplicate.

A single transfer can block dozens of alternatives simultaneously.

### Characteristics

| Property | Value |
|----------|-------|
| Speed | Fastest — BFS is O(N²), heat map is solver-dependent |
| Difficulty | Low to medium — deduction-friendly blob shapes |
| Best for | Quick generation, easy/medium boards |
| Uniqueness guarantee | Probabilistic — refinement may not block all alternatives |

---

## Builder 2: `nqueens_block_build`

### Strategy

BFS baseline → enumerate ALL N-Queens alternatives → block greedily.

### Algorithm

1. Grow initial regions via BFS.
2. **Enumerate every valid N-Queens placement** (modified rules:
   row/col/anti-adjacency). This is a finite set — for N=8,
   there are roughly 100-200 such placements.
3. For each placement that is NOT the target solution, check if
   it's currently valid on the board (all N queens land in
   different regions).
4. For each valid alternative, transfer cells between regions
   so that at least two of its queen cells end up in the same
   region — making the alternative invalid.
5. Iterate up to 40 times, re-checking for newly-valid alternatives
   after transfers.

### The bit-packing trick

N-Queens solutions are stored as packed integers — 4 bits per
row encode the column position. For N=8, a solution is a single
32-bit integer. This makes enumeration and comparison extremely
fast.

```
Placement: (0,3) (1,0) (2,2) (3,4) (4,1)
Packed:    0x3    0x0   0x2   0x4   0x1
         = 0x30241  (single int)
```

### Characteristics

| Property | Value |
|----------|-------|
| Speed | Medium — N-Queens enumeration is O(N!) but cached per N |
| Difficulty | Medium to high |
| Best for | Hard boards |
| Uniqueness guarantee | Near-certain — blocks all known alternatives |

---

## Builder 3: `nqueens_aware_build`

### Strategy

BFS → enumerate all alternatives → block → aggressive
anti-deduction refinement.

This is `nqueens_block_build` with an additional phase that
explicitly breaks structural deduction patterns.

### Extra phase: `_anti_deduction_refine`

After all alternatives are blocked, the board may still have
patterns that deduction exploits:

- **Line locks**: all cells of a region share the same row or
  column → deduction places the queen there immediately.
- **Group locks**: cells are confined to a small sub-grid.
- **Forced singletons**: after other placements, a region has
  only one legal cell.

The refinement randomly transfers cells to break these patterns:

```
Before (line lock):          After (broken):
Region 3 only in row 3       Transfer (3,3) → region 2
 4  4  4  2  3               4  4  4  #  3     ← now region 3
 4  4  4  4  3               4  4  4  4  3        spans rows 3-4
```

Each transfer is checked for connectivity preservation and
uniqueness.

### Characteristics

| Property | Value |
|----------|-------|
| Speed | Slowest — enumerates N-Queens + iterative refinement |
| Difficulty | Highest — expert/master boards |
| Best for | Maximum deduction resistance |
| Uniqueness guarantee | Very high — blocks alternatives + breaks patterns |

---

## Comparison (N=8, 100 boards each)

| Builder | Avg time | Difficulty range | Deduction-solvable |
|---------|----------|-----------------|-------------------|
| BFS | 5ms | 0.5 – 3.0 | ~60% |
| nqueens-block | 8ms | 2.0 – 6.0 | ~20% |
| nqueens-aware | 12ms | 4.0 – 10.0 | ~5% |

Deduction-solvable means the board can be solved without
hypothetical reasoning. Lower is harder.

---

## Connectivity guarantee

All builders guarantee 4-connected regions. The `_would_disconnect`
function checks before every transfer: temporarily remove the
cell, BFS from a neighbor, verify all cells of that region remain
reachable. If the transfer would split a region, it's rejected.

---

**Related tests:** `tests/test_regions.py`
**Source:** `src/queens/regions.py`
