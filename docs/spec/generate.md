# `generate` — Board generation

Creates a valid N×N Queens board with a unique solution and
connected regions. Boards are guaranteed solvable by pure
deduction — no guessing required.

All examples use a fixed `--seed` for reproducible output.

## Basic generation (ASCII)

```bash
$ uv run queens generate --size 5 --seed 42
# stdout: ♛
# stderr: Difficulty
```

The default output is an ASCII grid with region IDs and `♛`
queen markers. Difficulty analysis is printed to stderr.

## JSON output

```bash
$ uv run queens generate --size 5 --seed 42 --format json
# stdout: "n"
# stdout: "regions"
# stdout: "solution"
```

Valid JSON with `n`, `regions` (N×N grid), and `solution`
(N queen positions).

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
