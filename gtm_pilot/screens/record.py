"""Run `gputaskman record` with live progress, pause and resume, then show its summary."""

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

# How long to let record finish its last sample after Pause or Stop before killing it
STOP_GRACE = 10.0

# Where a recording is: "recording" (record running), "pausing" (asked to end,
# finishing its sample), "paused" (no record running), "stopping", "finished"
RECORDING, PAUSING, PAUSED, STOPPING, FINISHED = "recording", "pausing", "paused", "stopping", "finished"


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


def remaining_duration(duration: float | None, recorded: float) -> float | None:
    """Seconds left of a timed recording after recorded seconds; None when
    it runs until stopped. Never below zero."""
    if not duration:
        return None
    return max(0.0, duration - recorded)


class RecordScreen(FitsTerminal, Screen):
    """Runs gputaskman record. Pause ends the current record run cleanly
    (every finished sample is already in the file); Resume starts a new run
    that appends to the same file, for whatever time a timed recording has
    left. The same on every OS: no process is frozen."""

    # Scroll the box rather than letting the buttons fall off a short terminal
    BODY = "#record-box"
    BOX = None
    BODY_MAX = 40

    BINDINGS = [
        Binding("p", "toggle_pause", "Pause / Resume"),
        Binding("space", "toggle_pause", "Pause / Resume", show=False),
        Binding("s", "stop", "Stop recording"),
        Binding("escape", "stop", "Stop", show=False),
    ]

    def __init__(self, runner: Gputaskman, path: Path, gpu: int, interval: float,
                 duration: float | None, system: bool, resuming: bool = False):
        super().__init__()
        self.runner = runner
        self.path = path
        self.gpu = gpu
        self.interval = interval
        self.duration = duration
        self.system = system
        # Continuing a recording saved earlier (Resume Recording): samples
        # already in the file are counted apart from this session's
        self.resuming = resuming

        self.proc: subprocess.Popen | None = None
        self.stderr = tempfile.TemporaryFile()
        self.state = RECORDING
        self.samples = 0
        self.earlier_samples = 0
        self.pos = 0
        self.pauses = 0
        # Seconds spent recording (paused time left out) by finished runs;
        # the run going on now adds the time since run_started
        self.recorded = 0.0
        self.run_started = 0.0
        self.paused_at = 0.0
        self.end_requested_at: float | None = None

    @property
    def finished(self) -> bool:
        return self.state == FINISHED

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="record-box"):
            yield Static(id="record-title", classes="dialog-title")
            yield Static(id="record-status")
            yield ProgressBar(total=commands.expected_samples(self.interval, self.duration),
                              show_eta=False, id="record-progress")
            yield Static(
                "Samples are written as they are taken, so pausing or stopping keeps every one so far. "
                "Nothing is sampled while paused.",
                classes="hint",
            )
            with Horizontal(classes="buttons"):
                yield Button("Pause", id="pause", variant="warning")
                yield Button("Stop recording", id="stop", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = "Recording"
        how_long = f"for {elapsed_text(self.duration)}" if self.duration else "until you stop it"
        verb = "Continuing" if self.resuming else "Recording"
        self.query_one("#record-title", Static).update(Text(
            f"{verb} GPU {self.gpu} every {commands.secs(self.interval)} s {how_long}\n{self.path}"
        ))
        if not self.duration:
            self.query_one("#record-progress").display = False

        self.path.parent.mkdir(parents=True, exist_ok=True)
        # record appends: only count lines written by this session
        if self.path.exists():
            self.pos = self.path.stat().st_size
            if self.resuming:
                self.earlier_samples = count_new_samples(self.path, 0)[0]

        if self._start_run(self.duration):
            self.set_interval(0.5, self._poll)
            self._poll()

    # ---------- one gputaskman record run ---------- #

    def _start_run(self, duration: float | None) -> bool:
        args = commands.record_args(self.path, self.gpu, self.interval, duration, self.system)
        try:
            # record prints its own start/stop lines; this screen replaces them
            self.proc = self.runner.start(*args, stdout=subprocess.DEVNULL, stderr=self.stderr)
        except OSError as exc:
            self._fail(f"Could not start gputaskman record: {exc}")
            return False

        self.state = RECORDING
        self.end_requested_at = None
        self.run_started = time.monotonic()
        return True

    def _end_run(self) -> None:
        """Ask the running record to finish, for a pause or a stop"""
        now = time.monotonic()
        self.end_requested_at = now
        self.recorded += now - self.run_started

        if sys.platform == "win32":
            # No Ctrl+C for a background process on Windows. record flushes
            # every sample as it goes, so ending it keeps all finished ones.
            self.proc.terminate()
        else:
            # Same as Ctrl+C: record finishes cleanly
            self.proc.send_signal(signal.SIGINT)

    def recorded_time(self) -> float:
        if self.state == RECORDING:
            return self.recorded + time.monotonic() - self.run_started
        return self.recorded

    # ---------- polling ---------- #

    def _poll(self) -> None:
        if self.finished or self.proc is None:
            return

        new, self.pos = count_new_samples(self.path, self.pos)
        if new:
            self.samples += new
            self.query_one("#record-progress", ProgressBar).advance(new)

        self._show_status()

        if self.state == PAUSED:
            return

        if self.proc.poll() is None:
            if self.end_requested_at and time.monotonic() - self.end_requested_at > STOP_GRACE:
                self.proc.kill()
            return

        # The record run has ended: by a pause, a stop, or its duration running out
        if self.state == PAUSING:
            self._paused()
        else:
            self._done()

    def _show_status(self) -> None:
        state = {
            RECORDING: "Recording",
            PAUSING: "Pausing (finishing the current sample)",
            PAUSED: f"Paused for {elapsed_text(time.monotonic() - self.paused_at)}",
            STOPPING: "Stopping (finishing the current sample)",
        }.get(self.state, "")
        line = f"{state}   samples: {self.samples}   recorded: {elapsed_text(self.recorded_time())}"
        if self.pauses:
            line += f"   pauses: {self.pauses}"
        if self.earlier_samples:
            line += f"\n{self.earlier_samples} sample(s) were already in the file"
        self.query_one("#record-status", Static).update(Text(
            line, style="bold yellow" if self.state in (PAUSING, PAUSED) else ""
        ))

    # ---------- pause / resume ---------- #

    @on(Button.Pressed, "#pause")
    def action_toggle_pause(self) -> None:
        if self.state == RECORDING and self.proc is not None:
            self.state = PAUSING
            self.pauses += 1
            self._end_run()
            self._set_pause_button("Pausing...", disabled=True)
            self._show_status()
        elif self.state == PAUSED:
            self._resume()

    def _paused(self) -> None:
        self.state = PAUSED
        self.paused_at = time.monotonic()
        self.sub_title = "Recording paused"
        self._set_pause_button("Resume", variant="success")
        self._show_status()

    def _resume(self) -> None:
        left = remaining_duration(self.duration, self.recorded)
        if left is not None and left < min(self.interval, 1.0):
            # Nothing left of a timed recording: it is complete
            self._done()
            return

        if self._start_run(left):
            self.sub_title = "Recording"
            self._set_pause_button("Pause", variant="warning")
            self._show_status()

    def _set_pause_button(self, label: str, variant: str | None = None, disabled: bool = False) -> None:
        button = self.query_one("#pause", Button)
        button.label = label
        if variant:
            button.variant = variant
        button.disabled = disabled

    # ---------- stop ---------- #

    @on(Button.Pressed, "#stop")
    def action_stop(self) -> None:
        if self.finished:
            self.dismiss()  # the button reads "Back to menu" by now
            return
        if self.proc is None or self.state == STOPPING:
            return

        self.query_one("#stop", Button).disabled = True
        self.query_one("#pause", Button).disabled = True

        if self.state == PAUSED:
            self._done()  # nothing running: finish now
        elif self.state == PAUSING:
            self.state = STOPPING  # already ending: finish once it has
        else:
            self.state = STOPPING
            self._end_run()

    def _done(self) -> None:
        asked_to_end = self.end_requested_at is not None
        self.state = FINISHED
        new, self.pos = count_new_samples(self.path, self.pos)
        self.samples += new

        if self.proc.returncode != 0 and not asked_to_end:
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
        if self.pauses:
            intro += f" (paused {self.pauses} time(s); nothing was sampled while paused)"
        if self.earlier_samples:
            intro += f"\n{self.earlier_samples + self.samples} sample(s) in the file in all"
        intro += "\nTo add to it later: Resume Recording (e) on the menu."

        if runner.supports("summary"):
            self.app.switch_screen(OutputScreen("Recording summary", summary, intro=intro))
        else:
            self.app.switch_screen(OutputScreen(
                "Recording saved",
                lambda _w: Result(0, f"{intro}\n\nThis gputaskman has no summary command yet; "
                                     "update it to summarize recordings.", ""),
            ))

    def _fail(self, message: str) -> None:
        self.state = FINISHED
        self.query_one("#record-status", Static).update(Text(message, style="bold red"))
        self.query_one("#pause", Button).display = False
        button = self.query_one("#stop", Button)
        button.label = "Back to menu"
        button.variant = "default"
        button.disabled = False

    def on_unmount(self) -> None:
        # Leaving the app mid-recording: don't leave record running unseen
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
        self.stderr.close()
