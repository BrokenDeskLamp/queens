# `validate` — Board validation

Checks a board JSON file for the two requirements of a valid
Queens puzzle: every coloured region is connected, and the board
has exactly one unique solution.

## Valid board passes

```bash
$ echo '{"n":5,"regions":[[0,0,1,1,1],[0,0,0,1,1],[2,0,0,1,1],[2,2,3,4,1],[2,2,3,4,4]],"solution":[[0,0],[1,3],[2,1],[3,4],[4,2]]}' > /tmp/queens_valid.json && uv run queens validate /tmp/queens_valid.json
# stdout: OK: board is valid
```

A board with connected regions and exactly one solution passes
validation.

## Round-trip: generated boards pass validation

```bash
$ uv run queens generate --size 5 --seed 42 --format json 2>/dev/null > /tmp/queens_gen.json && uv run queens validate /tmp/queens_gen.json
# stdout: OK: board is valid
```

```bash
$ uv run queens generate --size 8 --seed 123 --algorithm nqueens-block --format json 2>/dev/null > /tmp/queens_gen8.json && uv run queens validate /tmp/queens_gen8.json
# stdout: OK: board is valid
```

Boards produced by the generator must pass validation. This
holds for all algorithms and sizes.

## File not found

```bash
$ uv run queens validate /tmp/queens_nonexistent_xyz.json
# exit: 1
```

Missing files produce an error and exit code 1.

## Disconnected region

```bash
$ echo '{"n":5,"regions":[[0,0,1,1,1],[0,0,0,1,1],[2,0,1,1,1],[2,2,3,4,1],[2,0,3,4,4]],"solution":[[0,0],[1,3],[2,1],[3,4],[4,2]]}' > /tmp/queens_disconnected.json && uv run queens validate /tmp/queens_disconnected.json
# exit: 1
# stderr: not all regions are connected
```

Region 0 has a disconnected cell at row 4, column 1 — the rest
of region 0 is in the top-left corner. Four-directional
connectivity is required.

## Multiple solutions

```bash
$ echo '{"n":5,"regions":[[0,1,2,3,4],[0,1,2,3,4],[0,1,2,3,4],[0,1,2,3,4],[0,1,2,3,4]],"solution":[[0,0],[1,1],[2,2],[3,3],[4,4]]}' > /tmp/queens_multi.json && uv run queens validate /tmp/queens_multi.json
# exit: 1
# stderr: solutions
```

A board where each column is its own region has many valid queen
placements. Exactly one solution is required.

## No solutions

```bash
$ echo '{"n":5,"regions":[[0,1,2,3,4],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0]],"solution":[[0,0],[1,1],[2,2],[3,3],[4,4]]}' > /tmp/queens_unsolvable.json && uv run queens validate /tmp/queens_unsolvable.json
# exit: 1
# stderr: no solutions found
```

Regions 1, 2, 3, and 4 each have exactly one cell, and all four
cells are in row 0. But a row can only hold one queen — making
the board structurally unsolvable. The validator reports "no
solutions found" because all regions are connected but the
solver finds zero valid placements.
