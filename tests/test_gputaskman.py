import os
import unittest
from unittest import mock

from gtm_pilot import gputaskman as g

LIST_GPUS = """\
TCC discovery: NVML TCC discovery succeeded; no TCC GPUs found.
0: NVIDIA GeForce RTX 4060 Laptop GPU (NVIDIA, LUID 0x00000000000147b4)
1: Intel(R) UHD Graphics (Intel, LUID 0x0000000000014389)
"""

HELP = """\
usage: gputaskman [-h] [--once] [--json] [--gpu GPU] [--list-gpus]

gputaskman diff BEFORE.json AFTER.json compares two --json snapshots;
gputaskman record -o FILE appends one --json snapshot per interval to FILE;
gputaskman summary FILE summarizes a record file; gputaskman replay FILE plays
a recording back offline.
"""


class ParseTests(unittest.TestCase):
    def test_gpus_skip_notes_and_split_details(self):
        gpus = g.parse_gpus(LIST_GPUS)
        self.assertEqual([gpu.index for gpu in gpus], [0, 1])
        self.assertEqual(gpus[0].name, "NVIDIA GeForce RTX 4060 Laptop GPU")
        self.assertEqual(gpus[0].details, "NVIDIA, LUID 0x00000000000147b4")
        self.assertEqual(gpus[1].name, "Intel(R) UHD Graphics")
        self.assertEqual(gpus[1].label, "1: Intel(R) UHD Graphics")

    def test_gpu_without_details(self):
        self.assertEqual(g.parse_gpus("2: Some GPU"), [g.Gpu(2, "Some GPU", "")])

    def test_subcommands_from_help(self):
        self.assertEqual(g.parse_subcommands(HELP), {"diff", "record", "summary", "replay"})

    def test_older_help_lacks_newer_subcommands(self):
        old = "gputaskman diff BEFORE AFTER compares; gputaskman record -o FILE appends"
        self.assertEqual(g.parse_subcommands(old), {"diff", "record"})


class ResultTests(unittest.TestCase):
    def test_text_falls_back_to_stderr(self):
        self.assertEqual(g.Result(1, "", "boom").text, "boom")
        self.assertEqual(g.Result(0, "out", "warn").text, "out")
        self.assertTrue(g.Result(0, "", "").ok)


class RunnerTests(unittest.TestCase):
    def test_env_asks_for_utf8_and_width(self):
        env = g.Gputaskman("gputaskman").env(columns=120)
        self.assertEqual(env["PYTHONIOENCODING"], "utf-8")
        self.assertEqual(env["COLUMNS"], "120")

    def test_missing_executable_is_a_result_not_a_crash(self):
        result = g.Gputaskman("definitely-not-a-real-gputaskman-exe").capture("--list-gpus")
        self.assertEqual(result.returncode, 127)
        self.assertIn("not found", result.stderr)

    def test_argv_stringifies(self):
        self.assertEqual(g.Gputaskman("gtm").argv("--gpu", 0), ["gtm", "--gpu", "0"])


class FindTests(unittest.TestCase):
    def test_env_variable_wins_over_path(self):
        with mock.patch.dict(os.environ, {g.ENV_EXE: "custom-gtm"}), \
             mock.patch.object(g.shutil, "which", side_effect=lambda n: f"/bin/{n}"):
            self.assertEqual(g.find_gputaskman(), "/bin/custom-gtm")

    def test_explicit_wins_over_env(self):
        with mock.patch.dict(os.environ, {g.ENV_EXE: "custom-gtm"}), \
             mock.patch.object(g.shutil, "which", side_effect=lambda n: f"/bin/{n}"):
            self.assertEqual(g.find_gputaskman("mine"), "/bin/mine")

    def test_nothing_found(self):
        env = {k: v for k, v in os.environ.items() if k != g.ENV_EXE}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(g.shutil, "which", return_value=None), \
             mock.patch.object(g.Path, "is_file", return_value=False):
            self.assertIsNone(g.find_gputaskman())


if __name__ == "__main__":
    unittest.main()
