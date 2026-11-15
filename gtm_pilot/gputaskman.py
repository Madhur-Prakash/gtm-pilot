"""Finding and running the gputaskman command.

gtm-pilot never reads the GPU itself: every reading comes from the
gputaskman you have installed, so its numbers and labels stay exactly as
gputaskman reports them.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

ENV_EXE = "GTM_PILOT_GPUTASKMAN"

# Subcommands gtm-pilot can drive; older gputaskman versions lack some
SUBCOMMANDS = ("diff", "record", "summary", "replay")


@dataclass(frozen=True)
class Gpu:
    index: int
    name: str
    details: str = ""

    @property
    def label(self) -> str:
        return f"{self.index}: {self.name}"


@dataclass(frozen=True)
class Result:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def text(self) -> str:
        """stdout, or stderr when there is no stdout (an error message)"""
        return self.stdout if self.stdout.strip() else self.stderr


def find_gputaskman(explicit: str | None = None) -> str | None:
    """--gputaskman, then $GTM_PILOT_GPUTASKMAN, then gputaskman or gtm on PATH,
    then uv's and pipx's default tool folder"""
    for candidate in (explicit, os.environ.get(ENV_EXE)):
        if candidate:
            found = shutil.which(candidate) or (candidate if Path(candidate).is_file() else None)
            if found:
                return found

    for name in ("gputaskman", "gtm"):
        found = shutil.which(name)
        if found:
            return found

    exe = "gputaskman.exe" if sys.platform == "win32" else "gputaskman"
    fallback = Path.home() / ".local" / "bin" / exe
    return str(fallback) if fallback.is_file() else None


def parse_gpus(text: str) -> list[Gpu]:
    """Gpu list from `gputaskman --list-gpus`. Lines look like
    0: NVIDIA GeForce RTX 4060 Laptop GPU (NVIDIA, LUID 0x...)
    and anything else (such as a TCC discovery note) is skipped."""
    gpus = []

    for line in text.splitlines():
        index, sep, rest = line.partition(":")
        if not (sep and index.strip().isdigit()):
            continue

        rest = rest.strip()
        name, sep, details = rest.rpartition(" (")
        if not sep:
            name, details = rest, ""

        gpus.append(Gpu(int(index), name.strip(), details.rstrip(")")))

    return gpus


def parse_subcommands(help_text: str) -> set[str]:
    """Subcommands named in `gputaskman --help`, e.g. 'gputaskman summary FILE'"""
    named = set(re.findall(r"gputaskman\s+([a-z]+)\b", help_text))
    return named & set(SUBCOMMANDS)


class Gputaskman:
    """Runs one gputaskman executable"""

    def __init__(self, exe: str):
        self.exe = exe

    def argv(self, *args: object) -> list[str]:
        return [self.exe, *map(str, args)]

    def env(self, columns: int | None = None) -> dict[str, str]:
        # gputaskman is a Python app: have it write UTF-8 when its output is
        # captured, and size its text tables to the pane showing them
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        if columns:
            env["COLUMNS"] = str(columns)
        return env

    def capture(self, *args: object, columns: int | None = None, timeout: float | None = 300) -> Result:
        """Run and collect the output (snapshots, diff, summary, --list-gpus)"""
        try:
            proc = subprocess.run(
                self.argv(*args),
                capture_output=True,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=self.env(columns),
                timeout=timeout,
                creationflags=_NO_WINDOW,
            )
        except FileNotFoundError:
            return Result(127, "", f"gputaskman not found: {self.exe}")
        except subprocess.TimeoutExpired:
            return Result(124, "", f"gputaskman {' '.join(map(str, args))} took longer than {timeout:g} s")

        return Result(proc.returncode, proc.stdout, proc.stderr)

    def run_attached(self, *args: object) -> int:
        """Run with the terminal, for gputaskman's own full-screen views"""
        try:
            return subprocess.run(self.argv(*args), env=self.env()).returncode
        except FileNotFoundError:
            return 127

    def start(self, *args: object, stdout, stderr) -> subprocess.Popen:
        """Start in the background (record). On Windows it gets its own
        process group, so a Ctrl+C typed in the terminal doesn't reach it."""
        flags = _NO_WINDOW
        if sys.platform == "win32":
            flags |= subprocess.CREATE_NEW_PROCESS_GROUP

        return subprocess.Popen(
            self.argv(*args),
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            env=self.env(),
            creationflags=flags,
        )

    def list_gpus(self) -> list[Gpu]:
        return parse_gpus(self.capture("--list-gpus", timeout=60).stdout)

    @cached_property
    def subcommands(self) -> set[str]:
        return parse_subcommands(self.capture("--help", timeout=60).stdout)

    def supports(self, subcommand: str) -> bool:
        return subcommand in self.subcommands


# Keep console windows from flashing up for captured runs on Windows
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
