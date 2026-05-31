# WatchAgent: Weather Monitor & AI Assistant

An autonomous meteorological monitoring system that polls live weather data from Open-Meteo, stores telemetry in SQLite, detects notable environmental events, and exposes everything through a validated HTTP API.

---

## System Overview

WatchAgent runs as a single FastAPI process with two concurrent responsibilities:

1. **Background poller** — every 10 minutes, fetches current weather for Ottawa, Toronto, and Vancouver from Open-Meteo, deduplicates readings at the database layer, and feeds new data into the event engine.
2. **HTTP API** — serves health metrics, raw readings, and detected events to clients on port `8000`.

The system is designed for **auditability** (append-only events log), **resiliency** (network failures never crash the poller), and **contract stability** (TDD-validated API responses). Cursor rules, agents, and skills are embedded in `.cursor/` to guide AI-assisted development and threshold tuning.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WatchAgent Process (Uvicorn)                        │
│                                                                             │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────────────┐  │
│  │  Open-Meteo  │    │  Background      │    │  FastAPI HTTP API        │  │
│  │  REST API    │───▶│  Poller Loop     │    │  (src/api/routes.py)     │  │
│  │  (external)  │    │  (poller.py)     │    │                          │  │
│  └──────────────┘    │                  │    │  GET /health             │  │
│         ▲            │  every 600s:     │    │  GET /readings           │  │
│         │            │  fetch → save →  │    │  GET /events             │  │
│         │            │  evaluate_events │    └────────────┬─────────────┘  │
│         │            └────────┬─────────┘                 │                │
│         │                     │                           │ read           │
│         │                     ▼                           ▼                │
│         │            ┌────────────────────────────────────────────┐        │
│         │            │         SQLite (data/weather.db)           │        │
│         │            │  ┌──────────────┐    ┌──────────────────┐  │        │
│         └────────────│  │   readings   │    │     events       │  │        │
│    weather_client.py │  │  (deduped)   │    │  (append-only)   │  │        │
│                      │  └──────────────┘    └──────────────────┘  │        │
│                      └────────────────────────────────────────────┘        │
│                                     ▲                                      │
│                                     │ LIMIT 3 history window               │
│                            ┌────────┴─────────┐                            │
│                            │  Event Engine    │                            │
│                            │  (engine.py)     │                            │
│                            │       │          │                            │
│                            │       ▼          │                            │
│                            │  triggers.py     │                            │
│                            │  (3 pure rules)  │                            │
│                            └──────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Data flow:** Open-Meteo → `weather_client.py` → `poller.py` → `queries.save_reading()` → SQLite → `engine.evaluate_events()` → `queries.save_event()` → SQLite → API reads via `get_readings()` / `get_events()`.

---

## Project Structure

```
WatchAgent_WeatherMonitorAIAssistant/
├── .cursor/
│   ├── agents/threshold_tuner.md      # AI agent for threshold analysis
│   ├── rules/                         # Cursor coding constraints
│   │   ├── immutable_events.md
│   │   └── poller_resiliency.md
│   └── skill/replay_historical_data.py
├── .github/workflows/ci.yml           # GitHub Actions pytest pipeline
├── src/
│   ├── api/
│   │   ├── main.py                    # FastAPI app + lifespan (poller startup)
│   │   └── routes.py                  # /health, /readings, /events
│   ├── core/
│   │   ├── config.py                  # Pydantic Settings (.env loading)
│   │   ├── poller.py                  # 10-minute background loop
│   │   └── weather_client.py          # Open-Meteo HTTP client
│   ├── db/
│   │   ├── database.py                # Connection pool + schema init
│   │   └── queries.py                 # Parameterized SQL (CRUD)
│   └── events/
│       ├── engine.py                  # Orchestrator + deduplication
│       └── triggers.py                # Pure trigger functions (Strategy Pattern)
├── tests/
│   ├── conftest.py                    # Isolated temp DB per test
│   ├── test_api.py                    # API contract tests
│   ├── test_event_reasoning.py        # Event trigger TDD tests
│   └── test_pollar.py                 # Poller + deduplication tests
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

---

## Setup & Run Instructions

### Prerequisites

- Python 3.11+ (3.14 works for local dev; Docker uses 3.11)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (optional, for containerized runs)

### Local Development

```bash
# 1. Clone and enter the project
cd WatchAgent_WeatherMonitorAIAssistant

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Ensure DATABASE_URL resolves to a plain SQLite path for local runs:
#   DATABASE_URL=data/weather.db

# 5. Start the API + background poller
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API is available at **http://localhost:8000**. Interactive docs at **http://localhost:8000/docs**.

> **Note:** The poller runs every 10 minutes. Readings may not appear immediately after startup — wait for the first poll cycle or check logs for `New reading stored for ...`.

### Docker

```bash
cp .env.example .env
docker compose up --build
```

After code changes, always rebuild:

```bash
docker compose down
docker compose up --build
```

Data persists in the Docker named volume `weather_data` mounted at `/app/data/weather.db`.

### Inspecting the Database

```bash
# Local
sqlite3 data/weather.db "SELECT COUNT(*) FROM readings;"

# Docker
docker compose exec api sqlite3 data/weather.db "SELECT city, timestamp, temperature_2m FROM readings LIMIT 5;"
```

---

## API Reference

All successful responses return **HTTP 200**. The status code is in the response header, not the JSON body. Use `curl -i` to see it.

### `GET /health`

Returns system status and stored record counts.

**Response:**
```json
{
  "status": "ok",
  "readings_stored": 3,
  "events_stored": 0
}
```

```bash
curl -i http://localhost:8000/health
curl http://localhost:8000/health
```

---

### `GET /readings`

Returns stored weather telemetry, most recent first.

| Parameter | Required | Default | Description |
|---|---|---|---|
| `city` | No | — | Filter by city name (e.g. `Ottawa`) |
| `limit` | No | `50` | Maximum number of records (minimum `1`) |

**Response:**
```json
{
  "readings": [
    {
      "id": 1,
      "city": "Ottawa",
      "timestamp": "2026-05-30T21:30",
      "temperature_2m": 16.4,
      "apparent_temperature": 14.5,
      "precipitation": 0.0,
      "wind_speed_10m": 7.0,
      "weather_code": 0,
      "created_at": "2026-05-31 01:42:16"
    }
  ]
}
```

```bash
curl "http://localhost:8000/readings?city=Ottawa&limit=50"
curl "http://localhost:8000/readings?limit=10"
curl "http://localhost:8000/readings"
```

---

### `GET /events`

Returns detected notable events, most recent first.

| Parameter | Required | Default | Description |
|---|---|---|---|
| `city` | No | — | Filter by city name |
| `limit` | No | `50` | Maximum number of records (minimum `1`) |

**Response:**
```json
{
  "events": [
    {
      "id": 1,
      "city": "Ottawa",
      "timestamp": "2026-01-01T11:00",
      "event_type": "FREEZING_RAIN_PIVOT",
      "description": "Temperature crossed the freezing point during active precipitation.",
      "reasoning": "Crossed the freezing point (2.0C -> -1.0C) with 5.0mm precip.",
      "created_at": "2026-05-31 02:00:00"
    }
  ]
}
```

```bash
curl "http://localhost:8000/events?city=Ottawa&limit=50"
curl "http://localhost:8000/events"
```

---

## Running Tests

Tests use an **isolated temporary SQLite database** — they never touch `data/weather.db`.

```bash
source venv/bin/activate
pip install -r requirements.txt
pytest          # run all tests
pytest -v       # verbose output
pytest tests/test_api.py -v          # API contract tests only
pytest tests/test_event_reasoning.py # event trigger tests only
```

**Test suites:**

| File | Coverage |
|---|---|
| `tests/test_api.py` | HTTP 200 contracts, JSON shapes, empty states |
| `tests/test_event_reasoning.py` | All three event triggers (TDD) |
| `tests/test_pollar.py` | Open-Meteo mocking (`respx`) + deduplication |

CI runs the full suite automatically on every push/PR to `main` via GitHub Actions (`.github/workflows/ci.yml`).

---

## Technology Choices

| Technology | Role | Justification |
|---|---|---|
| **FastAPI** | HTTP framework | Native `async`/`await` aligns with the poller and `aiosqlite`; automatic OpenAPI docs at `/docs`; dependency injection for DB connections; minimal boilerplate for the three required GET endpoints. |
| **Uvicorn** | ASGI server | Production-grade async server; standard FastAPI deployment target; used in both local dev and Docker. |
| **SQLite + aiosqlite** | Persistence | Zero external infrastructure for a monitoring agent; WAL mode enables concurrent poller writes and API reads; composite `UNIQUE` constraint handles deduplication atomically. |
| **Raw SQL (no ORM)** | Data access | Direct control over queries and indexes; no ORM overhead; `INSERT OR IGNORE` deduplication stays in the storage layer where it belongs. |
| **httpx** | HTTP client | Async-compatible Open-Meteo client; pairs with `respx` for test mocking. |
| **Pydantic Settings** | Configuration | Type-safe `.env` loading for API URLs and runtime flags without hardcoding secrets or endpoints. |
| **pytest + pytest-asyncio** | Testing | First-class async test support for poller, DB, and API layers. |
| **respx** | Test mocking | Intercepts outbound HTTP in tests — no live network calls, no rate-limit risk in CI. |
| **Docker Compose** | Deployment | Reproducible runtime; named volume isolates persistent DB from container lifecycle. |

---

## Event Detection Design

The event system uses a **Strategy Pattern** split across two modules:

- **`src/events/triggers.py`** — pure functions; no database imports; easy to unit test.
- **`src/events/engine.py`** — fetches the last 3 readings (`LIMIT 3` for O(1) memory), runs each trigger, deduplicates by `(city, timestamp, event_type)`, and appends to the immutable events log.

Events fire **only when a new reading is inserted** (not on duplicates).

### Trigger 1: Freezing Rain Pivot (`FREEZING_RAIN_PIVOT`)

**Condition:** Precipitation > 0 AND temperature crosses 0°C in either direction between the two most recent readings.

**Reasoning:** Rain falling while the air mass crosses the freezing line creates freezing rain — a high-impact municipal hazard (road icing, power lines). Bi-directional detection (both warming through 0°C and cooling through 0°C) captures thaw-refreeze cycles, not just drops below zero.

### Trigger 2: Stagnant Heat Dome (`HEAT_DOME_ALERT`)

**Condition:** All 3 most recent readings have apparent temperature > 32°C AND wind speed < 5 km/h.

**Reasoning:** Sustained high apparent heat with stagnant air indicates a heat dome — dangerous because the body cannot cool via convection. Requiring **3 consecutive** readings prevents single-spike false positives and models genuine persistence.

### Trigger 3: Apparent Divergence (`APPARENT_DIVERGENCE`)

**Condition:** \|actual − apparent temperature\| > 10°C AND wind speed > 30 km/h (on the current reading).

**Reasoning:** A large gap between measured and "feels like" temperature under high wind signals a hidden human hazard — conditions feel far worse (or better) than the raw number suggests. Wind amplifies perceived exposure risk in cold environments especially.

All events are **append-only** — no updates or deletes — preserving a complete audit trail.

---

## Cursor Setup

This project embeds AI-assisted development tooling in `.cursor/`. Each file serves a distinct purpose:

### Rules (`.cursor/rules/`)

Rules are persistent instructions injected into Cursor's code generation context.

| Rule | File | Purpose |
|---|---|---|
| **Poller Resiliency** | `poller_resiliency.md` | Forces defensive `try/except` around all Open-Meteo HTTP calls; requires `WARNING`-level logging with city, status code, and error message; forbids poller loop crashes on network failure. |
| **Immutable Events** | `immutable_events.md` | Forbids `UPDATE`/`DELETE` on the `events` table; enforces append-only event logging; requires deduplication via SQLite `UNIQUE` constraints + `INSERT OR IGNORE` on readings. |

### Agents (`.cursor/agents/`)

Agents are specialized AI personas with defined objectives.

| Agent | File | Purpose |
|---|---|---|
| **Meteorological Threshold Tuner** | `threshold_tuner.md` | Analyzes signal-to-noise ratio of event triggers; runs the replay skill script; suggests threshold adjustments in `triggers.py` if an event type fires more than 5 times in 24 hours. |

### Skills (`.cursor/skill/`)

Skills are executable scripts agents can invoke for data-driven decisions.

| Skill | File | Purpose |
|---|---|---|
| **Replay Historical Data** | `replay_historical_data.py` | Queries the local SQLite database and outputs JSON event frequency counts grouped by `event_type`. Used by the Threshold Tuner agent before recommending trigger adjustments. |

**Run the skill manually:**
```bash
python .cursor/skill/replay_historical_data.py
```

---

## Implementation Phases (Detailed Design Record)

The sections below document each architectural phase and the technical decisions made during development.

---

## 1. Cursor Integration Workspace (.cursor/)
This codebase integrates direct programmatic instructions and automated quality assurance metrics within the local IDE workspace:

### Rules (.cursor/rules/)

* **poller_resiliency.md:** Hard-constrains code generation engines to implement defensive exception-handling blocks across external API requests, forcing network logging at WARNING thresholds and protecting the longevity of background loop lifecycles.

* **immutable_events.md:** Protects audit data integrity by forbidding any auto-generation of destructive actions (UPDATE/DELETE) over event logging operations, ensuring an unalterable history log.


## 2. Data Persistence Layer & Native Deduplication Architecture
* **Implementation Focus:** High-concurrency data safety and zero-overhead structural operations.
* **Core Decisions and Technical Justifications:**
  1. **Raw SQL over ORM Layer:** To show deep mechanical sympathy with our engine storage targets, we chose pure parameterized SQL executed through asynchronous wrappers (`aiosqlite`). This completely eliminates the execution overhead, query bloat, and context window footprint of large ORM compilation engines like SQLAlchemy.
  2. **Write-Ahead Logging (WAL Mode):** SQLite naturally locks database files during write executions. By programmatically initializing connections with `PRAGMA journal_mode=WAL;`, we separate read and write channels. This guarantees our 10-minute automated background loop can write updates without ever causing a lock contention or blocking web users querying API analytics.
  3. **Atomic DB-Level Deduplication:** The requirement to store unique readings per city/timestamp combination is enforced using a database-level composite `UNIQUE(city, timestamp)` index. Rather than pulling records into memory and writing slow checking loops in Python, we handle collision prevention instantly inside the storage layer using `INSERT OR IGNORE`. This removes potential multi-threaded race conditions entirely.
  4. **Strict Immutability Constraints:** Aligning with our workspace configurations, our database access module provides no updates or deletion paths for event structures, treating security trends as an unalterable log.


## 3. Asynchronous Polling & Resiliency Infrastructure
* **Implementation Focus:** Network fault tolerance and API etiquette.
* **Core Decisions and Technical Justifications:**
  1. **10-Minute Polling Cadence:** The Open-Meteo API updates hourly. Instead of aggressive 1-minute polling (which wastes bandwidth and violates API etiquette), we implemented a 10-minute `asyncio.sleep` loop. This guarantees we capture the hourly update rapidly while keeping the network footprint microscopic.
  2. **Defensive Network Isolation:** Following the `.cursor/rules/poller_resiliency.md` contract, the HTTPX client strictly wraps all calls in exception handlers. Timeouts or 500-level upstream errors trigger a localized `WARNING` log but are swallowed by the client, ensuring the master `while True` daemon never crashes.
  3. **Schema Normalization:** The `weather_client.py` isolates third-party data structures, mapping Open-Meteo's `time` field to our internal `timestamp` schema before returning it, keeping the downstream database layer entirely agnostic of the third-party JSON shape.
  4. **Strict Configuration Decoupling:** The third-party API base URL (`OPEN_METEO_BASE_URL`) has been fully extracted out of the application code and bound to environment configurations using Pydantic Settings management. This allows seamless integration targeting mock HTTP engines during localized validation testing without changing source paths. Since the URL is public it is directly added to (.env.example).


## 4. Application Lifecycle & Resource Management
* **Implementation Focus:** Centralized startup and graceful teardown.
* **Core Decisions and Technical Justifications:**
  1. **FastAPI Lifespan Context:** Replaced legacy startup/shutdown events with the modern `lifespan` async context manager. This ensures the database schema initializes and the background polling safely spins up before the API accepts web traffic.
  2. **Graceful Task Cancellation:** The background poller is tracked as an explicit `asyncio.Task`. On application shutdown, the system intercepts the signal, cancels the polling task, and safely closes the database connection pool. This prevents unnecessary processes and corrupted SQLite locks during Docker container teardown.


## 5. Test-Driven Development (TDD) & Quality Assurance
* **Implementation Focus:** Validation of system constraints and business logic prior to implementation.
* **Core Decisions and Technical Justifications:**
  1. **Strict Mocking (`respx`):** The Open-Meteo API is strictly mocked during the test lifecycle to prevent rate-limiting and ensure tests can run reliably in offline CI/CD pipelines.
  2. **Deduplication Validation:** The `test_pollar.py` suite explicitly validates our Phase 3 SQLite constraints, proving that duplicate API fetches result in zero database mutations.
  3. **TDD for Domain Logic (The Three Custom Triggers):** As outlined by standard Software Quality Assurance principles, the complex meteorological reasoning engine was constructed using Test-Driven Development. We wrote strictly controlled, failing tests for our three custom events *before* implementing the logic to ensure zero regression:
     * **The Freezing Rain Pivot:** We assert that the system correctly fires an event when the temperature crosses the 0°C threshold while precipitation is actively falling (> 0mm).
     * **The Stagnant Heat Dome:** We assert that the system successfully tracks state over time, only firing when apparent temperature > 32°C AND wind speed < 5km/h for exactly three consecutive readings.
     * **The Apparent Divergence:** We assert that the system identifies hidden human hazards by firing when the delta between actual and apparent temperature exceeds 10°C under high wind conditions (> 30 km/h).


## 6. Meteorological Event Engine & Strategy Pattern
* **Implementation Focus:** Executing domain logic with strict memory boundaries and pure function isolation.
* **Core Decisions and Technical Justifications:**
  1. **Two-Tier Strategy Architecture (SRP):** We rejected single-file monolithic logic in favor of strict separation of concerns. `src/events/triggers.py` contains strictly pure Python functions evaluating numerical arrays, completely oblivious to the database. `src/events/engine.py` acts as the orchestrator, pulling data and handling storage. This guarantees our business logic can be unit-tested without complex database mocking.
  2. **O(1) Memory Constraints:** To prevent the application from crashing due to Out-Of-Memory (OOM) errors as the database grows, the engine enforces a strict context window (`LIMIT 3`) when querying historical readings. This guarantees the background polling daemon consumes the exact same microscopic memory footprint on Year 5 as it does on Day 1.
  3. **Bi-Directional Environmental Safety:** The AI-assisted baseline logic for the Freezing Rain Pivot only checked for temperature drops. We manually overrode this to include rapid thawing spikes (crossing 0°C from below while raining), reflecting a deeper domain awareness of municipal infrastructure hazards.


## 7. Data Delivery Layer & Agent Integration (API Contract Validation)
* **Implementation Focus:** Exposing raw telemetry and generated event buffers via validated API contracts, while establishing an agentic threshold tuner.
* **Core Decisions and Technical Justifications:**
  1. **Strict Query Parameter Scoping:** Implemented explicit routing contracts for `GET /health`, `GET /readings`, and `GET /events` using FastAPI dependencies. The endpoints enforce optional `city` filtering and a configurable `limit` parameter (default 50, minimum 1) to guarantee client-side performance remains stable while returning spec-compliant wrapped JSON payloads.
  2. **FastAPI Contract Inversion (TDD):** Adhering to strict SQA standards, we wrote functional contract validation tests inside `tests/test_api.py` using `httpx.AsyncClient` to force a `404 Red Phase` before activating the routing layer. This protects the frontend from silent data contract drift.
  3. **Cursor Agent Skill Ingestion:** Provisioned an automated threshold-tuning ecosystem (`.cursor/agents/threshold_tuner.md` and `.cursor/skill/replay_historical_data.py`). This allows an AI agent to execute local Python scripts, calculate event frequencies, and propose micro-adjustments to the rule matrix without human intervention.


## 8. Continuous Integration & Deployment Pipeline (CI/CD)
* **Implementation Focus:** Automated regression testing and DevOps readiness.
* **Core Decisions and Technical Justifications:**
  1. **GitHub Actions Integration:** Implemented a continuous integration workflow (`.github/workflows/ci.yml`) triggered on `main` branch pushes and Pull Requests.
  2. **Automated Validation:** The pipeline provisions an Ubuntu runner, restores cached pip dependencies (for optimal execution speed), and runs the full `pytest` suite. This guarantees that no pull request can be merged if it violates our core deduplication or meteorological logic.


## 9. Docker Containerization & Runtime Configuration
* **Implementation Focus:** Reproducible deployment, persistent storage isolation, and environment-driven runtime tuning.
* **Core Decisions and Technical Justifications:**
  1. **Production-Grade Base Image (`Dockerfile`):** The application is containerized on `python:3.11-slim` with `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1` to eliminate stale bytecode artifacts and guarantee real-time log streaming inside Docker Desktop and CI runners. Dependencies are installed strictly from `requirements.txt` before the full source tree is copied, maximizing Docker layer cache efficiency during iterative builds.
  2. **Operational SQLite Tooling:** The image installs the `sqlite3` CLI alongside Python dependencies, enabling direct in-container inspection of persisted telemetry (`SELECT` queries against `readings` and `events`) without rebuilding the image or attaching external debugging tools.
  3. **Single-Service Orchestration (`docker-compose.yml`):** A dedicated `api` service builds from the local `Dockerfile`, binds host port `8000:8000`, and injects runtime secrets and tuning parameters via `env_file: .env`. This decouples infrastructure wiring from application code while keeping local startup to a single `docker compose up` command.
  4. **Named Volume Persistence:** Rather than binding the entire repository into the container (which risks overwriting installed dependencies), a dedicated Docker named volume (`weather_data`) is mounted exclusively at `/app/data`. This guarantees the SQLite database survives container restarts, image rebuilds, and teardown cycles without polluting the host filesystem or leaking test artifacts into production data.
  5. **Environment Configuration Contract (`.env.example`):** All runtime variables are documented as a copy-paste template: `APP_ENV`, `LOG_LEVEL`, `DATABASE_URL` (targeting `data/weather.db` inside the persistent volume), `POLL_INTERVAL_SECONDS` (default 600-second polling cadence), and `OPEN_METEO_BASE_URL`. Developers duplicate this file to `.env` before launching Compose, ensuring identical configuration semantics across local machines and containerized deployments.
  6. **Process Supervision & Entrypoint:** The container declares `restart: always` for automatic recovery from daemon crashes, and the default `CMD` launches Uvicorn bound to `0.0.0.0:8000`, making the FastAPI lifespan handler (database initialization + background poller) immediately available to external HTTP clients upon container boot.


## 10. Debugging, API Contract Remediation & Runtime Verification
* **Implementation Focus:** Diagnosing stale deployment artifacts, enforcing exact HTTP response contracts, and validating live behaviour against automated tests.
* **Core Decisions and Technical Justifications:**
  1. **Single-Router Consolidation:** Removed the legacy inline `/health` handler from `src/api/main.py` and consolidated all three required endpoints inside `src/api/routes.py`. This eliminates route shadowing and guarantees a single authoritative contract surface for health metrics, readings, and events.
  2. **Spec-Compliant Response Envelopes:** Aligned live API output with the required contracts: `/health` returns `{ status, readings_stored, events_stored }` backed by `get_database_metrics()`, while `/readings` and `/events` return `{ readings: [...] }` and `{ events: [...] }` respectively rather than bare JSON arrays.
  3. **Contract-First Regression Tests:** Expanded `tests/test_api.py` to assert HTTP `200` status codes, exact JSON key shapes, full field presence on stored records, and empty-collection behaviour. This prevents silent contract drift between passing unit tests and broken curl verification.
  4. **Docker Stale-Image Diagnosis:** Identified that `docker compose up` without `--build` continues serving previously copied source layers inside the container. Operational fix: run `docker compose up --build` after any API change so the running container reflects the latest routing logic.
  5. **HTTP Status vs JSON Body Separation:** Verified that the `→ 200` requirement refers to the HTTP response status line (visible via `curl -i`), not a field inside the JSON payload. FastAPI automatically emits `200 OK` on successful GET handlers; the JSON body carries only domain data (`status`, `readings`, or `events`).
  6. **Runtime Database Path Resolution:** Ensured `_database_path()` resolves `DATABASE_URL` at call time rather than module import time, and that pytest sets the environment variable before importing database modules. This prevents test runs from accidentally targeting `data/weather.db` and producing `unable to open database file` errors during fixture setup.
