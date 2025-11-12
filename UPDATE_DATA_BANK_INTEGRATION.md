# Data‑Bank API Integration Update (Strict, Typed, Tested)

This document describes updates to integrate turkic‑api with data‑bank‑api while maintaining strict type safety and full coverage.

## Summary
- After a job completes, upload the result file to data‑bank‑api and record the returned `file_id`.
- Include `file_id` on `JobStatus` responses so downstream services can fetch the corpus from data‑bank‑api.
- Enforce strict typing (no `Any`, no casts, no ignores). Keep code modular and DRY.

## Required Changes

### Settings
Update `api/config.py` (`Settings.from_env`) to read:
- `TURKIC_DATA_BANK_API_URL`
- `TURKIC_DATA_BANK_API_KEY`
Add fields to the `Settings` dataclass:
- `data_bank_api_url: str`
- `data_bank_api_key: str`

### Job Implementation
In `api/jobs.py` (impl path):
- After writing the result file and marking the job `completed`, if both URL and KEY are set:
  - `httpx.post("{url}/files", headers={"X-API-Key": key}, files={"file": (f"{job_id}.txt", f, "text/plain; charset=utf-8")}, timeout=600.0)`
  - Parse `{ "file_id": "...", ... }` from response.
  - Store `file_id` in Redis hash for this job.
  - Log success/failure; failure MUST NOT fail the job (result remains available locally via `/result`).

### API Models
In `api/models.py`:
- Add `file_id: str | None = None` to `JobStatus`.

### Tests (100% Statements + Branches)
- Unit tests mocking `httpx` post:
  - 201 success returns JSON with `file_id`; redis updated; job stays `completed`.
  - Failure paths (401/403/5xx/transport) log error and do not change job completion status.
- API tests for `GET /api/v1/jobs/{id}` should include `file_id` when set.

## Linting, Typing, Guards
- `mypy --strict` across `api/` and `core/` must pass; zero `Any`, zero casts, zero ignores.
- Ruff: keep banned‑API rule for `typing.cast`, consistent formatting.
- Guard tooling remains green (typing/logging/exception guards).

## Environment (Railway)
- `TURKIC_DATA_BANK_API_URL="http://data-bank-api.railway.internal"`
- `TURKIC_DATA_BANK_API_KEY="<turkic-key>"`

## Make Commands
- `make check`: guard + ruff + mypy + tests (branch coverage).
- Keep coverage at 100% for statements and branches for all touched areas.

## Notes
- This flow complements the existing `/result` endpoint. Upload failure does not break job completion.
- Use the internal Railway URL for reliability/perf and X‑API‑Key for auth.
