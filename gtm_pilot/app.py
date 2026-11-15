"""The gtm-pilot Textual app: wires each menu action to a gputaskman command."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import App

from . import __version__, commands
from .gputaskman import Gpu, Gputaskman, Result, find_gputaskman, parse_gpus
from .screens.files import FilePicker
from .screens.forms import GpuField, OptionsForm, SecondsField, TextField, ToggleField
from .screens.measure import MeasureScreen
from .screens.menu import MenuScreen
from .screens.missing import MissingScreen
from .screens.output import OutputScreen
from .screens.record import RecordScreen
from .sessions import (
    default_recording_name,
    file_label,
    is_plain_name,
    open_folder,
    recording_path,
    snapshot_paths,
)


class PilotApp(App):
    TITLE = "gtm-pilot"
    SUB_TITLE = "a guided menu for gputaskman"
    CSS_PATH = "pilot.tcss"

    def __init__(self, runner: Gputaskman | None, sessions: Path, explicit_exe: str | None = None):
        """runner None means gputaskman wasn't found: an error screen explains
        how to install it, and the menu opens once it is found"""
        super().__init__()
        self.runner = runner
        self.sessions = sessions
        self.explicit_exe = explicit_exe
        self.gpus: list[Gpu] = []
        self.menu: MenuScreen | None = None

    # ---------- start-up ---------- #

    def on_mount(self) -> None:
        self.title = f"gtm-pilot {__version__}"
        if self.runner is None:
            self.push_screen(MissingScreen(self.explicit_exe))
        else:
            self._open_menu()

    def _open_menu(self) -> None:
        self.menu = MenuScreen(self.runner.subcommands)
        self.push_screen(self.menu)
        self.load_gpus()

    def retry_find(self) -> bool:
        """From the error screen: look for gputaskman again"""
        exe = find_gputaskman(self.explicit_exe)
        if exe is None:
            return False

        self.runner = Gputaskman(exe)
        self.pop_screen()
        self._open_menu()
        self.notify(f"Found gputaskman: {exe}")
        return True

    @work(thread=True, exclusive=True, group="gpus")
    def load_gpus(self) -> None:
        if self.menu:
            self.call_from_thread(self._show_gpus, None, None)
        result = self.runner.capture("--list-gpus", timeout=60)
        gpus = parse_gpus(result.stdout)
        # gputaskman found but failing (removed, broken install, driver error):
        # say why instead of just "no GPUs"
        error = None if result.ok or gpus else (
            result.text.strip() or f"gputaskman --list-gpus exited with {result.returncode}"
        )
        self.call_from_thread(self._show_gpus, gpus, error)

    def _show_gpus(self, gpus: list[Gpu] | None, error: str | None) -> None:
        if gpus is not None:
            self.gpus = gpus
        if self.menu:
            self.menu.show_gpus(gpus, str(self.sessions), self.runner.exe, error)
        if error:
            self.notify(error, title="gputaskman failed", severity="error", timeout=10)

    # ---------- dispatch ---------- #

    def run_action_by_id(self, action_id: str | None) -> None:
        handler = getattr(self, f"_do_{action_id}", None)
        if handler:
            handler()

    def _form(self, title: str, fields: list, then, submit_label: str = "Start") -> None:
        """Ask for options, then call then(values) unless cancelled"""
        def done(values: dict | None) -> None:
            if values is not None:
                then(values)

        self.push_screen(OptionsForm(title, fields, self.gpus, submit_label), done)

    def _pick(self, title: str, pattern: str, then) -> None:
        def done(path: Path | None) -> None:
            if path is not None:
                then(path)

        self.push_screen(FilePicker(title, self.sessions, pattern), done)

    def _show(self, title: str, args: list[str], intro: str | None = None) -> None:
        """Run a command and show its text output"""
        runner = self.runner

        def job(width: int) -> Result:
            return runner.capture(*args, columns=width)

        self.push_screen(OutputScreen(title, job, intro=intro))

    def _attached(self, args: list[str]) -> None:
        """Hand the terminal to one of gputaskman's own full-screen views"""
        with self.suspend():
            code = self.runner.run_attached(*args)
        if code not in (0, 130):  # 130: left with Ctrl+C
            self.notify(f"gputaskman exited with {code}", severity="error")

    # ---------- actions ---------- #

    def _do_live(self) -> None:
        self._form(
            "Live View",
            [
                GpuField(allow_all=True),
                SecondsField("interval", "Refresh every", commands.REFRESH, default=1.0),
            ],
            lambda v: self._attached(commands.live_args(v["gpu"], v["interval"])),
        )

    def _do_snapshot(self) -> None:
        self._form(
            "Snapshot",
            [GpuField()],
            lambda v: self._show(f"Snapshot of GPU {v['gpu']}", commands.snapshot_args(v["gpu"])),
            submit_label="Take snapshot",
        )

    def _do_record(self) -> None:
        def validate(name: str) -> str | None:
            return None if is_plain_name(name) else "enter a plain file name (no folders or <>:\"/\\|?*)"

        def start(v: dict) -> None:
            path = recording_path(self.sessions, v["name"])
            self.push_screen(RecordScreen(
                self.runner, path, v["gpu"], v["interval"], v["duration"], v["system"],
            ))

        self._form(
            "Record Session",
            [
                GpuField(),
                SecondsField("interval", "Take a sample every", commands.INTERVALS, default=1.0),
                SecondsField("duration", "Record for", commands.DURATIONS, default=None),
                ToggleField("system", "Include system RAM/CPU", default=True),
                TextField(
                    "name", "File name",
                    default=default_recording_name(),
                    placeholder="training-run.jsonl",
                    validate=validate,
                ),
            ],
            start,
            submit_label="Start recording",
        )

    def _do_summary(self) -> None:
        self._pick(
            "Summarize a recording",
            "*.jsonl",
            lambda p: self._show(f"Summary of {p.name}", commands.summary_args(p)),
        )

    def _do_replay(self) -> None:
        self._pick(
            "Replay a recording",
            "*.jsonl",
            lambda p: self._attached(commands.replay_args(p)),
        )

    def _do_measure(self) -> None:
        def start(v: dict) -> None:
            before, after = snapshot_paths(self.sessions, file_label(v["label"]))
            self.push_screen(MeasureScreen(self.runner, v["gpu"], before, after))

        self._form(
            "Measure a Change",
            [
                TextField(
                    "label", "What are you measuring? (names the files)",
                    placeholder="e.g. llama3.1 8b",
                ),
                GpuField(),
            ],
            start,
            submit_label="Take the 'before' snapshot",
        )

    def _do_compare(self) -> None:
        def got_before(before: Path) -> None:
            self._pick(
                f"'After' snapshot (before: {before.name})",
                "*.json",
                lambda after: self._show(
                    f"{before.name} -> {after.name}",
                    commands.diff_args(before, after),
                ),
            )

        self._pick("'Before' snapshot", "*.json", got_before)

    def _do_gpus(self) -> None:
        self._show("GPUs", ["--list-gpus"])

    def _do_folder(self) -> None:
        try:
            open_folder(self.sessions)
        except OSError as exc:
            self.notify(f"Could not open {self.sessions}: {exc}", severity="error")
        else:
            self.notify(f"Opened {self.sessions}")

    def _do_quit(self) -> None:
        self.exit()
