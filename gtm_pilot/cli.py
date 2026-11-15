"""Command line entry point: gtm-pilot [--sessions DIR] [--gputaskman PATH]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .gputaskman import ENV_EXE, Gputaskman, find_gputaskman
from .sessions import ENV_SESSIONS, default_sessions_dir

INSTALL_HINT = """\
gtm-pilot needs gputaskman: https://github.com/shanselman/gputaskman

Install it with uv tool (once a release has summary and replay):
  uv tool install gputaskman

Or build it from source (has the newest commands today):
  uv tool install --force git+https://github.com/shanselman/gputaskman

Already installed somewhere else? Point gtm-pilot at it with
--gputaskman PATH or the {env} environment variable.""".format(env=ENV_EXE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gtm-pilot",
        description="A guided menu for gputaskman: live view, snapshots, recordings, "
                    "summaries and before/after diffs without remembering the flags.",
        epilog=f"Unofficial companion to gputaskman; every reading comes from the "
               f"gputaskman you have installed. Environment: {ENV_SESSIONS}, {ENV_EXE}.",
    )
    parser.add_argument(
        "--sessions", metavar="DIR", type=Path,
        help=f"folder for recordings and snapshots (default: ${ENV_SESSIONS} or ~/gpu-sessions)",
    )
    parser.add_argument(
        "--gputaskman", metavar="PATH",
        help=f"gputaskman executable to run (default: ${ENV_EXE}, then gputaskman on PATH)",
    )
    parser.add_argument("--version", action="version", version=f"gtm-pilot {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    exe = find_gputaskman(args.gputaskman)
    runner = Gputaskman(exe) if exe else None
    sessions = (args.sessions or default_sessions_dir()).expanduser()

    if runner is not None:
        # Ask gputaskman which subcommands it has before the UI starts
        # (cached), so the menu can grey out what an older version can't do
        _ = runner.subcommands

    from .app import PilotApp  # imported late so --help stays fast

    # Without gputaskman the app opens on an error screen with install
    # steps, and moves on to the menu if it is installed meanwhile
    app = PilotApp(runner, sessions, explicit_exe=args.gputaskman)
    app.run()

    if app.runner is None:
        # Left from the error screen: keep the steps in the terminal too
        print("gputaskman was not found.\n", file=sys.stderr)
        print(INSTALL_HINT, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
