"""Synthetic child-state model and an unavailable runtime interface.

SimulationSupervisor preserves the local state-machine regression specimen.
Its healthy/ACTIVE defaults, degraded continuation and local recovery apply
only to explicit synthetic inputs and temporary fixtures. They do not decide
whether a real account may run. Supervisor refuses before state or persona I/O."""
from __future__ import annotations

import os
import sqlite3
import time
from enum import Enum
from pathlib import Path

try:
    from .runtime_boundary import refuse_runtime
except ImportError:  # direct-script import
    from runtime_boundary import refuse_runtime

STALE_HEALTH_S = 900
DEGRADED_ROLES = ("lead", "conversation")


class ChildState(str, Enum):
    ACTIVE = "ACTIVE"
    COOLING = "COOLING"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"
    DEGRADED = "DEGRADED"


def _ts(now=None) -> float:
    if now is None:
        return time.time()
    return float(now.timestamp()) if hasattr(now, "timestamp") else float(now)


class SimulationSupervisor:
    def __init__(self, db_path, personas):
        if not isinstance(personas, dict):
            raise TypeError("simulation personas must be an explicit mapping")
        self.db_path = str(db_path)
        Path(self.db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """CREATE TABLE IF NOT EXISTS child_state (
                 handle TEXT PRIMARY KEY, state TEXT NOT NULL,
                 reason TEXT NOT NULL DEFAULT '', cool_until REAL NOT NULL DEFAULT 0,
                 updated_at REAL NOT NULL);
               CREATE TABLE IF NOT EXISTS health (
                 id INTEGER PRIMARY KEY CHECK (id = 1), status TEXT NOT NULL,
                 reason TEXT NOT NULL DEFAULT '', updated_at REAL NOT NULL);""")
        if self.conn.execute("SELECT 1 FROM health WHERE id = 1").fetchone() is None:
            self.conn.execute(
                "INSERT INTO health(id, status, reason, updated_at) VALUES (1, 'healthy', '', ?)",
                (time.time(),))
            self.conn.commit()
        self._roles = self._load_roles(personas)

    def _load_roles(self, personas) -> dict[str, str]:
        """Roles supplied explicitly by the synthetic caller; no file discovery."""
        if not isinstance(personas, dict):
            raise TypeError("simulation personas must be an explicit mapping")
        roles: dict[str, str] = {}
        for handle, p in personas.items():
            role = p.get("role") if isinstance(p, dict) else getattr(p, "role", None)
            if role:
                roles[str(handle)] = str(role)
        return roles

    def role(self, handle: str) -> str:
        return self._roles.get(handle, "broadcast")

    # -- rows ---------------------------------------------------------------
    def _child(self, handle: str) -> dict:
        row = self.conn.execute("SELECT * FROM child_state WHERE handle = ?",
                                (handle,)).fetchone()
        if row is None:
            return {"handle": handle, "state": ChildState.ACTIVE.value, "reason": "",
                    "cool_until": 0.0, "updated_at": 0.0}
        return dict(row)

    def _put(self, handle: str, state: ChildState, reason: str = "", cool_until: float = 0.0,
             now=None) -> None:
        self.conn.execute(
            """INSERT INTO child_state(handle, state, reason, cool_until, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(handle) DO UPDATE SET state = excluded.state,
                 reason = excluded.reason, cool_until = excluded.cool_until,
                 updated_at = excluded.updated_at""",
            (handle, state.value, reason, cool_until, _ts(now)))
        self.conn.commit()

    def _health(self, now=None) -> dict:
        now = _ts(now)
        row = self.conn.execute("SELECT * FROM health WHERE id = 1").fetchone()
        if row is None:
            return {"status": "degraded", "reason": "no health row", "updated_at": 0.0,
                    "age_s": None, "stale": True, "effective": "degraded"}
        h = dict(row)
        age = now - h["updated_at"]
        stale = age > STALE_HEALTH_S
        h.update({"age_s": round(age, 3), "stale": stale,
                  "effective": "degraded" if h["status"] == "degraded" or stale else "healthy"})
        if stale and h["status"] != "degraded":
            h["reason"] = "health row older than 900 s"
        return h

    # -- health -------------------------------------------------------------
    def degrade(self, reason: str = "", now=None) -> None:
        self.conn.execute("UPDATE health SET status = 'degraded', reason = ?, updated_at = ?"
                          " WHERE id = 1", (reason, _ts(now)))
        self.conn.commit()

    def recover(self, now=None) -> None:
        self.conn.execute("UPDATE health SET status = 'healthy', reason = '', updated_at = ?"
                          " WHERE id = 1", (_ts(now),))
        self.conn.commit()

    # -- children -----------------------------------------------------------
    def activate(self, handle: str, now=None) -> None:
        self._put(handle, ChildState.ACTIVE, now=now)

    def cool(self, handle: str, minutes: float, now=None) -> None:
        now = _ts(now)
        self._put(handle, ChildState.COOLING, f"cooldown {minutes:g} min",
                  now + float(minutes) * 60.0, now=now)

    def quarantine(self, handle: str, reason: str = "", now=None) -> None:
        self._put(handle, ChildState.QUARANTINED, reason, now=now)

    def retire(self, handle: str, reason: str = "", now=None) -> None:
        self._put(handle, ChildState.RETIRED, reason, now=now)

    def can_run(self, handle: str, now=None) -> tuple[bool, str]:
        now = _ts(now)
        c = self._child(handle)
        state = c["state"]
        if state == ChildState.RETIRED.value:
            return False, c["reason"] or "retired"
        if state == ChildState.QUARANTINED.value:
            return False, c["reason"] or "quarantined"
        if state == ChildState.COOLING.value and now < c["cool_until"]:
            until = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(c["cool_until"]))
            return False, f"cooling until {until}"
        h = self._health(now)
        if h["effective"] != "healthy":
            role = self.role(handle)
            if role not in DEGRADED_ROLES:
                return False, f"degraded: {role} child paused ({h['reason'] or 'unhealthy'})"
        if state == ChildState.DEGRADED.value:
            return False, c["reason"] or "child degraded"
        return True, "ok"

    def pick(self, children: list[str], now=None) -> list[str]:
        now = _ts(now)
        return [h for h in children if self.can_run(h, now)[0]]

    def status(self, now=None) -> dict:
        now = _ts(now)
        rows = [dict(r) for r in self.conn.execute("SELECT * FROM child_state ORDER BY handle")]
        for r in rows:
            r["role"] = self.role(r["handle"])
            r["runnable"], r["why"] = self.can_run(r["handle"], now)
        health = self._health(now)
        counts = {s.lower(): sum(1 for r in rows if r["state"] == s.value) for s in ChildState}
        counts.update(children=len(rows), runnable=sum(1 for r in rows if r["runnable"]))
        return {"evidence_scope": "synthetic_model", "runtime_binding_available": False,
                "db": self.db_path, "health": health, "degraded": health["effective"] != "healthy",
                "children": rows, "counts": counts}

    def close(self) -> None:
        self.conn.close()


class Supervisor:
    """Unavailable runtime health/child interface; no state is initialized."""

    def __init__(self, db_path, personas=None):
        refuse_runtime("supervisor")
