# `generate` — Board generation

Creates a valid N×N Queens board with a unique solution and
connected regions. Boards are guaranteed solvable by pure
deduction — no guessing required.

All examples use a fixed `--seed` for reproducible output.

## Basic generation (ASCII)

```bash
$ uv run queens generate --size 5 --seed 42
# stdout_eq:    0 1 2 3 4
# stdout_eq:  0 1 1 2 ♛ 0
# stdout_eq:  1 ♛ 1 2 2 2
# stdout_eq:  2 1 2 ♛ 2 2
# stdout_eq:  3 4 4 4 2 ♛
# stdout_eq:  4 4 ♛ 4 4 3
# stderr: Difficulty
# stderr: trivial
# stderr: 5/5 by deduction
```

The default output is an ASCII grid with region IDs and `♛`
queen markers. The exact board above is the canonical output
for seed 42 — any change indicates a regression.

## JSON output

```bash
$ uv run queens generate --size 5 --seed 42 --format json
# stdout_eq: {"n": 5, "regions": [[1, 1, 2, 0, 0], [1, 1, 2, 2, 2], [1, 2, 2, 2, 2], [4, 4, 4, 2, 3], [4, 4, 4, 4, 3]], "solution": [[0, 3], [1, 0], [2, 2], [3, 4], [4, 1]]}
# stderr: Difficulty
# stderr: trivial
# stderr: 5/5 by deduction
# stderr: Generated in
```

Valid JSON with `n`, `regions` (N×N grid), and `solution`
(N queen positions). The exact JSON is locked as a regression test.
The difficulty report on stderr varies in timing, so we use
substring checks.

## Round-trip: generate → validate

```bash
$ uv run queens generate --size 5 --seed 42 --format json -o /dev/null 2>/dev/null > /tmp/queens_rt.json && uv run queens validate /tmp/queens_rt.json
# stdout: OK: board is valid
```

Every generated board must pass its own validator. The `-o /dev/null`
flag could produce a PNG side-effect. The board validates because the
pipeline guarantees exactly one unique solution and connected regions.

## Help output

```bash
$ uv run queens generate --help
# stdout: --size
# stdout: --difficulty
# stdout: --seed
# stdout: --format
# stdout: --attempts
# stdout: --algorithm
# stdout: --output
# stdout: --help
```

All generation flags are documented.

## Invalid difficulty name

```bash
$ uv run queens generate --difficulty bogus
# exit: 1
```

Unknown difficulty names cause an error message and exit code 1.

## Seed reproducibility

```bash
$ uv run queens generate --size 6 --seed 99 --format json
# stdout: "n": 6
```

The same seed always produces the same board. Run this twice and
compare — the output is identical every time.

## PNG output

```bash
$ uv run queens generate --size 5 --seed 1 --output /tmp/queens_spec_test.png
# stdout: ♛
# stderr: Saved board image
```

The `--output` flag renders the board as a PNG image in
LinkedIn Queens style (colored regions, no solution markers).

## Board sizes

```bash
$ uv run queens generate --size 4 --seed 7 --format json
# stdout: "n": 4
```

```bash
$ uv run queens generate --size 10 --seed 7 --format json
# stdout: "n": 10
```

Boards from 4×4 up to 15×15 are supported. Larger boards take
longer to generate but produce the same valid output structure.

## Algorithm selection

```bash
$ uv run queens generate --size 6 --seed 3 --algorithm bfs
# stdout: ♛
```

```bash
$ uv run queens generate --size 6 --seed 3 --algorithm nqueens-block
# stdout: ♛
```

```bash
$ uv run queens generate --size 6 --seed 3 --algorithm cpsat
# stdout: ♛
```

Three generation algorithms are available. All produce valid,
uniquely-solvable boards. BFS is the default and produces the
most deduction-friendly puzzles.
