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