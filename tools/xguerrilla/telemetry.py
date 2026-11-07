"""Telemetry (§26.6): what the harness did, in a form that survives a kill.

JSONL, one row per event, appended with a single O_APPEND write and fsync so a
truncated body never lands mid-line. Row `kind` is the discriminator; the
summariser reads the four kinds that matter — `typing` (IKI samples),
`label` (what the classifier said), `challenge` (X pushed a wall), and
`session` (did the cookie jar still work).
"""
from __future__ import annotations
import json
import math
import os
from collections import Counter
from datetime import datetime, timezone


def record(path: str, kind: str, **fields) -> dict:
    """Append one JSONL row. fsync'd before returning."""
    row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "kind": kind, **fields}
    line = (json.dumps(row, sort_keys=True, default=str) + "\n").encode("utf-8")
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line)
        os.fsync(fd)
    finally:
        os.close(fd)
    return row


def rows(path: str) -> list[dict]:
    try:
        fh = open(path, encoding="utf-8")
    except FileNotFoundError:
        return []
    out = []
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue           # a torn tail from a killed writer is not a crash
            if isinstance(obj, dict):
                out.append(obj)
    return out


def _stats(xs: list[float]) -> dict:
    n = len(xs)
    if n < 2:
        return {"n": n, "median": (xs[0] if xs else 0.0), "cv": 0.0, "skew": 0.0}
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    sd = math.sqrt(var)
    srt = sorted(xs)
    med = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2
    skew = sum(((x - mean) / sd) ** 3 for x in xs) / n if sd else 0.0
    return {"n": n, "median": med, "cv": sd / mean if mean else 0.0, "skew": skew}


def summarise(path: str) -> dict:
    """Per-kind counts, IKI shape, label histogram, challenges, re-login fraction."""
    data = rows(path)
    kinds: Counter = Counter()
    labels: Counter = Counter()
    ikis: list[float] = []
    challenges = 0
    sessions = relogins = 0

    for r in data:
        kind = r.get("kind")
        kinds[str(kind)] += 1
        if kind == "typing":
            sample = r.get("iki") or r.get("ikis") or []
            if isinstance(sample, (int, float)):
                sample = [sample]
            ikis.extend(float(v) for v in sample if isinstance(v, (int, float)))
        elif kind == "label":
            if r.get("label") is not None:
                labels[str(r["label"])] += 1
        elif kind == "challenge":
            challenges += 1
        elif kind == "session":
            sessions += 1
            if r.get("relogin") or r.get("ok") is False:
                relogins += 1

    iki = _stats(ikis)
    return {
        "rows": len(data),
        "kinds": dict(kinds),
        "labels": dict(labels),
        "challenges": challenges,
        "sessions": sessions,
        "relogin_fraction": (relogins / sessions) if sessions else 0.0,
        "iki": iki,
        "iki_n": iki["n"],
        "iki_median": iki["median"],
        "iki_cv": iki["cv"],
        "iki_skew": iki["skew"],
    }


def session_ok(path: str, handle: str) -> bool:
    """True when the newest `session` row for `handle` did not need a re-login."""
    last = None
    for r in rows(path):
        if r.get("kind") == "session" and r.get("handle") == handle:
            last = r
    if last is None:
        return False
    if last.get("ok") is not None:
        return bool(last["ok"])
    return not bool(last.get("relogin"))
