"""Offline CN integration experiment; a proposal, never a production entry point.

The caller injects the pinned native modules and a test object store. This module
has no network client and no production path. It retains the existing event
namespace, native state machine, native reconciliation functions and ledger shape.
New evidence fields and stricter preconditions are deliberately explicit.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import io
import json
import math
import re
from typing import Any
from unittest.mock import patch

UTC = timezone.utc
BOARD_PATH = "site/factordata/china_standouts.json"
PRIMARY_LANES = {"buy": "featured", "more_actionable": "more_actionable",
                 "late_or_unfillable": "late_or_unfillable", "forming": "forming"}
EVENT_SCHEMA = "cn_prophet_live.events/research-v2"
INGEST_CONTRACT = "cn_prophet_live.evidence/research-v1"
TICKER = re.compile(r"^[0-9]{6}\.(?:SS|SZ)$")
HASH = re.compile(r"^[a-f0-9]{64}$")


class Refused(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def encoded(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(obj: Any) -> str:
    return sha256(encoded(obj)).hexdigest()


def stamp(raw: Any) -> datetime:
    require(isinstance(raw, str), "invalid_timestamp")
    try:
        got = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise Refused("invalid_timestamp") from None
    require(got.tzinfo is not None, "naive_timestamp")
    return got.astimezone(UTC)


def finite(raw: Any, *, positive: bool = False) -> bool:
    return (not isinstance(raw, bool) and isinstance(raw, (int, float))
            and math.isfinite(raw) and (not positive or raw > 0))


def frozen_board(raw: bytes, *, expected_asof: str) -> tuple[dict, dict]:
    """Read only the real four primary arrays; aliases never duplicate names.

    score <- prophet.score; rank <- board_rank, never array position/score_rank.
    The latter remains a separately named proposed frozen field.
    """
    doc = json.loads(raw)
    require(isinstance(doc, dict), "invalid_board_document")
    require(doc.get("as_of") == expected_asof, "board_asof_mismatch")
    require(isinstance(doc.get("board_definition"), str), "missing_board_definition")
    out = {}
    for source_lane, lane in PRIMARY_LANES.items():
        rows = doc.get(source_lane)
        require(isinstance(rows, list), "missing_primary_lane")
        for row in rows:
            require(isinstance(row, dict), "invalid_board_row")
            ticker = row.get("ticker")
            require(isinstance(ticker, str) and bool(TICKER.fullmatch(ticker)),
                    "invalid_ticker")
            require(ticker not in out, "duplicate_primary_ticker")
            require(row.get("lane") == lane, "lane_disagreement")
            require(row.get("board_definition") == doc["board_definition"],
                    "board_definition_disagreement")
            if row.get("data_through") is not None:
                require(row["data_through"] == expected_asof, "row_date_disagreement")
            score = (row.get("prophet") or {}).get("score")
            rank = row.get("board_rank")
            require(finite(score) and 0 <= score <= 100, "invalid_frozen_score")
            require(type(rank) is int and rank > 0, "invalid_frozen_rank")
            mapped = deepcopy(row)
            mapped["prophet_score"] = score  # existing attach_frozen input names
            mapped["prophet_rank"] = rank
            out[ticker] = mapped
    ranking = (doc.get("ranking") or {}).get("ordering") or {}
    identity = {"as_of": expected_asof, "board_definition": doc["board_definition"],
                "artifact_sha256": sha256(raw).hexdigest(), "path": BOARD_PATH,
                "effective_order_basis": ranking.get("effective_order_basis")}
    return out, identity


def bind_pack(pack: dict, rows: dict, board_identity: dict) -> dict:
    """Small additive contract on the existing armed pack; no new score."""
    p = deepcopy(pack)
    require(p.get("as_of") == board_identity["as_of"], "pack_board_asof_mismatch")
    for ticker, entry in p["names"].items():
        row = rows.get(ticker)
        if row is not None:
            f = entry.get("frozen") or {}
            require(f.get("score") == row["prophet"]["score"], "score_projection_loss")
            require(f.get("rank") == row["board_rank"], "rank_projection_loss")
            f["score_rank"] = row.get("score_rank")
            f["score_basis"] = row["prophet"].get("score_basis")
            entry["frozen"] = f
            entry["frozen_status"] = "in_source_board"
        else:
            # A prospective cross outside yesterday's board has no invented rank.
            entry.pop("frozen", None)
            entry["frozen_status"] = "not_in_source_board"
    p["source_board"] = deepcopy(board_identity)
    p.pop("pack_id", None)
    p["pack_id"] = digest(p)
    return p


def pack_key(pack: dict, r2: Any) -> str:
    return f"{r2.CN_PACK_KEY.removesuffix('.json')}/{pack['as_of']}/{pack['pack_id']}.json"


def validate_pack(pack: dict, *, expected_asof: str | None = None,
                  known_by: datetime | None = None) -> None:
    require(isinstance(pack, dict) and pack.get("schema") == "cn_prophet_live.armed/v1"
            and pack.get("market") == "CN", "invalid_pack_schema")
    identity = pack.get("pack_id")
    require(isinstance(identity, str) and bool(HASH.fullmatch(identity)), "missing_pack_id")
    check = deepcopy(pack)
    check.pop("pack_id")
    require(digest(check) == identity, "pack_hash_mismatch")
    source = pack.get("source_board") or {}
    require(source.get("as_of") == pack.get("as_of")
            and bool(HASH.fullmatch(str(source.get("artifact_sha256") or ""))),
            "invalid_source_board_identity")
    if expected_asof is not None:
        require(pack.get("as_of") == expected_asof, "stale_or_future_pack")
    if known_by is not None:
        require(stamp(pack.get("built_at")) <= known_by, "future_pack_build")
    require(isinstance(pack.get("names"), dict), "invalid_pack_names")
    for ticker, entry in pack["names"].items():
        require(bool(TICKER.fullmatch(ticker)), "invalid_pack_ticker")
        require(isinstance(entry, dict), "invalid_pack_entry")
        require(finite(entry.get("as_of_close"), positive=True), "invalid_pack_close")
        if entry.get("frozen_status") == "in_source_board":
            frozen = entry.get("frozen") or {}
            require(finite(frozen.get("score")), "invalid_frozen_score")
            require(type(frozen.get("rank")) is int and frozen["rank"] > 0,
                    "invalid_frozen_rank")


def evaluate_checked(native, LS, clock, pack: dict, quotes: dict, prev: dict | None,
                     *, now: datetime, cfg: dict, **kwargs) -> dict:
    """Run the native CN state machine behind a proposed evidence preflight.

    The lab retains market-age arithmetic, intervals, debounce and basis checks.
    It adds future/identity checks and removes the accidental US close marker.
    The 60-second forward-clock allowance is a research fixture policy, not an
    approved production threshold.
    """
    validate_pack(pack, expected_asof=clock.last_completed_session(now), known_by=now)
    reset = bool(prev and prev.get("pack_id") != pack["pack_id"])
    if reset:
        prev = None
    clean = deepcopy(quotes)
    rejected = {}
    for ticker, quote in quotes.items():
        try:
            qts = stamp(quote.get("quote_ts") or quote.get("ts"))
            require(qts <= now + timedelta(seconds=60), "future_quote")
            require(qts.astimezone(clock.CST).date().isoformat()
                    == clock.session_date(now).isoformat(), "wrong_quote_session")
            require(finite(quote.get("price"), positive=True), "invalid_quote_price")
        except Refused as exc:
            clean[ticker] = {}
            rejected[ticker] = exc.reason
    real_state, real_transitions = LS.name_state, LS.transitions

    def cn_state(*args, **kw):
        st = real_state(*args, **kw)
        st.pop("confirming_into_close", None)
        return st

    def cn_transitions(*args, **kw):
        events = real_transitions(*args, **kw)
        for ev in events:
            ev["session_phase"] = clock.phase(kw["now"])
        return [ev for ev in events if ev["kind"] != "confirming_into_close"]

    with patch.object(LS, "name_state", cn_state), patch.object(LS, "transitions", cn_transitions):
        art = native(pack, clean, prev, now=now, cfg=cfg, **kwargs)
    art["pack_id"] = pack["pack_id"]
    art["source_board"] = deepcopy(pack["source_board"])
    art["meta"]["generation_reset"] = reset
    art["meta"]["quote_rejections"] = rejected
    art["meta"]["evaluation_policy"] = {
        "quote_max_age_min": cfg["quote_max_age_min"],
        "delay_floor_min": float(kwargs.get("delay_min") or 0),
        "future_clock_allowance_seconds": 60,
    }
    for ticker, reason in rejected.items():
        if ticker in art["names"]:
            art["names"][ticker].update(state="dark", reason=reason,
                                         market_status="unavailable")
    for ev in art.get("events", []):
        quote = clean.get(ev["ticker"]) or {}
        ev["quote_ts"] = quote.get("quote_ts") or quote.get("ts")
        ev["price_adjustment"] = "unadjusted_vendor_print"
        ev["event_id"] = digest({"pack_id": pack["pack_id"], **ev})
    if isinstance(art.get("close_board"), dict):
        art["close_board"]["session"] = art["session"]
        art["close_board"]["pack_id"] = pack["pack_id"]
    return art


class MemoryR2:
    """Explicitly synthetic S3-shaped store; writes only in Python memory."""
    def __init__(self, *, page_size: int = 2):
        self.objects = {}
        self.puts = []
        self.page_size = page_size
        self.fail_page = None
        self.fail_get = set()

    def get_object(self, *, Bucket, Key):
        if Key in self.fail_get:
            raise IOError("injected object read failure")
        return {"Body": io.BytesIO(self.objects[Key])}

    def put_object(self, *, Bucket, Key, Body, **kwargs):
        self.objects[Key] = bytes(Body)
        self.puts.append(Key)
        return {"ETag": sha256(bytes(Body)).hexdigest()}

    def list_objects_v2(self, *, Bucket, Prefix, ContinuationToken=None):
        start = int(ContinuationToken or 0)
        if start == self.fail_page:
            raise IOError("injected listing failure")
        keys = sorted(k for k in self.objects if k.startswith(Prefix))
        page = keys[start:start + self.page_size]
        end = start + len(page)
        return {"Contents": [{"Key": key} for key in page], "IsTruncated": end < len(keys),
                "NextContinuationToken": str(end) if end < len(keys) else None}

    def put(self, key: str, payload: dict):
        self.objects[key] = encoded(payload)
        self.puts.append(key)
        return True


def envelope(art: dict, events: list[dict], pack: dict) -> dict:
    return {"schema": EVENT_SCHEMA, "session": art["session"],
            "built_at": art["built_at"], "pack_id": pack["pack_id"],
            "pack_as_of": pack["as_of"], "source_board": deepcopy(pack["source_board"]),
            "evaluation_policy": deepcopy(art["meta"]["evaluation_policy"]),
            "events": deepcopy(events), "close_board": deepcopy(art.get("close_board"))}


def spool_key(doc: dict, r2: Any) -> str:
    # Existing namespace, one object per immutable content. Same-second reruns
    # cannot overwrite a different pass; identical replay has the same key.
    token = stamp(doc["built_at"]).strftime("%H%M%S") + "-" + digest(doc)
    return r2.events_key(doc["session"], token, prefix=r2.CN_EVENTS_PREFIX)


def list_complete(s3: Any, prefix: str) -> list[str]:
    """All-or-refuse variant of existing R2 pagination; never partial success."""
    out, token, seen = [], None, set()
    while True:
        try:
            page = s3.list_objects_v2(Bucket="offline-research", Prefix=prefix,
                                      **({"ContinuationToken": token} if token else {}))
        except Exception:
            raise Refused("incomplete_spool_list") from None
        out.extend(row["Key"] for row in page.get("Contents", []))
        if not page.get("IsTruncated"):
            break
        token = page.get("NextContinuationToken")
        require(bool(token) and token not in seen, "invalid_spool_pagination")
        seen.add(token)
    return sorted(set(out))


def read_object(s3, key: str) -> dict:
    try:
        doc = json.loads(s3.get_object(Bucket="offline-research", Key=key)["Body"].read())
    except Exception:
        raise Refused("unreadable_spool_object") from None
    require(isinstance(doc, dict), "invalid_spool_document")
    return doc


def consume(s3, r2, CR, clock, calendar, LS, *, session: str, now: datetime,
            existing: list[dict], settlement_pack: dict | None,
            canonical_board: dict | None, canonical_board_raw: bytes | None) -> tuple[list[dict], dict]:
    """Proposed validation around native events_to_rows/merge/receipt.

    Event authority = archived N-1 pack. Confirmed gate verdict = N settlement
    pack. Membership confirmation = N canonical board. They are different joins.
    """
    # Arrow list columns read back as ndarray with some pandas versions. Use an
    # explicit list conversion, never ndarray truthiness in the duplicate path.
    existing = [dict(row) for row in existing]
    for row in existing:
        for field, value in list(row.items()):
            # A wholly-null nullable parquet column can return float NaN. It is
            # missing evidence, never a non-null FIRST_WINS observation.
            if isinstance(value, float) and math.isnan(value):
                row[field] = None
        if row.get("event_ids") is not None:
            row["event_ids"] = list(row["event_ids"])
    require(date.fromisoformat(session) <= calendar.expected_last_session(now),
            "future_session")
    require(calendar.is_session(date.fromisoformat(session)), "non_session")
    prefix = f"{r2.CN_EVENTS_PREFIX}/{session}/"
    keys = list_complete(s3, prefix)
    require(bool(keys), "no_spool_evidence")
    expected_pack_asof = calendar.last_session_on_or_before(
        date.fromisoformat(session) - timedelta(days=1)).isoformat()
    all_events, packs, closes, seen_events = [], {}, [], {}
    allowed = set(LS.EVENT_KINDS) | set(LS.INTERNAL_MARKERS)
    allowed.discard("confirming_into_close")  # US-only clock is not CN evidence.
    for key in keys:
        doc = read_object(s3, key)
        require(doc.get("schema") == EVENT_SCHEMA, "legacy_or_unknown_spool_schema")
        require(doc.get("session") == session, "spool_session_mismatch")
        require(key == spool_key(doc, r2), "spool_content_identity_mismatch")
        built = stamp(doc.get("built_at"))
        require(built <= now, "future_spool")
        require(clock.session_date(built).isoformat() == session, "spool_clock_session_mismatch")
        pid = doc.get("pack_id")
        require(isinstance(pid, str) and bool(HASH.fullmatch(pid)), "missing_pack_id")
        require(doc.get("pack_as_of") == expected_pack_asof, "wrong_event_pack_session")
        archived_key = (f"{r2.CN_PACK_KEY.removesuffix('.json')}/"
                        f"{expected_pack_asof}/{pid}.json")
        pack = read_object(s3, archived_key)
        validate_pack(pack, expected_asof=expected_pack_asof, known_by=built)
        require(pack["pack_id"] == pid and pack["source_board"] == doc.get("source_board"),
                "event_generation_mismatch")
        packs[pid] = pack
        policy = doc.get("evaluation_policy") or {}
        require(finite(policy.get("quote_max_age_min"), positive=True)
                and finite(policy.get("delay_floor_min")) and policy["delay_floor_min"] >= 0,
                "missing_evaluation_policy")
        for ev in doc.get("events", []):
            require(isinstance(ev, dict), "invalid_event")
            ticker, kind = ev.get("ticker"), ev.get("kind")
            require(ticker in pack["names"] and bool(TICKER.fullmatch(str(ticker))),
                    "event_ticker_outside_pack")
            require(kind in allowed, "invalid_event_kind")
            event_ts, quote_ts = stamp(ev.get("ts")), stamp(ev.get("quote_ts"))
            require(event_ts <= built, "future_event")
            require(clock.session_date(event_ts).isoformat() == session,
                    "event_session_mismatch")
            require(clock.phase(event_ts) in {"morning", "afternoon", "post_close"},
                    "event_in_frozen_phase")
            require(ev.get("session_phase") == clock.phase(event_ts), "wrong_event_phase")
            require(quote_ts <= event_ts + timedelta(seconds=60), "future_event_quote")
            require(quote_ts.astimezone(clock.CST).date().isoformat() == session,
                    "wrong_event_quote_session")
            age = clock.quote_age_min(quote_ts, event_ts, delay_floor_min=policy["delay_floor_min"])
            require(age is not None and age <= policy["quote_max_age_min"], "stale_event_quote")
            require(finite(ev.get("price"), positive=True), "invalid_event_price")
            expected_entered = "board" if pack["names"][ticker].get("center_buyable") else "cross"
            require(ev.get("entered") == expected_entered, "event_entry_class_disagreement")
            require(ev.get("price_adjustment") == "unadjusted_vendor_print",
                    "unknown_event_price_adjustment")
            if ev.get("px") is not None:
                require(ev["px"] == ev["price"], "ambiguous_event_price")
            content = {k: v for k, v in ev.items() if k != "event_id"}
            require(ev.get("event_id") == digest({"pack_id": pid, **content}),
                    "event_identity_mismatch")
            identity = ev["event_id"]
            if identity in seen_events:
                require(seen_events[identity] == content, "conflicting_event_identity")
                continue
            seen_events[identity] = content
            all_events.append({**ev, "px": ev["price"], "_pack_id": pid})
        close = doc.get("close_board")
        if close is not None:
            require(isinstance(close, dict) and close.get("session") == session,
                    "close_board_session_mismatch")
            require(close.get("pack_id") == pid, "close_board_generation_mismatch")
            require(clock.phase(built) == "post_close", "close_board_outside_close_phase")
            for rows in (close.get("lanes") or {}).values():
                for row in rows:
                    ticker = row.get("ticker")
                    require(ticker in pack["names"], "close_ticker_outside_pack")
                    require(row.get("frozen") == pack["names"][ticker].get("frozen"),
                            "close_frozen_field_mismatch")
            closes.append((built, close))
    all_events.sort(key=lambda row: (stamp(row["ts"]), row["event_id"]))
    if settlement_pack is not None:
        validate_pack(settlement_pack, expected_asof=session, known_by=now)
    canonical_hash = None
    if canonical_board is not None and canonical_board.get("as_of") == session:
        require(canonical_board_raw is not None, "missing_canonical_board_bytes")
        require(json.loads(canonical_board_raw) == canonical_board, "canonical_board_bytes_disagree")
        canonical_hash = sha256(canonical_board_raw).hexdigest()
        if settlement_pack is not None:
            require(settlement_pack["source_board"]["artifact_sha256"] == canonical_hash,
                    "settlement_canonical_generation_disagreement")
    native_rows = CR.events_to_rows(all_events, session=session, confirmed=None)
    rows = []
    for row in native_rows:
        matched = [ev for ev in all_events if ev["ticker"] == row["ticker"]
                   and ev["kind"] == row["kind"]]
        pids = {ev["_pack_id"] for ev in matched}
        require(len(pids) == 1, "multiple_generations_for_daily_key")
        first = matched[0]
        source_pack = packs[first["_pack_id"]]
        entry = source_pack["names"][row["ticker"]]
        frozen = entry.get("frozen") or {}
        settle_entry = ((settlement_pack or {}).get("names") or {}).get(row["ticker"])
        verdict = settle_entry.get("center_buyable") if settle_entry else None
        require(verdict is None or type(verdict) is bool, "invalid_settlement_verdict")
        row.update({"confirmed": verdict, "schema": CR.FORWARD_SCHEMA,
                    "ingest_contract": INGEST_CONTRACT,
                    "first_pack_id": source_pack["pack_id"],
                    "source_board_sha256": source_pack["source_board"]["artifact_sha256"],
                    "source_board_asof": source_pack["source_board"]["as_of"],
                    "source_board_definition": source_pack["source_board"]["board_definition"],
                    "frozen_score": frozen.get("score"), "frozen_rank": frozen.get("rank"),
                    "frozen_score_rank": frozen.get("score_rank"),
                    "frozen_lane": frozen.get("lane"),
                    "first_event_id": first["event_id"],
                    "event_ids": sorted(ev["event_id"] for ev in matched),
                    "first_quote_ts": first["quote_ts"],
                    "entered": first.get("entered"), "from_state": first.get("from"),
                    "via": first.get("via"), "first_passes": first.get("passes"),
                    "first_quote_age_min": first.get("quote_age_min"),
                    "session_phase": first["session_phase"],
                    "price_adjustment": first["price_adjustment"],
                    "cross_basis_close": entry["as_of_close"],
                    "cross_basis_adjustment": entry.get("price_adjustment"),
                    "confirmation_pack_id": (settlement_pack or {}).get("pack_id"),
                    "confirmation_basis": "same_session_pack_center_buyable" if verdict is not None else None})
        old = next((p for p in existing if tuple(p.get(k) for k in CR.KEY)
                    == tuple(row.get(k) for k in CR.KEY)), None)
        if old:
            require(old.get("ingest_contract") == INGEST_CONTRACT, "legacy_unbound_row")
            for field in ("first_pack_id", "source_board_sha256", "first_event_id",
                          "frozen_score", "frozen_rank", "frozen_lane", "entered"):
                require(old.get(field) == row[field], "existing_identity_conflict")
            require(set(old.get("event_ids") or []) <= set(row["event_ids"]),
                    "spool_regression")
            if old.get("confirmed") is not None:
                require(old["confirmed"] == row["confirmed"], "confirmation_revision_conflict")
                require(old.get("confirmation_pack_id") == row["confirmation_pack_id"],
                        "confirmation_generation_conflict")
        rows.append(row)
    merged = CR.merge_rows(existing, rows)
    close = max(closes, key=lambda x: x[0])[1] if closes else None
    receipt = CR.confirmation_receipt(close, canonical_board, session=session, built_at=now)
    return merged, {"spool_objects": len(keys), "distinct_events": len(all_events),
                    "archived_packs": sorted(packs), "close_board_available": close is not None,
                    "canonical_board_sha256": canonical_hash,
                    "receipt": receipt, "row_count": len(merged),
                    "close_and_fill_labels": "unresolved; this lab does not manufacture price-basis-aligned fills"}


def reconcile_file(path, *, read_frame, write_rows, reconcile):
    """Proposed native-driver order: strict read, complete validation, atomic write.

    Absence means no prior rows. An unreadable existing ledger never means empty.
    The function is exercised solely with a temporary file and the native writer.
    """
    if path.exists():
        try:
            existing = read_frame(path).to_dict(orient="records")
        except Exception:
            raise Refused("unreadable_existing_ledger") from None
    else:
        existing = []
    rows, receipt = reconcile(existing)
    write_rows(path, rows)
    return rows, receipt
