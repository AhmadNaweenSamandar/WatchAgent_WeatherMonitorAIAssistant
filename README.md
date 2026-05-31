# WatchAgent_WeatherMonitorAIAssistant

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


## 4.5 Application Lifecycle & Resource Management
* **Implementation Focus:** Centralized startup and graceful teardown.
* **Core Decisions and Technical Justifications:**
  1. **FastAPI Lifespan Context:** Replaced legacy startup/shutdown events with the modern `lifespan` async context manager. This ensures the database schema initializes and the background polling safely spins up before the API accepts web traffic.
  2. **Graceful Task Cancellation:** The background poller is tracked as an explicit `asyncio.Task`. On application shutdown, the system intercepts the signal, cancels the polling task, and safely closes the database connection pool. This prevents unnecessary processes and corrupted SQLite locks during Docker container teardown.



## 5. Test-Driven Development (TDD) & Quality Assurance
* **Implementation Focus:** Validation of system constraints and business logic prior to implementation. 
* **Core Decisions and Technical Justifications:**
  1. **Strict Mocking (`respx`):** The Open-Meteo API is strictly mocked during the test lifecycle to prevent rate-limiting and ensure tests can run reliably in offline CI/CD pipelines.
  2. **Deduplication Validation:** The `test_poller.py` suite explicitly validates our Phase 3 SQLite constraints, proving that duplicate API fetches result in zero database mutations.
  3. **TDD for Domain Logic (The Three Custom Triggers):** As outlined by standard Software Quality Assurance principles, the complex meteorological reasoning engine was constructed using Test-Driven Development. We wrote strictly controlled, failing tests for our three custom events *before* implementing the logic to ensure zero regression:
     * **The Freezing Rain Pivot:** We assert that the system correctly fires an event when the temperature crosses the 0°C threshold while precipitation is actively falling (> 0mm).
     * **The Stagnant Heat Dome:** We assert that the system successfully tracks state over time, only firing when apparent temperature > 32°C AND wind speed < 5km/h for exactly three consecutive readings.
     * **The Apparent Divergence:** We assert that the system identifies hidden human hazards by firing when the delta between actual and apparent temperature exceeds 10°C under high wind conditions somehthing like 45km/hr.



## 6. Meteorological Event Engine & Strategy Pattern
* **Implementation Focus:** Executing domain logic with strict memory boundaries and pure function isolation.
* **Core Decisions and Technical Justifications:**
  1. **Two-Tier Strategy Architecture (SRP):** We rejected single-file monolithic logic in favor of strict separation of concerns. `src/events/triggers.py` contains strictly pure Python functions evaluating numerical arrays, completely oblivious to the database. `src/events/engine.py` acts as the orchestrator, pulling data and handling storage. This guarantees our business logic can be unit-tested without complex database mocking.
  2. **O(1) Memory Constraints:** To prevent the application from crashing due to Out-Of-Memory (OOM) errors as the database grows, the engine enforces a strict context window (`LIMIT 3`) when querying historical readings. This guarantees the background polling daemon consumes the exact same microscopic memory footprint on Year 5 as it does on Day 1.
  3. **Bi-Directional Environmental Safety:** The AI-assisted baseline logic for the Freezing Rain Pivot only checked for temperature drops. We manually overrode this to include rapid thawing spikes (crossing 0°C from below while raining), reflecting a deeper domain awareness of municipal infrastructure hazards.


## 7. Data Delivery Layer & Agent Integration (API Contract Validation)
* **Implementation Focus:** Exposing raw telemetry and generated event buffers via validated API contracts, while establishing an agentic threshold tuner.
* **Core Decisions and Technical Justifications:**
  1. **Strict Query Parameter Scoping:** Implemented explicit routing contracts for `GET /health`, `GET /readings`, and `GET /events` using FastAPI dependencies. The endpoints enforce strict filtering constraints (`city` string validation and a hard max capacity `limit=100`) to guarantee client-side performance remains stable.
  2. **FastAPI Contract Inversion (TDD):** Adhering to strict SQA standards, we wrote functional contract validation tests inside `tests/test_api.py` using `httpx.AsyncClient` to force a `404 Red Phase` before activating the routing layer. This protects the frontend from silent data contract drift.
  3. **Cursor Agent Skill Ingestion:** Provisioned an automated threshold-tuning ecosystem (`.cursor/agents/threshold_tuner.md` and `.cursor/skill/replay_historical_data.py`). This allows an AI agent to execute local Python scripts, calculate event frequencies, and propose micro-adjustments to the rule matrix without human intervention.