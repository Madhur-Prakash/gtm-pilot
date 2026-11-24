"""Where gtm-pilot keeps snapshots and recordings, and how it names them."""

from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

ENV_SESSIONS = "GTM_PILOT_SESSIONS"

# Characters no file name may hold on Windows (and whitespace, so a label
# like "llama 3.1 8b" becomes one readable word: llama-3.1-8b)
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f\s]+')
_FORBIDDEN = set('<>:"/\\|?*')


def default_sessions_dir() -> Path:
    """$GTM_PILOT_SESSIONS if set, else ~/gpu-sessions on every OS"""
    env = os.environ.get(ENV_SESSIONS)
    if env:
        return Path(env).expanduser()
    return Path.home() / "gpu-sessions"


def file_label(text: str, fallback: str = "change") -> str:
    """Free text as a short, file-name-safe label: 'Llama 3.1 8B' -> 'Llama-3.1-8B'"""
    label = _UNSAFE.sub("-", text)[:40].strip(".- ")
    return label or fallback


def is_plain_name(text: str) -> bool:
    """A bare file name: not empty, no folders, nothing Windows refuses"""
    text = text.strip()
    return bool(text) and not set(text) & _FORBIDDEN and text not in (".", "..")


def default_recording_name(now: datetime | None = None) -> str:
    return f"session_{(now or datetime.now()):%Y-%m-%d_%H-%M}.jsonl"


def recording_path(folder: Path, name: str) -> Path:
    name = name.strip()
    return folder / (name if name.endswith(".jsonl") else f"{name}.jsonl")


# The settings each recording was started with, so Resume Recording can keep
# recording it the same way. No .json extension: the snapshot pickers list
# *.json files, and this isn't one to compare.
SETTINGS_FILE = ".gtm-pilot-recordings"


@dataclass(frozen=True)
class RecordingSettings:
    gpu: int
    interval: float
    system: bool


def _settings_key(path: Path) -> str:
    return str(path.expanduser().resolve())


def _read_settings(folder: Path) -> dict:
    try:
        data = json.loads((folder / SETTINGS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_recording_settings(folder: Path, path: Path, settings: RecordingSettings) -> None:
    """Remember how path was recorded. Best effort: a read-only folder only
    means Resume asks for the settings again."""
    data = _read_settings(folder)
    data[_settings_key(path)] = asdict(settings)
    try:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / SETTINGS_FILE).write_text(json.dumps(data, indent=1), encoding="utf-8")
    except OSError:
        pass


def load_recording_settings(folder: Path, path: Path) -> RecordingSettings | None:
    entry = _read_settings(folder).get(_settings_key(path))
    try:
        return RecordingSettings(int(entry["gpu"]), float(entry["interval"]), bool(entry["system"]))
    except (TypeError, KeyError, ValueError):
        return None


@dataclass(frozen=True)
class RecordedSettings:
    """Settings worked out from a recording's own samples, for recordings
    made before gtm-pilot saved them (or by gputaskman directly)."""
    gpu_name: str | None
    gpu_index: int | None
    interval: float
    system: bool


def infer_recording_settings(path: Path, max_samples: int = 200) -> RecordedSettings | None:
    """Read the first samples of a recording: the interval is the median gap
    between their 'taken' times (so a pause in between doesn't skew it), the
    GPU and system RAM/CPU come from the samples themselves. None when the
    file has fewer than two readable samples."""
    samples = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    sample = json.loads(line)
                except ValueError:
                    continue  # a half-written last line
                if isinstance(sample, dict) and isinstance(sample.get("taken"), (int, float)):
                    samples.append(sample)
                if len(samples) >= max_samples:
                    break
    except OSError:
        return None

    if len(samples) < 2:
        return None

    taken = [s["taken"] for s in samples]
    gaps = sorted(b - a for a, b in zip(taken, taken[1:]) if b > a)
    if not gaps:
        return None
    # Samples land a few ms either side of the interval: 9.98, 10.01 -> 10
    interval = max(0.1, round(statistics.median(gaps), 1))

    first = samples[0]
    device = first.get("device") if isinstance(first.get("device"), dict) else {}
    index = device.get("index")
    return RecordedSettings(
        gpu_name=first.get("gpu") if isinstance(first.get("gpu"), str) else None,
        gpu_index=index if isinstance(index, int) else None,
        interval=interval,
        system=first.get("system") is not None,
    )


def snapshot_paths(folder: Path, label: str, now: datetime | None = None) -> tuple[Path, Path]:
    """Before/after paths named after what is measured, so a pair sits together
    when sorted by name: llama3.1-8b_2026-11-13_21-10_before.json"""
    base = f"{label}_{(now or datetime.now()):%Y-%m-%d_%H-%M}"
    name, n = base, 1

    # The same label twice in one minute gets -2, -3, ... rather than overwriting
    while any((folder / f"{name}_{side}.json").exists() for side in ("before", "after")):
        n += 1
        name = f"{base}-{n}"

    return folder / f"{name}_before.json", folder / f"{name}_after.json"


def recent_files(folder: Path, pattern: str, limit: int = 30) -> list[Path]:
    """Files in folder matching pattern, newest first"""
    if not folder.is_dir():
        return []

    files = [p for p in folder.glob(pattern) if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def describe(path: Path) -> str:
    """'name.jsonl  (14 Nov 09:37, 16.0 MB)' for file lists"""
    st = path.stat()
    size = st.st_size
    if size >= 1024 ** 2:
        size_text = f"{size / 1024 ** 2:.1f} MB"
    else:
        size_text = f"{max(1, round(size / 1024))} KB"
    return f"{path.name}  ({datetime.fromtimestamp(st.st_mtime):%d %b %H:%M}, {size_text})"


def open_folder(path: Path) -> None:
    """Open a folder in Explorer / Finder / the desktop's file manager"""
    path.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(
            ["xdg-open", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
