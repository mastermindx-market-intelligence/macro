"""Read-only native Press account-claim evidence. No planner, writer or publication effects."""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def ledger_snapshot(path: Path) -> tuple[list[dict], str | None, bool]:
    """One source read; preserve the old usable rows but flag incomplete custody."""
    try:
        raw = path.read_bytes()
        out, complete = [], True
        for line in raw.decode("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("Non-object ledger row")
                out.append(row)
            except (ValueError, TypeError):
                complete = False
        return out, hashlib.sha256(raw).hexdigest(), complete
    except (OSError, UnicodeError):
        return [], None, False


def _utc_instant(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Expected timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp has no timezone")
    return result.astimezone(timezone.utc)


def signup_claims(ledger: list[dict], digest: str | None, complete: bool, query, *, publication_limit: int) -> dict:
    """One aggregate-only read. Content claims are not referrals or conversions."""
    out = {"status": "unavailable", "reason": "publication_input_unavailable",
           "ledger_sha256": digest, "publication_limit": publication_limit,
           "total_publications": len(ledger), "rows": [], "observed_at": None,
           "scope": "currently_active_accounts_claiming_exact_publication_content"}
    if not complete:
        return out
    try:
        seen = set()
        for row in ledger:
            identity = row.get("id")
            if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", identity) or identity in seen:
                raise ValueError("Invalid or duplicate publication identity")
            seen.add(identity)
            _utc_instant(row.get("ts"))
        selected = ledger[-publication_limit:]
        if not selected:
            return {**out, "status": "no_publications", "reason": None}
        from .users import _ACTIVE  # native active-account semantics; no new roster
        values = ",".join("('%s','%s'::timestamptz)" %
                          (r["id"], _utc_instant(r["ts"]).isoformat()) for r in selected)
        sql = ("WITH publications(id,published_at) AS (VALUES " + values + ") "
               "SELECT p.id AS publication_id,p.published_at,now() AS observed_at,"
               "count(u.id)::int AS active_accounts_claiming_content,"
               "min(u.created_at) AS earliest_signup_at,max(u.created_at) AS latest_signup_at "
               "FROM publications p LEFT JOIN auth.users u ON "
               "jsonb_typeof(u.raw_user_meta_data->'utm')='object' AND "
               "jsonb_typeof(u.raw_user_meta_data->'utm'->'utm_content')='string' AND "
               "u.raw_user_meta_data #>> '{utm,utm_content}' = p.id "
               "AND u.created_at >= p.published_at AND u.created_at < now() AND " + _ACTIVE +
               " GROUP BY p.id,p.published_at ORDER BY p.id")
        out["reason"] = "account_read_unavailable"
        rows = query(sql)  # existing provisioned reader, one call, unchanged budget
        required = {"publication_id", "published_at", "observed_at", "active_accounts_claiming_content",
                    "earliest_signup_at", "latest_signup_at"}
        if not isinstance(rows, list) or len(rows) != len(selected):
            raise ValueError("Partial account read")
        by_id = {r["id"]: r for r in selected}
        results, observed, returned = {}, None, set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != required:
                raise ValueError("Invalid account aggregate")
            identity = row["publication_id"]
            if not isinstance(identity, str) or identity not in by_id or identity in returned:
                raise ValueError("Invalid aggregate identity")
            returned.add(identity)
            publication = by_id[identity]
            start, end = _utc_instant(row["published_at"]), _utc_instant(row["observed_at"])
            if start != _utc_instant(publication["ts"]) or end < start or (observed is not None and end != observed):
                raise ValueError("Invalid aggregate window")
            observed = end
            count = row["active_accounts_claiming_content"]
            if type(count) is not int or count < 0:
                raise ValueError("Invalid count")
            low, high = row["earliest_signup_at"], row["latest_signup_at"]
            if count == 0:
                if low is not None or high is not None:
                    raise ValueError("Zero with signup clocks")
            elif not (start <= _utc_instant(low) <= _utc_instant(high) < end) or (count == 1 and _utc_instant(low) != _utc_instant(high)):
                raise ValueError("Signup clocks outside publication window")
            results[identity] = {"publication_id": identity, "published_at": start.isoformat(),
                                 "desk": publication.get("desk"), "slug": publication.get("slug"),
                                 "urls": publication.get("urls") or [],
                                 "active_accounts_claiming_content": count,
                                 "earliest_signup_at": low, "latest_signup_at": high}
        return {**out, "status": "available", "reason": None, "observed_at": observed.isoformat(),
                "rows": [results[r["id"]] for r in reversed(selected)]}
    except Exception:  # no raw backend payload, SQL, metadata or identities in errors
        return out
