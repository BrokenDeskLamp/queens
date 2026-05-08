# LinkedIn Queens — Complete Guide

Queens is a daily logic puzzle by LinkedIn News. It is a **regional variant of the classic N-Queens problem**, combining row, column, and color-region constraints with a no-adjacency rule.

- **Official game**: [linkedin.com/games/queens](https://www.linkedin.com/games/queens)
- **Community archive (independent)**: [archivedqueens.com](https://www.archivedqueens.com/) — replayable past puzzles
- **Practice + hints**: [playqueensgame.com](https://www.playqueensgame.com/linkedin-queens-today)

---

## Rules

1. **One Queen per row** — every row must contain exactly one 👑.
2. **One Queen per column** — every column must contain exactly one 👑.
3. **One Queen per colored region** — each contiguous block of same-coloured cells must contain exactly one 👑.
4. **No two Queens touch** — Queens cannot be placed in adjacent cells, **including diagonally**. Every cell surrounding a Queen (up, down, left, right, and the four diagonals) is forbidden.

These four rules together guarantee exactly one solution per puzzle — no guessing is required.

---

## Board & Controls

- **Grid sizes**: Typically 7×7, 8×8, 9×10, or 10×10. The number of coloured regions always matches the board dimension.
- **Cell cycling**: Tap/click a cell to cycle: *empty → X (marker) → 👑 (Queen) → empty*.
- **Auto-place X's**: When enabled in Settings, the game automatically marks cells that become impossible after a Queen is placed.
- **Auto-check**: When enabled, rule violations are highlighted with red stripes.
- **Hint**: Highlights a region where a Queen must go, or flags a mistake.
- **Undo / Clear**: Undo removes the last placement; Clear resets the board.

---

## Core Techniques (Essential)

### 1. Forced Singleton

> If a region, row, or column has **exactly one legal cell**, that cell must be a Queen.

This is the most fundamental move. After every Queen placement and after marking any cell, scan all regions, rows, and columns for singletons.

### 2. Row / Column / Region Elimination

Once a Queen is placed:
- Every other cell in its **row** becomes invalid.
- Every other cell in its **column** becomes invalid.
- Every other cell in its **region** becomes invalid.
- The **eight surrounding cells** (including diagonals) become invalid.

Mark all of these with X's. The auto-mark feature does this for you, but training your eye to see the pattern is essential.

### 3. Region Line Lock

> If a region's **only remaining legal cells** all lie in a single row (or single column), that row (or column) is reserved for that region.

Mark every cell in that row/column that belongs to a *different* region as invalid — they can no longer hold a Queen.

This is the first technique that requires reasoning about multiple regions at once.

---

## Intermediate Techniques

### 4. Diagonal Neighbor Elimination

> If every possible Queen placement in a region would diagonally touch the same outside cell, that outside cell cannot hold a Queen.

Useful when a region is narrowed to 2–3 cells and they all share a diagonal neighbor. Regardless of which cell gets the Queen, that neighbor is touching diagonally and is therefore invalid.

### 5. Region Group Lock

> If N regions' legal cells fit entirely within exactly N rows (or N columns), those rows are reserved for the group.

This is the multi-region generalization of the Region Line Lock. For example: if two regions have legal cells only in rows 3 and 4, then rows 3 and 4 are spoken for by those two regions — no other region can place a Queen there.

### 6. Line Group Lock (the inverse)

> If N rows (or columns) can only be filled by the same N regions, those regions must supply those rows.

Mark cells from those regions that lie *outside* the locked rows/columns as invalid — the regions are already needed inside the locked lines.

---

## Expert Techniques

### 7. Test a Queen (Hypothetical Chain)

> If placing a Queen in a cell would leave **any region with zero legal cells**, that cell cannot be a Queen.

When all simpler techniques stall:
1. Pick a region with the fewest legal cells (ideally 2).
2. Mentally place a Queen in one candidate.
3. Apply all forced marks, forced Queens, and group locks that follow.
4. If any region ends up with no legal cells, the tested cell is impossible → mark it invalid.

This is the technique LinkedIn's hardest daily puzzles occasionally require. The hint system can perform this reasoning for you.

### 8. Follow a Test Chain

The same as Technique 7, but you continue chaining forced moves deeper before checking for contradictions. One tested Queen forces another, which forces another — the contradiction may only appear after several levels of deduction.

---

## Puzzle-Solving Flow

For every puzzle, follow this loop:

```
1. Scan for Forced Singletons → place Queen
2. Eliminate row / column / region / diagonals → mark X's
3. Scan for Region Line Locks → mark X's
4. If stuck, scan for Group Locks → mark X's
5. If still stuck, Test a Queen → eliminate candidates
6. Repeat from step 1 until solved
```

Most 7×7 and 8×8 puzzles yield to steps 1–3. Only the hardest 10×10+ puzzles require steps 5–6.

---

## Tips & Common Mistakes

| Tip | Why |
|---|---|
| **Mark before you place** | Most deductions work on X'd cells, not on Queens. |
| **Check diagonals last** | Row/column/region are easy; forgetting diagonals is the #1 error. |
| **Start with tight regions** | When stuck, pick the region with the fewest legal cells. |
| **Re-scan after every Queen** | A forced singleton can appear anywhere after each placement. |
| **Hints teach, not just give answers** | The hint button shows *which technique* applies and why. |
| **Every region matters** | If a technique eliminates a cell, check whether any region is now reduced to a single legal cell. |

---

## Quick Reference

| Technique | Difficulty | When to use |
|---|---|---|
| Forced Singleton | Essential | After every Queen or mark |
| Row/Column/Region Elimination | Essential | After every Queen |
| Region Line Lock | Essential | After a few Queens, on any board |
| Diagonal Neighbor Elimination | Intermediate | Region narrowed to 2–3 cells |
| Region Group Lock | Intermediate | 9×9 and 10×10 boards |
| Line Group Lock | Intermediate | Hard puzzles with many regions |
| Test a Queen | Expert | Stuck on any board |
| Follow a Test Chain | Expert | Hardest 10×10+ puzzles |

---

## Why It's Called "Queens"

The puzzle is a variant of the classic **N-Queens problem** from computer science: place N queens on an N×N chessboard such that none attack each other. LinkedIn's version adds **coloured regions** (each region must contain exactly one Queen) and removes standard chess-move attack patterns in favour of the simpler **adjacency (including diagonal) restriction**. This creates puzzles that are solvable by pure logical deduction rather than backtracking search.

---

## Resources

- **Official game**: [linkedin.com/games/queens](https://www.linkedin.com/games/queens)
- **Community archive (independent)**: [archivedqueens.com](https://www.archivedqueens.com/) — past puzzles, freely replayable
- **Practice puzzles with progressive hints**: [playqueensgame.com](https://www.playqueensgame.com/linkedin-queens-today)
- **LinkedIn Help article**: [linkedin.com/help/linkedin/answer/a6269510](https://www.linkedin.com/help/linkedin/answer/a6269510)
- **Daily hints & spoilers**: [lnkd.in/queenshints](http://lnkd.in/queenshints)
