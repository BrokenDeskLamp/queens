# `share` — Local interactive player

Generates a board and opens it in the browser via a local HTTP
server. The board is encoded in the URL fragment — no solution
data is ever sent. Others on the same network can connect using
the printed URL.

## Generates a board and prints URLs

```bash
$ perl -e 'alarm 5; exec @ARGV' uv run queens share --size 5 --seed 1 --no-open 2>&1 || true
# stdout: http://localhost
# stdout: Puzzle URL
# stdout: Press Ctrl+C
```

The local server prints both the localhost URL and (when a git
remote is detected) the public GitHub Pages URL.

## Public URL is shown when remote detected

```bash
$ perl -e 'alarm 5; exec @ARGV' uv run queens share --size 5 --seed 1 --no-open 2>&1 || true
# stdout: github.io
# stdout: #
```

The public URL points to the same board on GitHub Pages,
using the hash-fragment encoding.

## Help output lists all flags

```bash
$ uv run queens share --help
# stdout: --size
# stdout: --difficulty
# stdout: --seed
# stdout: --algorithm
# stdout: --port
# stdout: --open
```

All generation and server flags are documented in the help text.
