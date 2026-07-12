# Reliability & Observability

*Engineering-evidence deliverable for Master Specification §12 ("measurable
analytical and system evidence end to end", "API or processing latency",
"reliability and observability"). Complements the analytical metrics in
[RESPONSIBLE_DESIGN.md](./RESPONSIBLE_DESIGN.md) §2.*

This is a **prototype-scale** observability surface: single-process, in-memory
counters plus structured logs ([backend/obs.py](../backend/obs.py)). It is enough
to make latency, error rate, and degraded-path (LLM fallback) behaviour *visible
and measured* — not a production telemetry stack. Everything below was captured
against the running dev server; none of it is aspirational.

---

## 1. Structured request logging (trace)

Every HTTP request emits one structured log line via the `observe_requests`
middleware in [backend/api/main.py](../backend/api/main.py):

```
2026-07-12 08:17:19,802 INFO super_agent request method=GET path=/api/alerts status=200 duration_ms=4.0
2026-07-12 08:17:25,589 INFO super_agent request method=POST path=/api/alerts/alert_c00221/explain status=200 duration_ms=5674.0
```

`method`, `path`, `status`, and `duration_ms` are key=value so the log is
grep/parse-friendly. Unhandled exceptions are logged at `exception` level and
counted as server errors.

## 2. Reliability snapshot endpoint

`GET /api/health` (unauthenticated, so a monitor can poll it; exposes no agent,
provider, or alert data) returns a live snapshot:

```json
{ "status": "ok", "uptime_seconds": 10.4, "requests": 20,
  "server_errors": 0, "server_error_rate": 0.0, "llm_fallbacks": 1 }
```

- **requests / server_errors / server_error_rate** — request volume and the
  fraction that 5xx'd. Across this session's exercised traffic: **0 server
  errors**.
- **llm_fallbacks** — how many times the LLM explanation/chat layer degraded to
  its grounded template (see §4). A rising count is the signal that the upstream
  model is unavailable while the dashboard itself stays up.

## 3. Measured API latency

Measured live (`GET`, warm cache, N requests/route) against the running server at
the documented dataset volume (20 agents × 30 days, 227 calibration alerts):

| Endpoint | avg | p50 | p95 | max |
|---|---|---|---|---|
| `GET /api/alerts` (227 alerts) | 11.5 ms | 11.0 | 12.1 | 33.2 |
| `GET /api/agents/{id}/balances` | 5.1 ms | 4.3 | 5.4 | 38.6 |
| `GET /api/agents/{id}/analytics` (30-min buckets) | 77.8 ms | 76.0 | 84.8 | 146.5 |
| `GET /api/health` | 1.4 ms | 1.5 | 2.5 | 2.8 |

Batch pipeline (offline, not a request): **~63 s** to regenerate forecasts +
alerts for **16,046 transactions** (`python -m engine.main`). The transaction
CSV is parsed once and cached with mtime invalidation
([api/store.py](../backend/api/store.py)), which is why repeated `/alerts` and
`/balances` calls stay in the single-digit-millisecond range.

## 4. Degraded / late / conflicting input — measured behaviour

The spec asks specifically for "behaviour, logs, metrics, or traces during
delayed, missing, or inconsistent provider input". Three mechanisms, each with
captured evidence:

**(a) LLM upstream unavailable → grounded fallback (captured trace).** With the
OpenAI key rate-limited, an explain call degraded instead of failing:

```
2026-07-12 08:17:25,588 WARNING super_agent explain fallback alert=alert_c00221 lang=banglish reason=RateLimitError
```

The API still returned a correct, strictly-grounded Banglish answer built from the
alert's own fields — situation, evidence, uncertainty, and a safe next step — and
incremented `llm_fallbacks`:

> agent_05-er jonno liquidity shortage alert. Proman: bKash e-money balance:
> burn_rate -3,582 BDT/hour, time_to_shortage 0 minutes, confidence 59%

The request returned `200` (not `500`): the degrade is invisible to the user
except that the wording is the deterministic template rather than the model's
prose. The 5,674 ms latency on that one call is the model's own
timeout/rate-limit backoff before the fallback fired — visible in the request log
so a reviewer can see exactly where the time went.

**(b) Missing / null balances (Scenario C data faults) → lower confidence, no
misleading recommendation.** Corrupted (null) provider-balance readings are
forward-filled with the last known good value, and the fact that a fill happened
is tracked (`balance_was_filled`) and penalised in the confidence score, rather
than hidden ([engine/liquidity.py](../backend/engine/liquidity.py)). Measured on
the Scenario C provider/day: **mean confidence 0.32 in fault hours vs 0.43 in
that provider's clean hours** — the system lowers its own certainty exactly where
the feed is bad, and provider balances are never summed into a single
transferable figure.

**(c) Late / duplicated feeds → data-quality alert, not a silent guess.** A
dedicated `data_quality` alert type is raised from *observable* defects (null
balance, duplicate fingerprint, broken balance continuity) — independent of any
ground-truth label ([alerts/build.py](../backend/alerts/build.py)). Staleness
(gap since last reading) also feeds the confidence penalty, so a delayed feed
surfaces as reduced confidence on any forecast built over it.

## 5. Honest limitations

- In-memory counters reset on restart; there is no persistence, histogram export,
  or distributed tracing. A production deployment would emit these to a real
  metrics backend (Prometheus/OTel).
- Latency was measured on a single dev machine, warm cache, no concurrency load
  test. Numbers are illustrative of the shape (cached reads are cheap; the
  analytics grouping is the heaviest endpoint), not a capacity guarantee.
- `server_error_rate` counts only 5xx; expected authorization denials (401/403)
  and not-found (404) are normal control-flow, not reliability failures, and are
  deliberately excluded.
