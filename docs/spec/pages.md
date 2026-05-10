# `pages` — GitHub Pages sharing

Generates a puzzle and outputs a shareable URL. No per-board git
commits are needed — the board is encoded in the URL fragment and
rendered dynamically by the player page.

One-time setup deploys the player to `docs/`:

    uv run queens pages --deploy

## Deploy the player page

```bash
$ uv run queens pages --deploy
# stdout: Deployed play.html
```

Writes the interactive player as `docs/index.html`. After commit
and push, GitHub Pages serves the player at your repo URL.

## Post-deploy: player page exists

```bash
$ test -f docs/index.html
# stdout! FAIL
```

After `--deploy`, `docs/index.html` exists and is a complete
HTML page. The `# stdout!` assertion ensures the `test` command
succeeds (exits 0 — the opposite of containing "FAIL").

## Generate a shareable URL

```bash
$ uv run queens pages --size 5 --seed 42
# stdout: #
# stdout: queens
```

Outputs a full URL like `https://<user>.github.io/<repo>/#<hash>`.
The board encoding appears after the `#` fragment.

## URL includes repo name

```bash
$ uv run queens pages --size 5 --seed 42
# stdout: BrokenDeskLamp.github.io/queens#
```

When a git remote is detected, the URL auto-detects the
GitHub Pages base path from the origin remote.

## No difficulty needed

```bash
$ uv run queens pages --size 5 --seed 1
# stdout: #
```

Difficulty is optional — omitting it generates a board of
unconstrained difficulty.
