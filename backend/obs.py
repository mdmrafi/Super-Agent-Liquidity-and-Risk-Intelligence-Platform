"""Lightweight in-process observability for the prototype API.

Single-process and in-memory by design -- enough to make request latency,
server-error rate, and LLM-fallback rate *visible* (structured logs + a
/api/health snapshot) without pulling in a metrics stack. Not a production
telemetry system; see docs/RELIABILITY_AND_OBSERVABILITY.md.
"""
import logging
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("super_agent")

_lock = threading.Lock()
_counters = {"requests": 0, "server_errors": 0, "llm_fallbacks": 0}
_started_at = time.time()


def incr(name, n=1):
    with _lock:
        _counters[name] = _counters.get(name, 0) + n


def snapshot():
    with _lock:
        requests = _counters["requests"]
        return {
            "uptime_seconds": round(time.time() - _started_at, 1),
            "requests": requests,
            "server_errors": _counters["server_errors"],
            "server_error_rate": (
                round(_counters["server_errors"] / requests, 4) if requests else 0.0
            ),
            "llm_fallbacks": _counters["llm_fallbacks"],
        }
