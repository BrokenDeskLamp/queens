"""CLI for the Queens board generator."""

from __future__ import annotations

import json
import random
import socketserver
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Annotated

import typer

from .board import Board
from .difficulty import exhaustive_analyze
from .generator import GenerationError, generate_board
from .regions import RegionBuilder, nqueens_aware_build, nqueens_block_build, random_bfs_build
from .render import render_board_png
from .share import encode_board
from .solver import count_solutions

app = typer.Typer(no_args_is_help=True)


@app.command()
def generate(
    size: Annotated[int, typer.Option("--size", "-n", help="Board size (N×N)")] = 8,
    difficulty: Annotated[
        str | None,
        typer.Option(
            "--difficulty",
            "-d",
            help="Target difficulty: trivial, easy, medium, hard, expert, master",
        ),
    ] = None,
    seed: Annotated[int | None, typer.Option("--seed", "-s")] = None,
    format: Annotated[
        str, typer.Option("--format", "-f", help="Output format: ascii, json")
    ] = "ascii",
    attempts: Annotated[
        int, typer.Option("--attempts", "-a", help="Max generation attempts")
    ] = 1000,
    algorithm: Annotated[
        str,
        typer.Option(
            "--algorithm",
            "-A",
            help="Generation algorithm: bfs, nqueens-block, cpsat",
        ),
    ] = "bfs",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Save board as PNG image"),
    ] = None,
) -> None:
    """Generate a valid Queens board."""
    diff_map: dict[str, float] = {
        "trivial": 0.0,
        "easy": 1.0,
        "medium": 2.0,
        "hard": 4.0,
        "expert": 7.0,
        "master": 10.0,
    }
    target = diff_map.get(difficulty.lower()) if difficulty else None
    if difficulty and target is None:
        valid = ", ".join(diff_map)
        typer.echo(f"Invalid difficulty. Choose from: {valid}", err=True)
        raise typer.Exit(1)

    region_func = _resolve_algorithm(algorithm)

    start = time.perf_counter()
    board = generate_board(
        size,
        target_difficulty=target,
        seed=seed,
        max_attempts=attempts,
        region_func=region_func,
        harden_deduction=(algorithm == "bfs"),
    )
    elapsed = time.perf_counter() - start

    if format == "json":
        typer.echo(json.dumps(board.to_json()))
    else:
        typer.echo(board.to_ascii())

    if output is not None:
        render_board_png(board, output)
        typer.echo(f"Saved board image to {output}", err=True)

    report = exhaustive_analyze(board)
    typer.echo(
        f"\nDifficulty: {report.score:.1f} ({report.difficulty_class}) | "
        f"{report.deduction_placed}/{size} by deduction | "
        f"Generated in {elapsed:.3f}s",
        err=True,
    )


@app.command()
def validate(
    path: Annotated[Path, typer.Argument(help="Path to board JSON file")],
) -> None:
    """Validate a board file: check connectivity and uniqueness."""
    board = Board.load(path)

    if not board.is_connected():
        typer.echo("FAIL: not all regions are connected", err=True)
        raise typer.Exit(1)

    sol_count = count_solutions(board, limit=2)
    if sol_count == 0:
        typer.echo("FAIL: no solutions found", err=True)
        raise typer.Exit(1)
    if sol_count > 1:
        typer.echo(f"FAIL: {sol_count}+ solutions (expected exactly 1)", err=True)
        raise typer.Exit(1)

    typer.echo("OK: board is valid with exactly 1 solution")


@app.command()
def benchmark(
    size: Annotated[int, typer.Option("--size", "-n")] = 8,
    count: Annotated[int, typer.Option("--count", "-c")] = 100,
    seed: Annotated[int | None, typer.Option("--seed", "-s")] = None,
) -> None:
    """Benchmark board generation speed."""
    rng = random.Random(seed)
    total_time = 0.0
    success = 0

    for i in range(count):
        attempt_seed = rng.randint(0, 2**31 - 1)
        start = time.perf_counter()
        try:
            generate_board(size, seed=attempt_seed, max_attempts=500)
            elapsed = time.perf_counter() - start
            total_time += elapsed
            success += 1
        except GenerationError:
            elapsed = time.perf_counter() - start
            total_time += elapsed

        if (i + 1) % 10 == 0:
            typer.echo(f"  {i + 1}/{count}...", err=True)

    avg = total_time / count if count > 0 else 0
    typer.echo(
        f"\nSize: {size}×{size} | Generated: {success}/{count} | Avg: {avg * 1000:.1f}ms",
        err=True,
    )


@app.command()
def share(
    size: Annotated[int, typer.Option("--size", "-n", help="Board size (N×N)")] = 8,
    difficulty: Annotated[
        str | None,
        typer.Option(
            "--difficulty",
            "-d",
            help="Target difficulty: trivial, easy, medium, hard, expert, master",
        ),
    ] = None,
    seed: Annotated[int | None, typer.Option("--seed", "-s")] = None,
    algorithm: Annotated[
        str,
        typer.Option(
            "--algorithm",
            "-A",
            help="Generation algorithm: bfs, nqueens-block, cpsat",
        ),
    ] = "bfs",
    port: Annotated[int, typer.Option("--port", "-p", help="HTTP server port")] = 8765,
    open_browser: Annotated[
        bool, typer.Option("--open/--no-open", help="Open browser automatically")
    ] = True,
) -> None:
    """Generate a board and open it as an interactive puzzle in the browser.

    Starts a local HTTP server, generates a playable Queens puzzle,
    and opens it in your browser. The board data is encoded in the
    URL hash — no solution is ever sent. Share the URL with others
    on the same network.
    """
    diff_map: dict[str, float] = {
        "trivial": 0.0,
        "easy": 1.0,
        "medium": 2.0,
        "hard": 4.0,
        "expert": 7.0,
        "master": 10.0,
    }
    target = diff_map.get(difficulty.lower()) if difficulty else None
    if difficulty and target is None:
        valid = ", ".join(diff_map)
        typer.echo(f"Invalid difficulty. Choose from: {valid}", err=True)
        raise typer.Exit(1)

    region_func = _resolve_algorithm(algorithm)

    typer.echo(f"Generating {size}×{size} board ({algorithm})...", err=True)
    board = generate_board(
        size,
        target_difficulty=target,
        seed=seed,
        region_func=region_func,
        harden_deduction=(algorithm == "bfs"),
    )

    # Encode board as URL hash
    regions_list = board.regions.tolist()
    encoded = encode_board(size, regions_list)
    puzzle_url = f"/play.html#{encoded}"

    # Serve play.html from the package directory
    serve_dir = Path(__file__).resolve().parent
    play_html = serve_dir / "play.html"
    if not play_html.exists():
        typer.echo(f"Error: play.html not found at {serve_dir}", err=True)
        raise typer.Exit(1)

    # Start HTTP server in background
    handler = _quiet_handler(serve_dir)
    httpd = socketserver.TCPServer(("", port), handler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    full_url = f"http://localhost:{port}{puzzle_url}"

    typer.echo(f"\n  Puzzle URL: {full_url}\n")
    typer.echo(f"  Serving from: {serve_dir}")
    typer.echo("  Press Ctrl+C to stop the server.\n")

    if open_browser:
        webbrowser.open(full_url)

    try:
        # Keep the server running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        typer.echo("\nServer stopped.", err=True)
        httpd.shutdown()


@app.command()
def pages(
    size: Annotated[int, typer.Option("--size", "-n", help="Board size (N×N)")] = 8,
    difficulty: Annotated[
        str | None,
        typer.Option(
            "--difficulty",
            "-d",
            help="Target difficulty: trivial, easy, medium, hard, expert, master",
        ),
    ] = None,
    seed: Annotated[int | None, typer.Option("--seed", "-s")] = None,
    open_browser: Annotated[
        bool, typer.Option("--open/--no-open", help="Open the page in browser for preview")
    ] = False,
) -> None:
    """Generate a puzzle page for GitHub Pages hosting.

    Writes docs/index.html with the puzzle embedded. Commit and push
    to serve it at https://<user>.github.io/<repo>/.

    Only one puzzle is hosted at a time — each run overwrites the
    previous page.
    """
    diff_map: dict[str, float] = {
        "trivial": 0.0,
        "easy": 1.0,
        "medium": 2.0,
        "hard": 4.0,
        "expert": 7.0,
        "master": 10.0,
    }
    target = diff_map.get(difficulty.lower()) if difficulty else None
    if difficulty and target is None:
        valid = ", ".join(diff_map)
        typer.echo(f"Invalid difficulty. Choose from: {valid}", err=True)
        raise typer.Exit(1)

    region_func = _resolve_algorithm("bfs")

    typer.echo(f"Generating {size}×{size} board...", err=True)
    board = generate_board(
        size,
        target_difficulty=target,
        seed=seed,
        region_func=region_func,
        harden_deduction=True,
    )

    # Encode board as URL hash
    regions_list = board.regions.tolist()
    encoded = encode_board(size, regions_list)

    # Read play.html template
    serve_dir = Path(__file__).resolve().parent
    play_html_path = serve_dir / "play.html"
    if not play_html_path.exists():
        typer.echo(f"Error: play.html not found at {serve_dir}", err=True)
        raise typer.Exit(1)

    template = play_html_path.read_text()

    # Inject the puzzle hash before the closing </script> tag (the last one)
    # Find the position of the main <script> block
    inject_marker = "<script>"
    script_start = template.index(inject_marker) + len(inject_marker)
    hash_script = f"\n    window.__PUZZLE_HASH__ = '{encoded}';"
    output_html = template[:script_start] + hash_script + template[script_start:]

    # Write to docs/
    docs_dir = Path.cwd() / "docs"
    docs_dir.mkdir(exist_ok=True)
    output_path = docs_dir / "index.html"
    output_path.write_text(output_html)

    typer.echo(f"\n  Puzzle page written to: {output_path}")
    typer.echo(f"  Board: {size}×{size}")
    typer.echo(f"  Hash: {encoded}")
    typer.echo("\n  To publish:")
    typer.echo("    1. Enable GitHub Pages in repo Settings → Pages")
    typer.echo('       Source: "Deploy from a branch", branch: main, folder: /docs')
    typer.echo("    2. git add docs/ && git commit -m 'New puzzle' && git push")
    typer.echo("\n  Your puzzle will be live at:")
    typer.echo("    https://<your-username>.github.io/<repo>/")

    if open_browser:
        webbrowser.open(f"file://{output_path}")


def _resolve_algorithm(name: str) -> RegionBuilder:
    """Resolve an algorithm name to a region builder function."""
    mapping: dict[str, RegionBuilder] = {
        "bfs": random_bfs_build,
        "nqueens-block": nqueens_block_build,
        "cpsat": nqueens_aware_build,
    }
    if name not in mapping:
        valid = ", ".join(mapping)
        raise typer.BadParameter(f"Unknown algorithm '{name}'. Choose from: {valid}")
    return mapping[name]


def _quiet_handler(serve_dir: Path) -> type[SimpleHTTPRequestHandler]:
    """Create a request handler that serves from a specific directory silently."""
    serve_dir_str = str(serve_dir)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:  # noqa: ARG002
            super().__init__(*args, directory=serve_dir_str)  # type: ignore[misc]

        def log_message(self, format: str, *args: object) -> None:
            pass  # Suppress access log noise

    return Handler
