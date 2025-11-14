from __future__ import annotations

from pathlib import Path

import pytest
from tools.guards import suppress_guard


def test_suppress_guard_flags_marker_in_python_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    marker = "su" + "press"
    bad_file = tmp_path / "bad.py"
    bad_file.write_text(f"# {marker} in comment\n", encoding="utf-8")

    rc = suppress_guard.run([str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 1
    assert marker in captured.err
    assert "forbidden marker" in captured.err


def test_suppress_guard_allows_clean_python_file(tmp_path: Path) -> None:
    clean_file = tmp_path / "clean.py"
    clean_file.write_text("x = 1\n", encoding="utf-8")

    rc = suppress_guard.run([str(tmp_path)])

    assert rc == 0
