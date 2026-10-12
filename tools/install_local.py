"""Install original Knox Quest modules into an explicit existing PZ profile."""
import argparse
from datetime import datetime
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("KnoxQuest", "KnoxQuestDemo", "KnoxQuestAlpharius")


def enable(text, modules):
    match = re.search(r"(?m)^mods\s*\n\{\s*\n", text)
    if not match:
        raise ValueError("No supported mods block found; left unchanged")
    end = text.find("}", match.end())
    if end < 0:
        raise ValueError("Unterminated mods block; left unchanged")
    block = text[match.end():end]
    enabled = set(re.findall(r"(?m)^\s*mod\s*=\s*([^,\r\n]+),", block))
    addition = "".join("    mod = " + name + ",\n" for name in modules if name not in enabled)
    return text[:end] + addition + text[end:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--save", help="Optional relative save path, e.g. Sandbox/MyWorld")
    parser.add_argument("--demo", action="store_true", help="Enable starter demo as well")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    profile = args.profile.resolve()
    if not (profile / "options.ini").is_file():
        raise SystemExit("Expected an existing Project Zomboid profile containing options.ini")
    modules = ["KnoxQuest", "KnoxQuestAlpharius"]
    if args.demo:
        modules.insert(1, "KnoxQuestDemo")
    targets = [profile / "mods/default.txt"]
    if args.save:
        saves = (profile / "Saves").resolve()
        save = (saves / args.save).resolve()
        if save == saves or not save.is_relative_to(saves):
            raise SystemExit("Save path must remain inside this profile's Saves directory")
        targets.append(save / "mods.txt")
    changes = [(path, enable(path.read_text(encoding="utf-8-sig"), modules)) for path in targets]
    for module in modules:
        source = ROOT / "mods" / module
        if not (source / "42/mod.info").is_file():
            raise SystemExit("Build/source module missing: " + module)
        destination = profile / "mods" / module
        if destination.is_symlink() or (hasattr(destination, "is_junction") and destination.is_junction()):
            raise SystemExit("Refusing to overwrite linked mod directory: " + module)
        if destination.exists():
            info = (destination / "42/mod.info").read_text(encoding="utf8")
            if "id=" + module + "\n" not in info:
                raise SystemExit("Existing mod directory has a different identity: " + module)
    if args.dry_run:
        print("DRY RUN: install " + ", ".join(modules))
        for path, _ in changes:
            print("UPDATE " + path.relative_to(profile).as_posix())
        return
    backup = profile / "KnoxQuest-backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup.mkdir(parents=True)
    for path, _ in changes:
        copy = backup / path.relative_to(profile)
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, copy)
    for module in modules:
        destination = profile / "mods" / module
        if destination.exists():
            shutil.copytree(destination, backup / "previous-mods" / module)
        shutil.copytree(ROOT / "mods" / module, destination, dirs_exist_ok=True)
    for path, text in changes:
        temporary = path.with_name(path.name + ".knox-tmp")
        temporary.write_text(text, encoding="utf8", newline="\n")
        temporary.replace(path)
    print("Installed: " + ", ".join(modules))
    print("Backed up modified configuration and previous module copies to " + str(backup))
    print("Normal game restart required. Existing character and map data were not edited.")


if __name__ == "__main__":
    main()
