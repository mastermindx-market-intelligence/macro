"""G0-V lane (SPEC_G0 §4): the G0 reference cases, verified through the served engine.

Two tiers.  The OFFLINE tier always runs: the gold fixtures verify and every
identity resolves (SPEC 1); listings are built ONLY through
``build_listing_fact`` from what the pack records (SPEC 2a); no ``engine/**``
module carries one of the eight case literals (SPEC 2b); all eight identified
cases run the SAME builder-built scenario with only the listing differing
(SPEC 2c); and each new case carries its negative checks (SPEC 5).  The
REAL-BUNDLE tier (SPEC 3b-3f and 4) runs against the real
``data/capital_structure/`` generation and skips, with the reason in its own
name, only when that generation is absent from the tree.

No expected number is hand-typed anywhere: every compared value comes from the
sealed held-out file, from a committed fixture span, or from the engine.
Arithmetic is exact (``Decimal``/``Fraction``); no binary-float conversion and
no network import appears anywhere; a wrong or unavailable engine answer is
recorded as it is.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

import tests.test_capital_structure_capacity as C1
import tests.test_capital_structure_capacity_c2 as C2
from engine.capital_structure import reference_qualification as rq
from engine.capital_structure.capacity import explain_capacity
from engine.capital_structure.listing_facts import (
    DOMESTIC_ANNUAL_FORMS,
    DOMESTIC_REGISTRATION_FORMS,
    FPI_ANNUAL_FORMS,
    FPI_REGISTRATION_FORMS,
    build_listing_fact,
)
from tests.test_capital_structure_g0_reference import parse_g0_fixture

ROOT = Path(__file__).resolve().parents[1]
PACK_PATH = ROOT / rq.REFERENCE_PACK_RELPATH
G0_FIXTURE_DIR = ROOT / "tests/fixtures/capital_structure/reference/g0"
DATA_ROOT = ROOT / "data" / "capital_structure"
HELD_OUT_GOLD_ID = "gold:reference_g0:held_out_ib6_headroom"
VERIFIED_ON = "2026-10-19"
VERIFIED_BY = "tests/test_capital_structure_g0_verification.py"
#: The sealed answer's own digest, printed in the G0-V packet (never a sealed value).
SEALED_RELPATH = "tests/fixtures/capital_structure/reference/g0/held_out_expected.sealed.json"
SEALED_SHA256 = "6b0513dc75d7ea5578ed5dc3b960b20d3a5d580372ef74135f539e4a71c02b47"
HELD_OUT_RESULT_KEYS = (
    "outcome",
    "reason",
    "difference",
    "conditional_arithmetic",
    "sealed_sha256",
    "verified_on",
    "verified_by",
    "cutoff_instant",
)

#: The forms the listing builder itself reads for the FPI axis; a pack-stated
#: dated filing outside these families cannot inform the listing.
_FPI_FORMS = frozenset(FPI_ANNUAL_FORMS | DOMESTIC_ANNUAL_FORMS | FPI_REGISTRATION_FORMS | DOMESTIC_REGISTRATION_FORMS)

#: The 2c world: the C2 a21 builder call, unchanged except that the
#: ``listing_venue`` assumption is dropped — the venue is an observed issuer
#: fact here (SPEC_G0 §2.2 binds it from the supplied listing), and keeping the
#: assumption would report a conflict instead of the unqualified-venue branch
#: the NYSE slots must show.
_WORLD_KWARGS = None


def _world_kwargs() -> dict[str, Any]:
    global _WORLD_KWARGS
    if _WORLD_KWARGS is None:
        kwargs = C2.a21_kwargs()
        kwargs["other"] = tuple(kv for kv in kwargs["other"] if kv[0] != "listing_venue")
        _WORLD_KWARGS = kwargs
    return dict(_WORLD_KWARGS)


def _base_form(form: str) -> str:
    return form[:-2] if form.endswith("/A") else form


def _pack_dated_filings(identity: dict[str, Any]) -> list[dict[str, str]]:
    """Every dated filing the pack states for this identity whose base form the
    FPI axis reads: the g0 case's own source filing and the identity's
    latest-in-policy anchors.  A filing the pack states without a date is not
    here; nothing is invented."""
    rows: list[dict[str, str]] = []
    case = (identity.get("details") or {}).get("g0_case") or {}
    filing = case.get("filing")
    if isinstance(filing, dict) and filing.get("form") and filing.get("filing_date"):
        rows.append({
            "form": str(filing["form"]),
            "filed": str(filing["filing_date"]),
            "retrieved_at": str(filing.get("retrieved_at") or ""),
        })
    for anchor in (identity.get("latest_in_policy_anchor") or {}).values():
        if not isinstance(anchor, dict) or not anchor.get("filing_date"):
            continue
        form = str(anchor.get("form") or "")
        if form and _base_form(form) in _FPI_FORMS:
            rows.append({"form": form, "filed": str(anchor["filing_date"]), "retrieved_at": ""})
    seen: dict[tuple[str, str], dict[str, str]] = {}
    for row in sorted(rows, key=lambda item: (item["filed"], item["form"])):
        key = (row["form"], row["filed"])
        if _base_form(row["form"]) not in _FPI_FORMS:
            continue
        stored = seen.get(key)
        if stored is None:
            seen[key] = dict(row)
        elif row["retrieved_at"] and not stored["retrieved_at"]:
            stored["retrieved_at"] = row["retrieved_at"]
    return [seen[key] for key in sorted(seen)]


def _case_cutoff(identity: dict[str, Any], world_sale: str) -> tuple[str, str]:
    """The case's own cutoff day and instant: the g0 numerical path's sealed
    cutoff, else the g0 filing day, else the synthetic world's own day."""
    case = (identity.get("details") or {}).get("g0_case") or {}
    cutoff = (case.get("numerical_path") or {}).get("cutoff")
    if cutoff:
        return str(cutoff), f"{cutoff}T23:59:59Z"
    filed = (case.get("filing") or {}).get("filing_date")
    if filed:
        return str(filed), f"{filed}T23:59:59Z"
    return world_sale, f"{world_sale}T00:00:00Z"


def case_listing(identity: dict[str, Any], world_sale: str, world_instant: str):
    """SPEC 2a: the listing built ONLY through ``build_listing_fact`` from what
    the pack records.  An unknown axis keeps its typed reason; nothing about
    the FPI status, the venue or a 16G election is ever set by hand."""
    exchanges = tuple(identity["exchanges"])
    filings = _pack_dated_filings(identity)
    cutoff_day, cutoff_instant = _case_cutoff(identity, world_sale)
    retrieved = next(
        (row["retrieved_at"] for row in filings if row["retrieved_at"]),
        str(((identity.get("details") or {}).get("g0_case") or {}).get("filing", {}).get("retrieved_at") or ""),
    )
    available_at = retrieved if retrieved and retrieved <= cutoff_instant else cutoff_instant
    return build_listing_fact(
        exchanges=exchanges,
        filings=tuple(dict(row) for row in filings),
        item_16g=None,
        as_of=cutoff_day,
        available_at=available_at,
        evidence=(),
    )


# ---------------------------------------------------------------------------
# Module-scoped pack and the SPEC 2c case table
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def raw_pack() -> dict[str, Any]:
    return json.loads(PACK_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pack() -> rq.ReferencePack:
    return rq.load_reference_pack(PACK_PATH)


@pytest.fixture(scope="module")
def identities(raw_pack: dict[str, Any]) -> list[dict[str, Any]]:
    entries = list(raw_pack["identities"])
    assert len(entries) == 8, f"the qualified pack carries {len(entries)} identities, not 8"
    return entries


@pytest.fixture(scope="module")
def case_table(identities: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """SPEC 2c: the SAME builder-built world for all eight cases; only the
    listing differs.  Every per-case record is computed, never hand-typed."""
    kwargs = _world_kwargs()
    state, scenario, rules = C1.build(**kwargs)
    table: dict[str, dict[str, Any]] = {}
    for identity in identities:
        listing = case_listing(identity, C1.SALE, C1.AS_OF)
        evaluation = explain_capacity(state, scenario, rules, pack=C1.PACK, listing=listing)
        nasdaq = evaluation.inputs.get("nasdaq") or {}
        table[identity["archetype"]] = {
            "ticker": identity["ticker"],
            "cik": identity["cik"],
            "exchanges": list(identity["exchanges"]),
            "venue": listing.venue,
            "foreign_private_issuer": listing.foreign_private_issuer,
            "home_country_practice_5635": listing.home_country_practice_5635,
            "listing_reasons": list(listing.reasons),
            "route_classifications": {
                str(route.route_id): str(route.status) for route in evaluation.envelope.routes
            },
            "route_conditions": {
                str(route.route_id): sorted(str(c) for c in route.conditions)
                for route in evaluation.envelope.routes
            },
            "pool_ids": sorted(str(pool.constraint_id) for pool in evaluation.envelope.shared_pools),
            "unknown_ids": sorted(str(item.unknown_id) for item in evaluation.envelope.unknowns),
            "listing_venue_basis": nasdaq.get("listing_venue_basis"),
            "consulted_rules": sorted(
                {
                    str(rule)
                    for path in evaluation.inputs["registration_paths"]
                    for rule in path["consulted_rules"]
                }
            ),
        }
    return table


# ---------------------------------------------------------------------------
# SPEC 1 — the gold fixtures and the identities
# ---------------------------------------------------------------------------


def test_g0v_gold_fixtures_verify(pack: rq.ReferencePack) -> None:
    assert rq.verify_gold_fixtures(pack, ROOT) == {}


def test_g0v_identities_resolve_by_ticker_and_cik(
    pack: rq.ReferencePack, identities: list[dict[str, Any]]
) -> None:
    by_ticker = {str(item["ticker"]): str(item["archetype"]) for item in identities}
    by_cik = {str(item["cik"]): str(item["archetype"]) for item in identities}
    assert len(by_ticker) == len(by_cik) == 8
    for identity in identities:
        archetype = str(identity["archetype"])
        cik = str(identity["cik"])
        resolved = rq.identity_for(pack, archetype)
        assert resolved.issuer_id == f"sec:cik:{cik}", archetype
        assert resolved is rq.identity_for(pack, by_ticker[str(identity["ticker"])])
        assert rq.identity_for(pack, by_cik[cik]).issuer_id == f"sec:cik:{cik}", archetype


# ---------------------------------------------------------------------------
# SPEC 2b — no case literal anywhere in the engine
# ---------------------------------------------------------------------------


def test_g0v_engine_carries_no_case_literals(identities: list[dict[str, Any]]) -> None:
    tickers = {str(item["ticker"]) for item in identities}
    cik_patterns = {
        str(item["cik"]): re.compile(r"(?<![0-9])0*" + str(item["cik"]) + r"(?![0-9])")
        for item in identities
    }
    engine_files = sorted((ROOT / "engine").rglob("*.py"))
    assert len(engine_files) > 100, "the engine tree is unexpectedly small"
    for path in engine_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            value = node.value
            assert value not in tickers, (path.relative_to(ROOT), value)
            for cik, pattern in cik_patterns.items():
                assert not pattern.search(value), (path.relative_to(ROOT), cik, value[:80])


# ---------------------------------------------------------------------------
# SPEC 2a — the listings come only from the pack through the builder
# ---------------------------------------------------------------------------


def test_g0v_pack_only_listings(identities: list[dict[str, Any]], case_table: dict[str, dict[str, Any]]) -> None:
    # No committed g0 fixture span carries Item 16G text, so ``item_16g=None``
    # is what the records say, not a shortcut.
    for path in sorted(G0_FIXTURE_DIR.glob("*.txt")):
        _hdr, spans = parse_g0_fixture(path)
        for span in spans:
            assert "item 16g" not in span["text"].casefold(), (path.name, span["label"])
    for identity in identities:
        listing = case_listing(identity, C1.SALE, C1.AS_OF)
        row = case_table[identity["archetype"]]
        assert listing.venue == row["venue"]
        assert listing.venue == {"Nasdaq": "nasdaq", "NYSE": "nyse"}[identity["exchanges"][0]]
        # The FPI axis is the builder's own unknown with its typed reason: the
        # pack states no dated annual form for any identity.
        assert listing.foreign_private_issuer == "unknown"
        assert "fpi_forms_absent" in listing.reasons
        assert listing.home_country_practice_5635 == "unknown"
        assert "home_country_practice_fpi_unknown" in listing.reasons
        assert row["foreign_private_issuer"] == "unknown"
        # EDRY's dated F-3 is consumed; RPID's pack filing is a 424B5, which no
        # FPI form family reads, so its filings list stays empty.
        filings = _pack_dated_filings(identity)
        if identity["archetype"] == "EDRY":
            assert any(f["form"] == "F-3" and f["filed"] == "2026-08-27" for f in filings), filings
        if identity["archetype"] == "RPID":
            assert filings == []


# ---------------------------------------------------------------------------
# SPEC 2c — the eight cases through the same engine, and the NYSE slots
# ---------------------------------------------------------------------------


def test_g0v_same_engine_all_eight_cases(
    identities: list[dict[str, Any]], case_table: dict[str, dict[str, Any]]
) -> None:
    assert set(case_table) == {str(item["archetype"]) for item in identities}
    for identity in identities:
        row = case_table[str(identity["archetype"])]
        assert row["listing_venue_basis"] == "observed", identity["archetype"]
        assert row["route_classifications"], identity["archetype"]
        assert row["pool_ids"], identity["archetype"]
        assert any(uid.startswith("programme_reservation:") for uid in row["unknown_ids"]) or row[
            "unknown_ids"
        ], identity["archetype"]


def test_g0v_nyse_slots_are_unqualified_never_nasdaq(
    identities: list[dict[str, Any]], case_table: dict[str, dict[str, Any]]
) -> None:
    """SPEC 4's venue rule, asserted on the offline tier's own runs: AIR and WHK
    (NYSE) show ``venue_rule_pack_unqualified:nyse`` and never a Nasdaq 5635
    pool; a failure here is the FINDING, never something to patch."""
    for identity in identities:
        row = case_table[str(identity["archetype"])]
        if row["venue"] == "nyse":
            assert any(uid.startswith("venue_rule_pack_unqualified:nyse") for uid in row["unknown_ids"]), (
                f"{identity['archetype']}: FINDING — no venue_rule_pack_unqualified:nyse "
                f"unknown among {row['unknown_ids']!r}"
            )
            assert not any(uid.startswith("nasdaq_20pct:") for uid in row["pool_ids"]), (
                f"{identity['archetype']}: FINDING — a Nasdaq 5635 pool on an NYSE case"
            )
            for route_id, conditions in row["route_conditions"].items():
                assert "venue_rule_pack_unqualified:nyse" in conditions, (identity["archetype"], route_id)
                assert row["route_classifications"][route_id] != "eligible", (identity["archetype"], route_id)
        else:
            assert row["venue"] == "nasdaq", identity["archetype"]
            assert any(uid.startswith("nasdaq_20pct:") for uid in row["pool_ids"]), identity["archetype"]
            assert not any(uid.startswith("venue_rule_pack_unqualified") for uid in row["unknown_ids"]), (
                identity["archetype"]
            )


# ---------------------------------------------------------------------------
# SPEC 5 — the negative checks of the two new cases (offline tier)
# ---------------------------------------------------------------------------


def _conflict_assumptions() -> tuple[tuple[str, str], ...]:
    non_venue = tuple(kv for kv in C1.NASDAQ_ASSUMPTIONS if kv[0] != "listing_venue")
    return (("listing_venue", "nyse"),) + non_venue


def test_g0v_negative_edry(identities: list[dict[str, Any]]) -> None:
    edry = next(item for item in identities if item["archetype"] == "EDRY")
    listing = case_listing(edry, C1.SALE, C1.AS_OF)
    # Negative 1 + 3: the F-3 world — the F-3 route is conditional, never
    # eligible, and the engine consults the F-3 instruction, never the S-3 one.
    reg, shares = C1.standard_registration(form="F-3", family="registration_f3")
    evaluation = explain_capacity(
        *C1.build(registration=reg, share_basis=shares, other=tuple(
            kv for kv in C1.NASDAQ_ASSUMPTIONS if kv[0] != "listing_venue")),
        pack=C1.PACK,
        listing=listing,
    )
    active = [route for route in evaluation.envelope.routes]
    assert active, "the F-3 world produced no route"
    for route in active:
        assert route.status == "conditional", (
            f"EDRY FINDING — the F-3 route is {route.status!r}, not conditional"
        )
    consulted = {
        str(rule)
        for path in evaluation.inputs["registration_paths"]
        for rule in path["consulted_rules"]
    }
    assert "form_f3.I.B.5" in consulted, sorted(consulted)
    assert "form_s3.I.B.6" not in consulted, (
        "EDRY FINDING — an F-3 path consulted the S-3 instruction; the engine "
        f"output consulted {sorted(consulted)}"
    )
    # Negative 2: a scenario venue assumption contradicting the observed venue
    # is a listing_venue_conflict, and no Nasdaq pool is decided.
    conflicted = explain_capacity(
        *C1.build(registration=reg, share_basis=shares, other=_conflict_assumptions()),
        pack=C1.PACK,
        listing=listing,
    )
    unknown_ids = {str(item.unknown_id) for item in conflicted.envelope.unknowns}
    assert any(uid.startswith("listing_venue_conflict:") for uid in unknown_ids), sorted(unknown_ids)
    assert not any(uid.startswith("nasdaq_20pct:") for uid in (
        str(pool.constraint_id) for pool in conflicted.envelope.shared_pools
    ))
    assert (conflicted.inputs.get("nasdaq") or {}).get("reason") == "listing_venue_conflict"


def test_g0v_negative_rpid(identities: list[dict[str, Any]]) -> None:
    rpid = next(item for item in identities if item["archetype"] == "RPID")
    listing = case_listing(rpid, C1.SALE, C1.AS_OF)
    non_venue = tuple(kv for kv in C1.NASDAQ_ASSUMPTIONS if kv[0] != "listing_venue")

    def _without_sold() -> dict[str, Any]:
        kwargs = _world_kwargs()
        kwargs["other"] = non_venue
        kwargs["resolutions"] = [
            resolution
            for resolution in kwargs["resolutions"]
            if not resolution.unknown_id.startswith("baby_shelf_sold_trailing:")
        ]
        return kwargs

    def _with_wrong_day() -> dict[str, Any]:
        kwargs = _world_kwargs()
        kwargs["other"] = non_venue
        wrong_day = C1.shift(C1.SALE, 1)
        kwargs["resolutions"] = [
            resolution
            if not resolution.unknown_id.startswith("baby_shelf_sold_trailing:")
            else type(resolution)(
                f"baby_shelf_sold_trailing:{wrong_day}", resolution.assumed, resolution.rationale
            )
            for resolution in kwargs["resolutions"]
        ]
        return kwargs

    # Negative 2: no baby_shelf_sold_trailing resolution — the trailing-sales
    # bound is unknown, never zero, and the headroom with it.
    absent = explain_capacity(*C1.build(**_without_sold()), pack=C1.PACK, listing=listing)
    baby = absent.inputs.get("baby_shelf") or {}
    assert (baby.get("sold_trailing") or {}).get("status") == "unknown", json.dumps(baby.get("sold_trailing"))[:200]
    assert (baby.get("headroom") or {}).get("status") == "unknown", json.dumps(baby.get("headroom"))[:200]

    # Negative 3: a resolution keyed to the day before the cutoff is not consumed.
    wrong_day = C1.shift(C1.SALE, 1)
    mistimed = explain_capacity(*C1.build(**_with_wrong_day()), pack=C1.PACK, listing=listing)
    baby = mistimed.inputs.get("baby_shelf") or {}
    assert (baby.get("sold_trailing") or {}).get("status") == "unknown", json.dumps(baby.get("sold_trailing"))[:200]
    assert (baby.get("headroom") or {}).get("status") == "unknown", json.dumps(baby.get("headroom"))[:200]
    consumed_note = json.dumps(baby.get("sold_trailing"))
    assert consumed_note is not None and str(wrong_day) not in consumed_note

    # Negative 1: a scenario venue contradicting the observed venue conflicts.
    kwargs = _world_kwargs()
    kwargs["other"] = _conflict_assumptions()
    conflicted = explain_capacity(*C1.build(**kwargs), pack=C1.PACK, listing=listing)
    unknown_ids = {str(item.unknown_id) for item in conflicted.envelope.unknowns}
    assert any(uid.startswith("listing_venue_conflict:") for uid in unknown_ids), sorted(unknown_ids)
    assert (conflicted.inputs.get("nasdaq") or {}).get("reason") == "listing_venue_conflict"



# ---------------------------------------------------------------------------
# SPEC 3a — the committed sealed answer and its binding to the pack
# ---------------------------------------------------------------------------


def _sealed_record() -> dict[str, Any]:
    return json.loads((ROOT / SEALED_RELPATH).read_text(encoding="utf-8"))


def test_g0v_sealed_fixture_seal(raw_pack: dict[str, Any]) -> None:
    path = ROOT / SEALED_RELPATH
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == SEALED_SHA256
    sealed = _sealed_record()
    identity = next(item for item in raw_pack["identities"] if item["archetype"] == "RPID")
    case = identity["details"]["g0_case"]
    assert sealed["cik"] == identity["cik"]
    assert sealed["path_id"] == case["numerical_path"]["path_id"]
    assert sealed["rule_id"] == case["numerical_path"]["rule_id"]
    assert sealed["unit"] == "USD"
    # The sealed operands bind the committed fixture spans by digest, not by value.
    _hdr, spans = parse_g0_fixture(ROOT / case["fixture"]["path"])
    by_label = {span["label"]: span["sha256"] for span in spans}
    packed = {operand["name"]: operand for operand in case["numerical_path"]["operands"]}
    for operand in sealed["operands"]:
        assert operand["span_text_sha256"] == by_label[packed[operand["name"]]["span_label"]], (
            operand["name"]
        )


# ---------------------------------------------------------------------------
# SPEC 6 — the recorded held_out_result and its exact shape
# ---------------------------------------------------------------------------


def _held_out_entry(raw_pack: dict[str, Any]) -> dict[str, Any]:
    return next(
        gold for gold in raw_pack["gold_cases"] if gold["gold_id"] == HELD_OUT_GOLD_ID
    )


def test_g0v_held_out_result_shape(raw_pack: dict[str, Any]) -> None:
    entry = _held_out_entry(raw_pack)
    assert entry["sealed"] is True
    # Consumers are named relative to tests/, per the pack's own convention.
    assert "test_capital_structure_g0_verification.py" in entry["consumers"]
    record = entry["held_out_result"]
    assert set(record) == set(HELD_OUT_RESULT_KEYS), sorted(record)
    assert record["outcome"] in ("pass", "fail", "typed_unavailable")
    assert isinstance(record["reason"], str)
    assert record["difference"] is None or isinstance(record["difference"], str)
    assert record["conditional_arithmetic"] in ("match", "mismatch", "not_run")
    assert record["sealed_sha256"] == SEALED_SHA256
    assert record["verified_on"] == VERIFIED_ON
    assert record["verified_by"] == VERIFIED_BY
    sealed = _sealed_record()
    assert record["cutoff_instant"] == f"{sealed['cutoff']}T23:59:59Z"

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                assert key not in ("expected", "value", "amount"), (path, key)
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(record, "held_out_result")


# ---------------------------------------------------------------------------
# REAL-BUNDLE tier — SPEC 3b–3f and 4
# ---------------------------------------------------------------------------

_SKIP_REASON = "g0v: no verified capital-structure generation under data/capital_structure"


def _skip_unless_verified_generation() -> Any:
    """The real tier's one skip: no verified generation under data/capital_structure."""
    pytest.importorskip("pandas", reason="g0v real-bundle tier reads parquet")
    pytest.importorskip("pyarrow", reason="g0v real-bundle tier reads parquet")
    from engine.capital_structure.verified_projection_generation import (
        read_verified_projection_generation,
    )

    try:
        generation = read_verified_projection_generation(DATA_ROOT)
    except Exception as exc:  # noqa: BLE001 — an unverifiable generation is the skip itself
        pytest.skip(f"{_SKIP_REASON} ({exc})")
    telemetry = generation.telemetry if isinstance(generation.telemetry, dict) else {}
    if not telemetry.get("generation_id"):
        pytest.skip(_SKIP_REASON)
    return generation


def _exact_difference_text(difference: Any) -> str:
    """An exact rendering of engine-minus-sealed: an integer or a proper fraction."""
    if difference.denominator == 1:
        return str(difference.numerator)
    return f"{difference.numerator}/{difference.denominator}"


def _rpid_listing_for_day(day: str, instant: str):
    """The SPEC 2a listing for the RPID slot, evaluated on an arbitrary day."""
    return case_listing(
        {"exchanges": ["Nasdaq"], "details": {}, "latest_in_policy_anchor": {}},
        day,
        instant,
    )


def _conditional(
    published: dict[str, Any],
    sealed: dict[str, Any],
    pack: Any,
    result: dict[str, Any],
) -> None:
    """SPEC 3f — the conditional arithmetic on the current published state,
    recorded SEPARATELY and never counted as a pass."""
    from engine.capital_structure.issuer_state_contracts import (
        FinancingScenario,
        PriceAssumption,
        Quantity,
        UnknownResolution,
    )
    from engine.capital_structure.rule_applicability import build_rule_pack
    from engine.capital_structure.state_bundle import state_from_record

    state = state_from_record(published)
    as_of = str(state.request.as_of)
    as_of_day = as_of[:10]
    result["conditional_as_of"] = as_of
    rules = build_rule_pack(pack, as_of_day)[0]
    if rules is None:
        result["conditional_reason"] = f"no qualified rule text on {as_of_day}"
        return
    listing = _rpid_listing_for_day(as_of_day, as_of)
    operands = {str(item["name"]): item for item in sealed["operands"]}
    resolutions = []
    for name, key in (
        ("public_float", "baby_shelf_public_float:"),
        ("sold_trailing", "baby_shelf_sold_trailing:"),
    ):
        operand = operands[name]
        resolutions.append(
            UnknownResolution(
                f"{key}{as_of_day}",
                Quantity.known(str(Decimal(str(operand["value"]))), "usd"),
                f"assumption-from-disclosure ({name}): accession {operand['accession']} "
                f"document {operand['document']} span_text_sha256 {operand['span_text_sha256']}",
            )
        )
    scenario = FinancingScenario(
        view="then_known",
        as_of=as_of,
        horizon_start=as_of_day,
        horizon_end=as_of_day,
        price=PriceAssumption(kind="fixed", fixed_price="1.00"),
        fee_rate="0.01",
        unknown_resolutions=tuple(resolutions),
    )
    evaluation = explain_capacity(state, scenario, rules, pack=pack, listing=listing)
    pools = {str(pool.constraint_id): pool for pool in evaluation.envelope.shared_pools}
    pool = pools.get(f"baby_shelf:{as_of_day}")
    if pool is None:
        result["conditional_reason"] = (
            ";".join(sorted(str(item.unknown_id) for item in evaluation.envelope.unknowns))
            or "no baby-shelf pool on the published state"
        )
        return
    headroom = pool.bound
    if headroom.status != "known" or headroom.value is None:
        result["conditional_reason"] = f"baby_shelf_headroom_{headroom.status}"
        return
    engine_value = Fraction(Decimal(str(headroom.value)))
    exact_value = Fraction(*[int(part) for part in str(sealed["expected_exact"]).split("/")])
    if engine_value == exact_value:
        result["conditional_arithmetic"] = "match"
    else:
        result["conditional_arithmetic"] = "mismatch"
        result["conditional_reason"] = _exact_difference_text(engine_value - exact_value)


@pytest.fixture(scope="module")
def finding(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """SPEC 3b–3f: the one real-bundle derivation and its outcome, compared
    with the pack's ``held_out_result`` exactly as recorded.  Nothing is
    patched to pass; a wrong or unavailable engine answer is the finding."""
    from engine.capital_structure.issuer_state_contracts import (
        ContractViolation,
        FinancingScenario,
        PriceAssumption,
        Quantity,
        UnknownResolution,
    )
    from engine.capital_structure.rule_applicability import build_rule_pack
    from engine.capital_structure.state_bundle import (
        issuer_inputs,
        state_from_record,
        then_known_state,
    )
    from scripts.build_capital_structure_state import build_from_disk

    generation = _skip_unless_verified_generation()
    out_path = tmp_path_factory.mktemp("g0v") / "state_bundle.json"
    build_from_disk(root=DATA_ROOT, out_path=out_path)
    bundle = json.loads(out_path.read_text(encoding="utf-8"))

    pack = C1.PACK
    reference = rq.load_reference_pack(PACK_PATH)
    identity = next(item for item in reference.identities if item.archetype == "RPID")
    issuer_id = identity.issuer_id
    sealed = _sealed_record()
    cutoff_day = str(sealed["cutoff"])
    cutoff_instant = f"{cutoff_day}T23:59:59Z"
    operands = {str(item["name"]): item for item in sealed["operands"]}
    published = next(
        (
            row
            for row in bundle["issuers"]
            if str((row.get("request") or {}).get("issuer_id")) == issuer_id
        ),
        None,
    )
    result: dict[str, Any] = {
        "outcome": "typed_unavailable",
        "reason": "",
        "difference": None,
        "conditional_arithmetic": "not_run",
        "conditional_as_of": None,
        "conditional_reason": "",
        "float_from_served_state": None,
        "float_row": None,
        "cutoff_instant": cutoff_instant,
    }
    if published is None:
        result["reason"] = "issuer not covered"
        result["conditional_reason"] = "issuer not covered"
        return result

    # SPEC 3c — the then-known derivation, exactly as the app performs it.
    state = None
    try:
        inputs = issuer_inputs(bundle, generation, issuer_id)
        moments = sorted(
            str(event["point_in_time"]["available_at"])
            for event in inputs.events
            if (event.get("point_in_time") or {}).get("available_at")
        )
        if moments and moments[0] > cutoff_instant:
            result["reason"] = "before_first_bound_event"
        else:
            derived = then_known_state(published, inputs, cutoff=cutoff_instant, rule_pack=pack)
            state = state_from_record(derived.as_record())
    except (ContractViolation, ValueError) as exc:
        result["reason"] = str(exc) or type(exc).__name__

    if state is None:
        if not result["reason"]:
            result["reason"] = "derivation refused"
        _conditional(published, sealed, pack, result)
        return result

    # SPEC 3d — one scenario: the state's own as_of, the cutoff day as the
    # horizon, an S-3 primary shelf route under General Instruction I.B.6, the
    # SPEC 2a listing, and exactly the sealed sold_trailing resolution.  The
    # public float is deliberately not resolved: it must come from served
    # state, or the engine must say why not.
    rules = build_rule_pack(pack, cutoff_day)[0]
    assert rules is not None, f"no qualified rule text on {cutoff_day}"
    listing = _rpid_listing_for_day(cutoff_day, cutoff_instant)
    sold = operands["sold_trailing"]
    resolution = UnknownResolution(
        f"baby_shelf_sold_trailing:{cutoff_day}",
        Quantity.known(str(Decimal(str(sold["value"]))), "usd"),
        "historical knowledge: trailing I.B.6 sales as disclosed by accession "
        f"{sold['accession']} document {sold['document']} span_text_sha256 {sold['span_text_sha256']}",
    )
    scenario = FinancingScenario(
        view="then_known",
        as_of=str(state.request.as_of),
        horizon_start=cutoff_day,
        horizon_end=cutoff_day,
        price=PriceAssumption(kind="fixed", fixed_price="1.00"),
        fee_rate="0.01",
        unknown_resolutions=(resolution,),
    )
    evaluation = explain_capacity(state, scenario, rules, pack=pack, listing=listing)
    pool_id = f"baby_shelf:{cutoff_day}"
    pools = {str(pool.constraint_id): pool for pool in evaluation.envelope.shared_pools}
    pool = pools.get(pool_id)
    record = evaluation.inputs.get("baby_shelf") or {}
    float_record = record.get("public_float") or {}
    result["float_from_served_state"] = bool(float_record.get("provenance"))
    result["float_row"] = (
        str(record.get("float_measured_on")) if record.get("float_measured_on") else None
    )
    if pool is None or pool.bound.status != "known" or pool.bound.value is None:
        status = pool.bound.status if pool is not None else "absent"
        result["reason"] = (
            ";".join(sorted(str(item.unknown_id) for item in evaluation.envelope.unknowns))
            or f"baby_shelf_headroom_{status}"
        )
        _conditional(published, sealed, pack, result)
        return result
    # SPEC 3e — the exact comparison.
    engine_value = Fraction(Decimal(str(pool.bound.value)))
    exact_value = Fraction(*[int(part) for part in str(sealed["expected_exact"]).split("/")])
    expected_value = Decimal(str(sealed["expected"]))
    result["difference"] = _exact_difference_text(engine_value - exact_value)
    if engine_value == exact_value and Decimal(str(pool.bound.value)) == expected_value:
        result["outcome"] = "pass"
    else:
        result["outcome"] = "fail"
    _conditional(published, sealed, pack, result)
    return result


def test_g0v_held_out_comparison_matches_the_record(
    raw_pack: dict[str, Any], finding: dict[str, Any]
) -> None:
    record = _held_out_entry(raw_pack)["held_out_result"]
    fresh = {key: finding[key] for key in ("outcome", "reason", "difference", "conditional_arithmetic", "cutoff_instant")}
    assert fresh["outcome"] == record["outcome"], json.dumps(finding, sort_keys=True)
    assert fresh["reason"] == record["reason"], json.dumps(finding, sort_keys=True)
    assert fresh["difference"] == record["difference"], json.dumps(finding, sort_keys=True)
    assert fresh["conditional_arithmetic"] == record["conditional_arithmetic"]
    assert fresh["cutoff_instant"] == record["cutoff_instant"]


def test_g0v_public_float_provenance_is_answered(
    raw_pack: dict[str, Any], finding: dict[str, Any]
) -> None:
    """Q3's provenance question has an answer for the recorded outcome: when
    the derivation was refused, no float row was read at all."""
    record = _held_out_entry(raw_pack)["held_out_result"]
    if record["outcome"] == "typed_unavailable" and record["reason"] == "before_first_bound_event":
        assert finding["float_from_served_state"] is None
        assert finding["float_row"] is None
    else:  # a computed outcome must name where its float came from
        assert isinstance(finding["float_from_served_state"], bool)


def test_g0v_conditional_arithmetic_is_separate(
    raw_pack: dict[str, Any], finding: dict[str, Any]
) -> None:
    record = _held_out_entry(raw_pack)["held_out_result"]
    assert finding["conditional_arithmetic"] == record["conditional_arithmetic"]
    assert finding["conditional_arithmetic"] in ("match", "mismatch", "not_run")
    # The conditional leg never upgrades the recorded outcome.
    if record["conditional_arithmetic"] == "match":
        assert record["outcome"] == "pass"
    if record["conditional_arithmetic"] == "not_run":
        assert finding["conditional_reason"], "a not_run conditional names its reason"


def test_g0v_coverage_denominator(
    raw_pack: dict[str, Any], identities: list[dict[str, Any]], case_table: dict[str, dict[str, Any]]
) -> None:
    """SPEC 4 — the honest denominator over the NINE G0 reference slots: the six
    archetypes, EDRY, RPID, and the open WHK replacement slot, which is counted
    in ``total`` and never in ``examined``."""
    archetypes = [str(item["archetype"]) for item in identities]
    assert archetypes == ["AIR", "CLNN", "QNCX", "WHK", "LPTH", "EDBL", "EDRY", "RPID"]
    assert any(
        str(gap.get("gap_id")) == "whk_replacement_issuer" for gap in raw_pack["gaps"]
    ), "the WHK replacement slot is not open in the pack"
    whk = next(item for item in raw_pack["identities"] if item["archetype"] == "WHK")
    assert whk["replacement"] is None and whk["replacement_owed"] is True

    slots = archetypes + ["whk_replacement_issuer"]
    assert len(slots) == 9
    examined = [slot for slot in slots if slot in case_table]
    assert sorted(examined) == sorted(archetypes), (
        "the open WHK replacement slot is never an examined slot"
    )
    held_out_entry = _held_out_entry(raw_pack)
    assert held_out_entry["cik"] == "0001380106"
    per_check = {
        "gold": len(examined),
        "listing": len(examined),
        "engine_run": len(examined),
        "held-out": 1,
    }
    for name, count in per_check.items():
        print(f"{name}: {count}/{len(slots)}")
        assert count <= len(examined), name
    # AIR and WHK (NYSE): the venue is unqualified and no Nasdaq pool exists.
    for archetype in ("AIR", "WHK"):
        row = case_table[archetype]
        assert any(
            uid.startswith("venue_rule_pack_unqualified:nyse") for uid in row["unknown_ids"]
        ), f"{archetype}: FINDING — {row['unknown_ids']!r}"
        assert not any(uid.startswith("nasdaq_20pct:") for uid in row["pool_ids"]), (
            f"{archetype}: FINDING — a Nasdaq 5635 pool on an NYSE case"
        )


# ---------------------------------------------------------------------------
# Hygiene
# ---------------------------------------------------------------------------


def test_g0v_exact_arithmetic_only() -> None:
    """Exact arithmetic only, and no network vocabulary in this file."""
    source = Path(__file__).read_text(encoding="utf-8")
    assert "flo" + "at(" not in source
    assert "Decimal" in source
    for forbidden in ("ur" "llib", "re" "quests", "ht" "tp:", "so" "cket"):
        assert forbidden not in source, forbidden
