"""Validate Knox Quest's design-stage content format; no game integration."""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
import re
import sys


def validate_pack(data: object) -> list[str]:
    errors: list[str] = []

    def fail(where: str, message: str) -> None:
        errors.append(f"{where}: {message}")

    def text(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def fields(obj: dict, expected: set[str], where: str) -> None:
        for key in sorted(expected - obj.keys()):
            fail(where, f"missing field {key}")
        for key in sorted(obj.keys() - expected):
            fail(where, f"unknown field {key}")

    if not isinstance(data, dict):
        return ["pack: expected an object"]
    fields(data, {"schemaVersion", "packId", "packVersion", "title", "chapters", "quests"}, "pack")
    if type(data.get("schemaVersion")) is not int or data["schemaVersion"] != 1:
        fail("schemaVersion", "only integer version 1 is supported")
    pack_id = data.get("packId")
    if not isinstance(pack_id, str) or not re.fullmatch(r"[a-z][a-z0-9_.-]*", pack_id):
        fail("packId", "expected a lowercase namespace")
        pack_id = "__invalid__"
    version = data.get("packVersion")
    if not isinstance(version, str) or not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", version):
        fail("packVersion", "expected a three-part numeric version")
    if not text(data.get("title")):
        fail("title", "expected nonempty text")

    def namespaced(value: object) -> bool:
        return isinstance(value, str) and bool(re.fullmatch(re.escape(pack_id) + r":[a-z][a-z0-9_.-]*", value))

    chapters = data.get("chapters")
    quests = data.get("quests")
    if not isinstance(chapters, list) or not chapters:
        fail("chapters", "expected a nonempty array")
        chapters = []
    if not isinstance(quests, list) or not quests:
        fail("quests", "expected a nonempty array")
        quests = []
    chapter_ids: set[str] = set()
    for index, chapter in enumerate(chapters):
        where = f"chapters[{index}]"
        if not isinstance(chapter, dict):
            fail(where, "expected an object")
            continue
        fields(chapter, {"id", "title"}, where)
        chapter_id = chapter.get("id")
        if not namespaced(chapter_id):
            fail(where, "invalid namespaced chapter id")
        elif chapter_id in chapter_ids:
            fail(where, f"duplicate chapter id {chapter_id}")
        else:
            chapter_ids.add(chapter_id)
        if not text(chapter.get("title")):
            fail(where, "title must be nonempty text")

    graph: dict[str, list[str]] = {}
    for index, quest in enumerate(quests):
        where = f"quests[{index}]"
        if not isinstance(quest, dict):
            fail(where, "expected an object")
            continue
        fields(quest, {"id", "chapterId", "title", "description", "scope", "dependsOn", "dependencyMode", "tasks", "rewards"}, where)
        quest_id = quest.get("id")
        valid_id = namespaced(quest_id)
        unique_id = valid_id and quest_id not in graph
        if not valid_id:
            fail(where, "invalid namespaced quest id")
        elif not unique_id:
            fail(where, f"duplicate quest id {quest_id}")
        chapter_id = quest.get("chapterId")
        if not isinstance(chapter_id, str) or chapter_id not in chapter_ids:
            fail(where, "chapterId does not resolve")
        for key in ("title", "description"):
            if not text(quest.get(key)):
                fail(where, f"{key} must be nonempty text")
        if quest.get("scope") not in ("world", "character"):
            fail(where, "scope must be world or character")
        dependencies = quest.get("dependsOn")
        if not isinstance(dependencies, list) or any(not namespaced(d) for d in dependencies):
            fail(where, "dependsOn must be an array of same-pack quest ids")
            dependencies = []
        if len(dependencies) != len(set(dependencies)):
            fail(where, "duplicate dependency")
        if valid_id and quest_id in dependencies:
            fail(where, "self dependency")
        if quest.get("dependencyMode") not in ("all", "any"):
            fail(where, "dependencyMode must be all or any")
        elif not dependencies and quest["dependencyMode"] == "any":
            fail(where, "any requires at least one dependency")
        if unique_id:
            graph[quest_id] = dependencies
        if quest.get("rewards") != []:
            fail(where, "this prototype only supports an empty rewards array")
        tasks = quest.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            fail(where, "tasks must be a nonempty array")
            continue
        task_ids: set[str] = set()
        for task_index, task in enumerate(tasks):
            task_where = f"{where}.tasks[{task_index}]"
            if not isinstance(task, dict):
                fail(task_where, "expected an object")
                continue
            task_id = task.get("id")
            if not isinstance(task_id, str) or not re.fullmatch(r"[a-z][a-z0-9_.-]*", task_id):
                fail(task_where, "invalid local task id")
            elif task_id in task_ids:
                fail(task_where, f"duplicate task id {task_id}")
            else:
                task_ids.add(task_id)
            kind = task.get("type")
            if kind == "manual":
                fields(task, {"id", "type", "prompt"}, task_where)
                if not text(task.get("prompt")):
                    fail(task_where, "prompt must be nonempty text")
            elif kind == "skill":
                fields(task, {"id", "type", "skill", "level"}, task_where)
                if task.get("skill") not in ("electrical", "metalworking"):
                    fail(task_where, "unknown prototype skill")
                if type(task.get("level")) is not int or not 1 <= task["level"] <= 10:
                    fail(task_where, "level must be an integer from 1 to 10")
            elif kind == "item":
                fields(task, {"id", "type", "items", "count"}, task_where)
                items = task.get("items")
                if not isinstance(items, list) or not items or any(not isinstance(x, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*\.[A-Za-z][A-Za-z0-9_]*", x) for x in items):
                    fail(task_where, "items must be a nonempty array of full item types")
                elif len(items) != len(set(items)):
                    fail(task_where, "duplicate item alternative")
                if type(task.get("count")) is not int or not 1 <= task["count"] <= 10000:
                    fail(task_where, "count must be an integer from 1 to 10000")
            elif kind == "adapter":
                fields(task, {"id", "type", "capability", "params"}, task_where)
                capability = task.get("capability")
                if not isinstance(capability, str) or not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", capability):
                    fail(task_where, "invalid adapter capability")
                if not isinstance(task.get("params"), dict):
                    fail(task_where, "params must be an object")
            else:
                fail(task_where, "unknown condition type")

    for quest_id, dependencies in graph.items():
        for dependency in dependencies:
            if dependency not in graph:
                fail(quest_id, f"missing dependency {dependency}")
    # Kahn's algorithm avoids recursion limits on large authored quest graphs.
    indegree = {quest_id: 0 for quest_id in graph}
    children: dict[str, list[str]] = {quest_id: [] for quest_id in graph}
    for quest_id, dependencies in graph.items():
        for dependency in set(dependencies):
            if dependency in graph:
                indegree[quest_id] += 1
                children[dependency].append(quest_id)
    ready = deque(quest_id for quest_id, count in indegree.items() if count == 0)
    visited = 0
    while ready:
        quest_id = ready.popleft()
        visited += 1
        for child in children[quest_id]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if visited != len(graph):
        fail("quests", "dependency graph contains a cycle")
    return errors


def load_pack(path: Path) -> object:
    def unique_keys(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"nonstandard JSON constant {value}")

    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_keys, parse_constant=reject_constant)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    paths = args.paths or sorted((Path(__file__).resolve().parents[1] / "content").glob("*.json"))
    if not paths:
        print("No content files found.", file=sys.stderr)
        return 1
    failed = False
    pack_ids: set[str] = set()
    for path in paths:
        try:
            data = load_pack(path)
            errors = validate_pack(data)
        except (OSError, ValueError) as exc:
            errors = [str(exc)]
            data = None
        if isinstance(data, dict) and isinstance(data.get("packId"), str):
            pack_id = data["packId"]
            if pack_id in pack_ids:
                errors.append(f"duplicate packId across input files: {pack_id}")
            pack_ids.add(pack_id)
        if errors:
            failed = True
            print(f"FAIL {path.name}")
            for error in errors:
                print(f"  {error}")
        else:
            print(f"OK {path.name}: {len(data['chapters'])} chapters, {len(data['quests'])} quests (structure only)")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
