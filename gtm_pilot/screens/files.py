"""Pick a recording or snapshot: recent files from the sessions folder, or
type a path with autocomplete.

While the path box is empty the list shows recent files. Once you type, it
shows what matches: folders first, then files of the right type. Tab or →
takes the grey suggestion, ↓ moves into the list, and choosing a folder
opens it so you can keep typing.
"""

from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from ..pathcomplete import Match, PathSuggester, complete, matches, separator, suffixes_for
from ..sessions import describe, recent_files


class PathInput(Input):
    """Input where Tab completes the path instead of moving focus."""

    BINDINGS = [
        Binding("tab", "complete", "Complete", show=False),
        Binding("down", "into_list", "Matches", show=False),
    ]

    def __init__(self, base: Path, suffixes: tuple[str, ...], **kwargs):
        # Folder selection updates the path and returns focus here. Keep the
        # cursor at the end so typing continues the path instead of replacing it.
        kwargs.setdefault("select_on_focus", False)
        super().__init__(suggester=PathSuggester(base, suffixes), **kwargs)
        self.base = base
        self.suffixes = suffixes

    def action_complete(self) -> None:
        # Take the grey suggestion if one is showing, else the shared start
        # of all matches; with nothing to add, Tab moves on as usual
        new = self._suggestion or complete(self.value, self.base, self.suffixes)
        if new and new != self.value:
            self.value = new
            self.cursor_position = len(new)
        else:
            self.screen.focus_next()

    def action_into_list(self) -> None:
        lists = self.screen.query("#files")
        if lists and lists.first().display and lists.first().option_count:
            lists.first().focus()


class FilePicker(ModalScreen[Path | None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, title: str, folder: Path, pattern: str):
        super().__init__()
        self.picker_title = title
        self.folder = folder
        self.pattern = pattern
        self.suffixes = suffixes_for(pattern)
        self.recent = recent_files(folder, pattern)
        # What the list currently shows, by option index
        self.shown: list[Match] = []

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog wide"):
            yield Label(self.picker_title, classes="dialog-title")
            yield Label("", id="list-label", classes="field-label")
            yield OptionList(id="files")
            yield Static("", id="list-empty", classes="hint")
            yield Label("Or type a path  (Tab completes, ↓ goes to the list)", classes="field-label")
            yield PathInput(self.folder, self.suffixes, placeholder=str(self.folder / self.pattern), id="path")
            yield Static("", id="picker-error", classes="error")

            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Open", id="open", variant="primary")

    def on_mount(self) -> None:
        self._fill("")
        if self.shown:
            self.query_one("#files", OptionList).focus()
        else:
            self.query_one("#path", Input).focus()

    # ---------- the list ---------- #

    def _fill(self, typed: str) -> None:
        """Recent files when nothing is typed, else matches for the typed path"""
        options = self.query_one("#files", OptionList)
        label = self.query_one("#list-label", Label)
        empty = self.query_one("#list-empty", Static)

        if typed.strip():
            self.shown = matches(typed.strip().strip('"'), self.folder, self.suffixes)
            label.update("Matches")
            prompts = [self._match_prompt(m) for m in self.shown]
            empty.update(Text(f"Nothing here matches (showing folders and {self.pattern} files)."))
        else:
            self.shown = [Match(p, p.name, False, str(p)) for p in self.recent]
            label.update(Text(f"Recent in {self.folder}"))
            prompts = [Text(describe(p)) for p in self.recent]
            empty.update(Text(f"No {self.pattern} files in {self.folder} yet. Type a path below."))

        options.clear_options()
        options.add_options([Option(prompt, id=str(i)) for i, prompt in enumerate(prompts)])
        if self.shown:
            options.highlighted = 0
        options.display = bool(self.shown)
        empty.display = not self.shown

    @staticmethod
    def _match_prompt(m: Match) -> Text:
        if m.is_dir:
            return Text(m.name + separator(m.text), style="bold")
        try:
            return Text(describe(m.path))
        except OSError:
            return Text(m.name)

    @on(Input.Changed, "#path")
    def _typed(self, event: Input.Changed) -> None:
        self.query_one("#picker-error", Static).update("")
        self._fill(event.value)

    @on(OptionList.OptionSelected, "#files")
    def _picked(self, event: OptionList.OptionSelected) -> None:
        self._choose(self.shown[int(event.option_id)])

    def _choose(self, m: Match) -> None:
        if not m.is_dir:
            self.dismiss(m.path)
            return

        # A folder: update the path, then leave the matches list focused so
        # arrow keys can immediately choose the next entry.
        box = self.query_one("#path", Input)
        box.value = m.text
        box.cursor_position = len(m.text)
        files = self.query_one("#files", OptionList)
        if files.display and files.option_count:
            files.focus()
        else:
            box.focus()

    def on_key(self, event: events.Key) -> None:
        """Start editing the path directly when the matches list has focus."""
        files = self.query_one("#files", OptionList)
        if self.app.focused is not files or not event.character or not event.character.isprintable():
            return

        box = self.query_one("#path", Input)
        box.focus()
        box.insert_text_at_cursor(event.character)
        event.stop()

    # ---------- the path box ---------- #

    @on(Button.Pressed, "#open")
    @on(Input.Submitted, "#path")
    def _open(self) -> None:
        text = self.query_one("#path", Input).value.strip().strip('"')

        if not text:
            # Nothing typed: take the highlighted recent file
            highlighted = self.query_one("#files", OptionList).highlighted
            if self.shown and highlighted is not None:
                self._choose(self.shown[highlighted])
            else:
                self._error("Pick a file or type a path")
            return

        path = Path(text).expanduser()
        if not path.is_absolute():
            path = self.folder / path

        if path.is_file():
            self.dismiss(path)
        elif path.is_dir():
            self._choose(Match(path, path.name, True, text.rstrip("/\\") + separator(text)))
        elif len(self.shown) == 1:
            # Enter on a unique partial name takes it
            self._choose(self.shown[0])
        else:
            self._error(f"Not a file: {path}")

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        self.dismiss(None)

    def _error(self, message: str) -> None:
        self.query_one("#picker-error", Static).update(Text(message))
