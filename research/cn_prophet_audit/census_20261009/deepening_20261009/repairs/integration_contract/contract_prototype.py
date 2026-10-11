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
import ast
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
EVENT_SCHEMA = "cn_prophet_live.events/research-v3"
INGEST_CONTRACT = "cn_prophet_live.evidence/research-v2"
TICKER = re.compile(r"^[0-9]{6}\.(?:SS|SZ)$")
HASH = re.compile(r"^[a-f0-9]{64}$")
NATIVE_LEDGER_SCHEMA = "cn_prophet_live.forward/v1"
LEDGER_MIN_COLUMNS = {"schema", "date", "ticker", "kind", "first_ts", "first_px",
                      "cross_px", "last_ts", "last_px", "occurrences", "confirmed",
                      "close_same_day", "next_close_fill"}
FIRST_OBSERVATION_FIELDS = (
    "date", "ticker", "kind", "first_ts", "first_px", "cross_px", "first_event_id",
    "first_pack_id", "source_board_sha256", "source_board_asof", "source_board_definition",
    "frozen_score", "frozen_rank", "frozen_score_rank", "frozen_lane", "first_quote_ts",
    "entered", "from_state", "via", "first_passes", "first_quote_age_min", "session_phase",
    "price_adjustment", "quote_contract_id", "quote_payload_sha256", "first_quote_record_sha256",
    "cross_basis_close", "cross_basis_adjustment",
)
QUOTE_ADAPTER_SHA256 = "bd8bfd85bf4ff1279d564220b7f3f8b8b4e5f7263323252ae6489ed5163d1074"
SYNTHETIC_QUOTE_CONTRACT = {
    "schema": "cn_prophet_live.synthetic_quote_contract/research-v1",
    "origin": "SYNTHETIC_RESEARCH_ONLY",
    "provider_shape": "Yahoo v7 spark response; synthetic observations",
    "adapter_path": "engine/live_quotes.py",
    "adapter_function": "parse_yahoo_spark",
    "adapter_source_sha256": QUOTE_ADAPTER_SHA256,
    "adapter_git_blob": "f7ad6ebc550811708a20aaf259b30dd1df0a3699",
    "study_pin": "3d90aad6d83152dfeeaf8345bc995826ac9d3139",
    "price_adjustment": "unadjusted_research_fixture",
    "price_unit": "CNY per share in an explicitly synthetic unadjusted scenario",
    "price_field": "spark.result[].response[0].meta.regularMarketPrice",
    "previous_close_field": "spark.result[].response[0].meta.previousClose",
    "timestamp_field": "spark.result[].response[0].meta.regularMarketTime",
    "payload_codec": "Retained original UTF-8 source text, hashed before JSON parsing",
    "scope": "Defines the synthetic scenario's units; does not certify natural Yahoo or Tencent adjustment semantics.",
}


class Refused(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def encoded(obj: Any) -> bytes:
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError, OverflowError):
        raise Refused("unserializable_evidence") from None


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
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return False
    try:
        return math.isfinite(raw) and (not positive or raw > 0)
    except (TypeError, ValueError, OverflowError):
        return False


class SyntheticQuoteResolver:
    """A replayable fixture contract, with no natural provider admitted.

    Exact pinned parser bytes are required. The native parser is AST-extracted
    without importing its network module. The synthetic contract defines units;
    provider/source/basis strings on an arbitrary quote never qualify it.
    """
    def __init__(self, adapter_source: bytes):
        require(sha256(adapter_source).hexdigest() == QUOTE_ADAPTER_SHA256,
                "quote_adapter_source_identity_mismatch")
        wanted = {"_now", "_delay_min", "parse_yahoo_spark"}
        nodes = [n for n in ast.parse(adapter_source.decode()).body
                 if isinstance(n, ast.FunctionDef) and n.name in wanted]
        require({n.name for n in nodes} == wanted, "quote_adapter_function_missing")
        namespace = {"datetime": datetime, "timezone": timezone}
        exec(compile(ast.Module(body=nodes, type_ignores=[]),
                     "pinned_native_quote_parser", "exec"), namespace)
        self.parser = namespace["parse_yahoo_spark"]
        self.contract = deepcopy(SYNTHETIC_QUOTE_CONTRACT)
        self.contract_id = digest(self.contract)
        self.adjustment = self.contract["price_adjustment"]

    def _parsed(self, payload: dict, recorded_at: datetime) -> dict:
        require(isinstance(payload, dict), "invalid_quote_payload")
        spark = payload.get("spark")
        require(isinstance(spark, dict), "invalid_quote_payload")
        items = spark.get("result")
        require(isinstance(items, list) and bool(items), "invalid_quote_payload")
        seen = set()
        for item in items:
            require(isinstance(item, dict), "invalid_quote_payload_row")
            ticker = item.get("symbol")
            require(isinstance(ticker, str) and bool(TICKER.fullmatch(ticker)),
                    "invalid_quote_payload_ticker")
            require(ticker not in seen, "duplicate_quote_payload_ticker")
            seen.add(ticker)
            response = item.get("response")
            require(isinstance(response, list) and len(response) == 1
                    and isinstance(response[0], dict), "invalid_quote_payload_response")
            meta = response[0].get("meta")
            require(isinstance(meta, dict), "invalid_quote_payload_meta")
            require(finite(meta.get("regularMarketPrice"), positive=True)
                    and finite(meta.get("previousClose"), positive=True), "invalid_quote_payload_price")
            require(type(meta.get("regularMarketTime")) is int
                    and finite(meta["regularMarketTime"], positive=True), "invalid_quote_payload_clock")
            require(meta.get("currency") == "CNY", "quote_payload_unit_mismatch")
        try:
            parsed = self.parser(payload, now=recorded_at)
        except (TypeError, ValueError, OverflowError, OSError):
            raise Refused("quote_adapter_replay_failed") from None
        require(set(parsed) == seen, "quote_adapter_projection_incomplete")
        return parsed

    def quotes(self, payload_bytes: bytes, *, recorded_at: datetime) -> dict:
        """Construct only a labeled synthetic fixture by replaying native code."""
        require(isinstance(payload_bytes, bytes), "quote_source_bytes_required")
        try:
            payload_text = payload_bytes.decode("utf-8")
            payload = json.loads(payload_text)
        except (UnicodeError, ValueError):
            raise Refused("invalid_quote_source_json") from None
        parsed = self._parsed(payload, recorded_at)
        result = {}
        for ticker, row in parsed.items():
            evidence = {"schema": "cn_prophet_live.quote_source/research-v1",
                        "contract_id": self.contract_id,
                        "origin": self.contract["origin"],
                        "recorded_at": recorded_at.isoformat(),
                        "payload_sha256": sha256(payload_bytes).hexdigest(),
                        "payload_utf8": payload_text,
                        "quote_record_sha256": digest(row)}
            result[ticker] = {**deepcopy(row), "price_adjustment": self.adjustment,
                              "source_evidence": evidence}
        return result

    def resolve(self, ticker: str, evidence: Any, *, known_by: datetime) -> dict:
        require(isinstance(evidence, dict), "quote_basis_evidence_unavailable")
        require(evidence.get("schema") == "cn_prophet_live.quote_source/research-v1"
                and evidence.get("contract_id") == self.contract_id
                and evidence.get("origin") == self.contract["origin"],
                "unsupported_quote_source_contract")
        recorded_at = stamp(evidence.get("recorded_at"))
        require(recorded_at <= known_by, "future_quote_source_receipt")
        payload_text = evidence.get("payload_utf8")
        require(isinstance(payload_text, str), "quote_source_bytes_required")
        require(evidence.get("payload_sha256") == sha256(payload_text.encode("utf-8")).hexdigest(),
                "quote_payload_identity_mismatch")
        try:
            payload = json.loads(payload_text)
        except ValueError:
            raise Refused("invalid_quote_source_json") from None
        parsed = self._parsed(payload, recorded_at)
        require(ticker in parsed, "quote_ticker_not_in_source_payload")
        row = parsed[ticker]
        require(row.get("quote_ts_synthetic") is False, "synthetic_quote_clock_unavailable")
        require(evidence.get("quote_record_sha256") == digest(row), "quote_record_identity_mismatch")
        return row

    def validate_quote(self, ticker: str, quote: dict, *, known_by: datetime) -> dict:
        row = self.resolve(ticker, quote.get("source_evidence"), known_by=known_by)
        require(quote.get("price_adjustment") == self.adjustment,
                "unsupported_quote_price_adjustment")
        # Validate every native adapter output, not a caller-provided True flag.
        require(all(quote.get(field) == value for field, value in row.items()),
                "quote_disagrees_with_source_payload")
        return row


def normalize_storage(value: Any) -> Any:
    """Canonical logical null/list/scalar values after Arrow/pandas readback."""
    if isinstance(value, dict):
        return {k: normalize_storage(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_storage(v) for v in value]
    if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
        return normalize_storage(value.tolist())
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def first_observation(row: dict) -> dict:
    result = {field: normalize_storage(row.get(field)) for field in FIRST_OBSERVATION_FIELDS}
    for field in ("frozen_rank", "frozen_score_rank", "first_passes"):
        value = result[field]
        if finite(value) and float(value).is_integer():
            result[field] = int(value)
    for field in ("first_px", "cross_px", "frozen_score", "first_quote_age_min", "cross_basis_close"):
        if finite(result[field]):
            result[field] = float(result[field])
    return result


def validate_existing(existing: Any, *, CR, LS, calendar, session: str) -> list[dict]:
    require(isinstance(existing, list), "invalid_existing_ledger")
    normalized = []
    seen = set()
    allowed = set(LS.EVENT_KINDS) | set(LS.INTERNAL_MARKERS)
    for raw in existing:
        require(isinstance(raw, dict), "invalid_existing_ledger_row")
        row = normalize_storage(raw)
        require(LEDGER_MIN_COLUMNS <= set(row), "invalid_existing_ledger_schema")
        require(row.get("schema") == CR.FORWARD_SCHEMA == NATIVE_LEDGER_SCHEMA,
                "invalid_existing_ledger_schema")
        try:
            day = date.fromisoformat(row.get("date"))
        except (TypeError, ValueError):
            raise Refused("invalid_existing_daily_key") from None
        require(day.isoformat() == row["date"] and row["date"] >= CR.LEDGER_FLOOR_SESSION
                and calendar.is_session(day), "invalid_existing_daily_key")
        require(isinstance(row.get("ticker"), str) and bool(TICKER.fullmatch(row["ticker"]))
                and isinstance(row.get("kind"), str) and row["kind"] in allowed,
                "invalid_existing_daily_key")
        key = tuple(row[field] for field in CR.KEY)
        require(key not in seen, "duplicate_existing_daily_key")
        seen.add(key)
        for field in ("first_px", "cross_px", "last_px", "close_same_day", "next_close_fill"):
            require(row.get(field) is None or finite(row[field], positive=True),
                    "invalid_existing_ledger_price")
        for field in ("first_ts", "last_ts"):
            if row.get(field) is not None:
                stamp(row[field])
        count = row.get("occurrences")
        if isinstance(count, float) and finite(count) and count.is_integer():
            row["occurrences"] = count = int(count)
        require(type(count) is int and count > 0, "invalid_existing_occurrences")
        require(row.get("confirmed") is None or type(row["confirmed"]) is bool,
                "invalid_existing_confirmation")
        if row["date"] == session:
            require(row.get("ingest_contract") == INGEST_CONTRACT, "legacy_unbound_row")
            ids = row.get("event_ids")
            require(isinstance(ids, list) and all(isinstance(v, str) and bool(HASH.fullmatch(v)) for v in ids)
                    and len(ids) == len(set(ids)) and bool(ids), "invalid_existing_event_ids")
            require(row.get("first_event_id") in ids, "invalid_existing_first_event")
        normalized.append(row)
    return normalized


def close_economics(close: dict) -> dict:
    """Observation equivalence excludes envelope nonce and display metadata."""
    lanes = close.get("lanes")
    require(isinstance(lanes, dict), "invalid_close_lanes")
    seen = set()
    normalized = {}
    for lane, rows in lanes.items():
        require(lane in {"featured", "more_actionable", "forming", "cross", "late_or_unfillable"}
                and isinstance(rows, list), "invalid_close_lane")
        got = []
        for row in rows:
            require(isinstance(row, dict) and isinstance(row.get("ticker"), str)
                    and bool(TICKER.fullmatch(row["ticker"])),
                    "invalid_close_ticker")
            require(row["ticker"] not in seen, "duplicate_close_ticker")
            seen.add(row.get("ticker"))
            got.append({field: deepcopy(row.get(field)) for field in
                        ("ticker", "price", "state", "market_status", "frozen", "revision")})
        if got:
            normalized[lane] = sorted(got, key=lambda row: row["ticker"])
    return {"session": close.get("session"), "pack_id": close.get("pack_id"),
            "revision": close.get("revision"), "close_pending": close.get("close_pending"),
            "close_coverage_pct": close.get("close_coverage_pct"), "lanes": normalized}


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
            prophet = row.get("prophet")
            require(isinstance(prophet, dict), "invalid_frozen_score")
            score = prophet.get("score")
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
    require(isinstance(source, dict), "invalid_source_board_identity")
    require(source.get("as_of") == pack.get("as_of")
            and bool(HASH.fullmatch(str(source.get("artifact_sha256") or ""))),
            "invalid_source_board_identity")
    if expected_asof is not None:
        require(pack.get("as_of") == expected_asof, "stale_or_future_pack")
    if known_by is not None:
        require(stamp(pack.get("built_at")) <= known_by, "future_pack_build")
    require(isinstance(pack.get("names"), dict), "invalid_pack_names")
    for ticker, entry in pack["names"].items():
        require(isinstance(ticker, str) and bool(TICKER.fullmatch(ticker)), "invalid_pack_ticker")
        require(isinstance(entry, dict), "invalid_pack_entry")
        require(finite(entry.get("as_of_close"), positive=True), "invalid_pack_close")
        if entry.get("frozen_status") == "in_source_board":
            frozen = entry.get("frozen") or {}
            require(isinstance(frozen, dict), "invalid_frozen_score")
            require(finite(frozen.get("score")) and 0 <= frozen["score"] <= 100,
                    "invalid_frozen_score")
            require(type(frozen.get("rank")) is int and frozen["rank"] > 0,
                    "invalid_frozen_rank")


def evaluate_checked(native, LS, clock, pack: dict, quotes: dict, prev: dict | None,
                     *, now: datetime, cfg: dict, quote_resolver=None, **kwargs) -> dict:
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
    rejected, resolved = {}, {}
    for ticker, quote in quotes.items():
        try:
            require(isinstance(quote, dict), "invalid_quote")
            qts = stamp(quote.get("quote_ts") or quote.get("ts"))
            require(qts <= now + timedelta(seconds=60), "future_quote")
            require(qts.astimezone(clock.CST).date().isoformat()
                    == clock.session_date(now).isoformat(), "wrong_quote_session")
            require(finite(quote.get("price"), positive=True), "invalid_quote_price")
            require(quote_resolver is not None, "quote_basis_evidence_unavailable")
            resolved[ticker] = quote_resolver.validate_quote(ticker, quote, known_by=now)
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
    # The pinned native serializers truncate to seconds. Retain the actual
    # supplied evaluation instant in the existing ISO fields so a receipt from
    # the same fractional second is not made to appear later than its event.
    observed = now.astimezone(UTC)
    require(stamp(art.get("built_at")).replace(microsecond=0) == observed.replace(microsecond=0),
            "native_artifact_clock_disagreement")
    art["built_at"] = observed.isoformat(timespec="microseconds")
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
    art["meta"]["quote_evidence_contract"] = (quote_resolver.contract_id if quote_resolver else None)
    art["meta"]["quote_basis_scope"] = "Synthetic source contract only; natural provider basis remains unavailable"
    admitted = []
    for ev in art.get("events", []):
        if ev["ticker"] not in resolved:
            continue
        require(stamp(ev.get("ts")).replace(microsecond=0) == observed.replace(microsecond=0),
                "native_event_clock_disagreement")
        ev["ts"] = observed.isoformat(timespec="microseconds")
        quote = clean.get(ev["ticker"]) or {}
        ev["quote_ts"] = quote.get("quote_ts") or quote.get("ts")
        require(ev.get("price") == resolved[ev["ticker"]]["price"],
                "event_disagrees_with_resolved_quote")
        ev["price_adjustment"] = quote["price_adjustment"]
        ev["quote_source"] = resolved[ev["ticker"]]["source"]
        ev["source_evidence"] = deepcopy(quote["source_evidence"])
        ev["event_id"] = digest({"pack_id": pack["pack_id"], **ev})
        admitted.append(ev)
    art["events"] = admitted
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
            canonical_board: dict | None, canonical_board_raw: bytes | None,
            quote_resolver=None) -> tuple[list[dict], dict]:
    """Proposed validation around native events_to_rows/merge/receipt.

    Event authority = archived N-1 pack. Confirmed gate verdict = N settlement
    pack. Membership confirmation = N canonical board. They are different joins.
    """
    existing = validate_existing(existing, CR=CR, LS=LS, calendar=calendar, session=session)
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
        require(isinstance(policy, dict), "missing_evaluation_policy")
        require(finite(policy.get("quote_max_age_min"), positive=True)
                and finite(policy.get("delay_floor_min")) and policy["delay_floor_min"] >= 0,
                "missing_evaluation_policy")
        events = doc.get("events")
        require(isinstance(events, list), "invalid_event_list")
        for ev in events:
            require(isinstance(ev, dict), "invalid_event")
            ticker, kind = ev.get("ticker"), ev.get("kind")
            require(isinstance(ticker, str) and ticker in pack["names"]
                    and bool(TICKER.fullmatch(ticker)),
                    "event_ticker_outside_pack")
            require(isinstance(kind, str) and kind in allowed, "invalid_event_kind")
            event_ts, quote_ts = stamp(ev.get("ts")), stamp(ev.get("quote_ts"))
            require(event_ts <= built, "future_event")
            require(stamp(pack.get("built_at")) <= event_ts, "future_pack_build")
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
            require(quote_resolver is not None, "quote_basis_evidence_unavailable")
            require(ev.get("price_adjustment") == quote_resolver.adjustment,
                    "unknown_event_price_adjustment")
            if ev.get("px") is not None:
                require(ev["px"] == ev["price"], "ambiguous_event_price")
            resolved_quote = quote_resolver.resolve(ticker, ev.get("source_evidence"), known_by=event_ts)
            require(ev["price"] == resolved_quote["price"]
                    and stamp(ev["quote_ts"]) == stamp(resolved_quote["quote_ts"])
                    and ev.get("quote_source") == resolved_quote["source"],
                    "event_quote_source_disagreement")
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
            economics = close_economics(close)
            for rows in (close.get("lanes") or {}).values():
                for row in rows:
                    ticker = row.get("ticker")
                    require(ticker in pack["names"], "close_ticker_outside_pack")
                    require(row.get("frozen") == pack["names"][ticker].get("frozen"),
                            "close_frozen_field_mismatch")
            closes.append((built, economics, key))
    all_events.sort(key=lambda row: (stamp(row["ts"]), row["event_id"]))
    # A vanished daily key cannot evade full-session consumed-set validation.
    resolved_ids = set(seen_events)
    resolved_keys = {(session, event["ticker"], event["kind"]) for event in all_events}
    for old in existing:
        if old["date"] != session:
            continue
        require(set(old["event_ids"]) <= resolved_ids
                and tuple(old[field] for field in CR.KEY) in resolved_keys,
                "spool_regression")
        require(old["occurrences"] == len(old["event_ids"]), "invalid_existing_event_count")
    close_groups = {}
    for built, economics, key in closes:
        signature = digest(economics)
        group = close_groups.get(built)
        if group is None:
            close_groups[built] = {"economics": economics, "economics_sha256": signature,
                                   "object_keys": [key]}
        else:
            require(group["economics_sha256"] == signature, "conflicting_equal_time_close_evidence")
            group["object_keys"].append(key)
    close, close_evidence = None, None
    if close_groups:
        built = max(close_groups)
        group = close_groups[built]
        close = group["economics"]
        close_evidence = {"built_at": built.isoformat(),
                          "economics_sha256": group["economics_sha256"],
                          "object_keys": sorted(set(group["object_keys"])),
                          "authority": "latest observation time; equivalent economics coalesced; conflicting ties refused"}
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
        # Native event time has only second precision. A digest is an identity,
        # not an ordering authority for different observations at that instant.
        event_times = [stamp(ev["ts"]) for ev in matched]
        require(len(event_times) == len(set(event_times)), "ambiguous_equal_time_events")
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
                    "quote_contract_id": first["source_evidence"]["contract_id"],
                    "quote_payload_sha256": first["source_evidence"]["payload_sha256"],
                    "first_quote_record_sha256": first["source_evidence"]["quote_record_sha256"],
                    "cross_basis_close": entry["as_of_close"],
                    "cross_basis_adjustment": entry.get("price_adjustment"),
                    "confirmation_pack_id": (settlement_pack or {}).get("pack_id"),
                    "confirmation_basis": "same_session_pack_center_buyable" if verdict is not None else None})
        row["first_observation_sha256"] = digest(first_observation(row))
        old = next((p for p in existing if tuple(p.get(k) for k in CR.KEY)
                    == tuple(row.get(k) for k in CR.KEY)), None)
        if old:
            require(old.get("ingest_contract") == INGEST_CONTRACT, "legacy_unbound_row")
            for field in ("first_pack_id", "source_board_sha256", "first_event_id",
                          "frozen_score", "frozen_rank", "frozen_lane", "entered"):
                require(old.get(field) == row[field], "existing_identity_conflict")
            require(first_observation(old) == first_observation(row)
                    and old.get("first_observation_sha256") == row["first_observation_sha256"],
                    "existing_first_observation_conflict")
            require(set(old.get("event_ids") or []) <= set(row["event_ids"]),
                    "spool_regression")
            if old.get("confirmed") is not None:
                require(old["confirmed"] == row["confirmed"], "confirmation_revision_conflict")
                require(old.get("confirmation_pack_id") == row["confirmation_pack_id"],
                        "confirmation_generation_conflict")
        rows.append(row)
    merged = CR.merge_rows(existing, rows)
    receipt = CR.confirmation_receipt(close, canonical_board, session=session, built_at=now)
    return merged, {"spool_objects": len(keys), "distinct_events": len(all_events),
                    "archived_packs": sorted(packs), "close_board_available": close is not None,
                    "canonical_board_sha256": canonical_hash,
                    "selected_close_evidence": close_evidence,
                    "receipt": receipt, "row_count": len(merged),
                    "close_and_fill_labels": "unresolved; this lab does not manufacture price-basis-aligned fills"}


def reconcile_file(path, *, read_frame, write_rows, reconcile):
    """Proposed native-driver order: strict read, complete validation, atomic write.

    Absence means no prior rows. An unreadable existing ledger never means empty.
    The function is exercised solely with a temporary file and the native writer.
    """
    if path.exists():
        try:
            frame = read_frame(path)
        except Exception:
            raise Refused("unreadable_existing_ledger") from None
        columns = set(frame.columns)
        # Native _write_parquet emits a lone schema column for an empty ledger.
        require(LEDGER_MIN_COLUMNS <= columns or (len(frame) == 0 and columns == {"schema"}),
                "invalid_existing_ledger_schema")
        existing = frame.to_dict(orient="records")
    else:
        existing = []
    rows, receipt = reconcile(existing)
    write_rows(path, rows)
    return rows, receipt
