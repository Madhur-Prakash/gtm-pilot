import tempfile
import unittest
from pathlib import Path

from gtm_pilot import commands
from gtm_pilot.screens.forms import parse_seconds
from gtm_pilot.screens.record import count_new_samples, elapsed_text


class ArgsTests(unittest.TestCase):
    def test_secs(self):
        self.assertEqual(commands.secs(1.0), "1")
        self.assertEqual(commands.secs(0.5), "0.5")

    def test_live_all_gpus_omits_gpu(self):
        self.assertEqual(commands.live_args(None, 1.0), ["-i", "1"])
        self.assertEqual(commands.live_args(1, 0.5), ["-i", "0.5", "--gpu", "1"])

    def test_snapshots(self):
        self.assertEqual(commands.snapshot_args(0), ["--once", "--gpu", "0"])
        self.assertEqual(commands.json_snapshot_args(1), ["--json", "--gpu", "1"])

    def test_record(self):
        path = Path("s.jsonl")
        self.assertEqual(
            commands.record_args(path, 0, 1.0, None, True),
            ["record", "-o", "s.jsonl", "--gpu", "0", "-i", "1"],
        )
        self.assertEqual(
            commands.record_args(path, 1, 5.0, 300.0, False),
            ["record", "-o", "s.jsonl", "--gpu", "1", "-i", "5", "--duration", "300", "--no-system"],
        )

    def test_file_commands(self):
        a, b = Path("a.json"), Path("b.json")
        self.assertEqual(commands.diff_args(a, b), ["diff", "a.json", "b.json"])
        self.assertEqual(commands.summary_args(Path("r.jsonl")), ["summary", "r.jsonl"])
        self.assertEqual(commands.replay_args(Path("r.jsonl")), ["replay", "r.jsonl"])

    def test_expected_samples(self):
        self.assertIsNone(commands.expected_samples(1.0, None))
        self.assertEqual(commands.expected_samples(10.0, 300.0), 30)
        self.assertEqual(commands.expected_samples(10.0, 1.0), 1)


class HelperTests(unittest.TestCase):
    def test_parse_seconds(self):
        self.assertEqual(parse_seconds("3"), 3.0)
        self.assertEqual(parse_seconds("0.5"), 0.5)
        self.assertIsNone(parse_seconds("0"))
        self.assertIsNone(parse_seconds("-1"))
        self.assertIsNone(parse_seconds("abc"))

    def test_elapsed_text(self):
        self.assertEqual(elapsed_text(5), "00:05")
        self.assertEqual(elapsed_text(125), "02:05")
        self.assertEqual(elapsed_text(3725), "1:02:05")

    def test_count_new_samples_waits_for_full_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.jsonl"
            self.assertEqual(count_new_samples(path, 0), (0, 0))  # not created yet

            path.write_bytes(b'{"a": 1}\n{"a": 2}\n{"a": ')
            new, pos = count_new_samples(path, 0)
            self.assertEqual(new, 2)
            self.assertEqual(pos, len(b'{"a": 1}\n{"a": 2}\n'))

            with open(path, "ab") as f:
                f.write(b'3}\n')
            self.assertEqual(count_new_samples(path, pos)[0], 1)


if __name__ == "__main__":
    unittest.main()
