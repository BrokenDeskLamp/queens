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
$ uv run queens validate --help
# stdout: validate
```

The unsolvable-board edge case is covered by unit tests
(``test_unsolvable_board_returns_zero_5``).  Constructing a
small connected-but-unsolvable board by hand is non-trivial.
