"""A small form dialog: pick a GPU, a number of seconds, a yes/no, some text.

Each action describes its fields; the dialog returns {key: value} or None
when cancelled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Union

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select, Static

from ..gputaskman import Gpu

# Select values are strings or numbers; these stand in for "None" choices
ALL_GPUS = "all-gpus"
UNTIL_STOPPED = "until-stopped"
CUSTOM = "custom"


@dataclass
class GpuField:
    key: str = "gpu"
    label: str = "GPU"
    allow_all: bool = False


@dataclass
class SecondsField:
    key: str
    label: str
    presets: list[tuple[float | None, str]]
    default: float | None = None


@dataclass
class ToggleField:
    key: str
    label: str
    default: bool = True


@dataclass
class TextField:
    key: str
    label: str
    default: str = ""
    placeholder: str = ""
    # Returns an error message, or None when the text is fine
    validate: Callable[[str], str | None] | None = None


Field = Union[GpuField, SecondsField, ToggleField, TextField]


def parse_seconds(text: str) -> float | None:
    """A positive number of seconds, or None"""
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value > 0 else None


class OptionsForm(ModalScreen[dict | None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, title: str, fields: list[Field], gpus: list[Gpu], submit_label: str = "Start"):
        super().__init__()
        self.form_title = title
        self.fields = fields
        self.gpus = gpus
        self.submit_label = submit_label

    # ---------- layout ---------- #

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(self.form_title, classes="dialog-title")
            with VerticalScroll(classes="dialog-body"):
                for f in self.fields:
                    yield from self._compose_field(f)
            yield Static("", id="form-error", classes="error")
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button(self.submit_label, id="submit", variant="primary")

    def _compose_field(self, f: Field) -> ComposeResult:
        if isinstance(f, ToggleField):
            yield Checkbox(f.label, value=f.default, id=f"field-{f.key}")
            return

        yield Label(f.label, classes="field-label")

        if isinstance(f, GpuField):
            yield self._gpu_select(f)

        elif isinstance(f, SecondsField):
            options = [
                (label, UNTIL_STOPPED if seconds is None else seconds)
                for seconds, label in f.presets
            ]
            options.append(("Custom...", CUSTOM))
            default = UNTIL_STOPPED if f.default is None else f.default
            if default not in [value for _, value in options]:
                default = options[0][1]

            yield Select(options, value=default, allow_blank=False, id=f"field-{f.key}")
            yield Input(
                placeholder="Seconds, e.g. 3 or 0.5",
                id=f"field-{f.key}-custom",
                classes="custom-seconds",
            )

        elif isinstance(f, TextField):
            yield Input(value=f.default, placeholder=f.placeholder, id=f"field-{f.key}")

    def _gpu_select(self, f: GpuField) -> Select:
        options: list[tuple[str, object]] = []
        if f.allow_all and len(self.gpus) > 1:
            options.append(("All GPUs", ALL_GPUS))
        options += [(gpu.label, gpu.index) for gpu in self.gpus]

        if not options:
            options = [("0 (gputaskman's default)", 0)]

        return Select(options, value=options[0][1], allow_blank=False, id=f"field-{f.key}")

    def on_mount(self) -> None:
        for custom in self.query(".custom-seconds"):
            custom.display = False

        # Start on the first field so the keyboard works straight away
        for widget in self.query("Select, Input, Checkbox"):
            if widget.display:
                widget.focus()
                break

    # ---------- events ---------- #

    @on(Select.Changed)
    def _toggle_custom(self, event: Select.Changed) -> None:
        if not event.select.id:
            return
        custom = self.query(f"#{event.select.id}-custom")
        if custom:
            box = custom.first(Input)
            box.display = event.value == CUSTOM
            if box.display:
                box.focus()

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#submit")
    @on(Input.Submitted)
    def _submit(self) -> None:
        values: dict = {}

        for f in self.fields:
            value, error = self._read(f)
            if error:
                self.query_one("#form-error", Static).update(error)
                return
            values[f.key] = value

        self.dismiss(values)

    def _read(self, f: Field) -> tuple[object, str | None]:
        if isinstance(f, ToggleField):
            return self.query_one(f"#field-{f.key}", Checkbox).value, None

        if isinstance(f, GpuField):
            value = self.query_one(f"#field-{f.key}", Select).value
            return (None if value == ALL_GPUS else value), None

        if isinstance(f, SecondsField):
            value = self.query_one(f"#field-{f.key}", Select).value
            if value == UNTIL_STOPPED:
                return None, None
            if value != CUSTOM:
                return value, None

            text = self.query_one(f"#field-{f.key}-custom", Input).value
            seconds = parse_seconds(text)
            if seconds is None:
                return None, f"{f.label}: enter a number of seconds above 0"
            return seconds, None

        text = self.query_one(f"#field-{f.key}", Input).value.strip()
        error = f.validate(text) if f.validate else None
        return text, (f"{f.label}: {error}" if error else None)
