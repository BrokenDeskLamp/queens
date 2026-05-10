# `benchmark` — Generation speed test

Measures board generation throughput by generating many boards
and reporting average time.

## Runs with progress output

```bash
$ uv run queens benchmark --size 5 --count 10
# stderr: Generated
# stderr: Avg
```

Benchmark output (progress and final stats) is printed to stderr.

## Small board is fast

```bash
$ uv run queens benchmark --size 5 --count 20
# stderr: Generated: 20/20
```

5×5 boards generate quickly — 20 boards should all succeed.

## Help output

```bash
$ uv run queens benchmark --help
# stdout: --size
# stdout: --count
# stdout: --seed
```

All flags are documented.
