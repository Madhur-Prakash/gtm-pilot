"""Shown instead of the menu when gputaskman can't be found."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from ..gputaskman import ENV_EXE
from .fit import FitsTerminal


def missing_message(explicit: str | None) -> Text:
    text = Text()

    if explicit:
        text.append("gputaskman was not found at ", style="bold red")
        text.append(explicit, style="bold")
        text.append("\n\nCheck the --gputaskman path, or leave it out to look on PATH.\n")
    else:
        text.append("gputaskman was not found", style="bold red")
        text.append(
            "\n\ngtm-pilot is a menu for gputaskman, which reads the GPU. "
            "It looked on PATH for gputaskman and gtm, and in ~/.local/bin.\n"
        )

    text.append("\nInstall it with uv tool", style="bold")
    text.append(" (once a release has summary and replay):\n")
    text.append("  uv tool install gputaskman\n", style="cyan")

    text.append("\nOr build it from source", style="bold")
    text.append(" (has the newest commands today):\n")
    text.append("  uv tool install --force git+https://github.com/shanselman/gputaskman\n", style="cyan")

    text.append("\nAlready installed somewhere else? Start gtm-pilot with ", style="dim")
    text.append("--gputaskman PATH", style="cyan")
    text.append(f", or set the {ENV_EXE} environment variable.\n", style="dim")

    text.append("\nInstalled it just now? Press ", style="dim")
    text.append("r", style="bold")
    text.append(" to look again.", style="dim")
    return text


class MissingScreen(FitsTerminal, Screen):
    # The message is long: it scrolls rather than running off a short
    # terminal, where the install commands used to be out of reach
    BODY = "#missing-box"
    BOX = None
    BODY_MAX = 40

    BINDINGS = [
        Binding("r", "retry", "Look again"),
        Binding("q", "app.quit", "Quit"),
        Binding("escape", "app.quit", "Quit", show=False),
    ]

    def __init__(self, explicit: str | None):
        super().__init__()
        self.explicit = explicit

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="missing-box"):
            yield Static(missing_message(self.explicit), id="missing-message")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = "gputaskman not found"
        self.query_one("#missing-box").focus()

    def action_retry(self) -> None:
        if not self.app.retry_find():  # type: ignore[attr-defined]
            self.notify("Still not found. Open a new terminal if you just installed it, "
                        "so PATH is up to date.", severity="warning", timeout=6)
