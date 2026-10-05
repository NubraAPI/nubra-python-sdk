# Schema Reference: Overview

Original source path: `api_rate_limits/README.md`

Rate Limits & API Usage (SDK 0.5.x, V3 payloads).

| API Category | Limit | Scope |
| --- | --- | --- |
| Trading APIs in PROD | 10 operations per second | per IP, standard unregistered algo guidance |
| Trading APIs in UAT | 100 operations per second | testing and simulation guidance |
| Historical Data usage | 60 requests per minute | analytical access |
| Live WebSocket streams | weight-based | per session |

Rules:

- UAT and PROD trading limits differ; do not treat UAT throughput as production-safe.
- Higher PROD throughput requires algo registration (support@nubra.io).
- Prefer WebSocket subscriptions over REST polling; unsubscribe unused streams to free session weight.
- Cache historical data locally and centralize throttling; use backoff on retries.
