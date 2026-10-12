"""Build a local-mod ZIP from the audited Git snapshot, never the game directory."""
import hashlib
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    import audit_repository
    audit_repository.main()
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    archive = output / "KnoxQuest-0.1.0-alpha.1.zip"
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf8").split("\0")
    selected = [name for name in tracked if name and (name.startswith("mods/") or name in ("README.md", "LICENSE", "CHANGELOG.md") or name == "docs/TESTING.md")]
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        for name in selected:
            if name.endswith("/.gitkeep"):
                continue
            data = subprocess.check_output(["git", "show", ":" + name], cwd=ROOT)
            entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(entry, data)
        # B42 expects the versioned layout; preserve empty common directories.
        for name in ("KnoxQuest", "KnoxQuestDemo", "KnoxQuestAlpharius"):
            package.writestr(zipfile.ZipInfo("mods/"+name+"/common/", (2026,1,1,0,0,0)), b"")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / (archive.name + ".sha256")).write_text(digest + "  " + archive.name + "\n", encoding="utf8")
    print(archive.name + ": " + str(archive.stat().st_size) + " bytes; SHA256 " + digest)


if __name__ == "__main__":
    main()
