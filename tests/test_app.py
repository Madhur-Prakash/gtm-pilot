"""UI tests with a fake gputaskman: no GPU or real gputaskman needed."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textual.widgets import Button, Input, OptionList, Static

from gtm_pilot.app import PilotApp
from gtm_pilot.gputaskman import Gpu, Result
from gtm_pilot.screens.forms import OptionsForm
from gtm_pilot.screens.menu import MenuScreen
from gtm_pilot.screens.missing import MissingScreen
from gtm_pilot.screens.output import OutputScreen


class FakeGputaskman:
    exe = "fake-gputaskman"

    def __init__(self, subcommands=("diff", "record", "summary", "replay")):
        self.subcommands = set(subcommands)
        self.calls = []

    def supports(self, name):
        return name in self.subcommands

    def list_gpus(self):
        return [Gpu(0, "Test GPU A", "NVIDIA"), Gpu(1, "Test GPU B", "Intel")]

    def capture(self, *args, columns=None, timeout=None):
        self.calls.append(list(map(str, args)))
        if args and args[0] == "--list-gpus":
            return Result(0, "0: Test GPU A (NVIDIA)\n1: Test GPU B (Intel)\n", "")
        if args and args[0] == "--json":
            return Result(0, '{"gpu": "Test GPU A"}', "")
        return Result(0, f"output of {' '.join(map(str, args))}", "")

    def run_attached(self, *args):
        self.calls.append(list(map(str, args)))
        return 0


class AppTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sessions = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    async def test_menu_lists_gpus(self):
        app = PilotApp(FakeGputaskman(), self.sessions)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            panel = str(app.screen.query_one("#gpus", Static).render())
            self.assertIn("Test GPU A", panel)
            self.assertIn("Test GPU B", panel)

    async def test_missing_subcommands_are_disabled(self):
        app = PilotApp(FakeGputaskman(subcommands=("diff", "record")), self.sessions)
        async with app.run_test() as pilot:
            await pilot.pause()
            actions = app.screen.query_one("#actions", OptionList)
            self.assertTrue(actions.get_option("summary").disabled)
            self.assertTrue(actions.get_option("replay").disabled)
            self.assertFalse(actions.get_option("record").disabled)

    async def test_list_gpus_shows_output(self):
        runner = FakeGputaskman()
        app = PilotApp(runner, self.sessions)
        async with app.run_test() as pilot:
            await pilot.pause()
            app.run_action_by_id("gpus")
            await pilot.pause()
            self.assertIsInstance(app.screen, OutputScreen)
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertIn(["--list-gpus"], runner.calls)

    async def test_snapshot_form_runs_once_on_chosen_gpu(self):
        runner = FakeGputaskman()
        app = PilotApp(runner, self.sessions)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            app.run_action_by_id("snapshot")
            await pilot.pause()
            self.assertIsInstance(app.screen, OptionsForm)
            await pilot.click("#submit")
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertIn(["--once", "--gpu", "0"], runner.calls)

    async def test_missing_gputaskman_shows_error_screen(self):
        app = PilotApp(None, self.sessions)
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIsInstance(app.screen, MissingScreen)
            message = str(app.screen.query_one("#missing-message", Static).render())
            self.assertIn("gputaskman was not found", message)
            self.assertIn("uv tool install gputaskman", message)

    async def test_missing_explicit_path_is_named(self):
        app = PilotApp(None, self.sessions, explicit_exe=r"D:\tools\gputaskman.exe")
        async with app.run_test() as pilot:
            await pilot.pause()
            message = str(app.screen.query_one("#missing-message", Static).render())
            self.assertIn(r"D:\tools\gputaskman.exe", message)

    async def test_retry_opens_menu_once_found(self):
        app = PilotApp(None, self.sessions)
        async with app.run_test() as pilot:
            await pilot.pause()
            fake = FakeGputaskman()
            with mock.patch("gtm_pilot.app.find_gputaskman", return_value="fake-gputaskman"), \
                 mock.patch("gtm_pilot.app.Gputaskman", return_value=fake):
                self.assertTrue(app.retry_find())
            await pilot.pause()
            self.assertIsInstance(app.screen, MenuScreen)

    async def test_retry_stays_when_still_missing(self):
        app = PilotApp(None, self.sessions)
        async with app.run_test() as pilot:
            await pilot.pause()
            with mock.patch("gtm_pilot.app.find_gputaskman", return_value=None):
                self.assertFalse(app.retry_find())
            self.assertIsInstance(app.screen, MissingScreen)

    async def test_failing_gputaskman_explains_in_panel(self):
        runner = FakeGputaskman()
        runner.capture = lambda *a, **k: Result(1, "", "Traceback ...\nOSError: driver went away")
        app = PilotApp(runner, self.sessions)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            panel = str(app.screen.query_one("#gpus", Static).render())
            self.assertIn("driver went away", panel)

    # ---------- short and narrow terminals ---------- #

    async def _open_record_form(self, pilot, app):
        await app.workers.wait_for_complete()
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        self.assertIsInstance(app.screen, OptionsForm)

    async def test_record_form_keeps_its_buttons_on_a_short_terminal(self):
        """The dialog is taller than a 30-row terminal: it must still fit"""
        for height in (20, 24, 30, 40):
            app = PilotApp(FakeGputaskman(), self.sessions)
            async with app.run_test(size=(100, height)) as pilot:
                await self._open_record_form(pilot, app)
                screen = app.screen
                for button in screen.query(Button):
                    self.assertTrue(
                        screen.region.contains_region(button.region),
                        f"{button.id} is off a {height}-row screen: {button.region}",
                    )

    async def test_file_name_can_be_reached_and_typed_on_a_short_terminal(self):
        app = PilotApp(FakeGputaskman(), self.sessions)
        async with app.run_test(size=(100, 30)) as pilot:
            await self._open_record_form(pilot, app)
            screen = app.screen
            box = screen.query_one("#field-name", Input)

            for _ in range(10):  # tab round the fields until the name box has focus
                if app.focused is box:
                    break
                await pilot.press("tab")
                await pilot.pause()

            self.assertIs(app.focused, box)
            await pilot.pause()
            self.assertTrue(screen.region.contains_region(box.region), box.region)

            box.value = ""
            await pilot.press("r", "u", "n")
            self.assertEqual(box.value, "run")

    async def test_narrow_terminal_stacks_the_dialog_buttons(self):
        app = PilotApp(FakeGputaskman(), self.sessions)
        async with app.run_test(size=(40, 30)) as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            await pilot.press("m")  # Measure: its submit button is a long one
            await pilot.pause()
            screen = app.screen
            for button in screen.query(Button):
                self.assertTrue(
                    screen.region.contains_region(button.region),
                    f"{button.id} is off a 40-column screen: {button.region}",
                )

    async def test_missing_screen_scrolls_on_a_short_terminal(self):
        app = PilotApp(None, self.sessions)
        async with app.run_test(size=(100, 18)) as pilot:
            await pilot.pause()
            screen = app.screen
            box = screen.query_one("#missing-box")
            self.assertTrue(screen.region.contains_region(box.region), box.region)
            self.assertGreater(box.max_scroll_y, 0)  # the rest is a scroll away

    async def test_live_view_hands_over_the_terminal(self):
        runner = FakeGputaskman()
        app = PilotApp(runner, self.sessions)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            app._attached(["-i", "1"])
            self.assertIn(["-i", "1"], runner.calls)


if __name__ == "__main__":
    unittest.main()
