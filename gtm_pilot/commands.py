"""The gputaskman argument lists behind each menu action.

Kept apart from the UI so each one is plain data that is easy to check.
"""

from __future__ import annotations

from pathlib import Path

# (seconds, label) presets offered in the forms; None means "until stopped"
REFRESH = [(0.5, "0.5 s"), (1.0, "1 s"), (2.0, "2 s"), (5.0, "5 s")]
INTERVALS = [(1.0, "1 s"), (2.0, "2 s"), (5.0, "5 s"), (10.0, "10 s")]
DURATIONS = [
    (None, "Until I stop it"),
    (60.0, "1 min"),
    (300.0, "5 min"),
    (600.0, "10 min"),
    (1800.0, "30 min"),
    (3600.0, "1 hour"),
]


def secs(value: float) -> str:
    """1.0 -> '1', 0.5 -> '0.5'"""
    return f"{value:g}"


def live_args(gpu: int | None, interval: float) -> list[str]:
    """Live TUI; gpu None shows every GPU (gputaskman's TUI default)"""
    args = ["-i", secs(interval)]
    if gpu is not None:
        args += ["--gpu", str(gpu)]
    return args


def snapshot_args(gpu: int) -> list[str]:
    return ["--once", "--gpu", str(gpu)]


def json_snapshot_args(gpu: int) -> list[str]:
    return ["--json", "--gpu", str(gpu)]


def record_args(path: Path, gpu: int, interval: float, duration: float | None, system: bool) -> list[str]:
    args = ["record", "-o", str(path), "--gpu", str(gpu), "-i", secs(interval)]
    if duration:
        args += ["--duration", secs(duration)]
    if not system:
        args.append("--no-system")
    return args


def summary_args(path: Path) -> list[str]:
    return ["summary", str(path)]


def replay_args(path: Path) -> list[str]:
    return ["replay", str(path)]


def diff_args(before: Path, after: Path) -> list[str]:
    return ["diff", str(before), str(after)]


def expected_samples(interval: float, duration: float | None) -> int | None:
    """How many samples a timed recording should take, for the progress bar"""
    if not duration:
        return None
    return max(1, round(duration / interval))
