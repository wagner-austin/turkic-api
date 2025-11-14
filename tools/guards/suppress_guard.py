from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path

# Marker is built dynamically so the literal never appears in source,
# while still detecting the exact sequence in repository files.
MARKER: str = "su" + "press"


def iter_python_files(roots: Iterable[str]) -> Iterable[Path]:
    for root in roots:
        base = Path(root)
        if not base.exists():
            continue
        yield from base.rglob("*.py")


def check_path(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - guard must not crash silently
        sys.stderr.write(f"{path}: READ_ERROR {exc}\n")
        raise

    for line_number, line in enumerate(text.splitlines(), start=1):
        if MARKER in line.lower():
            errors.append(f"{path}:{line_number} forbidden marker '{MARKER}'")

    return errors


def run(roots: list[str]) -> int:
    all_errors: list[str] = []
    for path in iter_python_files(roots):
        all_errors.extend(check_path(path))
    if all_errors:
        sys.stderr.write("\n".join(all_errors) + "\n")
        return 1
    return 0


def main() -> int:
    return run(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
