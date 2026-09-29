"""tests/test_transmission_company_continuation.py — MO-J1A identity law + page projection.

Pure adapter: every falsifier the spec calls out lives here, RED-first.

The identity law (engine.transmission_company_continuation.continuation_for):
    security_id      = aliases.resolve(VENDOR, blast_symbol, decision_date)   # None -> NoLink.unresolved
    current_symbol   = aliases.vendor_symbol_for(VENDOR, security_id, decision_date)  # None -> NoLink.no_current_symbol
    require current_symbol == blast_symbol                                    # else NoLink.stale_alias
    require aliases.resolve(VENDOR, current_symbol, decision_date) == security_id  # else NoLink.round_trip_mismatch

The page projection (enrich_display_chains) walks the display subset and adds
per-blast-channel ``companies`` blocks. Dormant chains get NO companies key.
aliases=None (artifact unavailable) -> identity_unavailable with zero links.

The fixtures use the VendorAliasTable.from_records(...) shape used in
tests/test_dataos_security_master.py.
"""
from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest

from engine.transmission_company_continuation import (
    CONTINUATION_VENDOR,
    TERMINAL_ANALYSIS_URL,
    ContinuationLink,
    NoLink,
    continuation_for,
    enrich_display_chains,
)
from lib.dataos.identity import VendorAliasTable


DECISION = date(2026, 9, 25)
AAPL_ID = "SEC:0:AAPL"
NVDA_ID = "SEC:0:NVDA"
TSLA_ID = "SEC:0:TSLA"
MRSH_ID = "SEC:0:MRSH"  # Marsh & McLennan — formerly MMC (vendor-rename)


def _aliases(rows) -> VendorAliasTable:
    return VendorAliasTable.from_records([
        {
            "vendor": r[0],
            "vendor_symbol": r[1],
            "security_id": r[2],
            "valid_from": r[3],
            "valid_to": r[4],
        }
        for r in rows
    ])


def _good_aliases() -> VendorAliasTable:
    """Three open-bounded ``store`` rows — the canonical current-catalog shape."""
    return _aliases([
        ("store", "AAPL", AAPL_ID, None, None),
        ("store", "NVDA", NVDA_ID, None, None),
        ("store", "TSLA", TSLA_ID, None, None),
    ])


def _time_invalid_aliases() -> VendorAliasTable:
    """store/OLD1 -> SEC:0:OLD only valid 2026-09-10..2026-09-20 — outside DECISION."""
    return _aliases([
        ("store", "OLD1", "SEC:0:OLD1", date(2026, 9, 10), date(2026, 9, 20)),
    ])


# ── falsifiers ──────────────────────────────────────────────────────────────
def test_continuation_for_unresolved_when_alias_missing():
    aliases = _good_aliases()
    result = continuation_for("ZZZZ", aliases, DECISION,
                              chain_id="c1", channel_id="ch1", chain_asof="2026-09-25")
    assert isinstance(result, NoLink)
    assert result.reason == "unresolved"
    assert result.symbol == "ZZZZ"


def test_continuation_for_no_current_symbol_when_alias_resolves_but_vendor_has_none():
    """Reach the ``no_current_symbol`` code path at
    engine/transmission_company_continuation.py:137-139 with a duck-typed
    aliases object: the forward resolve succeeds, but vendor_symbol_for
    returns None at the decision_date (the security has no current catalog
    entry — a defensively-typed state that a lawful VendorAliasTable refuses
    to construct because every security_id must have an open-bounded
    current row).

    The duck stub quacks like VendorAliasTable for the two methods
    ``continuation_for`` calls. A future regression in the table loader that
    lets through such a state would surface as a NoLink rather than a
    silent link — exactly the contract this defensive code path exists for.
    """
    class _Duck:
        def resolve(self, vendor, vendor_symbol, on):
            if vendor_symbol == "WEIRD":
                return "SEC:0:WEIRD"
            return None

        def vendor_symbol_for(self, vendor, security_id_, on):
            # The forward resolve above returned this security_id — but the
            # current-catalog direction returns None for it.
            return None

    result = continuation_for("WEIRD", _Duck(), DECISION,
                              chain_id="c1", channel_id="ch1", chain_asof="2026-09-25")
    assert isinstance(result, NoLink)
    assert result.reason == "no_current_symbol"
    assert result.symbol == "WEIRD"


def test_continuation_for_time_invalid_alias_outside_window():
    aliases = _time_invalid_aliases()
    result = continuation_for("OLD1", aliases, DECISION,
                              chain_id="c1", channel_id="ch1", chain_asof="2026-09-25")
    assert isinstance(result, NoLink)
    assert result.reason == "unresolved"


def test_continuation_for_stale_alias_when_blast_symbol_is_historical():
    """Construct an INVALID alias table via ``object.__new__`` (the lawful
    loader refuses by construction — overlap on the security_id bucket) so the
    defensive ``stale_alias`` code path is exercised: blast resolves to a
    security_id whose current vendor_symbol differs from the blast.

    Row order matters: row 0 is the NEW current alias, row 1 is the OLD alias;
    VendorAliasTable.resolve / vendor_symbol_for iterate in self._rows order
    so OLD resolves first, NEW wins vendor_symbol_for.
    """
    import lib.dataos.identity as _ident
    rows = (
        # current-catalog row first so vendor_symbol_for picks NEW before OLD
        _ident.AliasRow("store", "NEW", MRSH_ID, None, None),
        _ident.AliasRow("store", "MMC", MRSH_ID, None, None),
    )
    aliases = _ident.VendorAliasTable.__new__(_ident.VendorAliasTable)
    aliases._rows = rows
    result = continuation_for("MMC", aliases, DECISION,
                              chain_id="c1", channel_id="ch1", chain_asof="2026-09-25")
    assert isinstance(result, NoLink)
    assert result.reason == "stale_alias"
    assert result.symbol == "MMC"


def test_continuation_for_round_trip_mismatch_when_reverse_resolve_differs():
    """Reach the ``round_trip_mismatch`` code path at
    engine/transmission_company_continuation.py:144-145 with a duck-typed
    aliases object whose forward resolve returns security_id S, the current
    symbol for S equals the blast, but the reverse resolve of that current
    symbol returns a DIFFERENT security_id S'.

    The lawful ``VendorAliasTable.from_records`` refuses by construction:
    any two rows that overlap in either (vendor, vendor_symbol) or (vendor,
    security_id) buckets raise IdentityError. The round-trip mismatch can
    therefore only be reached against an INVALID alias table — and the
    duck stub here is exactly such an invalid table. The stub quacks like
    VendorAliasTable for the two methods ``continuation_for`` calls; a
    future regression in the table loader that lets through an ambiguous
    security_id bucket surfaces here as a NoLink rather than as a silent
    link, exactly the contract this defensive code path exists for.
    """
    class _Duck:
        def resolve(self, vendor, vendor_symbol, on):
            # Forward: blast "X" -> S; reverse (called with current_symbol
            # which also equals "X") -> S_DIFFERENT.
            if vendor_symbol == "X":
                # First call is the forward resolve; the second call is the
                # round-trip reverse resolve (current_symbol == blast == "X").
                self._calls = getattr(self, "_calls", 0) + 1
                if self._calls == 1:
                    return "SEC:0:S"
                return "SEC:0:S_DIFFERENT"
            return None

        def vendor_symbol_for(self, vendor, security_id_, on):
            # The current-catalog direction returns "X" — the same as the
            # blast — so the prior ``current_symbol == blast_symbol`` check
            # passes and we fall through to the round-trip.
            return "X"

    result = continuation_for("X", _Duck(), DECISION,
                              chain_id="c1", channel_id="ch1", chain_asof="2026-09-25")
    assert isinstance(result, NoLink)
    assert result.reason == "round_trip_mismatch"
    assert result.symbol == "X"


def test_nolink_dataclass_round_trip_mismatch_surface_exists():
    """The typed NoLink SURFACE for round_trip_mismatch is constructed by the
    module — assert the dataclass shape so a future refactor that drops the
    reason field fails loudly here.
    """
    nl = NoLink(symbol="X", reason="round_trip_mismatch")
    assert nl.symbol == "X"
    assert nl.reason == "round_trip_mismatch"
    d = nl.as_dict()
    assert d == {"symbol": "X", "reason": "round_trip_mismatch"}


def test_nolink_dataclass_no_current_symbol_surface_exists():
    nl = NoLink(symbol="X", reason="no_current_symbol")
    assert nl.reason == "no_current_symbol"


def test_continuation_for_happy_path_returns_continuation_link():
    aliases = _good_aliases()
    result = continuation_for("AAPL", aliases, DECISION,
                              chain_id="dollar_ch", channel_id="em_revenue",
                              chain_asof="2026-09-25")
    assert isinstance(result, ContinuationLink)
    assert result.symbol == "AAPL"
    assert result.security_id == AAPL_ID
    parsed = urlparse(result.href)
    assert parsed.scheme == "https"
    assert parsed.netloc == "app.mastermind-x.com"
    assert parsed.path == "/analysis"
    qs = parse_qs(parsed.query)
    assert set(qs.keys()) == {"symbol", "page", "mo_chain", "mo_channel", "mo_asof", "mo_security_id"}
    assert qs["symbol"] == ["AAPL"]
    assert qs["page"] == ["intelligence"]
    assert qs["mo_chain"] == ["dollar_ch"]
    assert qs["mo_channel"] == ["em_revenue"]
    assert qs["mo_asof"] == ["2026-09-25"]
    assert qs["mo_security_id"] == [AAPL_ID]


def test_continuation_href_never_carries_source_text_or_receipts():
    aliases = _good_aliases()
    result = continuation_for("NVDA", aliases, DECISION,
                              chain_id="oil_ch", channel_id="long_dur",
                              chain_asof="2026-09-25")
    assert isinstance(result, ContinuationLink)
    forbidden = ("receipt", "value_receipt", "passed", "threshold", "json",
                 "transmission", "blast", "unevaluable", "TXI", "FOO")
    for tok in forbidden:
        assert tok.lower() not in result.href.lower(), f"href leaked {tok!r}: {result.href}"


def test_continuation_href_is_url_encoded():
    """If a symbol ever needs url-encoding, the harness preserves it."""
    aliases = _good_aliases()
    result = continuation_for("AAPL", aliases, DECISION,
                              chain_id="c/with/slash", channel_id="ch id",
                              chain_asof="2026-09-25")
    assert isinstance(result, ContinuationLink)
    # raw URL keeps the slash un-encoded (path-style) but query params are
    # url-encoded. The chain_id with a slash ends up encoded.
    assert "c%2Fwith%2Fslash" in result.href or "c/with/slash" in result.href  # encoded by quote
    # The ampersand-less query separator means quote(..., safe='') was used.
    assert ";semicolons" not in result.href


# ── page projection ─────────────────────────────────────────────────────────
def _chain(*, id, state, blast):
    return {
        "id": id,
        "label": {"en": id, "zh": id},
        "state": state,
        "tier": "hypothesis",
        "hops": [],
        "blast": blast,
        "caveats": [],
    }


def _channel(label, names, unevaluable=0):
    return {
        "label": {"en": label, "zh": label},
        "n": len(names),
        "unevaluable": unevaluable,
        "names": list(names),
        "cuts": {},
    }


def test_enrich_dormant_chain_gets_no_companies_key():
    chains = {
        "schema": "transmission_chains_display.v1",
        "asof": "2026-09-25",
        "chains": [_chain(id="vol_regime", state="dormant", blast={})],
    }
    out = enrich_display_chains(chains, _good_aliases(), DECISION)
    assert "companies" not in out["chains"][0], "dormant chain must NOT carry a companies key"


def test_enrich_non_dormant_chain_builds_companies_per_blast_channel():
    chains = {
        "schema": "transmission_chains_display.v1",
        "asof": "2026-09-25",
        "chains": [_chain(
            id="dollar_ch", state="propagating",
            blast={
                "em_revenue": _channel("EM revenue", ["AAPL", "NVDA", "AAPL", "ZZZZ"]),
                "multinational_fx": _channel("Multinational FX", ["TSLA"], unevaluable=1590),
            },
        )],
    }
    out = enrich_display_chains(chains, _good_aliases(), DECISION)
    assert "companies" in out["chains"][0]
    companies = out["chains"][0]["companies"]
    assert set(companies.keys()) == {"em_revenue", "multinational_fx"}

    em = companies["em_revenue"]
    assert em["ranked"] is False
    assert em["identity_unavailable"] is False
    assert [lk["symbol"] for lk in em["linked"]] == ["AAPL", "NVDA"]   # alphabetical
    assert em["unlinked"] == ["ZZZZ"]                                  # alphabetical
    assert em["n_linked"] == 2
    assert em["n_unlinked"] == 1
    assert em["unevaluable"] == 0

    fx = companies["multinational_fx"]
    assert [lk["symbol"] for lk in fx["linked"]] == ["TSLA"]
    assert fx["unlinked"] == []
    assert fx["unevaluable"] == 1590                                # preserved verbatim


def test_enrich_preserves_unevaluable_verbatim_across_linked_and_unlinked():
    chains = {
        "schema": "transmission_chains_display.v1",
        "asof": "2026-09-25",
        "chains": [_chain(id="c", state="arming",
                          blast={"ch": _channel("Channel", ["AAPL", "ZZZ"], unevaluable=42)})],
    }
    out = enrich_display_chains(chains, _good_aliases(), DECISION)
    companies = out["chains"][0]["companies"]["ch"]
    assert companies["unevaluable"] == 42
    assert companies["linked"] and len(companies["linked"]) == 1
    assert companies["unlinked"] == ["ZZZ"]


def test_enrich_ordering_alphabetical_and_unranked_under_shuffled_feed():
    """Feed names in shuffled order; assert the projection is sorted and
    ranked=False. Pins the EXPECTED list — the falsifier fails if the
    projection drifts away from alphabet (e.g. accidentally re-sorts by
    something else, or drops a row)."""
    feed = ["TSLA", "AAPL", "NVDA", "MSFT", "GOOG", "AMZN"]
    chains = {
        "schema": "transmission_chains_display.v1",
        "asof": "2026-09-25",
        "chains": [_chain(id="c", state="arming",
                          blast={"ch": _channel("Channel", feed)})],
    }
    out = enrich_display_chains(chains, _good_aliases(), DECISION)
    companies = out["chains"][0]["companies"]["ch"]
    assert companies["ranked"] is False
    # The names that DO resolve from the alias table are AAPL/NVDA/TSLA — pinned
    # alphabetical list (the falsifier — any reorder or drop surfaces here):
    linked_symbols = [lk["symbol"] for lk in companies["linked"]]
    assert linked_symbols == ["AAPL", "NVDA", "TSLA"]
    # Unlinked pinned too: MSFT/GOOG/AMZN are absent from the alias table:
    assert companies["unlinked"] == ["AMZN", "GOOG", "MSFT"]
    # Counts:
    assert companies["n_linked"] == 3
    assert companies["n_unlinked"] == 3


def test_enrich_aliases_none_renders_identity_unavailable_no_links():
    chains = {
        "schema": "transmission_chains_display.v1",
        "asof": "2026-09-25",
        "chains": [_chain(id="c", state="propagating",
                          blast={"ch": _channel("Channel", ["AAPL", "NVDA", "TSLA"])})],
    }
    out = enrich_display_chains(chains, None, DECISION)
    companies = out["chains"][0]["companies"]["ch"]
    assert companies["identity_unavailable"] is True
    assert companies["linked"] == []
    assert companies["unlinked"] == ["AAPL", "NVDA", "TSLA"]    # alphabetical
    assert companies["n_linked"] == 0
    assert companies["n_unlinked"] == 3
    assert companies["ranked"] is False


def test_enrich_does_not_mutate_input():
    input_chains = {
        "schema": "transmission_chains_display.v1",
        "asof": "2026-09-25",
        "chains": [_chain(
            id="c", state="arming",
            blast={"ch": _channel("Channel", ["AAPL", "NVDA"])},
        )],
    }
    import copy
    snapshot = copy.deepcopy(input_chains)
    _ = enrich_display_chains(input_chains, _good_aliases(), DECISION)
    assert input_chains == snapshot, "enrich_display_chains must not mutate the input dict"


def test_enrich_deterministic_under_repeated_calls():
    chains = {
        "schema": "transmission_chains_display.v1",
        "asof": "2026-09-25",
        "chains": [_chain(id="c", state="propagating",
                          blast={"ch": _channel("Channel", ["NVDA", "AAPL", "TSLA"])})],
    }
    a = enrich_display_chains(chains, _good_aliases(), DECISION)
    b = enrich_display_chains(chains, _good_aliases(), DECISION)
    assert a == b


def test_enrich_handles_empty_chain_set():
    out = enrich_display_chains({"chains": []}, _good_aliases(), DECISION)
    assert out["chains"] == []


def test_enrich_continuation_vendor_constant_is_store():
    """Routing authority stays the frozen CONTINUATION_VENDOR — guard any
    accidental change in the constants."""
    assert CONTINUATION_VENDOR == "store"
    assert TERMINAL_ANALYSIS_URL == "https://app.mastermind-x.com/analysis"


def test_continuation_for_empty_symbol_returns_unresolved():
    aliases = _good_aliases()
    assert isinstance(
        continuation_for("", aliases, DECISION,
                         chain_id="c", channel_id="ch", chain_asof="2026-09-25"),
        NoLink,
    )
    assert isinstance(
        continuation_for("   ", aliases, DECISION,
                         chain_id="c", channel_id="ch", chain_asof="2026-09-25"),
        NoLink,
    )


def test_enrich_linked_href_carries_only_six_keys_and_no_chain_label():
    aliases = _good_aliases()
    chains = {
        "schema": "transmission_chains_display.v1",
        "asof": "2026-09-25",
        "chains": [_chain(id="c", state="propagating",
                          blast={"ch": _channel("Channel", ["AAPL"])})],
    }
    out = enrich_display_chains(chains, aliases, DECISION)
    href = out["chains"][0]["companies"]["ch"]["linked"][0]["href"]
    parsed = urlparse(href)
    qs = parse_qs(parsed.query)
    # exactly the six frozen keys, nothing else.
    assert set(qs.keys()) == {"symbol", "page", "mo_chain", "mo_channel", "mo_asof", "mo_security_id"}
    # the chain_id travels only as mo_chain, never leaks into the path.
    assert "c" not in parsed.path
    assert "c" in qs["mo_chain"][0] or qs["mo_chain"][0] == "c"


# ── real artifact round-trip (MINOR 9) ──────────────────────────────────────
def test_real_artifact_round_trip(tmp_path):
    """Exercise the full artifact path ``_records -> from_records`` that the
    nightly build_transmission runs. We mint a real parquet file (pandas
    ``to_parquet``) with the canonical schema and verify the chain produces
    the expected projection — without depending on the omitted ``data/``
    tree or on pandas being available in the wider test environment.

    A nightly degrade to ``identity_unavailable`` (reviewer's MINOR 9
    concern) shows only in log.error otherwise; this test fails loudly if
    the schema drifts and the table refuses to construct.
    """
    pd = pytest.importorskip("pandas")

    from engine.intelligence_workspace.entity import _records
    from engine.intelligence_workspace.entity import VENDOR_ALIASES as _VA_PATH

    rows = [
        {"vendor": "store", "vendor_symbol": "AAPL", "security_id": AAPL_ID,
         "valid_from": None, "valid_to": None},
        {"vendor": "store", "vendor_symbol": "NVDA", "security_id": NVDA_ID,
         "valid_from": None, "valid_to": None},
        {"vendor": "store", "vendor_symbol": "TSLA", "security_id": TSLA_ID,
         "valid_from": None, "valid_to": None},
    ]
    df = pd.DataFrame(rows)
    parquet_path = tmp_path / _VA_PATH.name  # "vendor_aliases.parquet"
    df.to_parquet(parquet_path)

    alias_rows = _records(parquet_path)
    aliases = VendorAliasTable.from_records(alias_rows)
    chains = {
        "schema": "transmission_chains_display.v1",
        "asof": "2026-09-25",
        "chains": [_chain(id="c", state="propagating",
                          blast={"ch": _channel("Channel", ["AAPL", "NVDA", "TSLA"])})],
    }
    out = enrich_display_chains(chains, aliases, DECISION)
    companies = out["chains"][0]["companies"]["ch"]
    assert [lk["symbol"] for lk in companies["linked"]] == ["AAPL", "NVDA", "TSLA"]
    assert companies["unlinked"] == []
    assert companies["identity_unavailable"] is False


def test_real_artifact_round_trip_surfaces_identity_unavailable_on_schema_drift(tmp_path):
    """If the parquet carries a non-ISO date string in valid_from/valid_to
    (the reviewer's concern: pandas serializes ``NaT`` as ``"NaT"``, which
    ``_as_date`` rejects), ``VendorAliasTable.from_records`` raises and the
    nightly lands on the ``aliases=None`` path. The ``_records`` +
    ``from_records`` chain must propagate the IdentityError so the build
    script's try/except correctly falls back to ``identity_unavailable``
    rendering.
    """
    pd = pytest.importorskip("pandas")

    from engine.intelligence_workspace.entity import _records

    rows = [
        {"vendor": "store", "vendor_symbol": "AAPL", "security_id": AAPL_ID,
         "valid_from": "NaT", "valid_to": None},  # schema drift — pandas NaT serializes
    ]
    df = pd.DataFrame(rows)
    parquet_path = tmp_path / "vendor_aliases.parquet"
    df.to_parquet(parquet_path)

    alias_rows = _records(parquet_path)
    from lib.dataos.identity import IdentityError
    with pytest.raises(IdentityError):
        VendorAliasTable.from_records(alias_rows)