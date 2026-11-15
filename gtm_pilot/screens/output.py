"""Show the text output of a gputaskman command (snapshot, diff, summary,
GPU list) in a scrollable page."""

from __future__ import annotations

from typing import Callable

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, LoadingIndicator, Static

from ..gputaskman import Result

# A job runs off the UI thread; it gets the pane width and returns the
# command's result, or a list of results for multi-step jobs
Job = Callable[[int], "Result | list[Result]"]


def render(results: Result | list[Result]) -> Text:
    """Command output as Rich text (keeping any colours gputaskman used);
    a failed step shows its error in red"""
    if isinstance(results, Result):
        results = [results]

    out = Text()
    for i, result in enumerate(results):
        if i:
            out.append("\n")
        if result.ok:
            out.append_text(Text.from_ansi(result.text.rstrip()))
        else:
            out.append(result.text.strip() or f"gputaskman exited with {result.returncode}", style="bold red")
    return out


class OutputScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back to menu"),
        Binding("q", "back", "Back", show=False),
        Binding("enter", "back", "Back", show=False),
    ]

    def __init__(self, title: str, job: Job, intro: str | None = None):
        super().__init__()
        self.page_title = title
        self.job = job
        self.intro = intro

    def compose(self) -> ComposeResult:
        yield Header()
        if self.intro:
            yield Static(self.intro, classes="intro")
        yield LoadingIndicator(id="loading")
        with VerticalScroll(id="output-scroll"):
            yield Static("", id="output-body")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self.page_title
        self.query_one("#output-scroll").display = False
        self._run()

    @work(thread=True, exclusive=True)
    def _run(self) -> None:
        width = max(60, self.app.size.width - 4)
        try:
            results = self.job(width)
            text = render(results)
        except Exception as exc:  # show it rather than crash the app
            text = Text(f"{type(exc).__name__}: {exc}", style="bold red")
        self.app.call_from_thread(self._show, text)

    def _show(self, text: Text) -> None:
        self.query_one("#loading").display = False
        scroll = self.query_one("#output-scroll", VerticalScroll)
        scroll.display = True
        self.query_one("#output-body", Static).update(text)
        scroll.focus()

    def action_back(self) -> None:
        self.dismiss()
