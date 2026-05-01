"""Benchmarking via decorator + context var for per-conversation tracking.

Usage:
    # at request boundary, set session context
    bench.set_session("session-abc-123")

    # on any function — async or sync
    @benchmark
    async def classify(text: str) -> Classification:
        ...

    # later: pull timings
    bench.get_session_report("session-abc-123")
    bench.get_fn_report("classify")
"""

from __future__ import annotations

import contextvars
import time
from collections import defaultdict
from functools import wraps
from inspect import iscoroutinefunction

_session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "bench_session_id", default=None
)

# session_id -> [{fn, ms}]
_session_timings: dict[str, list[dict]] = defaultdict(list)
# fn_name -> [ms]
_fn_timings: dict[str, list[float]] = defaultdict(list)


def set_session(session_id: str):
    """Set the active session for benchmark attribution."""
    _session_id.set(session_id)


def benchmark(fn):
    """Decorator that records wall-clock time per call.

    Automatically attributes to the active session if set via set_session().
    Works on both async and sync functions.
    """
    name = fn.__qualname__

    if iscoroutinefunction(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = await fn(*args, **kwargs)
            ms = (time.perf_counter() - start) * 1000
            _record(name, ms)
            return result
    else:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = fn(*args, **kwargs)
            ms = (time.perf_counter() - start) * 1000
            _record(name, ms)
            return result

    return wrapper


def _record(fn_name: str, ms: float):
    ms = round(ms, 2)
    _fn_timings[fn_name].append(ms)
    sid = _session_id.get()
    if sid:
        _session_timings[sid].append({"fn": fn_name, "ms": ms})


def get_session_report(session_id: str) -> dict:
    """Per-conversation breakdown: each function call + total."""
    entries = _session_timings.get(session_id, [])
    total = sum(e["ms"] for e in entries)
    return {"session_id": session_id, "total_ms": round(total, 2), "calls": entries}


def get_fn_report(fn_name: str | None = None) -> dict:
    """Per-function stats across all sessions. Pass None for all functions."""
    if fn_name:
        times = _fn_timings.get(fn_name, [])
        return _fn_stats(fn_name, times)

    return {name: _fn_stats(name, times) for name, times in _fn_timings.items()}


def _fn_stats(name: str, times: list[float]) -> dict:
    if not times:
        return {"fn": name, "calls": 0}
    return {
        "fn": name,
        "calls": len(times),
        "avg_ms": round(sum(times) / len(times), 2),
        "min_ms": round(min(times), 2),
        "max_ms": round(max(times), 2),
        "p50_ms": round(sorted(times)[len(times) // 2], 2),
    }


def reset():
    """Clear all timings."""
    _session_timings.clear()
    _fn_timings.clear()
