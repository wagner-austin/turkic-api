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
- After writing the result file but **before** marking the job `completed`:
  - Validate that both `data_bank_api_url` and `data_bank_api_key` are non-empty; if not, raise `UploadError("data-bank configuration missing")`.
  - `httpx.post("{url}/files", headers={"X-API-Key": key}, files={"file": (f"{job_id}.txt", f, "text/plain; charset=utf-8")}, timeout=600.0)`
  - Parse `{ "file_id": "...", ... }` from response.
  - Store `file_id` in Redis hash for this job.
  - Mark the job `completed` **only if** upload and `file_id` persistence succeed.
- On any failure (invalid config, HTTP error, malformed JSON, missing `file_id`):
  - Log a structured error with `job_id` and HTTP status / error code.
  - Set job status to `failed` and persist an error code in Redis.
  - Raise `UploadError` so the RQ job is treated as failed (no local-only fallback).

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
- This flow removes legacy/local fallbacks: a job that cannot be uploaded to data-bank-api is considered `failed` and does not expose a `completed`+local result.
- Use the internal Railway URL for reliability/perf and X-API-Key for auth.
