from __future__ import annotations

import logging

from api.logging import setup_logging


def test_setup_logging_adds_handler_and_is_idempotent() -> None:
    root = logging.getLogger()
    # Clear any existing handlers
    for h in list(root.handlers):
        root.removeHandler(h)

    setup_logging("DEBUG")
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)
    count = len(root.handlers)

    # Calling again should not add duplicate handlers
    setup_logging("DEBUG")
    assert len(root.handlers) == count
