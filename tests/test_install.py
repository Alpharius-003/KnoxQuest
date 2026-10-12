import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("installer", Path(__file__).resolve().parents[1] / "tools/install_local.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class EnableConfigurationTests(unittest.TestCase):
    def test_enable_is_idempotent_and_preserves_maps(self):
        original = "VERSION = 1,\nmods\n{\n    mod = Existing,\n}\nmaps\n{\n    map = ExistingMap,\n}\n"
        updated = installer.enable(original, ["KnoxQuest", "KnoxQuestAlpharius"])
        self.assertEqual(updated, installer.enable(updated, ["KnoxQuest", "KnoxQuestAlpharius"]))
        self.assertIn("    mod = Existing,", updated)
        self.assertEqual(original.split("maps")[1], updated.split("maps")[1])

    def test_unrecognized_file_is_rejected(self):
        with self.assertRaises(ValueError):
            installer.enable("unexpected format", ["KnoxQuest"])
