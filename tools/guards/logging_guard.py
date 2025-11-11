from __future__ import annotations

import ast
import sys
from collections.abc import Iterable
from pathlib import Path


def iter_python_files(roots: Iterable[str]) -> Iterable[Path]:
    for root in roots:
        base = Path(root)
        if not base.exists():
            continue
        yield from base.rglob("*.py")


def run(roots: list[str]) -> int:
    errors: list[str] = []
    for path in iter_python_files(roots):
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except Exception as exc:  # pragma: no cover
            sys.stderr.write(f"{path}: PARSE_ERROR {exc}\n")
            raise
        errs = [
            f"{path}:{n.lineno} use logger; 'print' is forbidden"
            for n in ast.walk(tree)
            if (
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "print"
            )
        ]
        errors.extend(errs)
    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        return 1
    return 0


def main() -> int:
    return run(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
