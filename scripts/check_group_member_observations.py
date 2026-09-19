"""Fail closed on a split Group Pulse / member-observation / detail generation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import group_member_observations as observations
from engine.company_intelligence.contracts import canonical_json_bytes

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_ATTRS = {
    "projection": "data-member-observations-digest",
    "pulse": "data-member-observations-pulse-sha256",
}


def _read(path: Path, errors: list[str]) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError as exc:
        errors.append(f"{path}: absent or unreadable: {exc}")
        return None


def _json(raw: bytes | None, label: str, errors: list[str]) -> dict[str, Any] | None:
    if raw is None:
        return None
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        errors.append(f"{label}: invalid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label}: top level must be an object")
        return None
    return value

class _DetailHTML(HTMLParser):
    """Read the actual body and inline scripts without executing page JavaScript."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.bodies: list[list[tuple[str, str | None]]] = []
        self.scripts: list[str] = []
        self._script: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "body":
            self.bodies.append(attrs)
        elif tag == "script":
            attributes = dict(attrs)
            script_type = (attributes.get("type") or "").strip().lower()
            executable = script_type in ("", "text/javascript", "application/javascript", "module")
            self._script = [] if "src" not in attributes and executable else None

    def handle_data(self, data: str) -> None:
        if self._script is not None:
            self._script.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            if self._script is not None:
                self.scripts.append("".join(self._script))
            self._script = None


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate embedded JSON key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Any:
    raise ValueError("non-finite embedded JSON value")


def _read_detail(path: Path, errors: list[str]) -> tuple[dict[str, str | None], Any]:
    attrs: dict[str, str | None] = {key: None for key in _ATTRS}
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"detail page {path}: absent or unreadable: {exc}")
        return attrs, None
    page = _DetailHTML()
    page.feed(text)
    page.close()
    if len(page.bodies) != 1:
        errors.append(f"detail page {path}: requires exactly one body")
    else:
        for key, attr in _ATTRS.items():
            values = [value for name, value in page.bodies[0] if name == attr]
            if len(values) != 1:
                errors.append(f"detail page {path}: missing or duplicate {attr}")
            else:
                attrs[key] = values[0]

    # The existing template owns this JSON literal. Parse only that literal, not
    # a metadata-looking string/comment or an external script's ignored contents.
    # The owned template starts this script with the declaration; accepting a
    # declaration later in arbitrary JavaScript would also accept block comments.
    declaration = re.compile(r"\A\s*const[ \t]+DETAIL[ \t]*=[ \t]*")
    candidates = [(script, match.end()) for script in page.scripts
                  for match in declaration.finditer(script)]
    if len(candidates) != 1:
        errors.append(f"detail page {path}: requires one embedded DETAIL payload")
        return attrs, None
    script, start = candidates[0]
    decoder = json.JSONDecoder(object_pairs_hook=_unique_json_object,
                               parse_constant=_reject_json_constant)
    try:
        payload, end = decoder.raw_decode(script[start:].lstrip())
        suffix = script[start:].lstrip()[end:].lstrip()
        if not suffix.startswith(";") or not isinstance(payload, dict):
            raise ValueError("DETAIL must be one terminated JSON object literal")
    except (ValueError, TypeError, RecursionError) as exc:
        errors.append(f"detail page {path}: invalid embedded DETAIL payload: {exc}")
        return attrs, None
    return attrs, payload


def _bind_detail_payload(group_id: str, payload: Any, group: Any,
                         companion: Mapping[str, Any], pulse_digest: str | None,
                         errors: list[str]) -> None:
    if not isinstance(payload, Mapping):
        return  # The reader already records the missing/ambiguous payload.
    basket = payload.get("basket")
    if not isinstance(basket, Mapping) or basket.get("id") != group_id:
        errors.append(f"detail page {group_id}: embedded basket identity mismatch")
    expected = {
        key: companion.get(key) for key in (
            "schema", "authority", "as_of", "generated_at", "projection_digest",
        )
    }
    expected.update({"legacy_pulse_sha256": pulse_digest, "group": group})
    try:
        # Structural binding under the existing Python owner serialization also
        # distinguishes true from 1. Original pulse wire bytes are still hashed
        # directly; no browser parse/reserialize wire-digest check is introduced.
        matches = (canonical_json_bytes(payload.get("member_observations"))
                   == canonical_json_bytes(expected))
    except (ValueError, TypeError, OverflowError, RecursionError):
        matches = False
    if not matches:
        errors.append(f"detail page {group_id}: embedded member observations mismatch")


def _same_timestamp(left: Any, right: Any) -> bool:
    def parse(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except (TypeError, ValueError):
            return None
    left_dt = parse(left)
    right_dt = parse(right)
    return left_dt is not None and left_dt == right_dt


def _rounded_equal(left: Any, right: Any, digits: int = 4) -> bool:
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, bool) or isinstance(right, bool):
        return False
    try:
        return (math.isfinite(float(left)) and math.isfinite(float(right))
                and round(float(left), digits) == round(float(right), digits))
    except (TypeError, ValueError, OverflowError):
        return False


def _bind_legacy_metric(group_id: str, metric_id: str, metric: Any,
                        pulse_group: Mapping[str, Any], errors: list[str]) -> None:
    if not isinstance(metric, Mapping):
        return
    participation = pulse_group.get("participation")
    if not isinstance(participation, Mapping):
        errors.append(f"group {group_id}: pulse participation invalid")
        return
    if metric_id == "legacy_activity":
        expected_value = participation.get("activity_share")
        expected_numerator = participation.get("activity_n")
        expected_denominator = pulse_group.get("n_covered")
        if metric.get("numerator") != expected_numerator:
            errors.append(f"group {group_id}: legacy_activity numerator mismatch")
    elif metric_id == "legacy_trend_50":
        expected_value = participation.get("trend_share_50d")
        expected_denominator = participation.get("trend_n_50d")
    elif metric_id == "legacy_trend_200":
        expected_value = participation.get("trend_share_200d")
        expected_denominator = participation.get("trend_n_200d")
    else:
        return
    if metric.get("denominator") != expected_denominator:
        errors.append(f"group {group_id}: {metric_id} denominator mismatch")
    if not _rounded_equal(metric.get("value"), expected_value):
        errors.append(f"group {group_id}: {metric_id} value mismatch")

def current_run_errors(result: Mapping[str, Any]) -> list[str]:
    """Prove this invocation produced a complete companion before strict publish."""
    errors = [str(item) for item in (result.get("member_observation_errors") or [])]
    artifact = result.get("member_observations_artifact")
    digest = result.get("member_observations_digest")
    if not isinstance(artifact, str) or not artifact:
        errors.append("current invocation produced no member-observation artifact")
    if not isinstance(digest, str) or not _SHA_RE.fullmatch(digest):
        errors.append("current invocation produced no valid member-observation digest")
    return errors


def evaluate(site_root: Path) -> dict[str, Any]:
    site = Path(site_root)
    errors: list[str] = []
    pulse_raw = _read(site / "basketdata" / "pulse.json", errors)
    companion_raw = _read(site / "basketdata" / "member_observations.json", errors)
    pulse = _json(pulse_raw, "pulse.json", errors)
    companion = _json(companion_raw, "member_observations.json", errors)
    pulse_digest = hashlib.sha256(pulse_raw).hexdigest() if pulse_raw is not None else None
    group_count = 0
    if companion is not None:
        contract_errors = observations.validate_member_bundle(companion)
        errors.extend(f"member_observations.json: {item}" for item in contract_errors)
        source = companion.get("source") or {}
        if pulse_digest is not None and source.get("legacy_pulse_sha256") != pulse_digest:
            errors.append("member_observations.json: pulse byte digest mismatch")
        if pulse_raw is not None and source.get("legacy_pulse_bytes") != len(pulse_raw):
            errors.append("member_observations.json: pulse byte count mismatch")
        groups = companion.get("groups") or {}
        if isinstance(groups, dict):
            group_count = len(groups)
            if pulse is not None and set(groups) != set(pulse):
                errors.append("pulse and companion group key sets differ")
            projection = companion.get("projection_digest")
            for group_id, group in sorted(groups.items()):
                attrs, detail = _read_detail(site / "basket" / f"{group_id}.html", errors)
                _bind_detail_payload(group_id, detail, group, companion, pulse_digest, errors)
                if attrs.get("projection") != projection:
                    errors.append(f"detail page {group_id}: projection digest mismatch")
                if attrs.get("pulse") != pulse_digest:
                    errors.append(f"detail page {group_id}: pulse digest mismatch")
                if isinstance(group, dict) and group.get("legacy_pulse_digest") != pulse_digest:
                    errors.append(f"group {group_id}: legacy pulse digest mismatch")
                pulse_group = pulse.get(group_id) if isinstance(pulse, dict) else None
                if not isinstance(pulse_group, Mapping):
                    errors.append(f"group {group_id}: pulse object invalid")
                    continue
                if pulse_group.get("as_of") != companion.get("as_of"):
                    errors.append(f"group {group_id}: companion as_of mismatch")
                if not _same_timestamp(
                        pulse_group.get("generated_at"), companion.get("generated_at")):
                    errors.append(f"group {group_id}: companion generated_at mismatch")
                if isinstance(group, Mapping):
                    if pulse_group.get("n_members") != group.get("member_count"):
                        errors.append(f"group {group_id}: member count mismatch")
                    metrics = group.get("metrics") or {}
                    if isinstance(metrics, Mapping):
                        for metric_id in ("legacy_activity", "legacy_trend_50",
                                          "legacy_trend_200"):
                            _bind_legacy_metric(
                                group_id, metric_id, metrics.get(metric_id),
                                pulse_group, errors,
                            )
        else:
            errors.append("member_observations.json: groups must be an object")
    return {
        "ok": not errors,
        "errors": errors,
        "group_count": group_count,
        "pulse_sha256": pulse_digest,
        "projection_digest": (companion or {}).get("projection_digest"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-root", type=Path, default=Path("site"))
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    result = evaluate(args.site_root)
    if result["ok"]:
        if not args.quiet:
            print(f"group member observations coherent | groups={result['group_count']} "
                  f"pulse={result['pulse_sha256']} projection={result['projection_digest']}")
        return 0
    for error in result["errors"]:
        print(f"::error title=group-member-observations::{error}", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
