# Rule: Poller Resiliency and API Etiquette

## Context
This project polls the Open-Meteo API on a continuous background loop. Third-party APIs are inherently unreliable.

## Instructions for Cursor
Whenever generating, modifying, or reviewing code related to the Open-Meteo API fetching logic (for example, `src/core/poller.py` or `src/core/weather_client.py`), you must strictly adhere to the following defensive programming standards:

1. **Never Crash the Loop:** The main asynchronous polling loop must never crash due to a network error, timeout, or malformed JSON response from the upstream API.
2. **Explicit Try/Except:** All HTTP requests (for example, using `httpx`) must be wrapped in specific `try/except` blocks targeting network exceptions (for example, `httpx.RequestError`, `httpx.HTTPStatusError`).
3. **Strict Logging Contract:** If a fetch fails, you must catch the exception and log it using Python's standard `logging` module at the `WARNING` level. The log message MUST include:
   - The city name that failed.
   - The HTTP status code (if available).
   - The specific error message.
4. **No Silent Failures:** Do not use `pass` in the except block. You must log the failure and allow the loop to continue to the next city or the next sleep cycle.