import os
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from gtm_pilot import sessions

NOW = datetime(2026, 11, 13, 21, 10)


class FileLabelTests(unittest.TestCase):
    def test_spaces_become_dashes(self):
        self.assertEqual(sessions.file_label("Llama 3.1 8B"), "Llama-3.1-8B")

    def test_forbidden_characters_removed(self):
        self.assertEqual(sessions.file_label("  ollama: load  test?? "), "ollama-load-test")
        self.assertEqual(sessions.file_label("a/b\\c"), "a-b-c")

    def test_empty_or_dots_falls_back(self):
        self.assertEqual(sessions.file_label(""), "change")
        self.assertEqual(sessions.file_label("..."), "change")
        self.assertEqual(sessions.file_label("", fallback="x"), "x")

    def test_long_label_is_cut(self):
        self.assertEqual(len(sessions.file_label("x" * 60)), 40)


class NameTests(unittest.TestCase):
    def test_plain_names(self):
        self.assertTrue(sessions.is_plain_name("training run.jsonl"))
        self.assertFalse(sessions.is_plain_name(""))
        self.assertFalse(sessions.is_plain_name("   "))
        self.assertFalse(sessions.is_plain_name("a/b.jsonl"))
        self.assertFalse(sessions.is_plain_name("c:x"))
        self.assertFalse(sessions.is_plain_name(".."))

    def test_recording_path_adds_extension_once(self):
        folder = Path("sessions")
        self.assertEqual(sessions.recording_path(folder, "run"), folder / "run.jsonl")
        self.assertEqual(sessions.recording_path(folder, " run.jsonl "), folder / "run.jsonl")

    def test_default_recording_name_is_readable(self):
        self.assertEqual(sessions.default_recording_name(NOW), "session_2026-11-13_21-10.jsonl")


class SnapshotPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_pair_shares_a_prefix(self):
        before, after = sessions.snapshot_paths(self.folder, "llama3.1-8b", NOW)
        self.assertEqual(before.name, "llama3.1-8b_2026-11-13_21-10_before.json")
        self.assertEqual(after.name, "llama3.1-8b_2026-11-13_21-10_after.json")

    def test_never_overwrites_an_existing_pair(self):
        before, _ = sessions.snapshot_paths(self.folder, "x", NOW)
        before.write_text("{}")
        before2, after2 = sessions.snapshot_paths(self.folder, "x", NOW)
        self.assertEqual(before2.name, "x_2026-11-13_21-10-2_before.json")

        after2.write_text("{}")  # only the 'after' half exists: still taken
        before3, _ = sessions.snapshot_paths(self.folder, "x", NOW)
        self.assertEqual(before3.name, "x_2026-11-13_21-10-3_before.json")


class FolderTests(unittest.TestCase):
    def test_env_overrides_default(self):
        with mock.patch.dict(os.environ, {sessions.ENV_SESSIONS: "~/my-runs"}):
            self.assertEqual(sessions.default_sessions_dir(), Path.home() / "my-runs")

    def test_default_is_in_home(self):
        env = {k: v for k, v in os.environ.items() if k != sessions.ENV_SESSIONS}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(sessions.default_sessions_dir(), Path.home() / "gpu-sessions")

    def test_recent_files_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            old, new = folder / "old.jsonl", folder / "new.jsonl"
            old.write_text("{}\n")
            new.write_text("{}\n")
            past = time.time() - 3600
            os.utime(old, (past, past))
            (folder / "ignored.json").write_text("{}")

            self.assertEqual(sessions.recent_files(folder, "*.jsonl"), [new, old])
            self.assertEqual(sessions.recent_files(folder / "missing", "*.jsonl"), [])


class RecordingSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_round_trip(self):
        run = self.folder / "run.jsonl"
        settings = sessions.RecordingSettings(gpu=1, interval=2.5, system=False)
        sessions.save_recording_settings(self.folder, run, settings)
        self.assertEqual(sessions.load_recording_settings(self.folder, run), settings)
        self.assertIsNone(sessions.load_recording_settings(self.folder, self.folder / "other.jsonl"))

    def test_kept_per_recording(self):
        a, b = self.folder / "a.jsonl", self.folder / "b.jsonl"
        sessions.save_recording_settings(self.folder, a, sessions.RecordingSettings(0, 1.0, True))
        sessions.save_recording_settings(self.folder, b, sessions.RecordingSettings(1, 5.0, False))
        self.assertEqual(sessions.load_recording_settings(self.folder, a).gpu, 0)
        self.assertEqual(sessions.load_recording_settings(self.folder, b).gpu, 1)

    def test_broken_file_is_ignored(self):
        (self.folder / sessions.SETTINGS_FILE).write_text("not json")
        self.assertIsNone(sessions.load_recording_settings(self.folder, self.folder / "a.jsonl"))
        sessions.save_recording_settings(self.folder, self.folder / "a.jsonl", sessions.RecordingSettings(0, 1.0, True))
        self.assertIsNotNone(sessions.load_recording_settings(self.folder, self.folder / "a.jsonl"))

    def test_not_listed_by_the_file_pickers(self):
        sessions.save_recording_settings(self.folder, self.folder / "a.jsonl", sessions.RecordingSettings(0, 1.0, True))
        self.assertEqual(sessions.recent_files(self.folder, "*.json"), [])
        self.assertEqual(sessions.recent_files(self.folder, "*.jsonl"), [])


if __name__ == "__main__":
    unittest.main()
