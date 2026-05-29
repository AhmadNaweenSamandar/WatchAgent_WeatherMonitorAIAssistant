# WatchAgent_WeatherMonitorAIAssistant

1. Cursor Integration Workspace (.cursor/)
This codebase integrates direct programmatic instructions and automated quality assurance metrics within the local IDE workspace:

Rules (.cursor/rules/)

"*" poller_resiliency.md: Hard-constrains code generation engines to implement defensive exception-handling blocks across external API requests, forcing network logging at WARNING thresholds and protecting the longevity of background loop lifecycles.

"*" immutable_events.md: Protects audit data integrity by forbidding any auto-generation of destructive actions (UPDATE/DELETE) over event logging operations, ensuring an unalterable history log.