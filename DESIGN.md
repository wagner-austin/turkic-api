# Turkic API - Architecture & Design Document

## Project Vision

Production-grade API for Turkic language corpus processing with **zero technical debt**, **100% test coverage**, and **strict type safety**.

---

## Quality Standards (Non-Negotiable)

### Type Safety
- âœ… `mypy --strict` mode enabled
- âœ… **Zero `Any` types** (explicit or implicit)
- âœ… **Zero type casts**
- âœ… **Zero `type: ignore` comments**
- âœ… Full type coverage for all functions, methods, and variables

### Test Coverage
- âœ… **100% statement coverage**
- âœ… **100% branch coverage**
- âœ… Unit tests for all functions
- âœ… Integration tests for all endpoints
- âœ… `pytest-cov` with `--cov-report=term-missing --cov-branch`

### Code Quality
- âœ… **DRY** (Don't Repeat Yourself) - no code duplication
- âœ… **Modular** - single responsibility principle
- âœ… **Consistent** - unified patterns across codebase
- âœ… **Standardized** - follow Python conventions (PEP 8, PEP 484)

### Process
- âœ… `make check` must pass before commit
- âœ… All linters must pass (ruff, mypy)
- âœ… All tests must pass
- âœ… No warnings allowed

---

## Technology Stack

### Backend (Python 3.11+)
```yaml
Framework: FastAPI (async/await)
ASGI Server: Uvicorn
Dependency Management: Poetry
Job Queue: Redis + RQ
Type Checking: mypy (strict mode)
Linting: Ruff
Testing: pytest + pytest-cov + pytest-asyncio
Coverage: 100% (statements + branches)
```

### Infrastructure
```yaml
Hosting: Railway
Storage: Railway Persistent Volumes
Queue: Railway Redis addon
CI/CD: Railway auto-deploy from git
```

### Frontend (Phase 2 - Not Now)
```yaml
Language: TypeScript (strict mode)
Testing: Vitest
Linting: ESLint (strict rules)
Hosting: GitHub Pages
Deployment: GitHub Actions (YAML workflow)
```

---

## Architecture
### Integration: data-bank-api (Strict, Typed)

- Purpose: Publish completed job outputs to data-bank-api and surface a stable `file_id` to downstream services.
- Upload Semantics:
  - After a job transitions to `completed`, upload the result file via `POST /files` with `X-API-Key`.
  - The server generates `file_id` (sha256 hex); clients must not derive IDs from filenames.
  - On success, store `file_id` in the Redis job hash; include it in `JobStatus` responses.
  - On failure (auth/network/5xx), log error and keep job `completed`; `/result` endpoint continues to serve the file locally.
- Settings (env):
  - `TURKIC_DATA_BANK_API_URL`, `TURKIC_DATA_BANK_API_KEY`.
- API Models:
  - `JobStatus` includes `file_id: str | None`.
- Quality: mypy --strict, ruff, and guard checks green; tests cover success and failure branches; 100% statements and branches.

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚              Railway Platform               â”‚
â”‚                                             â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚  API Service (FastAPI + Uvicorn)     â”‚  â”‚
â”‚  â”‚  Port: $PORT                         â”‚  â”‚
â”‚  â”‚                                      â”‚  â”‚
â”‚  â”‚  Endpoints:                          â”‚  â”‚
â”‚  â”‚  â€¢ POST /api/v1/jobs                 â”‚  â”‚
â”‚  â”‚  â€¢ GET  /api/v1/jobs/{job_id}        â”‚  â”‚
â”‚  â”‚  â€¢ GET  /api/v1/jobs/{job_id}/result â”‚  â”‚
â”‚  â”‚  â€¢ GET  /api/v1/health                â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â”‚               â”‚                             â”‚
â”‚               â–¼                             â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚  Redis (Railway Addon)               â”‚  â”‚
â”‚  â”‚  â€¢ Job queue (RQ)                    â”‚  â”‚
â”‚  â”‚  â€¢ Job status cache                  â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â”‚               â”‚                             â”‚
â”‚               â–¼                             â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚  RQ Worker (Background Service)      â”‚  â”‚
â”‚  â”‚                                      â”‚  â”‚
â”‚  â”‚  Job: process_corpus()               â”‚  â”‚
â”‚  â”‚  1. Download corpus                  â”‚  â”‚
â”‚  â”‚  2. Filter by language               â”‚  â”‚
â”‚  â”‚  3. Transliterate to IPA             â”‚  â”‚
â”‚  â”‚  4. Save result                      â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â”‚               â”‚                             â”‚
â”‚               â–¼                             â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚  Persistent Volume                   â”‚  â”‚
â”‚  â”‚  /data/                              â”‚  â”‚
â”‚  â”‚  â”œâ”€â”€ models/lid.176.bin (126 MB)     â”‚  â”‚
â”‚  â”‚  â””â”€â”€ results/{job_id}.txt            â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Project Structure

```
turkic-api/
â”œâ”€â”€ pyproject.toml              # Poetry dependencies + tool configs
â”œâ”€â”€ poetry.lock                 # Locked dependencies
â”œâ”€â”€ Makefile                    # Development commands
â”œâ”€â”€ Dockerfile                  # Multi-stage build
â”œâ”€â”€ .dockerignore               # Docker build exclusions
â”œâ”€â”€ docker-compose.yml          # Local dev stack
â”œâ”€â”€ railway.toml                # Railway deployment
â”œâ”€â”€ .env.example                # Environment template
â”œâ”€â”€ .gitignore
â”œâ”€â”€ README.md
â”œâ”€â”€ DESIGN.md                   # This file
â”‚
â”œâ”€â”€ api/                        # FastAPI application
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ main.py                # App factory, routes
â”‚   â”œâ”€â”€ config.py              # Pydantic settings (type-safe config)
â”‚   â”œâ”€â”€ models.py              # Request/response schemas
â”‚   â”œâ”€â”€ jobs.py                # RQ job definitions
â”‚   â”œâ”€â”€ worker.py              # RQ worker entry
â”‚   â”œâ”€â”€ dependencies.py        # FastAPI DI (Redis, Config, Logger)
â”‚   â”œâ”€â”€ logging.py             # Structured logging setup
â”‚   â””â”€â”€ services.py            # Business logic services (injected)
â”‚
â”œâ”€â”€ core/                       # Business logic (from original repo)
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ translit.py            # PyICU transliteration
â”‚   â”œâ”€â”€ langid.py              # FastText language ID
â”‚   â”œâ”€â”€ corpus.py              # OSCAR/Wikipedia streaming
â”‚   â”œâ”€â”€ models.py              # Core domain models
â”‚   â””â”€â”€ rules/                 # ICU rules (*.rules)
â”‚
â”œâ”€â”€ tests/                      # 100% coverage required
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ conftest.py            # Pytest fixtures
â”‚   â”œâ”€â”€ test_api.py            # API endpoint tests
â”‚   â”œâ”€â”€ test_jobs.py           # Job processing tests
â”‚   â”œâ”€â”€ test_translit.py       # Transliteration tests
â”‚   â”œâ”€â”€ test_langid.py         # Language ID tests
â”‚   â”œâ”€â”€ test_corpus.py         # Corpus streaming tests
â”‚   â””â”€â”€ test_dependencies.py   # DI container tests
â”‚
â””â”€â”€ scripts/                    # Utilities
    â””â”€â”€ download_models.py     # Download FastText model
```

---

## Dependency Injection Architecture

### Pattern: FastAPI Depends() with Explicit Services

All dependencies are **explicitly injected** using FastAPI's `Depends()` mechanism. No global state, no singletons.

**api/dependencies.py:**
```python
from typing import Generator
from redis import Redis
from api.config import Settings
from api.logging import get_logger
import logging

def get_settings() -> Settings:
    """Dependency: Application settings (cached by FastAPI)."""
    return Settings()

def get_redis(settings: Settings = Depends(get_settings)) -> Generator[Redis, None, None]:
    """Dependency: Redis connection pool."""
    redis = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        yield redis
    finally:
        redis.close()

def get_request_logger() -> logging.Logger:
    """Dependency: Per-request logger with correlation ID."""
    return get_logger(__name__)
```

### Usage in Endpoints (Fully Typed)

**api/main.py:**
```python
from fastapi import FastAPI, Depends
from redis import Redis
from api.dependencies import get_redis, get_request_logger
from api.models import JobCreate, JobResponse
from api.services import JobService
import logging

@app.post("/api/v1/jobs")
async def create_job(
    job: JobCreate,
    redis: Redis = Depends(get_redis),
    logger: logging.Logger = Depends(get_request_logger),
) -> JobResponse:
    """Create a new corpus processing job."""
    logger.info("Creating job", extra={"source": job.source, "language": job.language})

    service = JobService(redis=redis, logger=logger)
    result = await service.create_job(job)

    logger.info("Job created", extra={"job_id": result.job_id})
    return result
```

### Service Layer (Explicit Injection)

**api/services.py:**
```python
from redis import Redis
import logging
from api.models import JobCreate, JobResponse
from uuid import uuid4
from datetime import datetime

class JobService:
    """Service for job management (all dependencies injected)."""

    def __init__(self, redis: Redis, logger: logging.Logger) -> None:
        self._redis = redis
        self._logger = logger

    async def create_job(self, job: JobCreate) -> JobResponse:
        """Create and enqueue a job."""
        job_id = str(uuid4())

        self._logger.debug("Enqueuing job", extra={"job_id": job_id})

        # Store job metadata in Redis
        self._redis.hset(
            f"job:{job_id}",
            mapping={
                "status": "queued",
                "source": job.source,
                "language": job.language,
                "created_at": datetime.utcnow().isoformat(),
            },
        )

        # Enqueue RQ job
        from rq import Queue
        queue = Queue(connection=self._redis)
        queue.enqueue("api.jobs.process_corpus", job_id, job.dict())

        return JobResponse(
            job_id=job_id,
            status="queued",
            created_at=datetime.utcnow(),
        )
```

### Benefits of This Pattern

âœ… **Testability**: Easy to mock dependencies in tests
âœ… **Type Safety**: All injections are type-checked by mypy
âœ… **No Globals**: No hidden state, explicit everywhere
âœ… **Lifecycle Management**: FastAPI handles cleanup automatically
âœ… **Request Isolation**: Each request gets fresh dependencies

---

## Structured Logging Architecture

### Pattern: Explicit Logger Injection with Structured Fields

All logging is **explicitly passed** as a dependency. No `logging.getLogger()` calls in business logic.

**api/logging.py:**
```python
import logging
import json
from datetime import datetime
from typing import Protocol

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include extra fields if present
        if hasattr(record, "job_id"):
            log_data["job_id"] = record.job_id
        if hasattr(record, "language"):
            log_data["language"] = record.language

        return json.dumps(log_data)

def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for the application."""
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given module."""
    return logging.getLogger(name)
```

### Logger Protocol (Type-Safe Interface)

**api/types.py:**
```python
from typing import Protocol

class LoggerProtocol(Protocol):
    """Protocol for logger interface (duck typing)."""

    def debug(self, msg: str, **kwargs: object) -> None: ...
    def info(self, msg: str, **kwargs: object) -> None: ...
    def warning(self, msg: str, **kwargs: object) -> None: ...
    def error(self, msg: str, **kwargs: object) -> None: ...
```

### Usage in Services

**core/translit.py:**
```python
import logging
from typing import Literal

def transliterate_to_ipa(
    text: str,
    lang: Literal["kk", "ky", "uz", "tr", "ug"],
    logger: logging.Logger,
) -> str:
    """Transliterate text to IPA (explicit logger)."""
    logger.debug(
        "Starting transliteration",
        extra={"language": lang, "text_length": len(text)},
    )

    # ... transliteration logic ...

    logger.debug(
        "Transliteration complete",
        extra={"output_length": len(result)},
    )

    return result
```

### Logging in RQ Workers

**api/jobs.py:**
```python
from rq import get_current_job
from api.logging import get_logger

def process_corpus(job_id: str, params: dict[str, object]) -> dict[str, object]:
    """RQ job function (explicit logger)."""
    logger = get_logger(__name__)

    logger.info("Job started", extra={"job_id": job_id, "params": params})

    try:
        # ... processing logic ...
        logger.info("Job completed", extra={"job_id": job_id, "result": result})
        return result
    except Exception as e:
        logger.error(
            "Job failed",
            extra={"job_id": job_id, "error": str(e)},
            exc_info=True,
        )
        raise
```

### Benefits of This Pattern

âœ… **Explicit**: Logger is always passed, never hidden
âœ… **Structured**: All logs are JSON for easy parsing
âœ… **Typed**: Logger interface is type-checked
âœ… **Contextual**: Extra fields provide rich context
âœ… **Testable**: Can inject mock loggers in tests

---

## API Design

### Endpoints

#### `POST /api/v1/jobs`

Create a new corpus processing job.

**Request Schema (`JobCreate`):**
```python
class JobCreate(BaseModel):
    source: Literal["oscar", "wikipedia"]
    language: Literal["kk", "ky", "uz", "tr", "ug"]
    max_sentences: int = Field(ge=1, le=100000)
    transliterate: bool = True
    confidence_threshold: float = Field(ge=0.0, le=1.0, default=0.95)
```

**Response Schema (`JobResponse`):**
```python
class JobResponse(BaseModel):
    job_id: str  # UUID
    status: Literal["queued", "processing", "completed", "failed"]
    created_at: datetime
```

**Business Rules:**
- Job ID is UUID v4
- Jobs expire after 24 hours
- Maximum 10 concurrent jobs per IP (rate limiting)

---

#### `GET /api/v1/jobs/{job_id}`

Get job status and metadata.

**Response Schema (`JobStatus`):**
```python
class JobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    progress: int  # 0-100
    message: str | None
    result_url: str | None  # Set when completed
    created_at: datetime
    updated_at: datetime
    error: str | None  # Set when failed
```

---

#### `GET /api/v1/jobs/{job_id}/result`

Download the processed result file.

**Response:**
- Content-Type: `text/plain; charset=utf-8`
- Content-Disposition: `attachment; filename="result_{job_id}.txt"`
- Body: Processed sentences (UTF-8, one per line)

**Error Responses:**
- `404` - Job not found
- `425` - Job not completed yet
- `410` - Job failed or expired

---

#### `GET /api/v1/health`

Health check endpoint.

**Response Schema (`HealthResponse`):**
```python
class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    redis: bool  # Redis connectivity
    volume: bool  # Persistent volume accessible
    timestamp: datetime
```

---

## Type Safety Implementation

### Strict Typing Rules

**pyproject.toml:**
```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_any_generics = true
disallow_subclassing_any = true
disallow_untyped_calls = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

# No escape hatches
allow_any_expr = false
allow_any_decorated = false
allow_any_explicit = false
allow_any_generics = false
```

### Type Annotations Example

**Bad (rejected):**
```python
def process(data):  # Missing return type
    result = json.loads(data)  # 'result' is Any
    return result

def fetch(url: str) -> Any:  # Explicit Any forbidden
    ...
```

**Good (required):**
```python
from typing import TypedDict

class ProcessedData(TypedDict):
    sentences: list[str]
    count: int

def process(data: str) -> ProcessedData:
    parsed: dict[str, object] = json.loads(data)
    # Validate and narrow types
    if not isinstance(parsed, dict):
        raise ValueError("Expected dict")
    sentences = parsed.get("sentences")
    if not isinstance(sentences, list):
        raise ValueError("Expected sentences list")
    count = parsed.get("count")
    if not isinstance(count, int):
        raise ValueError("Expected count int")
    return ProcessedData(sentences=sentences, count=count)
```

---

## Testing Strategy

### Coverage Requirements

**pytest.ini:**
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --cov=api
    --cov=core
    --cov-report=term-missing
    --cov-report=html
    --cov-branch
    --cov-fail-under=100
    --strict-markers
```

### Test Organization

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from api.main import create_app

@pytest.fixture
def client() -> TestClient:
    """Fixture providing test client."""
    app = create_app()
    return TestClient(app)

@pytest.fixture
def redis_mock() -> MockRedis:
    """Fixture providing mock Redis."""
    return MockRedis()
```

### Test Cases (Examples)

**Unit Test:**
```python
def test_transliterate_kazakh_to_ipa() -> None:
    """Test Kazakh Cyrillic -> IPA transliteration."""
    result = transliterate_to_ipa("ÒšÐ°Ð·Ð°Ò›ÑÑ‚Ð°Ð½", lang="kk")
    assert result == "qÉ‘zÉ‘qstÉ‘n"
    assert isinstance(result, str)
```

**Integration Test:**
```python
def test_create_job_returns_valid_id(client: TestClient) -> None:
    """Test POST /api/v1/jobs returns valid job ID."""
    response = client.post(
        "/api/v1/jobs",
        json={
            "source": "oscar",
            "language": "kk",
            "max_sentences": 1000,
            "transliterate": True,
            "confidence_threshold": 0.95,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert UUID(data["job_id"])  # Valid UUID
    assert data["status"] == "queued"
```

### Branch Coverage Example

```python
def process_sentence(text: str, lang: str) -> str:
    """Process sentence with full branch coverage."""
    if not text:  # Branch 1
        return ""
    if lang not in SUPPORTED_LANGS:  # Branch 2
        raise ValueError(f"Unsupported language: {lang}")
    return transliterate(text, lang)

# Tests must cover:
# 1. Empty string input
# 2. Unsupported language
# 3. Valid input
```

---

## Development Workflow

### Makefile Targets

```makefile
.PHONY: install check test lint format clean

install:
	poetry install --no-interaction

check: lint test
	@echo "All checks passed!"

lint:
	poetry run ruff check .
	poetry run mypy api core tests

test:
	poetry run pytest --cov=api --cov=core --cov-branch --cov-fail-under=100

format:
	poetry run ruff format .
	poetry run ruff check --fix .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov
```

### Pre-Commit Checklist

Before every commit:
```bash
make check  # Must pass 100%
```

This runs:
1. `ruff check .` - Linting (no warnings allowed)
2. `mypy api core tests` - Type checking (strict mode)
3. `pytest --cov-fail-under=100` - Tests with 100% coverage

---

## Dependency Management

### Poetry Configuration

**pyproject.toml (dependencies):**
```toml
[tool.poetry.dependencies]
python = "^3.11"

# Web framework
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.32.0"}
pydantic = "^2.9.0"
pydantic-settings = "^2.6.0"

# Job queue
redis = "^5.2.0"
rq = "^2.0.0"

# Core functionality (from original repo)
PyICU = "^2.13"
fasttext-wheel = "^0.9.2"
numpy = "^1.26,<2"
datasets = "^3.6.0"

# Utilities
python-dotenv = "^1.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.0"
pytest-cov = "^6.0.0"
pytest-asyncio = "^0.24.0"
ruff = "^0.8.0"
mypy = "^1.13.0"
types-redis = "^4.6.0"

[tool.poetry.group.test.dependencies]
httpx = "^0.27.0"  # For TestClient
fakeredis = "^2.25.0"  # Mock Redis
```

**Lock file discipline:**
- `poetry.lock` is committed
- `poetry update` only when intentional
- Review lock file changes in PRs

---

## Error Handling

### Structured Error Responses

```python
from typing import Literal

class ErrorResponse(BaseModel):
    error: str
    code: Literal[
        "INVALID_REQUEST",
        "JOB_NOT_FOUND",
        "JOB_FAILED",
        "RATE_LIMIT_EXCEEDED",
        "INTERNAL_ERROR",
    ]
    details: dict[str, object] | None = None
    timestamp: datetime
```

### Exception Hierarchy

```python
class TurkicAPIError(Exception):
    """Base exception for all API errors."""
    pass

class JobNotFoundError(TurkicAPIError):
    """Job ID not found."""
    pass

class UnsupportedLanguageError(TurkicAPIError):
    """Language not supported."""
    pass

class CorpusDownloadError(TurkicAPIError):
    """Failed to download corpus."""
    pass
```

### FastAPI Exception Handlers

```python
@app.exception_handler(JobNotFoundError)
async def job_not_found_handler(
    request: Request, exc: JobNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": str(exc),
            "code": "JOB_NOT_FOUND",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
```

---

## Deployment

### Railway Configuration

**railway.toml:**
```toml
[build]
builder = "dockerfile"

[deploy]
startCommand = "uvicorn api.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/v1/health"
healthcheckTimeout = 100
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 10
```

### Environment Variables (Railway)

```bash
# Auto-provided by Railway
PORT=8000
RAILWAY_ENVIRONMENT=production
REDIS_URL=redis://default:password@redis.railway.internal:6379

# Mount path for persistent volume
DATA_DIR=/data

# Application config
LOG_LEVEL=INFO
CORS_ORIGINS=https://yourdomain.github.io
```

### Docker Multi-Stage Build

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder
RUN pip install poetry==1.8.3
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# Stage 2: Runtime
FROM python:3.11-slim
RUN apt-get update && apt-get install -y libicu-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/ api/
COPY core/ core/
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Security

### Input Validation

- All inputs validated with Pydantic
- SQL injection: N/A (no SQL database)
- Command injection: No shell commands executed
- Path traversal: Job IDs are UUIDs, not user-provided paths

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/jobs")
@limiter.limit("10/hour")
async def create_job(request: Request, job: JobCreate) -> JobResponse:
    ...
```

### CORS Policy

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.github.io"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

---

## Monitoring & Observability

### Structured Logging

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        return json.dumps(log_obj)
```

### Health Checks

```python
@app.get("/api/v1/health")
async def health_check(redis: Redis = Depends(get_redis)) -> HealthResponse:
    redis_ok = await redis.ping()
    volume_ok = Path("/data").exists()

    status: Literal["healthy", "degraded", "unhealthy"]
    if redis_ok and volume_ok:
        status = "healthy"
    elif redis_ok or volume_ok:
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthResponse(
        status=status,
        redis=redis_ok,
        volume=volume_ok,
        timestamp=datetime.utcnow(),
    )
```

---

## Migration from Original Repo

### What We Keep
- âœ… `core/rules/*.rules` - ICU transliteration rules
- âœ… Core transliteration logic (refactored with strict types)
- âœ… FastText language ID (refactored)
- âœ… Corpus streaming utilities (refactored)

### What We Remove
- âŒ Gradio UI
- âŒ CLI tools
- âŒ HuggingFace Spaces config
- âŒ SentencePiece training
- âŒ Language model training/eval
- âŒ PyPI packaging

### Refactoring Strategy
1. Copy minimal code from original repo
2. Add complete type annotations
3. Remove all `Any` types
4. Write tests for 100% coverage
5. Run `make check` - must pass

---

## Success Criteria

Before considering this project "done":

- [ ] `make check` passes with zero warnings
- [ ] 100% test coverage (statements + branches)
- [ ] Zero `Any` types in codebase
- [ ] All endpoints return proper types
- [ ] API documented with OpenAPI schema
- [ ] Docker build succeeds
- [ ] Railway deployment works
- [ ] Health check endpoint returns 200
- [ ] Can process 10k sentence corpus end-to-end

---

## Open Questions

1. **Job retention**: How long do we keep completed jobs? (24h? 7d?)
2. **Rate limiting**: What limits? (10/hour? 100/day?)
3. **Authentication**: Do we need it? (JWT? API keys?)
4. **Analytics**: Do we track usage? (Plausible? PostHog?)
5. **Caching**: Should we cache common corpus downloads?

---

## Next Steps

1. Clean up forked repo (remove unnecessary files)
2. Set up `pyproject.toml` with strict type checking
3. Create API skeleton with full type annotations
4. Write tests (TDD approach)
5. Implement core logic with 100% coverage
6. Add Docker + Railway configs
7. Deploy and validate

---

## License

MIT / Apache-2.0 (inherited from original repo)

