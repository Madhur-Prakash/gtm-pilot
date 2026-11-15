"""The main menu: GPUs at the top, one line per action below."""

from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, OptionList, Static
from textual.widgets.option_list import Option

from ..gputaskman import Gpu


@dataclass(frozen=True)
class Action:
    id: str
    title: str
    description: str
    # One-key shortcut on the menu, shown in the footer and beside the title
    key: str
    # Footer label (shorter than the title)
    short: str
    # gputaskman subcommand this action needs, if any (older versions lack some)
    needs: str | None = None


ACTIONS = [
    Action("live", "Live View", "Full-screen GPU monitor (q to come back)", "l", "Live"),
    Action("snapshot", "Snapshot", "Current GPU use, once", "s", "Snapshot"),
    Action("record", "Record Session", "Log GPU use to a file over time", "n", "Record",
           needs="record"),
    Action("summary", "Summarize Recording", "Averages, peaks and top processes of a recording", "u", "Summary",
           needs="summary"),
    Action("replay", "Replay Recording", "Play a recording back offline (q to come back)", "p", "Replay",
           needs="replay"),
    Action("measure", "Measure a Change", "Snapshot before and after you load something, then diff", "m",
           "Measure", needs="diff"),
    Action("compare", "Compare Snapshots", "Diff two snapshots saved earlier", "c", "Compare",
           needs="diff"),
    Action("gpus", "List GPUs", "GPU index numbers and adapter details", "g", "GPUs"),
    Action("folder", "Open Sessions Folder", "Where recordings and snapshots are saved", "o", "Folder"),
    Action("quit", "Quit", "Leave gtm-pilot", "q", "Quit"),
]

TITLE_WIDTH = max(len(a.title) for a in ACTIONS) + 4


def action_prompt(action: Action, available: bool) -> Text:
    text = Text(f"[{action.key}] ", style="bold cyan" if available else "dim")
    text.append(action.title.ljust(TITLE_WIDTH), style="bold")
    if available:
        text.append(action.description)
    else:
        text.append(f"needs a newer gputaskman (no '{action.needs}' command)", style="dim italic")
    return text


class MenuScreen(Screen):
    # One key per action (also shown as [key] in the list), then the extras
    BINDINGS = [
        *(Binding(a.key, f"pick('{a.id}')", a.short) for a in ACTIONS if a.id != "quit"),
        Binding("r", "refresh_gpus", "Refresh GPUs"),
        Binding("question_mark", "keys", "Keys"),
        Binding("q", "app.quit", "Quit"),
        Binding("escape", "app.quit", "Quit", show=False),
    ]

    def __init__(self, subcommands: set[str]):
        super().__init__()
        self.subcommands = subcommands

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Finding GPUs...", id="gpus")
        yield OptionList(
            *(
                Option(
                    action_prompt(a, a.needs is None or a.needs in self.subcommands),
                    id=a.id,
                    disabled=bool(a.needs and a.needs not in self.subcommands),
                )
                for a in ACTIONS
            ),
            id="actions",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#actions", OptionList).focus()

    def show_gpus(self, gpus: list[Gpu] | None, sessions: str, exe: str, error: str | None = None) -> None:
        panel = Text()
        if gpus is None:
            panel.append("Finding GPUs...", style="dim")
        elif error:
            # The last line of the error is usually the useful one
            panel.append("gputaskman failed: ", style="bold red")
            panel.append(error.strip().splitlines()[-1], style="red")
        elif not gpus:
            panel.append("No GPUs found by gputaskman --list-gpus", style="bold red")
        else:
            for i, gpu in enumerate(gpus):
                if i:
                    panel.append("\n")
                panel.append(f"{gpu.index}  ", style="bold")
                panel.append(gpu.name)
        panel.append(f"\nSessions: {sessions}", style="dim")
        panel.append(f"\ngputaskman: {exe}", style="dim")
        self.query_one("#gpus", Static).update(panel)

    @on(OptionList.OptionSelected, "#actions")
    def _picked(self, event: OptionList.OptionSelected) -> None:
        self.app.run_action_by_id(event.option_id)  # type: ignore[attr-defined]

    def action_pick(self, action_id: str) -> None:
        """A shortcut key: same as choosing the line, unless it is greyed out"""
        actions = self.query_one("#actions", OptionList)
        option = actions.get_option(action_id)
        if option.disabled:
            needs = next(a.needs for a in ACTIONS if a.id == action_id)
            self.notify(f"Needs a newer gputaskman (no '{needs}' command)", severity="warning")
            return

        actions.highlighted = actions.get_option_index(action_id)
        self.app.run_action_by_id(action_id)  # type: ignore[attr-defined]

    def action_keys(self) -> None:
        from .keys import KeysScreen  # keys.py imports ACTIONS from here

        self.app.push_screen(KeysScreen())

    def action_refresh_gpus(self) -> None:
        self.app.load_gpus()  # type: ignore[attr-defined]
