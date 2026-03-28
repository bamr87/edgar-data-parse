"""Key=value job lines for ingestion commands (log aggregators can parse as structured)."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


def _format_kv(job: str, duration_ms: int, fields: dict[str, Any]) -> str:
    parts = [f"job={job}", f"duration_ms={duration_ms}"]
    for k in sorted(fields):
        v = fields[k]
        if v is None:
            continue
        parts.append(f"{k}={v}")
    return " ".join(parts)


@contextmanager
def ingest_job_context(
    logger: logging.Logger,
    job: str,
    **initial: Any,
) -> Iterator[dict[str, Any]]:
    """Attach timing and optional counters; log one line on success or failure."""
    t0 = time.monotonic()
    fields: dict[str, Any] = dict(initial)
    err: BaseException | None = None
    try:
        yield fields
    except BaseException as e:
        err = e
        fields["error_class"] = type(e).__name__
        raise
    finally:
        duration_ms = int((time.monotonic() - t0) * 1000)
        msg = _format_kv(job, duration_ms, fields)
        if err is None:
            logger.info(msg)
        else:
            logger.error(msg, exc_info=isinstance(err, Exception))
