"""S2 event selection and classification (metadata only; outcome-free).

Selection rule (frozen, E3): a data/hk_filings/events.parquet row is selected
for a counter ONLY when one EXACT token of its '<br/>'-split stock_code equals
that counter's profile local_code ('09988' for alibaba hkd_9988, '00700' for
tencent hkd_0700). Substring matches never select: the token '40700' is not
'00700' and the token '89988' is not '09988'. Rows that merely contain the
digits are listed as near-token exclusions in the census.

Classification (frozen, E2): the events.parquet category vocabulary maps
through CLASSIFICATION_TABLE to one of the three IL §1 families; anything the
table cannot map is UNCLASSIFIED — listed, never counted. A sentence-level
text classifier is out of scope.

Identity (A07): every event row carries identity_view RETROSPECTIVE_JOIN and
identity_resolved_as_of = the security_master ingested_at of the counter's
security id. No row presents an id as known before that instant.
"""
from __future__ import annotations

from datetime import datetime

from s2_clocklaw import (first_session_after, first_session_after_disclosure_date,
                         session_part, to_utc)
from s2_seal import (CLASSIFICATION_TABLE, COUNTER_LOCAL_CODE,
                     COUNTER_SECURITY_ID, EVENT_SOURCE_CELL, FAMILIES,
                     IDENTITY_RESOLVED_AS_OF, IDENTITY_VIEW)

HK_TZ = "Asia/Hong_Kong"
TIMESTAMP_QUALITY_PUBLISHER_STATED = "PUBLISHER_STATED"
TIMESTAMP_QUALITY_EVENT_DATE = "EVENT_DATE"


def split_tokens(stock_code) -> list[str]:
    """Exact '<br/>' tokens of a stock_code cell, stripped, order preserved."""
    if stock_code is None:
        return []
    return [tok.strip() for tok in str(stock_code).split("<br/>")]


def select_rows_for_counter(tokens_by_row: dict[int, list[str]],
                            local_code: str) -> list[int]:
    """Row indices whose EXACT token list contains local_code."""
    return [i for i, toks in tokens_by_row.items() if local_code in toks]


def near_token_rows(tokens_by_row: dict[int, list[str]],
                    local_code: str,
                    key_form: str | None = None) -> list[tuple[int, str]]:
    """Rows holding a token that CONTAINS the counter code (or its unpadded
    key form, e.g. '0700' for '00700') without EQUALING it — the substring
    false-positive class; listed, never selected."""
    needles = [n for n in (local_code, key_form) if n]
    out = []
    for i, toks in tokens_by_row.items():
        for tok in toks:
            if tok != local_code and any(n in tok for n in needles):
                out.append((i, tok))
    return out


def classify_category(category) -> str:
    cat = str(category).strip()
    return CLASSIFICATION_TABLE.get(cat, "UNCLASSIFIED")


def t_avail_for_event_row(announced_at: datetime) -> tuple[datetime, str]:
    """announced_at is the publisher-stated wall time in HKT -> UTC,
    quality PUBLISHER_STATED."""
    if announced_at.tzinfo is not None:
        aware = announced_at
    else:
        aware = to_utc(announced_at, HK_TZ)
    return aware, TIMESTAMP_QUALITY_PUBLISHER_STATED


def event_census_rows(events_df, issuer_of_counter: dict[str, str]) -> list[dict]:
    """Build the EVENT_CENSUS rows for the two counters (metadata only).

    Rows: every exact-token selection (disposition SELECTED), every near-token
    row (disposition EXCLUDED_AND_LISTED, substring reason). Every row carries
    id, counter, issuer group, category, family or UNCLASSIFIED, t_avail (UTC),
    quality, session parts, s_US, s_HK, identity fields and the disposition.
    """
    tokens = {i: split_tokens(v) for i, v in enumerate(events_df["stock_code"])}
    rows: list[dict] = []
    for counter, issuer in issuer_of_counter.items():
        local_code = COUNTER_LOCAL_CODE[issuer][counter]
        sec_id = COUNTER_SECURITY_ID[issuer][counter]
        selected = select_rows_for_counter(tokens, local_code)
        for i in selected:
            r = events_df.iloc[i]
            t_avail, quality = t_avail_for_event_row(r["announced_at"])
            rows.append({
                "id": str(r["news_id"]),
                "source": "data/hk_filings/events.parquet",
                "counter": counter,
                "issuer_key": issuer,
                "category": str(r["category"]),
                "family": classify_category(r["category"]),
                "title": str(r["title"]),
                "t_avail_utc": t_avail.isoformat(),
                "t_avail_quality": quality,
                "session_part_hk": session_part(t_avail, "HK"),
                "session_part_us": session_part(t_avail, "US"),
                "s_us": first_session_after(t_avail, "US").isoformat(),
                "s_hk": first_session_after(t_avail, "HK").isoformat(),
                "identity_security_id": sec_id,
                "identity_view": IDENTITY_VIEW,
                "identity_resolved_as_of": IDENTITY_RESOLVED_AS_OF[sec_id],
                "disposition": "SELECTED",
                "listed_exclusion_reason": None,
                "near_token": None,
            })
        selected_ids = {str(events_df.iloc[i]["news_id"]) for i in selected}
        key_form = counter.replace("hkd_", "", 1)
        for i, tok in near_token_rows(tokens, local_code, key_form):
            r = events_df.iloc[i]
            if str(r["news_id"]) in selected_ids:
                continue  # already selected via the exact token; no double listing
            rows.append({
                "id": str(r["news_id"]),
                "source": "data/hk_filings/events.parquet",
                "counter": counter,
                "issuer_key": issuer,
                "category": str(r["category"]),
                "family": classify_category(r["category"]),
                "title": str(r["title"]),
                "t_avail_utc": None,
                "t_avail_quality": None,
                "session_part_hk": None,
                "session_part_us": None,
                "s_us": None,
                "s_hk": None,
                "identity_security_id": sec_id,
                "identity_view": IDENTITY_VIEW,
                "identity_resolved_as_of": IDENTITY_RESOLVED_AS_OF[sec_id],
                "disposition": "EXCLUDED_AND_LISTED",
                "listed_exclusion_reason": (
                    f"exact-token selection refused: token {tok!r} is not "
                    f"{local_code!r}"),
                "near_token": tok,
            })
    rows.sort(key=lambda r: (r["issuer_key"], r["id"]))
    return rows


def earnings_census_rows(earnings_df) -> list[dict]:
    """BABA rows of the earnings calendar: quality EVENT_DATE -> excluded and
    listed (IL §1), never an anchor. Rows of other tickers are not candidates
    and are never listed (E3(b): rows for BABA)."""
    rows = []
    sec_id = "SEC:US-XNYS-BABA"
    baba = earnings_df[earnings_df["ticker"] == "BABA"]
    for _, r in baba.iterrows():
        rows.append({
            "id": f"earnings.parquet#ticker={r['ticker']}",
            "source": "data/earnings/earnings.parquet",
            "counter": "adr_baba",
            "issuer_key": "alibaba",
            "category": "earnings_calendar_row",
            "family": "results",
            "title": f"next_date={r['next_date']} next_time={r['next_time']} as_of={r['as_of']}",
            "t_avail_utc": None,
            "t_avail_quality": TIMESTAMP_QUALITY_EVENT_DATE,
            "session_part_hk": None,
            "session_part_us": None,
            "s_us": None,
            "s_hk": None,
            "identity_security_id": sec_id,
            "identity_view": IDENTITY_VIEW,
            "identity_resolved_as_of": IDENTITY_RESOLVED_AS_OF[sec_id],
            "disposition": "EXCLUDED_AND_LISTED",
            "listed_exclusion_reason": (
                "TIMESTAMP_QUALITY EVENT_DATE is not an admissible t_avail "
                "(IL §1); the row is listed, never an anchor"),
            "near_token": None,
        })
    return rows


def derive_programmes(selected_rows: list[dict]) -> list[dict]:
    """Frozen programme rule (REG P05: one announced programme = ONE event).

    Rule: among the selected rows of one issuer group, the capital_action rows
    whose category is general_mandate and whose title carries PLACING form ONE
    programme (proposal, pricing and completion are evidence rows of the single
    programme event). Deterministic on metadata only; the grouping is frozen in
    the seal census. Returns programme descriptors with member ids.
    """
    programmes: dict[str, dict] = {}
    for r in selected_rows:
        if r.get("family") != "capital_action":
            continue
        if str(r.get("category")) != "general_mandate":
            continue
        if "PLACING" not in str(r.get("title", "")).upper():
            continue
        key = f"placing:{r['issuer_key']}"
        prog = programmes.setdefault(key, {
            "key": key,
            "issuer_key": r["issuer_key"],
            "counter": r["counter"],
            "member_ids": [],
        })
        prog["member_ids"].append(r["id"])
    for prog in programmes.values():
        prog["member_ids"] = sorted(prog["member_ids"])
    return [programmes[k] for k in sorted(programmes)]


def event_source_cells(coverage_reports: dict) -> dict:
    """E3(c): the per-issuer coverage cell that owns the (a) event source."""
    out = {}
    for issuer, cell in EVENT_SOURCE_CELL.items():
        report = coverage_reports[issuer]
        out[issuer] = {
            "cell": cell,
            "state": report["metrics"][cell]["status"],
        }
    return out


def coverage_census_rows(coverage_reports: dict) -> list[dict]:
    """Every E1/E2 coverage cell with its state and disposition (E3(c))."""
    rows = []
    for issuer in ("alibaba", "tencent"):
        report = coverage_reports[issuer]
        source_cell = EVENT_SOURCE_CELL[issuer]
        for cell, meta in sorted(report["metrics"].items()):
            state = meta["status"]
            if cell == source_cell:
                disposition = "event source used (data/hk_filings/events.parquet, exact local_code token match)"
            else:
                disposition = f"not an S2 event source (state {state})"
            rows.append({
                "issuer_key": issuer,
                "report": "E1" if issuer == "alibaba" else "E2",
                "cell": cell,
                "family": cell.split(".", 1)[0],
                "counter": cell.split(".", 1)[1],
                "state": state,
                "evidence_rows": meta.get("evidence_rows"),
                "disposition": disposition,
            })
    rows.sort(key=lambda r: (r["report"], r["cell"]))
    return rows
