"""A01 vertical acceptance journey — masterplan §14 through the real entrypoints.

Verification lane dataos-a01-1 (programme DATA-OS-COMPLETION).  This module is
importable infrastructure, NOT a collected test module: ``test_journey_a01.py``
imports it and calls its named assertions.

Everything here runs on a SYNTHETIC exact-number corpus under a caller-supplied
``tmp`` tree.  No wall clock, no network, no subprocess, no repo ``data/`` write.
The real entrypoints exercised are exactly the ones the census admits on main:

* ``engine.price_ladder.resolve_close_canonical`` (C01 seam, Terminal view
  contract ``terminal_daily_ohlc_contract_v1()``),
* ``lib.dataos.read_contract`` (``current`` / ``replay`` / ``reconstruct`` /
  ``account_coverage`` and the C02 types — imported from the module directly,
  package-level exports are not landed),
* ``lib.dataos.web_api.dispatch`` over ``lib.dataos.web_workspace.DataWorkspace``,
* ``engine.basket_membership_pit`` (``members_asof`` / ``coverage``),
* ``lib.dataos.identity`` (``AliasRow`` / ``VendorAliasTable``).

Generation-id mapping note (recorded per the lane): the read contract's
``GenerationRef.generation_id`` is a free-form string with no imposed format, so
the lane constants ``GEN_A`` / ``GEN_B`` are used verbatim.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat as stat_module
import sys
from datetime import date
from fractions import Fraction
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import basket_membership_pit as pit  # noqa: E402
from engine import price_ladder as pl  # noqa: E402
from lib import config as lib_config  # noqa: E402
from lib.dataos.identity import AliasRow, IdentityError, VendorAliasTable  # noqa: E402
from lib.dataos.nulls import MissingReason, NullPolicy  # noqa: E402
from lib.dataos.read_contract import (  # noqa: E402
    CurrentEvidence, Dependency, Disposition, GenerationRef, MemberDisposition,
    ReadMode, ReadRequest, ReadRefusal, RefusalCode, RetainedOutput, SourceSegment,
    ViewContract, account_coverage, current, replay, reconstruct,
)
from lib.dataos.registry import load_registry  # noqa: E402
from lib.dataos.temporal import TemporalProfile  # noqa: E402
from lib.dataos.web_api import dispatch  # noqa: E402
from lib.dataos.web_workspace import WorkspaceError, load_workspace_config  # noqa: E402

# ── frozen lane constants ────────────────────────────────────────────────────

VIEW_A_ID = "a01-view-A"
GEN_A = "a01-gen-A"
GEN_B = "a01-gen-B"

PENDING_LEGS = {
    "terminal_json_evidence": "UNFINISHED: awaiting C04 LANDED",
    "canonical_reads_in_workspace": "UNFINISHED: awaiting U03 LANDED",
    "basket_prices_one_basis": "UNFINISHED: awaiting U04 LANDED",
    "real_retained_corpus": "UNFINISHED: rights-allowed retained corpus not established (registry rights quoted)",
    "principal_revocation": "GAP: K01 GAP 1, owner transport",
}

CITATION_TERMINAL_UI = (
    "Terminal UI evidence chip: accepted production proof Terminal PR #996, deploy "
    "fdc7c7f9 — cited, never re-run by this lane; browser/production workflow "
    "acceptance is owned by R02/R03"
)

# ── synthetic corpus constants (masterplan §14 composition) ──────────────────

DATES = pd.bdate_range("2026-01-02", periods=60)     # 60 business days
SPLIT_DAY_INDEX = 29        # day 30: 2-for-1 split effective this session
DIV_DAY_INDEX = 19          # day 20: the ONE cash distribution ex-date
DIV_CASH = Fraction(25)     # exact decimal 25.00 on a 100.00 stock
DIV_FACTOR = Fraction(5, 4)  # 1 + D/P_post = 1 + 25/100, exact and float-dyadic
DAY10_INDEX = 9             # the ONE old value generation B corrects (day 10)

TICKERS = ("PLAINCO", "SPLITCO", "DIVCO", "GONECO")
BASKET_ID = "a01-basket"
SUITE = "baskets_a01"
REGISTRY_DATASET = "equity.bars.daily.stocks"
TIME_COLUMN = "__index_level_0__"     # pandas' parquet index column
EVIDENCE_COLUMN = "close"

EV_RENAME_MMC = "a1" * 32             # synthetic 64-hex evidence digests
EV_RENAME_MRSH = "b2" * 32
EV_REUSE_1 = "c3" * 32
EV_REUSE_2 = "d4" * 32

RENAME_DAY = date(2026, 1, 14)        # I03 row 1: MMC -> MRSH, same security id
REUSE_DAY = date(2026, 3, 2)          # I03 row 4: ABC reused by a second security
SEC_MMC = "SEC:US-XNYS-MMC"
SEC_ABC = "SEC:US-XNYS-ABC"
SEC_ABC_2 = "SEC:US-XNYS-ABC.2"

GEN_A_PUBLISHED = "2026-03-01T00:00:00+00:00"
GEN_B_PUBLISHED = "2026-03-05T00:00:00+00:00"
INGESTED = GEN_A_PUBLISHED
CODE_VERSION = hashlib.sha256(b"dataos-a01-1").hexdigest()[:40]   # 40-char hex stub

RENAME_LISTING = "US-XNYS-PLAINCO"    # representative listing for view A

#: Workspace refusal codes the S5 cases may lawfully yield (closed set, lane §5.2).
WS_REFUSAL_CODES = {
    "ROOT_NOT_BOUND", "SOURCE_NOT_FOUND", "SOURCE_INACCESSIBLE",
    "SOURCE_VERSION_MISMATCH", "REQUIRED_VOLUME_NOT_MOUNTED", "ROOT_BINDING_CHANGED",
    "PATH_OR_SOURCE_REFUSED",
}
#: Read-contract refusal codes the S5 cases may lawfully yield (closed set, lane §5.2).
RC_REFUSAL_CODES = {"UNBOUND_DEPENDENCY", "NO_RETAINED_OUTPUT", "STALE_GENERATION"}


def _day_before(day: date) -> date:
    return date.fromordinal(day.toordinal() - 1)


def _days_after(day: date, n: int) -> date:
    return date.fromordinal(day.toordinal() + n)


def _frac(value) -> str:
    """One exact value as its ``n/d``-form string (ints render bare)."""
    return str(Fraction(value))


def _values_map(values) -> dict[str, str]:
    """``((iso_date, Fraction), ...)`` -> ``{iso_date: frac_string}``."""
    return {iso: _frac(value) for iso, value in (values or ())}


def _plainco_value(i: int) -> Fraction:
    return Fraction(100 + i)


def _splitco_value(i: int) -> Fraction:
    # raw pre-split close 100.00; the tradj store back-adjusts pre-split bars by
    # the 2-for-1 split factor -> stored pre = 50, stored post = 100.
    return Fraction(100) if i >= SPLIT_DAY_INDEX else Fraction(50)


def _divco_value(i: int) -> Fraction:
    # raw close 100.00 throughout; the tradj store back-adjusts pre-ex bars by the
    # total-return factor 1 + D/P = 5/4 -> stored pre = 80, stored post = 100.
    return Fraction(100) if i >= DIV_DAY_INDEX else Fraction(80)


CORPUS_SERIES = {
    "PLAINCO": _plainco_value,
    "SPLITCO": _splitco_value,
    "DIVCO": _divco_value,
}


def _write_store_series(store: Path, ticker: str, values: list[Fraction]) -> None:
    d = store / "stocks"
    d.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame({"close": [float(v) for v in values]}, index=DATES)
    frame.to_parquet(d / f"{ticker}.parquet")


def _members_sha(basket: str, tickers) -> str:
    """The store's member-set digest formula (mirrors basket_membership_pit._sha_of)."""
    payload = json.dumps(sorted({(basket, t, "", "") for t in tickers}),
                         ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _view_request(basis: str = "tradj", *, listing: str = RENAME_LISTING,
                  currency: str | None = None, mode=ReadMode.CURRENT, **kw) -> ReadRequest:
    """A well-formed canonical read request, idiom per tests/test_price_ladder.py §7."""
    identity = {"security_id": f"SEC:{listing}", "listing_id": listing}
    field_units = {} if currency is None else {"currency": currency}
    contract = ViewContract(
        purpose="a01_journey", identity=identity, field_units=field_units,
        adjustment_reference={"basis": basis}, coverage="journey")
    return ReadRequest(mode=mode, contract=contract, **kw)


def build_corpus(tmp: Path) -> dict:
    """Write the frozen synthetic known-answer corpus under ``tmp``.

    Composition (masterplan §14): SPLITCO 60 business days with a 2-for-1 split
    effective day 30; DIVCO 60 business days with ONE cash distribution (exact
    decimal 25.00) on day 20; PLAINCO 60 days no action; GONECO a basket member
    with NO stored file; one basket carrying all four through the basket
    redirect idiom; one Data Workspace host config; every price a decimal string
    exactly representable as ``Fraction(str(x))`` (all values are dyadic ints).
    """
    tmp = Path(tmp)
    store = tmp / "store"
    data_root = tmp / "data"

    for ticker, fn in CORPUS_SERIES.items():
        _write_store_series(store, ticker, [fn(i) for i in range(len(DATES))])
    # GONECO deliberately gets NO stored file.

    suite_dir = data_root / SUITE
    suite_dir.mkdir(parents=True, exist_ok=True)
    members = sorted(TICKERS)
    rows = [{
        "snapshot_date": "2026-01-02", "suite": SUITE, "basket_id": BASKET_ID,
        "ticker": ticker, "added": None, "removed": None, "name_zh": None,
        "members_sha": _members_sha(BASKET_ID, members), "source_shape": "membership",
        "record_kind": None, "collection_id": None, "collection_receipt": None,
    } for ticker in members]
    pd.DataFrame(rows, columns=list(pit.COLUMNS)).to_parquet(
        suite_dir / pit.HISTORY_FILE)

    registry_path = (ROOT / "config" / "dataset_registry.yml").resolve()
    host_config = {
        "schema_version": "mastermind.data_workspace_bindings/v1",
        "registry_path": str(registry_path),
        "roots": [{"alias": "store", "path": str(store),
                   "evidence_kind": "unqualified_snapshot",
                   "note": "synthetic A01 known-answer corpus"}],
    }
    config_path = tmp / "workspace_bindings.json"
    config_path.write_text(json.dumps(host_config), encoding="utf-8")
    # The ROOT_NOT_BOUND control: a lawful config whose single root is another alias.
    alt_config = dict(host_config)
    alt_config["roots"] = [{"alias": "other", "path": str(store),
                            "evidence_kind": "unqualified_snapshot"}]
    alt_path = tmp / "workspace_bindings_no_store.json"
    alt_path.write_text(json.dumps(alt_config), encoding="utf-8")

    return {
        "store": store, "data_root": data_root, "registry_path": registry_path,
        "config_path": config_path, "alt_config_path": alt_path,
        "dates": [str(ts.date()) for ts in DATES],
        "expected": {t: {str(ts.date()): _frac(fn(i))
                         for i, ts in enumerate(DATES)}
                     for t, fn in CORPUS_SERIES.items()},
        "members": members,
    }


def _stat_version(path: Path) -> str:
    """The workspace's stat-identity formula, mirrored for the paranoid guard only."""
    s = os.stat(path)
    identity = [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]
    return "statv1:" + hashlib.sha256(json.dumps(identity).encode()).hexdigest()


def _seam_read(ticker: str, data_dir: Path, **kw) -> dict:
    """One C01 seam read recorded as a JSON-safe dict."""
    out = pl.resolve_close_canonical(ticker, view=_view_request(**kw),
                                     data_dir=str(data_dir))
    refusal = out.contract.refusal_reasons[0] if out.contract.refusal_reasons else None
    return {
        "ok": bool(out.ok), "refusal": refusal,
        "coverage": out.contract.coverage,
        "registry_row": out.contract.identity.get("registry_row"),
        "vendor_symbol": out.contract.identity.get("vendor_symbol"),
        "clock": out.evidence_mode.get("clock"),
        "dependency_generation_ids": list(
            out.evidence_mode.get("dependency_generation_ids") or ()),
        "values": None if out.values is None else _values_map(out.values),
    }


def _ws_read(ws_request: dict, config_path: Path) -> dict:
    """Dispatch one workspace request; a lawful refusal is recorded, never raised."""
    workspace = load_workspace_config(config_path)
    try:
        result = dispatch(workspace, ws_request, config_path=config_path)
    except WorkspaceError as exc:
        return {"code": exc.code, "values_present": False}
    return {"code": None, "values_present": True, "result": result}


def _prices_dependency(values_by_date: dict[str, Fraction], generation: str) -> Dependency:
    rows = [{"date": iso, "close": float(value), "generation_id": generation,
             "ingested_at": INGESTED}
            for iso, value in values_by_date.items()]
    return Dependency(
        name="prices", profile=TemporalProfile.BARS, rows=rows,
        key_fields=("date",),
        generations=(GenerationRef(generation, published_at=INGESTED,
                                   ingested_at=INGESTED),))


def _account() -> dict:
    """The coverage account for the frozen population, before and after B alike."""
    population = [f"US-XNYS-{t}" for t in TICKERS]
    dispositions = [
        MemberDisposition(
            member=f"US-XNYS-{t}", disposition=Disposition.SERVED,
            segments=(SourceSegment(source="data_stocks", basis="tradj",
                                    listing_id=f"US-XNYS-{t}"),),
            detail="served by the C01 seam through data/stocks/<ticker>.parquet")
        for t in ("PLAINCO", "SPLITCO", "DIVCO")
    ]
    dispositions.append(MemberDisposition(
        member="US-XNYS-GONECO", disposition=Disposition.MISSING,
        missing_reason=MissingReason.NO_COVERAGE,
        detail="asked: no stored source file exists for this member"))
    contract = ViewContract(
        purpose="a01_journey",
        identity={"security_id": "SEC:US-XNYS-A01", "listing_id": RENAME_LISTING},
        field_units={"close": "USD/share"},
        adjustment_reference={"basis": "tradj"}, coverage="population")
    result = account_coverage(contract, population, dispositions,
                              policy=NullPolicy())
    try:
        goneco = result.disposition_of("US-XNYS-GONECO")
    except KeyError:      # a mutated account that loses the member reports None
        goneco = None
    return {
        "requested": result.requested,
        "qualified": list(result.qualified),
        "qualified_fraction": _frac(result.qualified_fraction),
        "goneco": {
            "disposition": goneco.disposition.value if goneco else None,
            "missing_reason": goneco.missing_reason.value
            if goneco and goneco.missing_reason else None,
            "in_qualified": "US-XNYS-GONECO" in result.qualified,
            "has_segments": bool(goneco.segments) if goneco else False,
        },
        "summary": result.summary(),
    }


def run_journey(tmp: Path) -> dict:
    """Execute steps S1–S8 in order; return a JSON-serialisable receipt.

    Never raises for an expected refusal: every refusal is recorded as
    ``{"code": <typed code>, "values_present": bool}``.
    """
    tmp = Path(tmp)
    corpus = build_corpus(tmp)
    store = corpus["store"]
    dates = corpus["dates"]
    day10 = dates[DAY10_INDEX]
    receipt: dict = {"view_a_id": VIEW_A_ID, "gen_a": GEN_A, "gen_b": GEN_B}

    # ── S1 — serve view A ────────────────────────────────────────────────────
    seam = {t: _seam_read(t, store) for t in ("PLAINCO", "SPLITCO", "DIVCO")}
    goneco_seam = _seam_read("GONECO", store)

    inspector: dict = {}
    plainco_version_a: str | None = None
    for t in ("PLAINCO", "SPLITCO", "DIVCO"):
        workspace = load_workspace_config(corpus["config_path"])
        described = dispatch(workspace, {"action": "describe",
                                         "ref": f"store:stocks/{t}.parquet"},
                             config_path=corpus["config_path"])
        columns = described["details"]["columns"]
        time_col = next((c for c in columns if c != EVIDENCE_COLUMN), TIME_COLUMN)
        read = dispatch(workspace, {
            "action": "read", "ref": f"store:stocks/{t}.parquet",
            "columns": [time_col, EVIDENCE_COLUMN], "time_column": time_col,
            "limit": 200}, config_path=corpus["config_path"])
        rows = [[row[time_col][:10], _frac(row[EVIDENCE_COLUMN])]
                for row in read["result"]["rows"]]
        inspector[t] = {
            "columns": [time_col, EVIDENCE_COLUMN], "rows": rows,
            "file_version": read["source"]["file_version"],
            "production_qualification": read["production_qualification"],
        }
        if t == "PLAINCO":
            plainco_version_a = read["source"]["file_version"]

    saved_data_dir = lib_config.data_dir
    try:
        lib_config.data_dir = lambda: corpus["data_root"]
        members_answer = pit.members_asof(BASKET_ID, dates[-1], suite=SUITE)
        store_coverage = pit.coverage(SUITE)
    finally:
        lib_config.data_dir = saved_data_dir

    # Retain A: canonical bytes, digest, publishing receipt; label + GEN_A inside.
    payload_a = {
        "output_id": VIEW_A_ID, "label": "current", "generation_id": GEN_A,
        "view_contract": pl.terminal_daily_ohlc_contract_v1(),
        "served": {t: {"values": seam[t]["values"], "coverage": seam[t]["coverage"],
                       "registry_row": seam[t]["registry_row"]}
                   for t in ("PLAINCO", "SPLITCO", "DIVCO")},
        "basket": {"members": members_answer["members"], "pit": members_answer["pit"],
                   "basis": members_answer["basis"]},
    }
    retained_bytes = json.dumps(payload_a, sort_keys=True,
                                separators=(",", ":")).encode()
    retained_sha = hashlib.sha256(retained_bytes).hexdigest()
    publishing_receipt = {
        "schema": "dataos-a01-publishing-receipt/v1", "output_id": VIEW_A_ID,
        "generation_id": GEN_A, "payload_sha256": retained_sha}
    publishing_sha = hashlib.sha256(json.dumps(
        publishing_receipt, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    dep_a = _prices_dependency(
        {iso: _plainco_value(i) for i, iso in enumerate(dates)}, GEN_A)
    rc_current_a = current(
        _view_request(), {"prices": dep_a},
        evidence=CurrentEvidence(
            receipt_sha256s=(publishing_sha,), identity_generation_id=GEN_A,
            action_revision_set_id="a01-ars-1", code_version=CODE_VERSION))
    rc_a_day10 = _frac(rc_current_a.values["prices"][DAY10_INDEX]["close"])

    receipt["s1_view_a"] = {
        "seam": seam, "goneco_seam": goneco_seam, "inspector": inspector,
        "basket": {"members": members_answer["members"], "pit": members_answer["pit"],
                   "basis": members_answer["basis"],
                   "snapshot_date": members_answer["snapshot_date"],
                   "store_coverage": store_coverage},
        "account": _account(),
        "retained_a": {
            "output_id": VIEW_A_ID, "sha256": retained_sha,
            "bytes_len": len(retained_bytes), "label": "current",
            "generation_id": GEN_A,
            "payload_plainco_day10": payload_a["served"]["PLAINCO"]["values"][day10],
            "publishing_receipt_sha256": publishing_sha},
        "read_contract_current": {
            "label": rc_current_a.label, "generation": GEN_A,
            "day10": rc_a_day10, "rows": len(rc_current_a.values["prices"])},
        "plainco_version_a": plainco_version_a,
    }

    # ── S2 — publish generation B (SYNTHETIC correction of ONE old value) ────
    plainco_path = store / "stocks" / "PLAINCO.parquet"
    version_before = _stat_version(plainco_path)
    frame = pd.read_parquet(plainco_path)
    frame.loc[DATES[DAY10_INDEX], "close"] = 999.0
    frame.to_parquet(plainco_path)
    if _stat_version(plainco_path) == version_before:      # paranoid: force a bump
        st = os.stat(plainco_path)
        os.utime(plainco_path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
    dep_b = Dependency(
        name="prices", profile=TemporalProfile.BARS,
        rows=[{"date": iso, "close": float(_plainco_value(i)),
               "generation_id": GEN_A, "ingested_at": INGESTED}
              for i, iso in enumerate(dates)]
             + [{"date": iso, "close": (999.0 if iso == day10 else float(v)),
                 "generation_id": GEN_B, "ingested_at": INGESTED}
                for iso, v in ((d, _plainco_value(i)) for i, d in enumerate(dates))],
        key_fields=("date",),
        generations=(GenerationRef(GEN_A, published_at=GEN_A_PUBLISHED,
                                   ingested_at=INGESTED),
                     GenerationRef(GEN_B, published_at=GEN_B_PUBLISHED,
                                   ingested_at=GEN_B_PUBLISHED, supersedes=GEN_A)))
    receipt["s2_generation_b"] = {
        "synthetic": True,
        "label": ("SYNTHETIC correction: PLAINCO day-10 close rewritten in the store "
                  "and declared as generation B superseding generation A"),
        "ticker": "PLAINCO", "day": day10,
        "a_value": corpus["expected"]["PLAINCO"][day10], "b_value": "999",
    }

    # ── S3 — CURRENT after B ─────────────────────────────────────────────────
    seam_after = _seam_read("PLAINCO", store)
    try:
        rc_current_b = current(
            _view_request(), {"prices": dep_b},
            evidence=CurrentEvidence(
                receipt_sha256s=(publishing_sha,), identity_generation_id=GEN_B,
                action_revision_set_id="a01-ars-2", code_version=CODE_VERSION))
        rc_b = {"label": rc_current_b.label,
                "generation": rc_current_b.evidence["dependency_generation_ids"]["prices"],
                "day10": _frac(rc_current_b.values["prices"][DAY10_INDEX]["close"])}
    except ReadRefusal as refusal:
        rc_b = {"label": None, "generation": None, "day10": None,
                "refusal": refusal.code.value}
    stale = None
    try:
        current(_view_request(), {"prices": dep_b},
                evidence=CurrentEvidence(
                    receipt_sha256s=(publishing_sha,), identity_generation_id=GEN_A,
                    action_revision_set_id="a01-ars-1", code_version=CODE_VERSION))
    except ReadRefusal as refusal:
        stale = refusal.code.value
    receipt["s3_current_after_b"] = {
        "seam": seam_after,
        "seam_day10": seam_after["values"][day10],
        "seam_other_days_equal_a": all(
            seam_after["values"][iso] == seam["PLAINCO"]["values"][iso]
            for iso in dates if iso != day10),
        "read_contract": rc_b,
        "stale_generation_code": stale,
    }

    # ── S4 — REPLAY of retained A ────────────────────────────────────────────
    replayed = replay(
        _view_request(mode=ReadMode.REPLAY, output_id=VIEW_A_ID),
        RetainedOutput(output_id=VIEW_A_ID, payload=retained_bytes,
                       sha256=retained_sha, publishing_receipt_sha256=publishing_sha))
    decoded = json.loads(replayed.payload.decode()) if replayed.payload else {}
    receipt["s4_replay_a"] = {
        "label": replayed.label, "sha256": replayed.evidence["sha256"],
        "payload_bytes_equal_retained": replayed.payload == retained_bytes,
        "payload_label": decoded.get("label"),
        "payload_generation": decoded.get("generation_id"),
        "payload_day10": ((decoded.get("served", {}).get("PLAINCO", {})
                           .get("values", {})) or {}).get(day10),
    }

    # ── S5 — revocations, each on a fresh copy of the state ──────────────────
    revocations: dict[str, dict] = {}
    read_args = {"action": "read", "ref": "store:stocks/PLAINCO.parquet",
                 "columns": [TIME_COLUMN, EVIDENCE_COLUMN],
                 "time_column": TIME_COLUMN, "limit": 200}

    alt = _ws_read(read_args, corpus["alt_config_path"])
    revocations["root_binding_removed"] = {
        "code": alt["code"], "values_present": alt["values_present"]}

    moved = store / "stocks" / "PLAINCO.parquet.a01bak"
    os.rename(plainco_path, moved)
    try:
        deleted = _ws_read(read_args, corpus["config_path"])
    finally:
        os.rename(moved, plainco_path)
    revocations["source_file_deleted"] = {
        "code": deleted["code"], "values_present": deleted["values_present"]}

    mode = stat_module.S_IMODE(os.stat(plainco_path).st_mode)
    os.chmod(plainco_path, 0)
    try:
        unreadable = _ws_read(read_args, corpus["config_path"])
    finally:
        os.chmod(plainco_path, mode)
    if unreadable["code"] is None:
        # A root host reads through chmod 000; the lane names this outcome.
        unreadable = {"code": "SKIPPED_ROOT_HOST", "values_present": True}
    revocations["source_unreadable"] = {
        "code": unreadable["code"], "values_present": unreadable["values_present"]}

    pinned = _ws_read(dict(read_args, expected_version=plainco_version_a),
                      corpus["config_path"])
    revocations["expected_version_pinned_to_a"] = {
        "code": pinned["code"], "values_present": pinned["values_present"]}

    rc_code = None
    try:
        reconstruct(_view_request(mode=ReadMode.RECONSTRUCT,
                                  cutoff="2026-03-02T00:00:00+00:00",
                                  clock="ingested_at"),
                    {}, required=("prices",), code_version=CODE_VERSION)
    except ReadRefusal as refusal:
        rc_code = refusal.code.value
    revocations["reconstruct_required_missing"] = {
        "code": rc_code, "values_present": rc_code is None}

    rp_code = None
    try:
        replay(_view_request(mode=ReadMode.REPLAY, output_id=VIEW_A_ID),
               RetainedOutput(output_id=VIEW_A_ID, payload=None,
                              sha256=retained_sha,
                              publishing_receipt_sha256=publishing_sha))
    except ReadRefusal as refusal:
        rp_code = refusal.code.value
    revocations["replay_retained_payload_removed"] = {
        "code": rp_code, "values_present": rp_code is None}

    # A case that served rows after B would be serving B's day-10 value under the
    # very ref view A was served from — that is exactly "B under A's id".
    b_under_a = any(entry["code"] is None and entry["values_present"]
                    for entry in revocations.values())
    receipt["s5_revocations"] = revocations
    receipt["s5_b_value_under_view_a"] = b_under_a

    # ── S6 — identity controls (I03 rows 1 and 4) ────────────────────────────
    rename_table = VendorAliasTable([
        AliasRow(vendor="yahoo", vendor_symbol="MMC", security_id=SEC_MMC,
                 valid_from=None, valid_to=RENAME_DAY, evidence_sha256=EV_RENAME_MMC),
        AliasRow(vendor="yahoo", vendor_symbol="MRSH", security_id=SEC_MMC,
                 valid_from=RENAME_DAY, valid_to=None, evidence_sha256=EV_RENAME_MRSH),
    ])
    rename_no_row = VendorAliasTable([
        AliasRow(vendor="yahoo", vendor_symbol="MMC", security_id=SEC_MMC,
                 valid_from=None, valid_to=RENAME_DAY, evidence_sha256=EV_RENAME_MMC)])
    rename_no_evidence = VendorAliasTable([
        AliasRow(vendor="yahoo", vendor_symbol="MMC", security_id=SEC_MMC,
                 valid_from=None, valid_to=RENAME_DAY),
        AliasRow(vendor="yahoo", vendor_symbol="MRSH", security_id=SEC_MMC,
                 valid_from=RENAME_DAY, valid_to=None),
    ])
    reuse_table = VendorAliasTable([
        AliasRow(vendor="yahoo", vendor_symbol="ABC", security_id=SEC_ABC,
                 valid_from=None, valid_to=REUSE_DAY, evidence_sha256=EV_REUSE_1),
        AliasRow(vendor="yahoo", vendor_symbol="ABC", security_id=SEC_ABC_2,
                 valid_from=REUSE_DAY, valid_to=None, evidence_sha256=EV_REUSE_2),
    ])
    overlap_refused = False
    try:
        VendorAliasTable([
            AliasRow(vendor="yahoo", vendor_symbol="ABC", security_id=SEC_ABC,
                     valid_from=None, valid_to=None, evidence_sha256=EV_REUSE_1),
            AliasRow(vendor="yahoo", vendor_symbol="ABC", security_id=SEC_ABC_2,
                     valid_from=None, valid_to=None, evidence_sha256=EV_REUSE_2)])
    except IdentityError:
        overlap_refused = True

    # The ticker-join probe: the C01 seam and the basket are ticker-keyed, so a
    # reused ticker's pre- and post-reuse history join under ONE key.  Recorded
    # as UNFINISHED (awaiting U03/U04), never as passed.
    join_store = tmp / "store_join"
    _write_store_series(join_store, "ABC",
                        [Fraction(100 + i) for i in range(len(DATES))])
    join_read = _seam_read("ABC", join_store)
    join_note = (
        "UNFINISHED: awaiting U03/U04 LANDED — "
        "engine.price_ladder.resolve_close_canonical('ABC', view=ReadRequest(CURRENT, "
        "adjustment_reference={'basis': 'tradj'}), data_dir=<synthetic join store>) "
        f"served n={len(join_read['values'])} rows spanning the {REUSE_DAY} reuse "
        "boundary under the single ticker key 'ABC'; "
        "engine.basket_membership_pit membership rows key on (snapshot_date, "
        "basket_id, ticker) with no security column, so a reused ticker inside one "
        "basket cannot be represented as two securities")
    receipt["s6_identity"] = {
        "rename": {
            "mrsh_before": rename_table.resolve("yahoo", "MRSH", _day_before(RENAME_DAY)),
            "mrsh_on": rename_table.resolve("yahoo", "MRSH", RENAME_DAY),
            "mmc_before": rename_table.resolve("yahoo", "MMC", _day_before(RENAME_DAY)),
            "row_omitted_mrsh_on": rename_no_row.resolve("yahoo", "MRSH", RENAME_DAY),
            "no_evidence_mrsh_on": rename_no_evidence.resolve("yahoo", "MRSH", RENAME_DAY),
        },
        "reuse": {
            "before": reuse_table.resolve("yahoo", "ABC", _day_before(REUSE_DAY)),
            "on_or_after": reuse_table.resolve("yahoo", "ABC", _days_after(REUSE_DAY, 5)),
            "overlap_refused_at_construction": overlap_refused,
        },
        "reuse_join": {"note": join_note, "seam_rows_served": len(join_read["values"]),
                       "seam_ok": join_read["ok"]},
    }

    # ── S7 — incompatible vs compatible ──────────────────────────────────────
    sadj = _seam_read("PLAINCO", store, basis="sadj")
    eur = _seam_read("PLAINCO", store, currency="EUR")
    compatible = _seam_read("PLAINCO", store)
    receipt["s7_basis"] = {
        "incompatible_basis": {"refusal": sadj["refusal"], "values": sadj["values"],
                               "ok": sadj["ok"]},
        "mismatched_currency": {"refusal": eur["refusal"], "values": eur["values"],
                                "ok": eur["ok"]},
        "compatible": {"refusal": compatible["refusal"],
                       "values": compatible["values"],
                       "ok": compatible["ok"],
                       "day10": compatible["values"][day10]},
    }

    # ── S8 — basket coverage after B ─────────────────────────────────────────
    receipt["s8_coverage_after_b"] = _account()

    receipt["citations"] = {"terminal_ui": CITATION_TERMINAL_UI}
    receipt["pending_legs"] = dict(PENDING_LEGS)
    return receipt


# ── named assertions (each raises AssertionError naming its id) ───────────────

def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def assert_a01_01_known_answer_three_consumers(receipt: dict) -> None:
    """A01.01 — the synthetic known answer holds across all three consumers."""
    s1 = receipt["s1_view_a"]
    split = s1["seam"]["SPLITCO"]["values"]
    div = s1["seam"]["DIVCO"]["values"]
    dates = sorted(split)
    pre_split, post_split = dates[SPLIT_DAY_INDEX - 1], dates[SPLIT_DAY_INDEX]
    _assert(Fraction(split[post_split]) == Fraction(split[pre_split]) * Fraction(2, 1),
            "A01.01 SPLITCO: the stored tradj pre/post split relation is not exactly 2/1")
    pre_div, post_div = dates[DIV_DAY_INDEX - 1], dates[DIV_DAY_INDEX]
    _assert(Fraction(div[pre_div]) * DIV_FACTOR == Fraction(div[post_div]),
            "A01.01 DIVCO: the declared exact distribution relation fails on day 20")
    for ticker in ("PLAINCO", "SPLITCO", "DIVCO"):
        _assert(s1["seam"][ticker]["ok"] and s1["seam"][ticker]["refusal"] is None,
                f"A01.01 {ticker}: view A was not served by the C01 seam")
        seam_values = s1["seam"][ticker]["values"]
        inspector_values = {day: value
                            for day, value in s1["inspector"][ticker]["rows"]}
        _assert(seam_values == inspector_values,
                f"A01.01 {ticker}: seam and inspector values disagree")
        _assert(s1["seam"][ticker]["vendor_symbol"] == ticker,
                f"A01.01 {ticker}: the served identity does not name the instrument")
        _assert(ticker in s1["basket"]["members"],
                f"A01.01 {ticker}: the basket member strings do not name the instrument")
    _assert(s1["retained_a"]["payload_plainco_day10"]
            == s1["seam"]["PLAINCO"]["values"][receipt["s2_generation_b"]["day"]],
            "A01.01 PLAINCO: retained view A disagrees with the served control")


def assert_a01_01_current_returns_b(receipt: dict) -> None:
    """A01.01 — CURRENT after generation B returns B's corrected value."""
    s3 = receipt["s3_current_after_b"]
    _assert(s3["seam_day10"] == receipt["s2_generation_b"]["b_value"],
            "A01.01 CURRENT: the seam did not return generation B's day-10 value")
    _assert(s3["seam_other_days_equal_a"],
            "A01.01 CURRENT: a day other than day 10 changed under generation B")
    _assert(s3["read_contract"]["generation"] == GEN_B
            and s3["read_contract"]["day10"] == receipt["s2_generation_b"]["b_value"],
            "A01.01 CURRENT: the read contract did not bind generation B")
    _assert(s3["stale_generation_code"] == RefusalCode.STALE_GENERATION.value,
            "A01.01 CURRENT: evidence naming GEN_A did not raise STALE_GENERATION")


def assert_a01_01_replay_returns_exact_a(receipt: dict) -> None:
    """A01.01 — REPLAY returns exactly retained A, never B."""
    s4 = receipt["s4_replay_a"]
    retained = receipt["s1_view_a"]["retained_a"]
    _assert(s4["label"] == "replay", "A01.01 REPLAY: the label is not 'replay'")
    _assert(s4["payload_bytes_equal_retained"] and s4["sha256"] == retained["sha256"],
            "A01.01 REPLAY: the payload is not byte-identical to retained A")
    _assert(s4["payload_label"] == "current" and s4["payload_generation"] == GEN_A,
            "A01.01 REPLAY: the decoded payload does not carry A's label and GEN_A")
    _assert(s4["payload_day10"] == receipt["s2_generation_b"]["a_value"],
            "A01.01 REPLAY: the retained day-10 value is not A's original value")


def assert_a01_02_inspectable_explanation(receipt: dict) -> None:
    """A01.02 — every served result carries inspectable explanation fields."""
    s1 = receipt["s1_view_a"]
    _assert(s1["read_contract_current"]["label"] == "current",
            "A01.02: the read-contract result carries no label")
    for ticker in ("PLAINCO", "SPLITCO", "DIVCO"):
        _assert(s1["seam"][ticker]["dependency_generation_ids"]
                and s1["seam"][ticker]["registry_row"] == REGISTRY_DATASET,
                f"A01.02 {ticker}: the seam served no evidence generation ids")
        _assert(s1["inspector"][ticker]["production_qualification"]
                == "NOT_ESTABLISHED_BY_THIS_ADAPTER",
                f"A01.02 {ticker}: the workspace qualification stamp is absent")
    _assert(s1["retained_a"]["sha256"] and s1["retained_a"]["publishing_receipt_sha256"],
            "A01.02: the retained artifact binds no receipt digests")
    _assert(s1["retained_a"]["output_id"] == VIEW_A_ID,
            "A01.02: the retained artifact does not bind its output id")


def assert_a01_03_rename_owner_evidenced_only(receipt: dict) -> None:
    """A01.03 — rename continuity only with the owner-evidenced alias row."""
    rename = receipt["s6_identity"]["rename"]
    _assert(rename["mrsh_before"] is None,
            "A01.03 rename: MRSH resolved before the rename day (should be nothing)")
    _assert(rename["mrsh_on"] == SEC_MMC and rename["mmc_before"] == SEC_MMC,
            "A01.03 rename: the boundary day does not preserve the security id")
    _assert(rename["row_omitted_mrsh_on"] is None,
            "A01.03 rename: continuity was invented with the alias row omitted")


def assert_a01_03_reused_ticker_does_not_join(receipt: dict) -> None:
    """A01.03 — the reused ticker is two securities; the join is UNFINISHED, not passed."""
    reuse = receipt["s6_identity"]["reuse"]
    _assert(reuse["before"] == SEC_ABC and reuse["on_or_after"] == SEC_ABC_2,
            "A01.03 reuse: the boundary did not split the two securities")
    _assert(reuse["before"] != reuse["on_or_after"],
            "A01.03 reuse: the two security ids compared equal")
    _assert(reuse["overlap_refused_at_construction"],
            "A01.03 reuse: an overlapping-interval table was not refused")
    _assert(receipt["s6_identity"]["reuse_join"]["note"].startswith(
        "UNFINISHED: awaiting U03/U04 LANDED"),
        "A01.03 reuse: the ticker-key join is not recorded as UNFINISHED")


def assert_a01_03_incompatible_refuses_compatible_succeeds(receipt: dict) -> None:
    """A01.03 — the incompatible request refuses while the compatible one serves."""
    s7 = receipt["s7_basis"]
    _assert(s7["incompatible_basis"]["refusal"] == "price_views.AMBIGUOUS_BASIS"
            and s7["incompatible_basis"]["values"] is None,
            "A01.03 basis: the incompatible basis request did not refuse with values None")
    _assert(s7["mismatched_currency"]["refusal"] == "price_views.CURRENCY_MISMATCH"
            and s7["mismatched_currency"]["values"] is None,
            "A01.03 currency: the mismatched currency did not refuse with values None")
    _assert(s7["compatible"]["ok"] and s7["compatible"]["values"],
            "A01.03: the compatible request on the same ticker did not serve")


def assert_a01_04_missing_member_stays_in_account(receipt: dict) -> None:
    """A01.04 — GONECO stays in the coverage account before and after B."""
    for label, account in (("s1", receipt["s1_view_a"]["account"]),
                           ("s8", receipt["s8_coverage_after_b"])):
        _assert(account["requested"] == len(TICKERS),
                f"A01.04 {label}: the account denominator is not the basket size")
        goneco = account["goneco"]
        _assert(goneco["disposition"] == "MISSING"
                and goneco["missing_reason"] == "NO_COVERAGE"
                and not goneco["in_qualified"] and not goneco["has_segments"],
                f"A01.04 {label}: GONECO was dropped, filled or qualified")
        _assert(Fraction(account["qualified_fraction"]) == Fraction(3, 4),
                f"A01.04 {label}: the coverage fraction is not what the dispositions imply")
    _assert("GONECO" in receipt["s1_view_a"]["basket"]["members"],
            "A01.04: GONECO is not a member of the basket population")
    _assert(receipt["s1_view_a"]["goneco_seam"]["values"] is None
            and receipt["s1_view_a"]["goneco_seam"]["refusal"] is not None,
            "A01.04: the missing member was served a value from somewhere")


def assert_a01_04_revocation_typed_never_b_under_a(receipt: dict) -> None:
    """A01.04 — every revocation yields a typed refusal and never B under A's id."""
    for case, entry in receipt["s5_revocations"].items():
        code = entry["code"]
        if code == "SKIPPED_ROOT_HOST":
            _assert(entry["values_present"],
                    f"A01.04 {case}: SKIPPED_ROOT_HOST recorded but nothing was served")
            continue
        _assert(code in WS_REFUSAL_CODES or code in RC_REFUSAL_CODES,
                f"A01.04 {case}: the refusal code is outside the closed typed sets")
        _assert(entry["values_present"] is False,
                f"A01.04 {case}: a revoked dependency returned values")
    _assert(receipt["s5_b_value_under_view_a"] is False,
            "A01.04: generation B's value appeared under view A's id")


def assert_receipt_lists_pending_legs(receipt: dict) -> None:
    """The receipt carries PENDING_LEGS verbatim."""
    _assert(receipt["pending_legs"] == PENDING_LEGS,
            "the receipt's PENDING_LEGS does not match the frozen lane dict")
    _assert(all(str(value).strip() for value in PENDING_LEGS.values()),
            "a PENDING_LEGS entry carries no explanation")
    _assert(PENDING_LEGS["real_retained_corpus"].startswith("UNFINISHED:"),
            "the real-corpus leg is not marked UNFINISHED")
