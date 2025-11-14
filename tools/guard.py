from __future__ import annotations

from collections.abc import Callable

from tools.guards import exceptions_guard, logging_guard, suppress_guard, typing_guard

Runner = Callable[[list[str]], int]


def run_guards(roots: list[str]) -> int:
    runners: list[Runner] = [
        typing_guard.run,
        exceptions_guard.run,
        suppress_guard.run,
        logging_guard.run,
    ]
    for runner in runners:
        rc = runner(roots)
        if rc != 0:
            return rc
    return 0


def main() -> int:
    # Scan primary application and tooling modules, including legacy src.
    return run_guards(["api", "core", "tests", "tools", "scripts", "src"])


if __name__ == "__main__":
    raise SystemExit(main())
