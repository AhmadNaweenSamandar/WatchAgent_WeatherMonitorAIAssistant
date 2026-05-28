# Rule: Immutable Event Sourcing

## Context
Our system detects "notable events" based on weather readings. To maintain a strict audit trail and preserve historical integrity, the `events` table in our database must be treated as an append-only log.

## Instructions for Cursor
Whenever writing SQL queries, database schemas, or Python logic interacting with the database (`src/db/queries.py` or similar), you MUST follow these constraints:

1. **Append-Only:** The `events` table is strictly append-only. 
2. **Forbidden Operations:** You are strictly forbidden from generating `UPDATE` or `DELETE` SQL statements targeting the `events` table. 
3. **Error Handling:** If an event is generated incorrectly, the system must not attempt to overwrite it. 
4. **Readings Deduplication:** The `readings` table should handle deduplication via SQLite `UNIQUE` constraints (for example, `UNIQUE(city, timestamp)` with `INSERT OR IGNORE`), rather than manual Python check-then-insert logic.