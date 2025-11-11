"""Internal tooling for repository guard checks.

This package hosts guard scripts that enforce strict standards such as:
- No use of typing.Any or casts
- No "type: ignore" comments
- No bare except and require re-raise in handlers
- No use of print; use centralized logging instead

These checks are wired into the Makefile via `make lint` / `make check`.
"""
