import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.validate_content import load_pack, validate_pack

ROOT = Path(__file__).resolve().parents[1]


class ContentValidationTests(unittest.TestCase):
    def test_b42_json_translations_are_complete(self):
        root = ROOT / "mods/KnoxQuest/42/media/lua/shared/Translate"
        english = json.loads((root / "EN/UI.json").read_text(encoding="utf8"))
        chinese = json.loads((root / "CN/UI.json").read_text(encoding="utf8"))
        self.assertEqual(set(english), set(chinese))
        self.assertIn("UI_KQ_Title", chinese)
        for data in (english, chinese):
            self.assertTrue(all(key.startswith("UI_KQ_") and isinstance(value, str) and value for key, value in data.items()))

    def setUp(self):
        self.pack = load_pack(ROOT / "content" / "vanilla-demo.json")

    def test_all_shipped_examples(self):
        paths = list((ROOT / "content").glob("*.json"))
        self.assertGreaterEqual(len(paths), 2)
        for path in paths:
            with self.subTest(path=path.name):
                self.assertEqual([], validate_pack(load_pack(path)))

    def test_cycles_rejected(self):
        self.pack["quests"][0]["dependsOn"] = [self.pack["quests"][-1]["id"]]
        self.assertTrue(any("cycle" in e for e in validate_pack(self.pack)))

    def test_missing_dependency_rejected(self):
        self.pack["quests"][1]["dependsOn"] = ["vanilla_demo:missing"]
        self.assertTrue(any("missing dependency" in e for e in validate_pack(self.pack)))

    def test_duplicate_quest_rejected(self):
        self.pack["quests"].append(copy.deepcopy(self.pack["quests"][0]))
        self.assertTrue(any("duplicate quest" in e for e in validate_pack(self.pack)))

    def test_duplicate_task_rejected(self):
        task = self.pack["quests"][0]["tasks"][0]
        self.pack["quests"][0]["tasks"].append(copy.deepcopy(task))
        self.assertTrue(any("duplicate task" in e for e in validate_pack(self.pack)))

    def test_unknown_type_rejected(self):
        self.pack["quests"][0]["tasks"][0]["type"] = "magic_completion"
        self.assertTrue(any("unknown condition" in e for e in validate_pack(self.pack)))

    def test_wrong_namespace_rejected(self):
        self.pack["quests"][0]["id"] = "another:welcome"
        self.assertTrue(any("namespaced quest" in e for e in validate_pack(self.pack)))

    def test_empty_any_rejected(self):
        self.pack["quests"][0]["dependencyMode"] = "any"
        self.assertTrue(any("any requires" in e for e in validate_pack(self.pack)))

    def test_dangling_chapter_rejected(self):
        self.pack["quests"][0]["chapterId"] = "vanilla_demo:missing"
        self.assertTrue(any("chapterId" in e for e in validate_pack(self.pack)))

    def test_bad_skill_levels_rejected(self):
        for level in (True, 0, 11, 1.5, "7", None):
            with self.subTest(level=level):
                self.pack["quests"][0]["tasks"] = [{"id": "skill", "type": "skill", "skill": "electrical", "level": level}]
                self.assertTrue(any("level must" in e for e in validate_pack(self.pack)))

    def test_rewards_not_silently_accepted(self):
        self.pack["quests"][0]["rewards"] = [{"type": "item", "item": "unknown"}]
        self.assertTrue(any("rewards" in e for e in validate_pack(self.pack)))

    def test_malformed_shapes_return_errors(self):
        for value in (None, True, 1, "text", [], {}, [None]):
            with self.subTest(value=value):
                self.assertTrue(validate_pack(value))
                for key in ("chapters", "quests", "packId", "packVersion"):
                    pack = copy.deepcopy(self.pack)
                    pack[key] = value
                    self.assertTrue(validate_pack(pack))

    def test_missing_fields_rejected(self):
        del self.pack["quests"][0]["description"]
        self.assertTrue(any("missing field description" in e for e in validate_pack(self.pack)))

    def test_unknown_fields_rejected(self):
        self.pack["quests"][0]["dependOn"] = []
        self.assertTrue(any("unknown field dependOn" in e for e in validate_pack(self.pack)))

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"packId":"one","packId":"two"}', encoding="utf8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                load_pack(path)

    def test_nonstandard_json_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nan.json"
            path.write_text('{"value":NaN}', encoding="utf8")
            with self.assertRaisesRegex(ValueError, "nonstandard JSON"):
                load_pack(path)

    def test_cli_failure_and_pack_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "one.json"
            second = Path(directory) / "two.json"
            for path in (first, second):
                path.write_text(json.dumps(self.pack), encoding="utf8")
            result = subprocess.run([sys.executable, str(ROOT / "tools" / "validate_content.py"), str(first), str(second)], capture_output=True, text=True)
            self.assertEqual(1, result.returncode)
            self.assertIn("duplicate packId", result.stdout)


if __name__ == "__main__":
    unittest.main()
