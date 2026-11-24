"""Every key gtm-pilot understands, on one page (? on the menu)."""

from __future__ import annotations

from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, Static

from .fit import FitsTerminal
from .menu import ACTIONS


def keys_table() -> Table:
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()

    def section(title: str) -> None:
        if table.row_count:
            table.add_row("", "")
        table.add_row(Text(title, style="bold"), "")

    section("Menu")
    for a in ACTIONS:
        table.add_row(a.key, a.title)
    table.add_row("r", "Refresh the GPU list")
    table.add_row("↑ ↓  Enter", "Move and choose")
    table.add_row("?", "This page")

    section("Forms")
    table.add_row("Tab / Shift+Tab", "Next / previous field")
    table.add_row("Enter", "Start")
    table.add_row("Esc", "Cancel")

    section("Picking a file")
    table.add_row("Tab or →", "Complete the path you're typing")
    table.add_row("↓", "From the path box into the list")
    table.add_row("Enter", "Open the file, or go into the folder")

    section("Recording")
    table.add_row("p or Space", "Pause / resume (nothing is sampled while paused)")
    table.add_row("s or Esc", "Stop (every finished sample is kept)")

    section("Output pages")
    table.add_row("↑ ↓  PgUp PgDn", "Scroll")
    table.add_row("Esc, q or Enter", "Back to the menu")

    section("Live View and Replay (gputaskman's own screens)")
    table.add_row("q", "Back to gtm-pilot")
    table.add_row("?", "gputaskman's help for its keys")

    section("Anywhere")
    table.add_row("Ctrl+P", "Command palette (themes and more)")
    table.add_row("Ctrl+Q", "Quit")
    return table


class KeysScreen(FitsTerminal, ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("question_mark", "dismiss", "Close", show=False),
        Binding("q", "dismiss", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog wide"):
            yield Label("Keys", classes="dialog-title")
            with VerticalScroll(classes="dialog-body"):
                yield Static(keys_table())
            yield Static("Esc closes this page.", classes="hint")
