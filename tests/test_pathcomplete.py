import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

from gtm_pilot import pathcomplete as pc


class PathCompleteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        (self.base / "college_model_work.jsonl").write_text("{}\n")
        (self.base / "college_notes.txt").write_text("")
        (self.base / "Coll-runs").mkdir()
        (self.base / "Coll-runs" / "night.jsonl").write_text("{}\n")
        (self.base / ".hidden.jsonl").write_text("{}\n")
        (self.base / "snap_before.json").write_text("{}")

    def tearDown(self):
        self.tmp.cleanup()

    def names(self, value, suffixes=(".jsonl",)):
        return [m.name for m in pc.matches(value, self.base, suffixes)]

    def test_folders_first_then_matching_files_ignoring_case(self):
        self.assertEqual(self.names("coll"), ["Coll-runs", "college_model_work.jsonl"])

    def test_other_file_types_hidden(self):
        self.assertNotIn("college_notes.txt", self.names("coll"))
        self.assertNotIn("snap_before.json", self.names(""))
        self.assertEqual(self.names("snap", (".json",)), ["snap_before.json"])

    def test_hidden_only_when_asked(self):
        self.assertNotIn(".hidden.jsonl", self.names(""))
        self.assertEqual(self.names(".h"), [".hidden.jsonl"])

    def test_folder_text_ends_with_separator_in_users_style(self):
        folder = pc.matches("Coll-r", self.base, (".jsonl",))[0]
        self.assertTrue(folder.is_dir)
        self.assertEqual(folder.text, "Coll-runs" + pc.separator("Coll-r"))

        absolute = str(self.base).replace("\\", "/") + "/Coll-r"
        self.assertEqual(pc.matches(absolute, self.base, (".jsonl",))[0].text,
                         absolute[:-len("Coll-r")] + "Coll-runs/")

    def test_inside_a_folder(self):
        self.assertEqual(self.names("Coll-runs/"), ["night.jsonl"])

    @unittest.skipUnless(sys.platform == "win32", "backslashes and case-insensitive folders are Windows")
    def test_inside_a_folder_windows_style(self):
        self.assertEqual(self.names("coll-runs\\n"), ["night.jsonl"])

    def test_missing_folder_has_no_matches(self):
        self.assertEqual(self.names("no-such-folder/x"), [])

    def test_complete_unique_and_shared_prefix(self):
        self.assertEqual(pc.complete("college_m", self.base, (".jsonl",)), "college_model_work.jsonl")
        # "Coll-runs" and "college_model_work.jsonl" share only "coll"
        self.assertIsNone(pc.complete("coll", self.base, (".jsonl",)))
        self.assertIsNone(pc.complete("zzz", self.base, (".jsonl",)))

    def test_complete_keeps_real_case(self):
        self.assertEqual(pc.complete("coll-", self.base, (".jsonl",)), "Coll-runs" + pc.separator("coll-"))

    def test_suffixes_for(self):
        self.assertEqual(pc.suffixes_for("*.jsonl"), (".jsonl",))
        self.assertEqual(pc.suffixes_for("*.json"), (".json",))
        self.assertEqual(pc.suffixes_for("*"), ())
        self.assertEqual(pc.suffixes_for("*.js*"), ())

    def test_suggester(self):
        suggester = pc.PathSuggester(self.base, (".jsonl",))
        self.assertEqual(asyncio.run(suggester.get_suggestion("college")), "college_model_work.jsonl")
        self.assertIsNone(asyncio.run(suggester.get_suggestion("")))


if __name__ == "__main__":
    unittest.main()
