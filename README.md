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