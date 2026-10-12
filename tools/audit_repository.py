"""Audit the Git index before publishing. Only original project files are allowed."""
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TOP = {"README.md", "LICENSE", "CONTRIBUTING.md", "CHANGELOG.md", ".gitignore", ".gitattributes", "requirements-dev.txt"}
DIRS = {"docs", "tools", "tests", "content", "mods", ".github"}
EXTENSIONS = {".md", ".py", ".lua", ".json", ".yml", ".yaml", ".txt", ".info"}


def main():
    top = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip()
    if Path(top).resolve() != ROOT:
        raise SystemExit("Refusing to publish: Git root is not the KnoxQuest project directory")
    entries = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=ROOT).decode("utf8").split("\0")
    count, total, errors = 0, 0, []
    for entry in filter(None, entries):
        metadata, name = entry.split("\t", 1)
        mode, sha, stage = metadata.split()
        path = PurePosixPath(name)
        if mode not in ("100644", "100755") or stage != "0":
            errors.append(name + ": symlink, submodule or unresolved entry")
            continue
        if path.is_absolute() or ".." in path.parts or (name not in TOP and path.parts[0] not in DIRS):
            errors.append(name + ": outside publication allowlist")
        if name not in TOP and path.name != ".gitkeep" and path.suffix not in EXTENSIONS:
            errors.append(name + ": unexpected file type")
        data = subprocess.check_output(["git", "cat-file", "blob", sha], cwd=ROOT)
        count += 1
        total += len(data)
        if len(data)>300_000:
            errors.append(name + ": oversized source file")
        try:
            text = data.decode("utf8")
        except UnicodeDecodeError:
            errors.append(name + ": not UTF-8 source text")
            continue
        patterns = [r"gh[pousr]_" + r"[A-Za-z0-9]{30,}", r"github_pat_" + r"[A-Za-z0-9_]{30,}", r"-----BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----", r"[A-Za-z]:[/\\]Users[/\\][^/\\\s]+", r"[A-Za-z]:[/\\]SteamLibrary[/\\]"]
        if any(re.search(pattern, text) for pattern in patterns):
            errors.append(name + ": credential or private machine path pattern")
    if count==0:
        errors.append("No staged files to audit")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"PASS: {count} staged UTF-8 project files, {total} bytes; no binaries, symlinks or files outside the allowlist")


if __name__ == "__main__":
    main()
