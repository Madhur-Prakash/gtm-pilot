"""Command line entry point: gtm-pilot [--sessions DIR] [--gputaskman PATH] [--resume FILE]"""

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
    parser.add_argument(
        "--resume", metavar="FILE", type=Path,
        help="keep recording into a saved recording (.jsonl): opens Resume Recording for it, "
             "with the settings it was recorded with. A bare name is looked for in the sessions folder.",
    )
    parser.add_argument("--version", action="version", version=f"gtm-pilot {__version__}")
    return parser


def resolve_resume(given: Path, sessions: Path) -> Path | None:
    """The recording --resume names: the path as given, else the name in the
    sessions folder, with or without its .jsonl"""
    given = given.expanduser()
    candidates = [given]
    if not given.is_absolute():
        candidates.append(sessions / given)
    candidates += [c.with_name(c.name + ".jsonl") for c in list(candidates) if c.suffix != ".jsonl"]

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    exe = find_gputaskman(args.gputaskman)
    runner = Gputaskman(exe) if exe else None
    sessions = (args.sessions or default_sessions_dir()).expanduser()

    resume = None
    if args.resume is not None:
        resume = resolve_resume(args.resume, sessions)
        if resume is None:
            parser.error(f"--resume: no recording at {args.resume} (or in {sessions})")

    if runner is not None:
        # Ask gputaskman which subcommands it has before the UI starts
        # (cached), so the menu can grey out what an older version can't do
        _ = runner.subcommands

    from .app import PilotApp  # imported late so --help stays fast

    # Without gputaskman the app opens on an error screen with install
    # steps, and moves on to the menu if it is installed meanwhile
    app = PilotApp(runner, sessions, explicit_exe=args.gputaskman, resume=resume)
    app.run()

    if app.runner is None:
        # Left from the error screen: keep the steps in the terminal too
        print("gputaskman was not found.\n", file=sys.stderr)
        print(INSTALL_HINT, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
