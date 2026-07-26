"""core/ must stay pure Python — no Django, DRF, or Firebase (CLAUDE.md rule 2)."""

from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core"
FORBIDDEN_SUBSTRINGS = ("django", "firebase", "rest_framework")


def test_core_package_imports_no_framework_code():
    py_files = sorted(CORE_DIR.glob("*.py"))
    assert py_files, "expected core/*.py files to exist"
    offenders = []
    for path in py_files:
        text = path.read_text(encoding="utf-8").lower()
        for line in text.splitlines():
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("from ")):
                continue
            if any(bad in stripped for bad in FORBIDDEN_SUBSTRINGS):
                offenders.append((path.name, stripped))
    assert offenders == []
