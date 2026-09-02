"""Content-addressed disk cache for network + LLM calls.

Makes the pipeline replayable and cheap: identical inputs never re-hit the
network or the model. Keyed by a hash of (namespace + payload). Stored as JSON
under .cache/ (gitignored). Committed *outputs* live under data/, not here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from .config import CACHE


def _key(namespace: str, payload: str) -> Path:
    h = hashlib.sha256(f"{namespace}\x00{payload}".encode()).hexdigest()[:24]
    return CACHE / f"{namespace}-{h}.json"


def cached(namespace: str, payload: str, produce: Callable[[], Any], *, use_cache: bool = True) -> Any:
    """Return cached value for (namespace, payload) or compute+store it.

    `produce` is only called on a miss (or when use_cache is False).
    """
    path = _key(namespace, payload)
    if use_cache and path.exists():
        return json.loads(path.read_text())["value"]
    value = produce()
    path.write_text(json.dumps({"payload": payload[:2000], "value": value}, indent=0))
    return value
