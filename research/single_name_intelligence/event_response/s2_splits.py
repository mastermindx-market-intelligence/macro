"""S2 splits and membership manifests (SL §1, §2, §5; A23, immutable).

Split membership is a function of the opener's first session on the counting
clock (MARKET_US here). TRAIN s < 2024-01-01; TUNE 2024-01-01 <= s <
2026-10-01; QUARANTINE s >= 2026-10-01 (listed, counted, never evaluated).
TEST is prospective-only and cannot exist in a historical-descriptive run
(REG §2 registration gate is not met).

Purge, per h: a TRAIN episode whose window's last session is on or after
2024-01-01, or a TUNE episode whose window's last session is on or after
2026-10-01, is PURGED — the label is kept, the flag is visible, the episode is
never moved.

Manifest lines carry the SL §5 fields plus the packet's E6 fields, sorted by
(horizon, episode_key), canonical JSON + newline. membership_sha256 per
(protocol, h, split) = sha256 of that split's lines in order.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date

from engine.qledger import (MARKET_US, resolve_horizon_window,
                            HORIZON_UNIT_TRADING)
from s2_clocklaw import ClockLawFailure
from s2_seal import (COUNTING_CLOCK, GRADE_HORIZONS, GRADED_LEG_LABEL,
                     PROTOCOL_FAMILY, PROTOCOL_VERSION, SPLIT_QUARANTINE_START,
                     SPLIT_TUNEE_START)


def episode_key(issuer_key: str, opener_family: str, opener_t_avail_utc: str,
                opener_evidence_pointer: str) -> str:
    """SL §1 membership key for an event episode."""
    raw = f"{issuer_key}|{opener_family}|{opener_t_avail_utc}|{opener_evidence_pointer}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def split_label(s_date: date) -> str:
    if s_date >= SPLIT_QUARANTINE_START:
        return "QUARANTINE"
    if s_date >= SPLIT_TUNEE_START:
        return "TUNE"
    return "TRAIN"


def window_last_session(s_date: date, h: int) -> date | None:
    """The last session of W_h (sessions s..s+h inclusive) on MARKET_US —
    calendar arithmetic only (no price is read)."""
    anchor = s_date.fromordinal(s_date.toordinal() - 1)
    w = resolve_horizon_window(anchor, h, HORIZON_UNIT_TRADING, MARKET_US)
    if w is None:
        return None
    return w.coverage_date


def purge_flag(split: str, coverage: date | None) -> bool:
    if coverage is None:
        return False
    if split == "TRAIN" and coverage >= SPLIT_TUNEE_START:
        return True
    if split == "TUNE" and coverage >= SPLIT_QUARANTINE_START:
        return True
    return False


def manifest_line(protocol_id: str, episode, h: int, split: str,
                  purged: bool, census_only: bool,
                  counting_clock: str = COUNTING_CLOCK) -> dict:
    """One SL §5 + E6 membership line (field order is fixed by construction;
    the canonical encoding sorts keys)."""
    op = episode.opener
    return {
        "protocol_id": protocol_id,
        "version": PROTOCOL_VERSION,
        "horizon": h,
        "episode_key": episode_key(op.issuer_key, op.family, op.t_avail_utc,
                                   op.evidence_pointer),
        "issuer_key": op.issuer_key,
        "opener_family": op.family,
        "opener_t_avail_utc": op.t_avail_utc,
        "opener_evidence_pointer": op.evidence_pointer,
        "s_us": op.s_us,
        "s_hk": op.s_hk,
        "cluster_key": op.s_us,
        "graded_leg": "NONE — census only (V0 row 14)" if census_only
                      else GRADED_LEG_LABEL["alibaba"],
        "split": split,
        "flags": {
            "purged": purged,
            "confounded": episode.confounded,
            "absorbed_count": episode.absorbed_count,
            "census_only": census_only,
            "member_ids": sorted(op.member_ids),
        },
        "counting_clock": counting_clock,
        "s_date": op.s_us,
    }


def canonical_line(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False) + "\n"


def build_membership(protocol_id: str, episodes_by_h: dict[int, list],
                     census_only_by_h: dict[int, list] | None = None,
                     ) -> tuple[list[str], dict, dict]:
    """Manifest lines per h for one protocol, the per-(h, split)
    membership_sha256 table and the per-(h, split) counts.

    episodes_by_h: counted (graded-cohort) episodes from the collapse.
    census_only_by_h: census-only episodes of other issuer groups; they appear
    with graded_leg NONE — census only (V0 row 14) and never count in honest-N.
    The purge flag is computed PER EPISODE from calendar arithmetic (the last
    session of that episode's own W_h), never from a shared split value.
    Every (protocol, h, split) cell gets a hash — an empty split hashes the
    empty line payload.
    """
    census_only_by_h = census_only_by_h or {}
    lines: list[str] = []
    table: dict[str, dict] = {}
    for h in GRADE_HORIZONS:
        rows = []
        for ep in episodes_by_h.get(h, []):
            split = split_label(date.fromisoformat(ep.opener.s_us))
            coverage = window_last_session(date.fromisoformat(ep.opener.s_us), h)
            rows.append((split, manifest_line(protocol_id, ep, h, split,
                                              purge_flag(split, coverage),
                                              census_only=False)))
        for ep in census_only_by_h.get(h, []):
            split = split_label(date.fromisoformat(ep.opener.s_us))
            coverage = window_last_session(date.fromisoformat(ep.opener.s_us), h)
            rows.append((split, manifest_line(protocol_id, ep, h, split,
                                              purge_flag(split, coverage),
                                              census_only=True)))
        rows.sort(key=lambda p: p[1]["episode_key"])
        for split, line in rows:
            lines.append(canonical_line(line))
            table.setdefault(str(h), {}).setdefault(split, []).append(line)
    sha_table: dict[str, dict] = {}
    count_table: dict[str, dict] = {}
    for h in GRADE_HORIZONS:
        for split in ("TRAIN", "TUNE", "QUARANTINE"):
            split_lines = table.get(str(h), {}).get(split, [])
            payload = "".join(canonical_line(l) for l in split_lines)
            sha_table.setdefault(str(h), {})[split] = hashlib.sha256(
                payload.encode("utf-8")).hexdigest()
            count_table.setdefault(str(h), {})[split] = len(split_lines)
    return lines, sha_table, count_table


def membership_table_rows(sha_table: dict, count_table: dict,
                          protocol_id: str) -> list[dict]:
    """The seal's membership table rows for one protocol."""
    rows = []
    for h in GRADE_HORIZONS:
        for split in ("TRAIN", "TUNE", "QUARANTINE"):
            shas = sha_table.get(str(h), {})
            counts = count_table.get(str(h), {})
            rows.append({
                "protocol_id": protocol_id,
                "horizon": h,
                "split": split,
                "count": counts.get(split, 0),
                "membership_sha256": shas.get(split),
            })
    return rows
