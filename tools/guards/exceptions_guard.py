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


def handler_has_raise(handler: ast.ExceptHandler) -> bool:
    return any(isinstance(node, ast.Raise) for node in ast.walk(handler))


def run(roots: list[str]) -> int:
    errors: list[str] = []
    for path in iter_python_files(roots):
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(path))
        except Exception as exc:  # pragma: no cover
            # Print and re-raise to avoid swallowing errors
            sys.stderr.write(f"{path}: PARSE_ERROR {exc}\n")
            raise
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    errors.append(f"{path}:{node.lineno} bare 'except' is forbidden")
                if not handler_has_raise(node):
                    errors.append(
                        f"{path}:{node.lineno} except without re-raise is forbidden"
                    )
    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        return 1
    return 0


def main() -> int:
    return run(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
