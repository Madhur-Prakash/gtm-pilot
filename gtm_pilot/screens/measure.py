"""Measure a change: a --json snapshot, a pause while you load something,
a second snapshot, then `gputaskman diff` on the two."""

from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, LoadingIndicator, Static

from .. import commands
from ..gputaskman import Gputaskman, Result
from .output import render


def save_snapshot(runner: Gputaskman, gpu: int, path: Path) -> Result:
    """Take a --json snapshot and write it to path"""
    result = runner.capture(*commands.json_snapshot_args(gpu))
    if result.ok:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.stdout, encoding="utf-8")
    return result


class MeasureScreen(Screen):
    BINDINGS = [Binding("escape", "back", "Back to menu")]

    def __init__(self, runner: Gputaskman, gpu: int, before: Path, after: Path):
        super().__init__()
        self.runner = runner
        self.gpu = gpu
        self.before = before
        self.after = after
        self.busy = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="measure-box"):
            yield Static(id="measure-status")
            yield LoadingIndicator(id="measure-loading")
            with Horizontal(classes="buttons", id="measure-buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Take the 'after' snapshot", id="continue", variant="primary")
        with VerticalScroll(id="output-scroll"):
            yield Static("", id="output-body")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = "Measure a change"
        self.query_one("#measure-buttons").display = False
        self.query_one("#output-scroll").display = False
        self._status(f"Taking the 'before' snapshot of GPU {self.gpu}...")
        self._take_before()

    def _status(self, message: str, style: str = "") -> None:
        self.query_one("#measure-status", Static).update(Text(message, style=style))

    def _loading(self, on: bool) -> None:
        self.busy = on
        self.query_one("#measure-loading").display = on

    # ---------- step 1: before ---------- #

    @work(thread=True, exclusive=True)
    def _take_before(self) -> None:
        self.app.call_from_thread(self._loading, True)
        result = save_snapshot(self.runner, self.gpu, self.before)
        self.app.call_from_thread(self._before_done, result)

    def _before_done(self, result: Result) -> None:
        self._loading(False)
        if not result.ok:
            self._status(result.text.strip() or "The 'before' snapshot failed", "bold red")
            return

        self._status(
            f"Saved {self.before}\n\n"
            "Now load your model or start your script. When it is ready, "
            "take the 'after' snapshot."
        )
        self.query_one("#measure-buttons").display = True
        self.query_one("#continue", Button).focus()

    # ---------- step 2: after + diff ---------- #

    @on(Button.Pressed, "#continue")
    def _continue(self) -> None:
        if self.busy:
            return
        self.query_one("#measure-buttons").display = False
        self._status(f"Taking the 'after' snapshot of GPU {self.gpu}...")
        self._take_after()

    @work(thread=True, exclusive=True)
    def _take_after(self) -> None:
        self.app.call_from_thread(self._loading, True)
        after = save_snapshot(self.runner, self.gpu, self.after)
        if not after.ok:
            self.app.call_from_thread(self._after_done, after, None)
            return

        width = max(60, self.app.size.width - 4)
        diff = self.runner.capture(*commands.diff_args(self.before, self.after), columns=width)
        self.app.call_from_thread(self._after_done, after, diff)

    def _after_done(self, after: Result, diff: Result | None) -> None:
        self._loading(False)
        if diff is None:
            self._status(after.text.strip() or "The 'after' snapshot failed", "bold red")
            return

        self._status(f"Saved {self.before.name} and {self.after.name} in {self.after.parent}")
        scroll = self.query_one("#output-scroll", VerticalScroll)
        scroll.display = True
        self.query_one("#output-body", Static).update(render(diff))
        scroll.focus()

    # ---------- leaving ---------- #

    @on(Button.Pressed, "#cancel")
    def action_back(self) -> None:
        self.dismiss()
