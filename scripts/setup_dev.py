#!/usr/bin/env python
"""
Development Environment Setup Script for Turkic API

Uses logging (no print), avoids bare excepts, and exits on errors.
"""

from __future__ import annotations

import importlib.util
import logging
import pathlib
import platform
import subprocess
import sys
from collections.abc import Sequence


def _in_virtual_env() -> bool:
    return hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )


def _run(cmd: Sequence[str]) -> int:
    proc = subprocess.run(cmd, capture_output=True, check=False)
    return proc.returncode


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("setup_dev")

    script_path = pathlib.Path(__file__).resolve()
    project_root = script_path.parent.parent

    log.info("Setting up development environment for Turkic API")
    log.info("Project root: %s", project_root)

    if not _in_virtual_env():
        log.warning("Not running in a virtual environment.")
        log.info("It is recommended to use a virtual environment (virtualenv/conda).")
        ans = input("Continue anyway? [y/N]: ")
        if ans.strip().lower() != "y":
            log.error("Aborting.")
            sys.exit(1)

    log.info("=== Installing package with development extras ===")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-e", f"{project_root}[dev,ui,winlid]"]
    )

    if platform.system() == "Windows":
        log.info("=== Checking PyICU (Windows) ===")
        if importlib.util.find_spec("icu") is not None:
            import icu  # noqa: F401

            log.info("PyICU is installed (ICU %s)", icu.ICU_VERSION)
        else:
            log.info("PyICU not installed. Invoking installer…")
            subprocess.check_call(
                [sys.executable, "-m", "turkic_translit.cli.pyicu_install"]
            )

    log.info("=== Verifying common dev tools ===")
    for tool in ("black", "ruff", "mypy", "pytest"):
        rc = _run([tool, "--version"])
        if rc == 0:
            log.info("[ok] %s is installed", tool)
        else:
            log.warning("[warn] %s not found or not working properly", tool)

    if platform.system() == "Windows":
        has_make = _run(["make", "--version"]) == 0
        if has_make:
            log.info("GNU Make detected. Common commands:")
            log.info("  make help   - Show available commands")
            log.info("  make lint   - Run linting checks")
            log.info("  make test   - Run tests")
        else:
            log.info("PowerShell alternatives:")
            log.info("  ./scripts/run.ps1 help    - Show available commands")
            log.info("  ./scripts/run.ps1 lint    - Run linting checks")
            log.info("  ./scripts/run.ps1 test    - Run tests")
            log.info("To install GNU Make (recommended): 'choco install make'")
    else:
        log.info("You can run:")
        log.info("  make help   - Show available commands")
        log.info("  make lint   - Run linting checks")
        log.info("  make test   - Run tests")


if __name__ == "__main__":
    main()
