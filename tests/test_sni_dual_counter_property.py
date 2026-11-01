"""SNI-local DRAFT contract: dual-counter relation and ADS:ordinary ratio.

Consumes owner-supplied coverage-profile values (counters, pooling text,
adr_h_basis source strings, S1/S2 instrument keys). Does not fork or
re-implement Data OS identity, Company Event/Earnings, FIF, Capital
Structure, Stock Identity, Options, Research Vault, or qledger/Evaluation.
Identity ids are caller-supplied opaque strings owned by Stock Identity /
Data OS; this module never mints, derives, or guesses them from a ticker,
name, code, or CIK.

Evidence for A01 (BABA ADS distinct from ordinary-share counters) and A02
(dual counters keep relations without minted IDs). Nothing here feeds a
ranker, gate, sizer, signal, escalation, or trade path. Every authority
flag stays literal false; setting any of them true raises.

Fixtures written under tmp_path are synthetic. The C1/C4 owner ratio and
relationship contracts are R1-gated and are not tested here.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / "config" / "single_name_intelligence" / "coverage_profiles"
RUNS_DIR = ROOT / "research" / "single_name_intelligence" / "runs"
PROFILES = ("alibaba", "tencent")
SEEDS = range(200)

AUTHORITY_FLAGS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)
_AUTHORITY_CANONICAL = {name.casefold(): name for name in AUTHORITY_FLAGS}
_AUTHORITY_FOLDED = set(_AUTHORITY_CANONICAL)

OWNER_ISSUE_RE = re.compile(r"^ISS:[A-Z]{2}-[A-Z]{4}-[A-Z0-9.]+$")
OWNER_SEC_RE = re.compile(r"^SEC:[A-Z]{2}-[A-Z]{4}-[A-Z0-9.]+$")
RATIO_KEY_RE = re.compile(
    r"(?:ads|adr).{0,24}ratio|ratio.{0,24}(?:ads|adr|ordinary)",
    re.IGNORECASE,
)
BRIDGE_RE = re.compile(
    r"display bridge (\S+) -> (\S+) \(pair kind (\w+)\)",
    re.IGNORECASE,
)
IDENTITY_KEYS = frozenset(
    {
        "canonical_issuer_id",
        "issuer_id",
        "security_id",
        "canonical_security_id",
        "instrument_id",
        "listing_id",
    }
)
MINT_CONCAT_RE = re.compile(r"^[A-Z]{1,5}-\d{3,5}-")
HASHISH_RE = re.compile(r"^[0-9a-f]{32}$|^[0-9a-f]{40}$|^[0-9a-f]{64}$", re.I)

PINNED_ALIBABA_COUNTERS = ("hkd_9988", "rmb_89988", "adr_baba")
PINNED_TENCENT_COUNTERS = ("hkd_0700", "rmb_80700")
PINNED_S1_COUNTERS = frozenset({"adr_baba", "hkd_9988", "hkd_0700"})
PINNED_S1_SECURITY_IDS = frozenset(
    {"SEC:US-XNYS-BABA", "SEC:HK-XHKG-09988", "SEC:HK-XHKG-00700"}
)
PINNED_COUNTER_TO_SID = {
    "adr_baba": "SEC:US-XNYS-BABA",
    "hkd_9988": "SEC:HK-XHKG-09988",
    "hkd_0700": "SEC:HK-XHKG-00700",
}
ADS_COUNTERS = frozenset({"adr_baba"})
ORDINARY_COUNTERS = frozenset({"hkd_9988", "hkd_0700", "rmb_89988", "rmb_80700"})
S1_OBS_NAME_RE = re.compile(r"^(P\d+)_([a-z]+_[a-z0-9]+)_(\d+)\.json$")


def _authority_refuse(key):
    return "authority flag %s must be literal False" % key


class AuthorityMap(dict):
    """Mapping that refuses any authority flag other than literal False."""

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.update(*args, **kwargs)

    def __setitem__(self, key, value):
        folded = key.strip().casefold() if isinstance(key, str) else None
        if folded in _AUTHORITY_FOLDED:
            canonical = _AUTHORITY_CANONICAL[folded]
            if key != canonical or value is not False:
                raise ValueError(_authority_refuse(key))
        super().__setitem__(key, value)

    def update(self, *args, **kwargs):
        incoming = dict(*args, **kwargs)
        for key, value in incoming.items():
            self[key] = value

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


def refuse_nonfalse_authority(authority):
    if not isinstance(authority, dict):
        raise ValueError("authority must be a mapping")
    for name in AUTHORITY_FLAGS:
        if authority.get(name) is not False:
            raise ValueError(_authority_refuse(name))
    for key, value in authority.items():
        folded = key.strip().casefold() if isinstance(key, str) else None
        if folded in _AUTHORITY_FOLDED and (
            key != _AUTHORITY_CANONICAL[folded] or value is not False
        ):
            raise ValueError(_authority_refuse(key))
    return authority


def _profile_path(name):
    return PROFILE_DIR / ("%s.yml" % name)


def load_profile(name):
    payload = yaml.safe_load(_profile_path(name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("profile must be a mapping")
    auth = payload.get("authority")
    if isinstance(auth, dict):
        payload["authority"] = AuthorityMap(auth)
    else:
        payload["authority"] = AuthorityMap()
    refuse_nonfalse_authority(payload["authority"])
    return payload


def instrument_class(counter_key, counter):
    label = str((counter or {}).get("label") or "")
    if "ADS" in label or str(counter_key).startswith("adr_"):
        return "ads"
    if "RMB counter" in label or str(counter_key).startswith("rmb_"):
        return "ordinary_rmb"
    if "HKD counter" in label or str(counter_key).startswith("hkd_"):
        return "ordinary_hkd"
    return "unknown"


def _endpoint(counter_key, counter, extra=None):
    body = {
        "counter_key": counter_key,
        "symbol": str(counter.get("local_code")),
        "venue": str(counter.get("venue_mic")),
        "currency": counter.get("currency"),
        "instrument_class": instrument_class(counter_key, counter),
    }
    if extra:
        body.update(extra)
    return body


def _endpoint_key(endpoint):
    if not isinstance(endpoint, dict):
        return ("UNRESOLVED", "UNRESOLVED")
    symbol = endpoint.get("symbol") or endpoint.get("counter_key") or "UNRESOLVED"
    venue = endpoint.get("venue") or "UNRESOLVED"
    return (str(symbol), str(venue))


def _bridge_hits(profile):
    basis = ((profile or {}).get("families") or {}).get("adr_h_basis") or {}
    hits = []
    if not isinstance(basis, dict):
        return hits
    for counter_key, cell in basis.items():
        if not isinstance(cell, dict):
            continue
        source = cell.get("source") or ""
        match = BRIDGE_RE.search(str(source))
        if match:
            hits.append(
                {
                    "counter_key": counter_key,
                    "left": match.group(1),
                    "right": match.group(2),
                    "pair_kind": match.group(3).lower(),
                    "source": source,
                    "status": cell.get("status"),
                    "coverage": cell.get("coverage") or "",
                    "notes": cell.get("notes") or "",
                }
            )
    return hits


def us_proxy_entries(profile):
    """US OTC/ADR/proxy lines that are not admitted equivalent counters."""
    entries = []
    for hit in _bridge_hits(profile):
        if hit["pair_kind"] != "proxy":
            continue
        entries.append(
            {
                "symbol": hit["right"],
                "venue": "UNRESOLVED",
                "instrument_class": "proxy",
                "status": "proxy_not_admitted",
                "pair_kind": "proxy",
                "admitted_counter": False,
                "source": hit["source"],
            }
        )
        coverage = hit["coverage"]
        if "TCEHY" in coverage and "not admitted" in coverage.lower():
            entries.append(
                {
                    "symbol": "TCEHY",
                    "venue": "UNRESOLVED",
                    "instrument_class": "otc_adr_mention",
                    "status": "not_admitted",
                    "admitted_counter": False,
                    "source": coverage,
                }
            )
    return entries


def extract_relations(profile):
    """Build the relation list from pooling text, adr_h_basis bridges, and any
    explicit `relations` list (used only by synthetic tmp_path copies).
    """
    rels = []
    declared = profile.get("relations")
    if isinstance(declared, list):
        for item in declared:
            if isinstance(item, dict):
                rels.append(copy.deepcopy(item))
    counters = profile.get("counters") or {}
    if not isinstance(counters, dict):
        return rels
    by_code = {}
    for key, counter in counters.items():
        if not isinstance(counter, dict):
            continue
        by_code[str(counter.get("local_code"))] = (key, counter)
        by_code[str(counter.get("local_code")).lstrip("0") or "0"] = (key, counter)
    for key, counter in counters.items():
        if not isinstance(counter, dict):
            continue
        pooling = str(counter.get("pooling") or "")
        cls = instrument_class(key, counter)
        if "same economic security" in pooling.lower() or "one economic security" in pooling.lower():
            partner = None
            for code, pair in by_code.items():
                if pair[0] == key:
                    continue
                if code and code in pooling.replace(" ", ""):
                    partner = pair
                    break
            if partner is None:
                digits = re.findall(r"\d{3,5}", pooling)
                for code in digits:
                    if code in by_code and by_code[code][0] != key:
                        partner = by_code[code]
                        break
            if partner is not None:
                rels.append(
                    {
                        "a": _endpoint(key, counter),
                        "b": _endpoint(partner[0], partner[1]),
                        "kind": "dual_hk_counter",
                    }
                )
        if cls == "ads" and "ordinary" in pooling.lower():
            ordinary = None
            for other_key, other in counters.items():
                if instrument_class(other_key, other) == "ordinary_hkd":
                    ordinary = (other_key, other)
                    break
            if ordinary is not None:
                rels.append(
                    {
                        "a": _endpoint(key, counter),
                        "b": _endpoint(ordinary[0], ordinary[1]),
                        "kind": "ads_ordinary",
                    }
                )
    for hit in _bridge_hits(profile):
        left = hit["left"]
        right = hit["right"]
        kind = "overnight_proxy" if hit["pair_kind"] == "proxy" else "ads_ordinary"
        left_ep = _symbol_to_endpoint(left, counters)
        right_ep = _symbol_to_endpoint(right, counters)
        if hit["pair_kind"] == "proxy":
            right_ep = {
                "counter_key": None,
                "symbol": right,
                "venue": "UNRESOLVED",
                "instrument_class": "proxy",
                "status": "proxy_not_admitted",
            }
        rels.append({"a": left_ep, "b": right_ep, "kind": kind, "source": hit["source"]})
    return rels


def _symbol_to_endpoint(token, counters):
    raw = str(token)
    stripped = raw.replace(".HK", "").replace(".hk", "")
    for key, counter in counters.items():
        if not isinstance(counter, dict):
            continue
        code = str(counter.get("local_code") or "")
        if raw == code or stripped == code or stripped == code.lstrip("0") or raw == key:
            return _endpoint(key, counter)
        if code.lstrip("0") and stripped.lstrip("0") == code.lstrip("0"):
            return _endpoint(key, counter)
    return {
        "counter_key": None,
        "symbol": raw,
        "venue": "UNRESOLVED",
        "instrument_class": "unresolved",
        "status": "UNRESOLVED",
    }


def canonical_relation_tuples(relations, *, order_sensitive=False):
    tuples = []
    for rel in relations:
        a = _endpoint_key(rel.get("a") if isinstance(rel, dict) else None)
        b = _endpoint_key(rel.get("b") if isinstance(rel, dict) else None)
        kind = str((rel or {}).get("kind") or "")
        if order_sensitive:
            pair = (a, b, kind)
        else:
            pair = tuple(sorted((a, b))) + (kind,)
        tuples.append(pair)
    if order_sensitive:
        return tuple(tuples)
    return tuple(sorted(set(tuples)))


def loader_digest(named_profiles, *, order_sensitive=False):
    payload = {}
    items = list(named_profiles)
    if not order_sensitive:
        items = sorted(items, key=lambda kv: kv[0])
    for name, profile in items:
        rels = extract_relations(profile)
        payload[name] = [list(t) for t in canonical_relation_tuples(rels, order_sensitive=order_sensitive)]
    blob = json.dumps(payload, sort_keys=not order_sensitive, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).digest()


def as_plain(obj):
    """Strip AuthorityMap / other dict subclasses so yaml.safe_dump can emit them."""
    if isinstance(obj, dict):
        return {k: as_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [as_plain(v) for v in obj]
    return obj


def shuffle_mapping(obj, rng):
    if isinstance(obj, dict):
        keys = list(obj.keys())
        rng.shuffle(keys)
        return {k: shuffle_mapping(obj[k], rng) for k in keys}
    if isinstance(obj, list):
        items = [shuffle_mapping(x, rng) for x in obj]
        rng.shuffle(items)
        return items
    return obj


def permute_profile(profile, rng):
    """Shuffle counter insertion order and every mapping's key order, then
    re-serialise through yaml so key order is a real round-trip.
    """
    dup = copy.deepcopy(profile)
    counters = dup.get("counters")
    if isinstance(counters, dict):
        keys = list(counters.keys())
        rng.shuffle(keys)
        dup["counters"] = {k: counters[k] for k in keys}
    shuffled = shuffle_mapping(dup, rng)
    dumped = yaml.safe_dump(as_plain(shuffled), sort_keys=False, allow_unicode=True)
    reloaded = yaml.safe_load(dumped)
    auth = reloaded.get("authority")
    if isinstance(auth, dict):
        reloaded["authority"] = AuthorityMap(auth)
        refuse_nonfalse_authority(reloaded["authority"])
    return reloaded


def iter_ratio_fields(obj, path=""):
    if isinstance(obj, dict):
        for key, value in obj.items():
            here = "%s.%s" % (path, key) if path else str(key)
            if isinstance(key, str) and RATIO_KEY_RE.search(key):
                yield here, value
            yield from iter_ratio_fields(value, here)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from iter_ratio_fields(value, "%s[%d]" % (path, i))


def ratio_source_of(value):
    if isinstance(value, dict):
        for key in ("source", "citation", "source_citation", "cited_source"):
            cited = value.get(key)
            if cited not in (None, "", []):
                return key, cited
        return None
    return None


def check_ads_ratio_declared(profile, *, allow_xfail=True):
    """Require a declared ADS:ordinary ratio field that carries a source.

    Absence is DCP-F1 (xfail when allow_xfail). A present field without a
    source/citation is a hard failure. Never invents a numeric ratio.
    """
    issuer = profile.get("issuer_key") or "?"
    records = list(iter_ratio_fields(profile))
    if not records:
        reason = (
            "DCP-F1: profile=%s field=ads_ordinary_ratio is absent; "
            "no declared ADS:ordinary ratio with a source/citation "
            "(identity_listing.adr_baba.notes states the ratio is not "
            "carried by any Data OS field)"
            % issuer
        )
        if allow_xfail:
            # pytest 9.1 xfail() takes reason only; absence is the expected
            # finding (DCP-F1). A later declared ratio with a source makes
            # this path unreachable and the test pins that value instead.
            pytest.xfail(reason)
        raise AssertionError(reason)
    pinned = []
    for path, value in records:
        src = ratio_source_of(value)
        if src is None:
            raise AssertionError(
                "profile=%s field=%s has an ADS:ordinary ratio without a "
                "source/citation"
                % (issuer, path)
            )
        pinned.append((path, value, src))
    return pinned


def _allowed_id(value):
    if value is None or value == "UNRESOLVED":
        return True
    if not isinstance(value, str):
        return False
    return bool(OWNER_ISSUE_RE.match(value) or OWNER_SEC_RE.match(value))


def _looks_minted(value):
    if not isinstance(value, str) or value in ("", "UNRESOLVED"):
        return False
    if _allowed_id(value):
        return False
    if MINT_CONCAT_RE.match(value):
        return True
    if HASHISH_RE.match(value):
        return True
    return True


def minted_id_hits(relations):
    """Flag relation endpoints/ids that are not symbol/venue, owner-shaped, or UNRESOLVED."""
    hits = []

    def walk(obj, path):
        if isinstance(obj, dict):
            for key, value in obj.items():
                here = "%s.%s" % (path, key) if path else str(key)
                folded = key.strip().casefold() if isinstance(key, str) else ""
                if folded in IDENTITY_KEYS or folded in {"issuer_link"}:
                    if _looks_minted(value):
                        hits.append((here, value))
                elif folded in {"symbol", "venue", "counter_key", "kind", "source", "status", "instrument_class", "currency"}:
                    pass
                walk(value, here)
        elif isinstance(obj, list):
            for i, value in enumerate(obj):
                walk(value, "%s[%d]" % (path, i))
        elif isinstance(obj, str) and MINT_CONCAT_RE.match(obj):
            hits.append((path, obj))

    for i, rel in enumerate(relations):
        walk(rel, "relations[%d]" % i)
        if not isinstance(rel, dict):
            continue
        for side in ("a", "b"):
            ep = rel.get(side)
            if not isinstance(ep, dict):
                hits.append(("relations[%d].%s" % (i, side), ep))
                continue
            symbol = ep.get("symbol")
            venue = ep.get("venue")
            if not symbol:
                hits.append(("relations[%d].%s.symbol" % (i, side), symbol))
            if venue not in (None, "UNRESOLVED") and not (
                isinstance(venue, str) and re.match(r"^[A-Z]{4}$", venue)
            ):
                if venue != "UNRESOLVED":
                    hits.append(("relations[%d].%s.venue" % (i, side), venue))
            for key, value in ep.items():
                folded = key.strip().casefold() if isinstance(key, str) else ""
                if folded in IDENTITY_KEYS and _looks_minted(value):
                    hits.append(("relations[%d].%s.%s" % (i, side, key), value))
    return hits


def assert_alibaba_distinct(profile, *, seed="committed"):
    issuer = profile.get("issuer_key")
    counters = profile.get("counters") or {}
    assert set(counters) == set(PINNED_ALIBABA_COUNTERS), (
        "seed=%s profile=%s field=counters keys=%s"
        % (seed, issuer, sorted(counters))
    )
    hk = counters["hkd_9988"]
    ads = counters["adr_baba"]
    rmb = counters["rmb_89988"]
    assert instrument_class("hkd_9988", hk) == "ordinary_hkd", (
        "seed=%s profile=%s field=counters.hkd_9988.instrument_class"
        % (seed, issuer)
    )
    assert instrument_class("adr_baba", ads) == "ads", (
        "seed=%s profile=%s field=counters.adr_baba.instrument_class"
        % (seed, issuer)
    )
    assert hk.get("venue_mic") == "XHKG", (
        "seed=%s profile=%s field=counters.hkd_9988.venue_mic got=%r"
        % (seed, issuer, hk.get("venue_mic"))
    )
    assert ads.get("venue_mic") == "XNYS", (
        "seed=%s profile=%s field=counters.adr_baba.venue_mic got=%r"
        % (seed, issuer, ads.get("venue_mic"))
    )
    assert hk.get("currency") == "HKD", (
        "seed=%s profile=%s field=counters.hkd_9988.currency got=%r"
        % (seed, issuer, hk.get("currency"))
    )
    assert ads.get("currency") == "USD", (
        "seed=%s profile=%s field=counters.adr_baba.currency got=%r"
        % (seed, issuer, ads.get("currency"))
    )
    assert hk.get("venue_mic") != ads.get("venue_mic")
    assert hk.get("currency") != ads.get("currency")
    assert instrument_class("hkd_9988", hk) != instrument_class("adr_baba", ads)
    assert str(hk.get("local_code")) == "09988", (
        "seed=%s profile=%s field=counters.hkd_9988.local_code got=%r"
        % (seed, issuer, hk.get("local_code"))
    )
    assert str(ads.get("local_code")) == "BABA", (
        "seed=%s profile=%s field=counters.adr_baba.local_code got=%r"
        % (seed, issuer, ads.get("local_code"))
    )
    assert rmb.get("venue_mic") == "XHKG"
    assert rmb.get("currency") == "CNH"
    assert instrument_class("rmb_89988", rmb) == "ordinary_rmb"


def assert_tencent_hk_vs_proxy(profile, *, seed="committed"):
    issuer = profile.get("issuer_key")
    counters = profile.get("counters") or {}
    assert set(counters) == set(PINNED_TENCENT_COUNTERS), (
        "seed=%s profile=%s field=counters keys=%s"
        % (seed, issuer, sorted(counters))
    )
    hk = counters["hkd_0700"]
    assert instrument_class("hkd_0700", hk) == "ordinary_hkd"
    assert hk.get("venue_mic") == "XHKG", (
        "seed=%s profile=%s field=counters.hkd_0700.venue_mic got=%r"
        % (seed, issuer, hk.get("venue_mic"))
    )
    assert hk.get("currency") == "HKD"
    assert str(hk.get("local_code")) == "00700"
    rmb = counters["rmb_80700"]
    assert rmb.get("venue_mic") == "XHKG"
    assert rmb.get("currency") == "CNH"
    for key in counters:
        assert not str(key).startswith("adr_"), (
            "seed=%s profile=%s field=counters.%s is an ADS/ADR key; Tencent US line is a proxy"
            % (seed, issuer, key)
        )
        label = str(counters[key].get("label") or "")
        assert "KWEB" not in label and "TCEHY" not in label
        assert "ADS" not in label
    proxies = us_proxy_entries(profile)
    assert proxies, (
        "seed=%s profile=%s field=families.adr_h_basis proxy entry missing"
        % (seed, issuer)
    )
    kweb = [p for p in proxies if str(p.get("symbol")).upper().startswith("KWEB")]
    assert kweb, (
        "seed=%s profile=%s field=families.adr_h_basis KWEB proxy missing"
        % (seed, issuer)
    )
    for entry in kweb:
        assert entry.get("status") == "proxy_not_admitted"
        assert entry.get("admitted_counter") is False
        assert entry.get("pair_kind") == "proxy"
        assert entry.get("venue") == "UNRESOLVED"
    assert "kweb" not in {k.lower() for k in counters}
    tcehy = [p for p in proxies if p.get("symbol") == "TCEHY"]
    for entry in tcehy:
        assert entry.get("admitted_counter") is False
        assert entry.get("status") == "not_admitted"


def permutation_payloads(seed, *, order_sensitive=False):
    rng = random.Random(seed)
    names = list(PROFILES)
    rng.shuffle(names)
    loaded = []
    for name in names:
        loaded.append((name, permute_profile(load_profile(name), rng)))
    rel_map = {}
    for name, profile in loaded:
        rel_map[name] = canonical_relation_tuples(
            extract_relations(profile), order_sensitive=order_sensitive
        )
    digest = loader_digest(loaded, order_sensitive=order_sensitive)
    return rel_map, digest


def _row_claims_both_counters(blob):
    has_ads = "adr_baba" in blob or "XNYS-BABA" in blob
    has_ord = (
        "hkd_9988" in blob
        or "hkd_0700" in blob
        or "XHKG-09988" in blob
        or "XHKG-00700" in blob
    )
    return has_ads and has_ord


def test_dcp_01_counter_census():
    alibaba = load_profile("alibaba")
    tencent = load_profile("tencent")
    assert_alibaba_distinct(alibaba)
    assert_tencent_hk_vs_proxy(tencent)


def test_dcp_02_ads_ratio_declared():
    check_ads_ratio_declared(load_profile("alibaba"), allow_xfail=True)


def test_dcp_03_relation_permutation_invariant():
    baseline_rel = {}
    baseline_named = []
    for name in PROFILES:
        profile = load_profile(name)
        baseline_named.append((name, profile))
        baseline_rel[name] = canonical_relation_tuples(extract_relations(profile))
    baseline_digest = loader_digest(baseline_named)
    assert baseline_rel["alibaba"], "profile=alibaba field=relations is empty"
    assert baseline_rel["tencent"], "profile=tencent field=relations is empty"
    for seed in SEEDS:
        rel_map, digest = permutation_payloads(seed)
        for name in PROFILES:
            assert rel_map[name] == baseline_rel[name], (
                "seed=%s profile=%s field=relation_set"
                % (seed, name)
            )
        assert digest == baseline_digest, (
            "seed=%s profile=combined field=loader_digest"
            % seed
        )


def test_dcp_04_relations_carry_no_minted_ids(tmp_path):
    for name in PROFILES:
        profile = load_profile(name)
        rels = extract_relations(profile)
        hits = minted_id_hits(rels)
        assert hits == [], (
            "profile=%s field=relations minted=%s" % (name, hits)
        )
        for rel in rels:
            for side in ("a", "b"):
                ep = rel[side]
                assert ep.get("symbol") not in (None, "")
                venue = ep.get("venue")
                assert venue == "UNRESOLVED" or (
                    isinstance(venue, str) and re.match(r"^[A-Z]{4}$", venue)
                )
                status = ep.get("status")
                if status in {"proxy_not_admitted", "not_admitted", "UNRESOLVED"}:
                    continue
                assert ep.get("counter_key") in (profile.get("counters") or {})
    alibaba = copy.deepcopy(load_profile("alibaba"))
    mint = "BABA" + "-" + "9988" + "-" + "MINT"
    alibaba["relations"] = [
        {
            "a": {"symbol": "BABA", "venue": "XNYS", "counter_key": "adr_baba"},
            "b": {"symbol": "09988", "venue": "XHKG", "counter_key": "hkd_9988"},
            "kind": "ads_ordinary",
            "issuer_id": mint,
        }
    ]
    dest = tmp_path / "alibaba_mint.yml"
    dest.write_text(yaml.safe_dump(as_plain(alibaba), sort_keys=False), encoding="utf-8")
    loaded = yaml.safe_load(dest.read_text(encoding="utf-8"))
    hits = minted_id_hits(extract_relations(loaded))
    assert hits, "positive-control mint on a relation was not flagged"
    assert any(value == mint for _, value in hits)


def test_dcp_05_cross_listing_does_not_merge():
    observed_counters = set()
    observed_sids = set()
    v1_roots = sorted(
        p for p in RUNS_DIR.glob("*_v1_1") if p.is_dir()
    )
    assert v1_roots, "no runs/*_v1_1 directories"
    for root in v1_roots:
        manifests = root / "manifests"
        if manifests.is_dir():
            for path in sorted(manifests.glob("*.jsonl")):
                for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    blob = json.dumps(row, sort_keys=True)
                    counter = row.get("counter")
                    sid = row.get("security_id")
                    if counter is not None:
                        observed_counters.add(counter)
                        assert counter in PINNED_S1_COUNTERS, (
                            "profile=%s field=counter file=%s line=%s got=%r"
                            % (row.get("issuer_key"), path.name, lineno, counter)
                        )
                        assert not isinstance(counter, (list, tuple))
                        if sid is not None:
                            observed_sids.add(sid)
                            assert PINNED_COUNTER_TO_SID[counter] == sid, (
                                "profile=%s field=security_id file=%s line=%s counter=%s sid=%s"
                                % (row.get("issuer_key"), path.name, lineno, counter, sid)
                            )
                    graded = row.get("graded_leg")
                    if isinstance(graded, str) and graded.startswith("adr_baba"):
                        assert "hkd_9988" not in graded and "hkd_0700" not in graded
                    if counter in ADS_COUNTERS:
                        assert sid == PINNED_COUNTER_TO_SID["adr_baba"]
                        assert counter not in ORDINARY_COUNTERS
                    if counter in {"hkd_9988", "hkd_0700"}:
                        assert sid != PINNED_COUNTER_TO_SID["adr_baba"]
                    if counter is not None:
                        assert not (
                            counter in ADS_COUNTERS and counter in ORDINARY_COUNTERS
                        )
                    if counter is None:
                        assert not _row_claims_both_counters(blob), (
                            "file=%s line=%s field=row claims ADS and ordinary"
                            % (path.name, lineno)
                        )
        observations = root / "observations"
        if not observations.is_dir():
            continue
        for path in sorted(observations.iterdir()):
            if path.suffix not in {".json", ".jsonl"}:
                continue
            match = S1_OBS_NAME_RE.match(path.name)
            if match:
                file_counter = match.group(2)
                observed_counters.add(file_counter)
                assert file_counter in PINNED_S1_COUNTERS, (
                    "file=%s field=filename_counter got=%r" % (path.name, file_counter)
                )
                ads_in_name = sum(1 for c in ADS_COUNTERS if c in path.name)
                ord_in_name = sum(1 for c in ("hkd_9988", "hkd_0700") if c in path.name)
                assert ads_in_name + ord_in_name == 1, (
                    "file=%s field=filename claims both ADS and ordinary"
                    % path.name
                )
            text = path.read_text(encoding="utf-8")
            if path.suffix == ".jsonl":
                rows = [json.loads(line) for line in text.splitlines() if line.strip()]
            else:
                payload = json.loads(text)
                rows = payload if isinstance(payload, list) else [payload]
            for idx, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                for key in ("counter", "security_id", "instrument_id", "instrument_key"):
                    if key in row and row[key] is not None:
                        if key == "counter":
                            observed_counters.add(row[key])
                            assert row[key] in PINNED_S1_COUNTERS
                        if key == "security_id":
                            observed_sids.add(row[key])
                blob = json.dumps(row, sort_keys=True)
                if match:
                    assert not (
                        match.group(2) in ADS_COUNTERS and _row_claims_both_counters(blob)
                    ), "file=%s row=%s field=observation claims both" % (path.name, idx)
    assert observed_counters == PINNED_S1_COUNTERS, (
        "field=s1_counters observed=%s" % sorted(observed_counters)
    )
    assert PINNED_S1_SECURITY_IDS <= observed_sids or observed_sids <= PINNED_S1_SECURITY_IDS, (
        "field=s1_security_ids observed=%s" % sorted(observed_sids)
    )
    assert observed_sids == PINNED_S1_SECURITY_IDS, (
        "field=s1_security_ids observed=%s" % sorted(observed_sids)
    )


def test_dcp_06_authority_false():
    for name in PROFILES:
        profile = load_profile(name)
        authority = profile["authority"]
        assert set(authority) == set(AUTHORITY_FLAGS), (
            "profile=%s field=authority keys=%s" % (name, sorted(authority))
        )
        for flag in AUTHORITY_FLAGS:
            assert authority[flag] is False, (
                "profile=%s field=authority.%s got=%r" % (name, flag, authority[flag])
            )
        refuse_nonfalse_authority(authority)
        with pytest.raises(ValueError, match="must be literal False"):
            authority["signal_authority"] = True
        with pytest.raises(ValueError, match="must be literal False"):
            AuthorityMap(rank_authority=True)


@pytest.mark.parametrize("mutant", ["m1_swap_venues", "m2_drop_ratio_source"])
def test_dcp_07_mutants_are_caught(mutant, tmp_path):
    alibaba = copy.deepcopy(load_profile("alibaba"))
    if mutant == "m1_swap_venues":
        hk_venue = alibaba["counters"]["hkd_9988"]["venue_mic"]
        ads_venue = alibaba["counters"]["adr_baba"]["venue_mic"]
        alibaba["counters"]["hkd_9988"]["venue_mic"] = ads_venue
        alibaba["counters"]["adr_baba"]["venue_mic"] = hk_venue
        dest = tmp_path / "alibaba_m1.yml"
        dest.write_text(yaml.safe_dump(as_plain(alibaba), sort_keys=False), encoding="utf-8")
        loaded = yaml.safe_load(dest.read_text(encoding="utf-8"))
        with pytest.raises(AssertionError, match="venue_mic"):
            assert_alibaba_distinct(loaded, seed="m1")
        return
    alibaba["ads_ordinary_ratio"] = {
        "source": "tmp_path synthetic citation (not an owner ratio)",
    }
    check_ads_ratio_declared(alibaba, allow_xfail=False)
    dest = tmp_path / "alibaba_m2.yml"
    dest.write_text(yaml.safe_dump(as_plain(alibaba), sort_keys=False), encoding="utf-8")
    loaded = yaml.safe_load(dest.read_text(encoding="utf-8"))
    del loaded["ads_ordinary_ratio"]["source"]
    with pytest.raises(AssertionError, match="without a source"):
        check_ads_ratio_declared(loaded, allow_xfail=False)
