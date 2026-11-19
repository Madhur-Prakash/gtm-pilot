"""Run `gputaskman record` with live progress, then show its summary."""

from __future__ import annotations

import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, ProgressBar, Static

from .. import commands
from ..gputaskman import Gputaskman, Result
from .fit import FitsTerminal
from .output import OutputScreen

# How long to let record finish its last sample after Stop before killing it
STOP_GRACE = 10.0


def count_new_samples(path: Path, pos: int) -> tuple[int, int]:
    """(complete lines appended after byte pos, new pos). A half-written
    last line is left for the next call."""
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return 0, pos

    if size <= pos:
        return 0, pos

    with open(path, "rb") as f:
        f.seek(pos)
        chunk = f.read(size - pos)

    end = chunk.rfind(b"\n") + 1
    return chunk[:end].count(b"\n"), pos + end


def elapsed_text(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


class RecordScreen(FitsTerminal, Screen):
    # Scroll the box rather than letting Stop fall off a short terminal
    BODY = "#record-box"
    BOX = None
    BODY_MAX = 40

    BINDINGS = [
        Binding("s", "stop", "Stop recording"),
        Binding("escape", "stop", "Stop", show=False),
    ]

    def __init__(self, runner: Gputaskman, path: Path, gpu: int, interval: float,
                 duration: float | None, system: bool):
        super().__init__()
        self.runner = runner
        self.path = path
        self.gpu = gpu
        self.interval = interval
        self.duration = duration
        self.system = system

        self.proc: subprocess.Popen | None = None
        self.stderr = tempfile.TemporaryFile()
        self.samples = 0
        self.pos = 0
        self.started = 0.0
        self.stop_requested_at: float | None = None
        self.finished = False

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="record-box"):
            yield Static(id="record-title", classes="dialog-title")
            yield Static(id="record-status")
            yield ProgressBar(total=commands.expected_samples(self.interval, self.duration),
                              show_eta=False, id="record-progress")
            yield Static(
                "Samples are written as they are taken, so stopping early keeps every one so far.",
                classes="hint",
            )
            with Horizontal(classes="buttons"):
                yield Button("Stop recording", id="stop", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = "Recording"
        how_long = f"for {elapsed_text(self.duration)}" if self.duration else "until you stop it"
        self.query_one("#record-title", Static).update(Text(
            f"Recording GPU {self.gpu} every {commands.secs(self.interval)} s {how_long}\n{self.path}"
        ))
        if not self.duration:
            self.query_one("#record-progress").display = False

        self.path.parent.mkdir(parents=True, exist_ok=True)
        # record appends: only count lines written by this run
        self.pos = self.path.stat().st_size if self.path.exists() else 0

        args = commands.record_args(self.path, self.gpu, self.interval, self.duration, self.system)
        try:
            # record prints its own start/stop lines; this screen replaces them
            self.proc = self.runner.start(*args, stdout=subprocess.DEVNULL, stderr=self.stderr)
        except OSError as exc:
            self._fail(f"Could not start gputaskman record: {exc}")
            return

        self.started = time.monotonic()
        self.set_interval(0.5, self._poll)
        self._poll()

    def _poll(self) -> None:
        if self.finished or self.proc is None:
            return

        new, self.pos = count_new_samples(self.path, self.pos)
        if new:
            self.samples += new
            self.query_one("#record-progress", ProgressBar).advance(new)

        state = "Stopping (finishing the current sample)" if self.stop_requested_at else "Recording"
        self.query_one("#record-status", Static).update(Text(
            f"{state}   samples: {self.samples}   elapsed: {elapsed_text(time.monotonic() - self.started)}"
        ))

        if self.proc.poll() is None:
            if self.stop_requested_at and time.monotonic() - self.stop_requested_at > STOP_GRACE:
                self.proc.kill()
            return

        self._done()

    @on(Button.Pressed, "#stop")
    def action_stop(self) -> None:
        if self.finished:
            self.dismiss()  # the button reads "Back to menu" by now
            return
        if self.proc is None or self.stop_requested_at:
            return

        self.stop_requested_at = time.monotonic()
        self.query_one("#stop", Button).disabled = True

        if sys.platform == "win32":
            # No Ctrl+C for a background process on Windows. record flushes
            # every sample as it goes, so ending it keeps all finished ones.
            self.proc.terminate()
        else:
            # Same as Ctrl+C: record finishes cleanly
            self.proc.send_signal(signal.SIGINT)

    def _done(self) -> None:
        self.finished = True
        new, self.pos = count_new_samples(self.path, self.pos)
        self.samples += new

        stopped = self.stop_requested_at is not None
        if self.proc.returncode != 0 and not stopped:
            self.stderr.seek(0)
            message = self.stderr.read().decode("utf-8", "replace").strip()
            self._fail(message or f"gputaskman record exited with {self.proc.returncode}")
            return

        if self.samples == 0:
            self._fail("Recording ended before any sample was written.")
            return

        runner, path = self.runner, self.path

        def summary(width: int) -> Result:
            return runner.capture(*commands.summary_args(path), columns=width)

        intro = f"Recorded {self.samples} sample(s) to {path}"
        if runner.supports("summary"):
            self.app.switch_screen(OutputScreen("Recording summary", summary, intro=intro))
        else:
            self.app.switch_screen(OutputScreen(
                "Recording saved",
                lambda _w: Result(0, f"{intro}\n\nThis gputaskman has no summary command yet; "
                                     "update it to summarize recordings.", ""),
            ))

    def _fail(self, message: str) -> None:
        self.finished = True
        self.query_one("#record-status", Static).update(Text(message, style="bold red"))
        button = self.query_one("#stop", Button)
        button.label = "Back to menu"
        button.variant = "default"
        button.disabled = False

    def on_unmount(self) -> None:
        # Leaving the app mid-recording: don't leave record running unseen
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
        self.stderr.close()
