"""Synthetic selector/ledger models and unavailable runtime entry points.

The simulation_* functions operate only on explicit fake drivers and temporary
fixture data. They do not grant continuation, recovery or production quarantine.
Public check/quarantine/read interfaces refuse before driver or ledger effects."""
from __future__ import annotations

import datetime
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from .runtime_boundary import refuse_runtime
except ImportError:  # direct-script import
    from runtime_boundary import refuse_runtime


@dataclass(frozen=True)
class Step:
    """One locatable step in a write flow."""

    name: str
    locate: dict


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-") or "step"


def _screenshot(driver, step: Step, screenshots_dir: Path) -> str | None:
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = screenshots_dir / f"shadow-{_slug(step.name)}-{stamp}.png"
    try:
        got = driver.screenshot(str(path))
    except Exception:
        return None
    if isinstance(got, (bytes, bytearray)):
        path.write_bytes(got)
    elif isinstance(got, (str, os.PathLike)) and str(got) != str(path):
        src = Path(got)
        if src.exists() and not path.exists():
            path.write_bytes(src.read_bytes())
    return str(path) if path.exists() else None


def simulation_check(driver, steps: list[Step], screenshots_dir: str | os.PathLike) -> dict:
    """Model resolution with an explicitly injected fake driver.

    Only locate and screenshot are invoked on that fake; missing steps and
    locate exceptions become modeled drift. This helper grants no live
    browser, continuation or quarantine authority.
    """
    shots_dir = Path(screenshots_dir)
    drifted: list[str] = []
    errors: dict[str, str] = {}
    screenshots: dict[str, str] = {}
    for step in steps:
        try:
            found = bool(driver.locate(dict(step.locate)))
        except Exception as exc:  # a throwing locator is a drifted locator
            found = False
            errors[step.name] = f"{type(exc).__name__}: {exc}"
        if found:
            continue
        drifted.append(step.name)
        shot = _screenshot(driver, step, shots_dir)
        if shot:
            screenshots[step.name] = shot
    return {
        "ok": not drifted,
        "drifted": drifted,
        "checked": len(steps),
        "screenshots": screenshots,
        "errors": errors,
    }


def _ledger(store_path: str | os.PathLike) -> Path:
    return Path(store_path) / "quarantine.jsonl"


def simulation_quarantine(store_path: str | os.PathLike, handle: str, step_name: str, reason: str) -> str:
    """Append one quarantine record. Never edits the child's profile or state."""
    path = _ledger(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"handle": handle, "step": step_name, "reason": reason, "at": _now()}
    with open(path, "a") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return str(path)


def simulation_is_quarantined(store_path: str | os.PathLike, handle: str, step_name: str) -> bool:
    path = _ledger(store_path)
    if not path.exists():
        return False
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("handle") == handle and rec.get("step") == step_name:
                return True
    return False


def simulation_quarantined_steps(store_path: str | os.PathLike, handle: str) -> list[str]:
    """Every step currently quarantined for one child, oldest first."""
    path = _ledger(store_path)
    if not path.exists():
        return []
    out: list[str] = []
    with open(path) as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("handle") == handle and rec.get("step") not in out:
                out.append(rec.get("step"))
    return out

def check(driver, steps: list[Step], screenshots_dir: str | os.PathLike) -> dict:
    """Unavailable until driver and original action ownership are bound."""
    refuse_runtime("selector_shadow.check")


def quarantine(store_path: str | os.PathLike, handle: str, step_name: str, reason: str) -> str:
    refuse_runtime("selector_shadow.quarantine")


def is_quarantined(store_path: str | os.PathLike, handle: str, step_name: str) -> bool:
    refuse_runtime("selector_shadow.is_quarantined")


def quarantined_steps(store_path: str | os.PathLike, handle: str) -> list[str]:
    refuse_runtime("selector_shadow.quarantined_steps")
