"""S2 shared state: the outcome-free metadata computation both sides import.

build_seal.py (C1) renders the seal from this module; run_s2.py (C2/C3)
recomputes the SAME state and verifies the seal's membership hashes and prereg
digest before any outcome is computed (exit non-zero on mismatch). One
implementation, no drift.

Everything here is metadata-only: profiles, coverage reports, events/earnings
metadata columns, security-master id columns, calendar arithmetic. No price or
volume column is ever requested.
"""
from __future__ import annotations

from collections import Counter
from datetime import date

from s2_collapse import run_collapse
from s2_clocklaw import session_dates
from s2_selection import (classify_category, coverage_census_rows,
                          derive_programmes, earnings_census_rows,
                          event_census_rows)
from s2_seal import (EARNINGS_METADATA_COLUMNS, EVENTS_METADATA_COLUMNS,
                     GRADE_HORIZONS, GRADED_ISSUER, SECURITY_MASTER_ID_COLUMNS,
                     IDENTITY_RESOLVED_AS_OF)
from s2_splits import build_membership, membership_table_rows

PROTOCOL_FAMILY = {"P04": "results", "P05": "capital_action",
                   "P06": "regulatory_material"}
EVENT_SOURCE_PATHS = ("data/hk_filings/events.parquet",
                      "data/earnings/earnings.parquet")


def compute_state(loader) -> dict:
    """The complete outcome-free state of the lane at the pinned inputs."""
    coverage_reports = {
        "alibaba": loader.read_json(
            "research/single_name_intelligence/evidence/Alibaba/E1_COVERAGE_REPORT_2026-10-11.json"),
        "tencent": loader.read_json(
            "research/single_name_intelligence/evidence/Tencent/E2_COVERAGE_REPORT_2026-10-11.json"),
    }
    events_df = loader.read_parquet("data/hk_filings/events.parquet",
                                    columns=EVENTS_METADATA_COLUMNS)
    earnings_df = loader.read_parquet("data/earnings/earnings.parquet",
                                      columns=EARNINGS_METADATA_COLUMNS)
    if "ticker" not in earnings_df.columns:  # ticker is the INDEX of this store
        earnings_df = earnings_df.rename_axis("ticker").reset_index()
    secmaster_df = loader.read_parquet("data/reference/security_master.parquet",
                                       columns=SECURITY_MASTER_ID_COLUMNS)

    # A07 guard: the pinned identity instants must match the security master.
    master = {str(r.security_id): str(r.ingested_at).replace(" ", "T")
              for r in secmaster_df.itertuples()}
    for sec_id, want in IDENTITY_RESOLVED_AS_OF.items():
        got = master.get(sec_id)
        if got != want:
            raise SystemExit(
                f"security_master ingested_at for {sec_id} is {got!r}, seal pins {want!r}")

    issuer_of_counter = {"hkd_9988": "alibaba", "hkd_0700": "tencent"}
    event_rows = event_census_rows(events_df, issuer_of_counter)
    earning_rows = earnings_census_rows(earnings_df)
    census_rows = event_rows + earning_rows

    vocab = sorted({str(v) for v in events_df["category"]})
    counts = Counter(str(v) for v in events_df["category"])
    class_summary = {
        "count_per_category": dict(sorted(counts.items())),
        "mapping": {v: classify_category(v) for v in vocab},
    }

    selected = [r for r in event_rows if r["disposition"] == "SELECTED"]
    programmes = derive_programmes(selected)
    prog_keys = sorted(p["key"] for p in programmes)
    event_exclusions = [{
        "match": {"programme": key},
        "reason": ("E0 gap 10: HK placement coverage misses general-mandate "
                   "placings; the one programme (one event under REG P05) is "
                   "excluded and listed, never silently dropped"),
        "family_scope": "capital_action",
    } for key in prog_keys]

    import lib.hk_calendar as hk_calendar
    import lib.nyse_calendar as nyse_calendar
    us_dates = session_dates(nyse_calendar)
    hk_dates = session_dates(hk_calendar)

    rows_for_collapse = [{
        "id": r["id"],
        "issuer_key": r["issuer_key"],
        "family": r["family"],
        "category": r["category"],
        "title": r.get("title", ""),
        "t_avail_utc": r["t_avail_utc"],
        "t_avail_quality": r["t_avail_quality"],
        "s_us": r["s_us"],
        "s_hk": r["s_hk"],
        "evidence_pointer": f"{r['source']}#id={r['id']}",
        "disposition": r["disposition"],
        "listed_exclusion_reason": r["listed_exclusion_reason"],
    } for r in census_rows]

    collapse = run_collapse(rows_for_collapse, programmes, us_dates, hk_dates,
                            GRADE_HORIZONS, event_exclusions=event_exclusions)

    membership: dict[str, dict] = {}
    prereg_membership_table: list[dict] = []
    for pid, fam in PROTOCOL_FAMILY.items():
        counted = {h: [ep for ep in collapse["per_h"][h]["episodes"]
                       if ep.opener.family == fam
                       and ep.opener.issuer_key == GRADED_ISSUER]
                   for h in GRADE_HORIZONS}
        census_only = {h: [ep for ep in collapse["per_h"][h]["episodes"]
                           if ep.opener.family == fam
                           and ep.opener.issuer_key != GRADED_ISSUER]
                       for h in GRADE_HORIZONS}
        lines, sha_table, count_table = build_membership(pid, counted, census_only)
        lines_by_h: dict[int, list[str]] = {h: [] for h in GRADE_HORIZONS}
        for line in lines:
            import json as _json
            lines_by_h.setdefault(_json.loads(line)["horizon"], []).append(line)
        rows = membership_table_rows(sha_table, count_table, pid)
        membership[pid] = {"lines_by_h": lines_by_h, "sha_table": sha_table,
                           "count_table": count_table, "table_rows": rows,
                           "counted": counted, "census_only": census_only}
        prereg_membership_table.extend(rows)

    return {
        "census_rows": census_rows,
        "event_rows": event_rows,
        "earning_rows": earning_rows,
        "class_summary": class_summary,
        "vocab": vocab,
        "selected": selected,
        "programmes": programmes,
        "event_exclusions": event_exclusions,
        "collapse": collapse,
        "membership": membership,
        "prereg_membership_table": prereg_membership_table,
        "coverage_reports": coverage_reports,
    }
