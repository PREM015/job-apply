from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "archive", "data", "__pycache__", ".pytest_cache"}
TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".txt", ".json", ".bat", ".sh", ".toml"}
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{7,}\d)(?!\d)")
SENSITIVE_NAME = re.compile(
    r"(?i)^(profile\.yaml|answers\.yaml|\.env|.*resume.*\.pdf|.*\.(pdf|xlsx|sqlite|sqlite3|db|exe))$"
)


def _profile_values() -> set[str]:
    path = ROOT / "profile.yaml"
    if not path.is_file():
        return set()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("profile.yaml must contain a mapping")
    keys = ("full_name", "email", "phone", "address", "street_address")
    return {
        str(data[key]).strip() for key in keys
        if data.get(key) and str(data[key]).strip()
    }


def _files(selected: list[str]) -> Iterable[Path]:
    if selected:
        for item in selected:
            path = Path(item)
            resolved = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
            if resolved.is_file():
                yield resolved
        return
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        yield path


def main() -> int:
    parser = argparse.ArgumentParser(description="Report PII scan file names and counts only.")
    parser.add_argument("paths", nargs="*", help="optional explicit paths to scan")
    args = parser.parse_args()
    personal = _profile_values()
    found = 0
    for path in sorted(_files(args.paths)):
        filename_match = bool(SENSITIVE_NAME.search(path.name))
        content_matches = 0
        if path.suffix.lower() in TEXT_SUFFIXES:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                text = ""
            content_matches += len(EMAIL.findall(text))
            content_matches += len(PHONE.findall(text))
            content_matches += sum(text.count(value) for value in personal if value)
        if filename_match or content_matches:
            found += 1
            print(
                f"{path.relative_to(ROOT)}: filename_matches={int(filename_match)} "
                f"content_matches={content_matches}"
            )
    print(f"PII_SCAN_FILES_WITH_MATCHES={found}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
