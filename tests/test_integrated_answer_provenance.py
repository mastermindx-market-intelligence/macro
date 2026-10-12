"""Freeze-list provenance for the integrated answer (flag stays default-off).

Pins census rows #4 common source, #6 membership basis, #8 circularity, and
#12 trace. Composition is driven through ``_compose_page`` with the same
monkeypatched readers ``tests/test_integrated_answer_v0.py`` uses. No test
sets ``MACRO_INTEGRATED_ANSWER_ENABLED``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import app.integrated_answer as integrated_answer
from engine.company_theme_exposure.views import build_bundle, write_generation
from engine.k3e_expectation_surface import QueryRefusal
from tests.test_company_theme_exposure import _company_tree, _crosswalk, _membership, _state

COMPOSED_AT = "2026-10-11T15:00:00Z"
ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "app" / "integrated_answer.py"

ROUTE_ALLOWLIST = frozenset({
    "/api/forensics/v1/financial/query",
    "k3e:inspect_expectation_surface+expectation_state:expectation_states",
    "/api/forensics/v1/attested-history/latest",
    "theme_context:read_context",
    "company_theme_exposure:published_generation",
})
EVENT_ROUTE = "/api/event-workspace/{ticker}"

BASKET_ABSENT_REASON = "not_read_in_v0:owner_not_recorded;direct_site_json_reads_forbidden(I-R2)"
MEMBERSHIP_FILE_ABSENT_REASON = "not_read_in_v0:owner_not_recorded;direct_site_json_reads_forbidden(I-R2)"

MEMBERSHIP_BASIS = {
    "value": "current_generation_not_point_in_time",
    "en": "Theme membership reflects the current published generation, not membership as of each past date.",
    "zh": "主题成分反映当前发布的版本，而非各历史日期当时的成分。",
}
STANCE = {"en": "Watch — don't chase", "zh": "观望，勿追"}
FOOTER = {"en": "Heads-up only, not a buy signal.", "zh": "仅为提示，非买入信号。"}
LEG_ORDER = (
    "financial_facts",
    "earnings_expectation",
    "capital_structure",
    "publication_seam",
    "event_workspace",
    "theme_tape",
    "company_theme_exposure",
    "basket_labels",
    "theme_membership_file",
)
BANNED_KEYS = frozenset({"count", "score", "agreement", "consensus", "confidence"})
SPAN_KEYS = frozenset({"span_id", "source_span", "spans"})

SHARED_HASH = "ab" * 32
OTHER_HASH = "cd" * 32


def _canonical(payload: object) -> str:
    return json.dumps(payload, sort_keys=True)


def _assert_no_banned_keys(node: object) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in BANNED_KEYS, key
            _assert_no_banned_keys(value)
    elif isinstance(node, list):
        for item in node:
            _assert_no_banned_keys(item)


def _span_keys(node: object, found: set[str] | None = None) -> set[str]:
    acc = found if found is not None else set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key in SPAN_KEYS:
                acc.add(key)
            _span_keys(value, acc)
    elif isinstance(node, list):
        for item in node:
            _span_keys(item, acc)
    return acc


def _content_digest(payload: object) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _leg(page: dict, leg_id: str) -> dict:
    for item in page["legs"]:
        if item["leg"] == leg_id:
            return item
    raise KeyError(leg_id)


def _silence(monkeypatch) -> None:
    """Every reader answers absent. Tests override the legs they care about."""
    monkeypatch.setattr(integrated_answer, "_utc_now", lambda: COMPOSED_AT)
    monkeypatch.setenv("MACRO_CTE_DIR", "/nonexistent/cte-provenance-test")
    monkeypatch.setattr(
        integrated_answer, "_k3e_source", lambda: (_ for _ in ()).throw(QueryRefusal("absent"))
    )
    monkeypatch.setattr(integrated_answer, "_expectation_chips", lambda _day: {})
    monkeypatch.setattr(
        integrated_answer, "_receipt_identity", lambda: (_ for _ in ()).throw(RuntimeError("off"))
    )
    monkeypatch.setattr(integrated_answer, "_event_result", lambda _t: {"available": False, "note": "n/a"})
    monkeypatch.setattr(integrated_answer, "_theme_context", lambda: None)
    monkeypatch.setattr(
        integrated_answer,
        "_leg_financial_facts",
        lambda _t, *_a, **_k: integrated_answer._leg_shell("financial_facts"),
    )


def _page(monkeypatch, ticker: str = "AAPL") -> dict:
    _silence(monkeypatch)
    return integrated_answer._compose_page(ticker)


def _install_financial(
    monkeypatch,
    *,
    owner_hash: str | None,
    as_of: str,
    generation_id: str | None = None,
) -> None:
    def _return(_ticker: str, *_a, **_k) -> dict:
        payload = {
            "request": {"entity_id": "ISS:US-XNAS-AAPL"},
            "query_hash": "q" * 64,
            "response_sha256": owner_hash,
            "replay_route": "/api/forensics/v1/financial/query",
        }
        leg = integrated_answer._leg_shell("financial_facts")
        leg["status"] = "ok"
        leg["payload"] = payload
        leg["ref"] = integrated_answer._make_ref(
            route="/api/forensics/v1/financial/query",
            as_of=as_of,
            payload=payload,
            generation_id=generation_id,
            owner_hash=owner_hash,
        )
        integrated_answer._apply_copy(leg)
        return leg

    monkeypatch.setattr(integrated_answer, "_leg_financial_facts", _return)


def _install_earnings(
    monkeypatch,
    *,
    query_identity: str | None,
    chip: dict | None,
    clock: str | None,
    inspection_extra: dict | None = None,
) -> dict:
    inspection = {
        "query_identity": query_identity,
        "latest_captured_snapshot": (
            {"derived_capture_available_at": clock} if clock else {}
        ),
        "source": {"source_revision": "0" * 40, "inputs": {}},
    }
    if inspection_extra:
        inspection.update(inspection_extra)

    def _inspect(*_a, **_k):
        return inspection

    monkeypatch.setattr(integrated_answer, "_k3e_source", lambda: ([], [], {"source_revision": "0" * 40, "inputs": {}}))
    monkeypatch.setattr("engine.k3e_expectation_surface.inspect_expectation_surface", _inspect)
    if chip is None:
        monkeypatch.setattr(integrated_answer, "_expectation_chips", lambda _day: {})
    else:
        monkeypatch.setattr(integrated_answer, "_expectation_chips", lambda _day, _chip=chip: {"AAPL": _chip})
    return inspection


def _install_publication(
    monkeypatch,
    *,
    query_hash: str | None,
    snapshot_id: str | None,
    published_at: str,
) -> None:
    monkeypatch.setattr(
        integrated_answer,
        "_receipt_identity",
        lambda: {
            "snapshot_id": snapshot_id,
            "base_snapshot_id": "ffqs_base",
            "query_hash": query_hash,
            "published_at": published_at,
        },
    )


def _install_event(
    monkeypatch,
    *,
    generation_id: str | None,
    generated_at: str,
    facts: list | None = None,
) -> dict:
    result = {
        "available": True,
        "ticker": "AAPL",
        "event_alias": None,
        "workspace": {
            "generated_at": generated_at,
            "generation_id": generation_id,
            "event_id": "evt-1",
            "fiscal_period": {},
            "lifecycle": {},
            "facts": facts or [],
            "claims": [],
            "guidance": [],
        },
    }
    monkeypatch.setattr(integrated_answer, "_event_result", lambda _t, _result=result: {**_result, "ticker": _t})
    return result


def _install_theme(monkeypatch, *, as_of: str, leadership: object, extra: dict | None = None) -> dict:
    ctx = {
        "schema": "theme_context.v1",
        "as_of": as_of,
        "region": "us",
        "display_only": True,
        "leadership": leadership,
    }
    if extra:
        ctx.update(extra)
    monkeypatch.setattr(integrated_answer, "_theme_context", lambda: ctx)
    return ctx


def _write_cte(tmp_path: Path, *, theme_as_of: str | None, run_as_of: str = "2026-10-11") -> tuple[Path, dict]:
    root = tmp_path / "cte"
    contexts, ci_manifest = _company_tree(tmp_path / "ci-src")
    state = None if theme_as_of is None else _state(as_of=theme_as_of)
    exposures, manifest = build_bundle(
        contexts,
        company_manifest=ci_manifest,
        membership=_membership(),
        crosswalk=_crosswalk(),
        theme_state=state,
        as_of=run_as_of,
    )
    write_generation(root, exposures, manifest)
    return root, manifest


def _assert_provenance_shape(page: dict, *, membership: bool) -> dict:
    assert [item["leg"] for item in page["legs"]] == list(LEG_ORDER)
    assert page["stance"] == STANCE
    assert page["footer"] == FOOTER
    provenance = page["provenance"]
    expected = {"schema", "shared_sources", "price_derived_legs"}
    if membership:
        expected.add("membership_basis")
    assert set(provenance) == expected
    assert provenance["schema"] == "integrated_answer.provenance.v0"
    assert isinstance(provenance["shared_sources"], list)
    assert isinstance(provenance["price_derived_legs"], list)
    assert provenance["price_derived_legs"] == sorted(provenance["price_derived_legs"])
    for group in provenance["shared_sources"]:
        assert set(group) == {"key_kind", "key", "legs"}
        assert group["key_kind"] in {"owner_hash", "generation_id"}
        assert isinstance(group["key"], str) and group["key"]
        assert group["legs"] == sorted(group["legs"])
        assert len(group["legs"]) >= 2
        assert len(group["legs"]) == len(set(group["legs"]))
    kinds_keys = [(group["key_kind"], group["key"]) for group in provenance["shared_sources"]]
    assert kinds_keys == sorted(kinds_keys)
    if membership:
        assert provenance["membership_basis"] == MEMBERSHIP_BASIS
    else:
        assert "membership_basis" not in provenance
    _assert_no_banned_keys(page)
    return provenance


def test_flag_default_is_unchanged() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    needle = 'os.environ.get("MACRO_INTEGRATED_ANSWER_ENABLED") != "1"'
    assert source.count(needle) == 1
    assert "MACRO_INTEGRATED_ANSWER_ENABLED" not in source.replace(needle, "")


def test_common_source_same_owner_hash_groups_once_and_stale_still_counts(monkeypatch) -> None:
    """Two surfaced legs sharing owner_hash emit one group; distinct keys do not.

    A leg the stale sweep marks stale stays in the group. Forgetting to sort
    legs fails because page order is financial then earnings, alpha order is
    the reverse.
    """
    _silence(monkeypatch)
    _install_financial(monkeypatch, owner_hash=SHARED_HASH, as_of="2020-01-01T00:00:00Z")
    _install_earnings(
        monkeypatch,
        query_identity=SHARED_HASH,
        chip={"pead_drift_20d": 0.1, "bad_news_absorption": False},
        clock="2026-10-10T00:00:00Z",
    )
    _install_publication(
        monkeypatch,
        query_hash=OTHER_HASH,
        snapshot_id="snap-unique-publication",
        published_at="2026-10-11T00:00:00Z",
    )
    _install_theme(monkeypatch, as_of="2026-10-11", leadership=[])
    page = integrated_answer._compose_page("AAPL")
    provenance = _assert_provenance_shape(page, membership=False)
    assert _leg(page, "financial_facts")["status"] == "stale"
    assert _leg(page, "earnings_expectation")["status"] == "ok"
    owner_groups = [group for group in provenance["shared_sources"] if group["key_kind"] == "owner_hash"]
    assert owner_groups == [{
        "key_kind": "owner_hash",
        "key": SHARED_HASH,
        "legs": ["earnings_expectation", "financial_facts"],
    }]
    assert all(group["key"] != OTHER_HASH for group in provenance["shared_sources"])
    grouped = {leg_id for group in provenance["shared_sources"] for leg_id in group["legs"]}
    assert "capital_structure" not in grouped
    assert "basket_labels" not in grouped
    assert "theme_membership_file" not in grouped
    assert "theme_tape" not in grouped


def test_common_source_distinct_and_null_hashes_do_not_group(monkeypatch) -> None:
    """Distinct hashes emit nothing. Null owner_hash and generation_id never group."""
    _silence(monkeypatch)
    _install_financial(monkeypatch, owner_hash="11" * 32, as_of="2026-10-09T00:00:00Z")
    _install_earnings(
        monkeypatch,
        query_identity=None,
        chip=None,
        clock="2026-10-10T00:00:00Z",
    )
    _install_publication(
        monkeypatch,
        query_hash="22" * 32,
        snapshot_id=None,
        published_at="2026-10-11T00:00:00Z",
    )
    _install_event(monkeypatch, generation_id=None, generated_at="2026-10-08T00:00:00Z")
    _install_theme(monkeypatch, as_of="2026-10-11", leadership=[])
    page = integrated_answer._compose_page("AAPL")
    provenance = _assert_provenance_shape(page, membership=False)
    assert provenance["shared_sources"] == []
    assert _leg(page, "theme_tape")["ref"]["owner_hash"] is None
    assert _leg(page, "event_workspace")["ref"]["owner_hash"] is None
    assert _leg(page, "earnings_expectation")["ref"]["owner_hash"] is None
    assert _leg(page, "theme_tape")["ref"]["generation_id"] is None
    assert _leg(page, "event_workspace")["ref"]["generation_id"] is None
    assert _leg(page, "publication_seam")["ref"]["generation_id"] is None


def test_common_source_generation_id_groups_independently_of_owner_hash(monkeypatch) -> None:
    """generation_id groups do not collapse into owner_hash groups, and the reverse.

    Same key string under both kinds stays two groups. Group order is
    (key_kind, key), so generation_id/zzz precedes owner_hash/aaa.
    """
    _silence(monkeypatch)
    _install_financial(monkeypatch, owner_hash="aaa", as_of="2026-10-09T00:00:00Z")
    _install_earnings(
        monkeypatch,
        query_identity="aaa",
        chip=None,
        clock="2026-10-10T00:00:00Z",
    )
    _install_publication(
        monkeypatch,
        query_hash="pub-only-hash",
        snapshot_id="zzz",
        published_at="2026-10-11T00:00:00Z",
    )
    _install_event(monkeypatch, generation_id="zzz", generated_at="2026-10-08T00:00:00Z")
    _install_theme(monkeypatch, as_of="2026-10-11", leadership=[])
    page = integrated_answer._compose_page("AAPL")
    provenance = _assert_provenance_shape(page, membership=False)
    assert provenance["shared_sources"] == [
        {
            "key_kind": "generation_id",
            "key": "zzz",
            "legs": ["event_workspace", "publication_seam"],
        },
        {
            "key_kind": "owner_hash",
            "key": "aaa",
            "legs": ["earnings_expectation", "financial_facts"],
        },
    ]
    assert _leg(page, "event_workspace")["ref"]["owner_hash"] is None
    assert _leg(page, "publication_seam")["ref"]["owner_hash"] == "pub-only-hash"
    assert _leg(page, "financial_facts")["ref"]["generation_id"] is None


def test_membership_basis_present_iff_cte_surfaced(monkeypatch, tmp_path) -> None:
    """membership_basis is on the page exactly when company_theme_exposure is ok or stale."""
    root, _manifest = _write_cte(tmp_path, theme_as_of="2026-10-11")
    _silence(monkeypatch)
    _install_theme(monkeypatch, as_of="2026-10-11", leadership=[])
    monkeypatch.setenv("MACRO_CTE_DIR", str(root))

    surfaced = integrated_answer._compose_page("AAPL")
    assert _leg(surfaced, "company_theme_exposure")["status"] == "ok"
    assert _assert_provenance_shape(surfaced, membership=True)["membership_basis"] == MEMBERSHIP_BASIS

    stale_root, _stale_manifest = _write_cte(tmp_path / "stale", theme_as_of=None)
    monkeypatch.setenv("MACRO_CTE_DIR", str(stale_root))
    stale = integrated_answer._compose_page("AAPL")
    assert _leg(stale, "company_theme_exposure")["status"] == "stale"
    assert _leg(stale, "company_theme_exposure")["degraded_reason"] == "no_owner_clock"
    assert _assert_provenance_shape(stale, membership=True)

    monkeypatch.setenv("MACRO_CTE_DIR", str(root))
    missing_ticker = integrated_answer._compose_page("MSFT")
    assert _leg(missing_ticker, "company_theme_exposure")["status"] == "absent"
    assert _leg(missing_ticker, "company_theme_exposure")["degraded_reason"] == "ticker_not_in_generation"
    assert _assert_provenance_shape(missing_ticker, membership=False)

    monkeypatch.setenv("MACRO_CTE_DIR", "/nonexistent/cte-provenance-test")
    absent = integrated_answer._compose_page("AAPL")
    assert _leg(absent, "company_theme_exposure")["status"] == "absent"
    assert "membership_basis" not in absent["provenance"]


def test_membership_cte_as_of_is_manifest_theme_state_clock(monkeypatch, tmp_path) -> None:
    """CTE ref.as_of is the published generation's theme-state clock.

    That clock is manifest source.theme_state.as_of, not composed_at, not
    manifest generated_at, and not another leg's as_of.
    """
    root, manifest = _write_cte(tmp_path, theme_as_of="2026-10-11", run_as_of="2026-10-11")
    marker = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    gid = marker["generation_id"]
    immutable = json.loads((root / "generations" / gid / "manifest.json").read_text(encoding="utf-8"))
    assert marker == immutable
    assert marker["source"]["theme_state"]["as_of"] == "2026-10-11"
    assert marker["generated_at"] != "2026-10-11T00:00:00Z"
    assert manifest["generation_id"] == gid

    _silence(monkeypatch)
    monkeypatch.setenv("MACRO_CTE_DIR", str(root))
    _install_financial(monkeypatch, owner_hash="33" * 32, as_of="2026-10-09T00:00:00Z")
    _install_earnings(monkeypatch, query_identity="44" * 32, chip=None, clock="2026-10-08T00:00:00Z")
    _install_publication(
        monkeypatch,
        query_hash="55" * 32,
        snapshot_id="snap-cte-clock",
        published_at="2026-10-10T00:00:00Z",
    )
    _install_event(monkeypatch, generation_id="evt-cte-clock", generated_at="2026-10-07T00:00:00Z")
    _install_theme(monkeypatch, as_of="2026-10-06", leadership={"state": "narrow"})
    page = integrated_answer._compose_page("AAPL")
    cte = _leg(page, "company_theme_exposure")
    assert cte["status"] == "ok"
    expected = integrated_answer._normalize_clock(marker["source"]["theme_state"]["as_of"])
    assert expected == "2026-10-11T00:00:00Z"
    assert cte["ref"]["as_of"] == expected
    assert cte["ref"]["as_of"] == integrated_answer._normalize_clock(cte["payload"]["theme_state"]["as_of"])
    assert cte["ref"]["generation_id"] == gid
    assert cte["ref"]["as_of"] != page["composed_at"]
    assert cte["ref"]["as_of"] != integrated_answer._normalize_clock(marker["generated_at"])
    for other in page["legs"]:
        if other["leg"] == "company_theme_exposure" or not other.get("ref"):
            continue
        assert other["ref"]["as_of"] != cte["ref"]["as_of"]


def test_membership_files_stay_absent_and_tape_has_no_membership(monkeypatch, tmp_path) -> None:
    """basket_labels and theme_membership_file stay unread. Tape does not absorb membership."""
    root, _manifest = _write_cte(tmp_path, theme_as_of="2026-10-11")
    _silence(monkeypatch)
    monkeypatch.setenv("MACRO_CTE_DIR", str(root))
    _install_theme(
        monkeypatch,
        as_of="2026-10-11",
        leadership={"state": "narrow"},
        extra={
            "members": ["AAPL"],
            "exposures": [{"theme_id": "canonical_theme", "basket_id": "mapped"}],
            "theme_membership": {"AAPL": ["mapped"]},
        },
    )
    page = integrated_answer._compose_page("AAPL")
    baskets = _leg(page, "basket_labels")
    membership_file = _leg(page, "theme_membership_file")
    assert baskets["status"] == "absent"
    assert baskets["degraded_reason"] == BASKET_ABSENT_REASON
    assert baskets["payload"] is None
    assert membership_file["status"] == "absent"
    assert membership_file["degraded_reason"] == MEMBERSHIP_FILE_ABSENT_REASON
    assert membership_file["payload"] is None

    tape = _leg(page, "theme_tape")
    assert set(tape["payload"]) == {"schema", "as_of", "region", "display_only", "leadership"}
    assert tape["payload"]["leadership"] == {"state": "narrow"}
    dumped = _canonical(tape["payload"])
    for leaked in ("members", "basket_id", "theme_membership", "canonical_theme", "mapped"):
        assert leaked not in dumped
    cte = _leg(page, "company_theme_exposure")
    assert cte["status"] == "ok"
    assert "canonical_theme" in _canonical(cte["payload"])
    assert "membership_basis" in page["provenance"]


def test_circularity_leadership_and_chip_do_not_move_stance_or_other_legs(monkeypatch) -> None:
    """Mutating tape leadership or chip price fields leaves stance, footer, and other payloads.

    Compared with json.dumps(sort_keys=True). The mutated leg's own payload must
    change, so a no-op mutation cannot pass.
    """
    _silence(monkeypatch)
    _install_financial(monkeypatch, owner_hash="66" * 32, as_of="2026-10-09T00:00:00Z")
    chip_holder = {
        "chip": {"pead_drift_20d": 0.25, "bad_news_absorption": False, "_benchmark": "SPY"},
    }
    _install_earnings(
        monkeypatch,
        query_identity="77" * 32,
        chip=chip_holder["chip"],
        clock="2026-10-10T00:00:00Z",
    )
    monkeypatch.setattr(
        integrated_answer,
        "_expectation_chips",
        lambda _day: {"AAPL": chip_holder["chip"]},
    )
    _install_publication(
        monkeypatch,
        query_hash="88" * 32,
        snapshot_id="snap-circ",
        published_at="2026-10-11T00:00:00Z",
    )
    _install_event(monkeypatch, generation_id="evt-circ", generated_at="2026-10-08T00:00:00Z")
    theme_holder = {
        "ctx": {
            "schema": "theme_context.v1",
            "as_of": "2026-10-11",
            "region": "us",
            "display_only": True,
            "leadership": {"state": "narrow", "stance_en": "Chase it", "stance_zh": "追"},
        }
    }
    monkeypatch.setattr(integrated_answer, "_theme_context", lambda: theme_holder["ctx"])

    first = integrated_answer._compose_page("AAPL")
    first_payloads = {item["leg"]: _canonical(item["payload"]) for item in first["legs"]}
    assert first["stance"] == STANCE
    assert first["footer"] == FOOTER
    assert "Chase it" not in _canonical(first["stance"])

    theme_holder["ctx"] = {
        **theme_holder["ctx"],
        "leadership": {"state": "broad", "stance_en": "Press it", "stance_zh": "推进", "days_in_state": 3},
    }
    after_tape = integrated_answer._compose_page("AAPL")
    assert after_tape["stance"] == STANCE
    assert after_tape["footer"] == FOOTER
    assert _canonical(after_tape["stance"]) == _canonical(first["stance"])
    assert _canonical(after_tape["footer"]) == _canonical(first["footer"])
    assert _canonical(_leg(after_tape, "theme_tape")["payload"]) != first_payloads["theme_tape"]
    for item in after_tape["legs"]:
        if item["leg"] == "theme_tape":
            continue
        assert _canonical(item["payload"]) == first_payloads[item["leg"]]

    chip_holder["chip"] = {"pead_drift_20d": -0.5, "bad_news_absorption": True, "_benchmark": "SPY"}
    after_chip = integrated_answer._compose_page("AAPL")
    tape_after = _canonical(_leg(after_tape, "theme_tape")["payload"])
    assert after_chip["stance"] == STANCE
    assert after_chip["footer"] == FOOTER
    assert _canonical(_leg(after_chip, "earnings_expectation")["payload"]) != _canonical(
        _leg(after_tape, "earnings_expectation")["payload"]
    )
    assert _leg(after_chip, "earnings_expectation")["payload"]["expectation_chip"]["pead_drift_20d"] == -0.5
    for item in after_chip["legs"]:
        if item["leg"] == "earnings_expectation":
            continue
        if item["leg"] == "theme_tape":
            assert _canonical(item["payload"]) == tape_after
            continue
        assert _canonical(item["payload"]) == first_payloads[item["leg"]]


def test_circularity_one_reader_raising_leaves_other_legs(monkeypatch) -> None:
    """A raising reader degrades only its own leg. Other payloads stay byte-identical."""
    _silence(monkeypatch)
    _install_financial(monkeypatch, owner_hash="66" * 32, as_of="2026-10-09T00:00:00Z")
    _install_earnings(
        monkeypatch,
        query_identity="77" * 32,
        chip={"pead_drift_20d": 0.25, "bad_news_absorption": False},
        clock="2026-10-10T00:00:00Z",
    )
    _install_publication(
        monkeypatch,
        query_hash="88" * 32,
        snapshot_id="snap-ind",
        published_at="2026-10-11T00:00:00Z",
    )
    _install_event(monkeypatch, generation_id="evt-ind", generated_at="2026-10-08T00:00:00Z")
    _install_theme(monkeypatch, as_of="2026-10-11", leadership={"state": "narrow"})
    baseline = integrated_answer._compose_page("AAPL")
    baseline_payloads = {item["leg"]: _canonical(item["payload"]) for item in baseline["legs"]}
    assert _leg(baseline, "theme_tape")["status"] == "ok"
    assert _leg(baseline, "earnings_expectation")["status"] == "ok"

    def _theme_down():
        raise RuntimeError("theme-down")

    monkeypatch.setattr(integrated_answer, "_theme_context", _theme_down)
    without_tape = integrated_answer._compose_page("AAPL")
    assert _leg(without_tape, "theme_tape")["status"] == "absent"
    assert _leg(without_tape, "theme_tape")["payload"] is None
    assert without_tape["stance"] == STANCE
    assert without_tape["footer"] == FOOTER
    for item in without_tape["legs"]:
        if item["leg"] == "theme_tape":
            continue
        assert _canonical(item["payload"]) == baseline_payloads[item["leg"]]
        assert item["status"] == _leg(baseline, item["leg"])["status"]

    monkeypatch.setattr(integrated_answer, "_theme_context", lambda: {
        "schema": "theme_context.v1",
        "as_of": "2026-10-11",
        "region": "us",
        "display_only": True,
        "leadership": {"state": "narrow"},
    })

    def _k3e_down():
        raise RuntimeError("k3e-down")

    def _chip_down(_day):
        raise RuntimeError("chip-down")

    monkeypatch.setattr(integrated_answer, "_k3e_source", _k3e_down)
    monkeypatch.setattr(integrated_answer, "_expectation_chips", _chip_down)
    without_earnings = integrated_answer._compose_page("AAPL")
    assert _leg(without_earnings, "earnings_expectation")["status"] == "absent"
    assert _leg(without_earnings, "earnings_expectation")["payload"] is None
    assert "k3e:" in _leg(without_earnings, "earnings_expectation")["degraded_reason"]
    assert without_earnings["stance"] == STANCE
    assert without_earnings["footer"] == FOOTER
    for item in without_earnings["legs"]:
        if item["leg"] == "earnings_expectation":
            continue
        assert _canonical(item["payload"]) == baseline_payloads[item["leg"]]
        assert item["status"] == _leg(baseline, item["leg"])["status"]


def test_trace_hash_route_allowlist_and_no_invented_spans(monkeypatch, tmp_path) -> None:
    """Surfaced refs hash the payload and use a route from the module allowlist.

    Owners that embed no per-fact span are stored unchanged. The financial
    envelope's source_span and the event workspace source_span locator are not
    copied into the page and are not replaced with an invented span id.
    """
    from engine.fundamental_forensics import query_service

    span = {"span_id": "fif-span-1", "start": 0, "end": 4}
    envelope = {
        "receipt": {
            "query_hash": "q" * 64,
            "nodes": [{
                "cell_id": "cell-1",
                "provenance": {
                    "recorded_at": "2026-10-09T00:00:00Z",
                    "accepted_at": "2026-10-08T00:00:00Z",
                    "selected_raw_fact": {"source_span": span},
                },
            }],
        }
    }
    result_body = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    result_sha = hashlib.sha256(result_body).hexdigest()

    def _fake_execute(*, body: bytes, provider: object):
        return query_service.FinancialQueryResult(
            body=result_body,
            sha256=result_sha,
            envelope=envelope,
        )

    root, _manifest = _write_cte(tmp_path, theme_as_of="2026-10-11")
    real_financial = integrated_answer._leg_financial_facts
    _silence(monkeypatch)
    monkeypatch.setattr(integrated_answer, "_leg_financial_facts", real_financial)
    monkeypatch.setattr(query_service, "execute_financial_query", _fake_execute)
    inspection = _install_earnings(
        monkeypatch,
        query_identity="ee" * 32,
        chip={"pead_drift_20d": 0.2, "bad_news_absorption": True, "_benchmark": "SPY"},
        clock="2026-10-10T00:00:00Z",
    )
    _install_publication(
        monkeypatch,
        query_hash="ff" * 32,
        snapshot_id="snap-trace",
        published_at="2026-10-11T00:00:00Z",
    )
    event_span = {
        "receipt_state": "byte_replayed",
        "rights_profile": "rp_public_primary_v1",
        "document_id": "ew-span-doc-1",
        "start_byte": 10,
        "end_byte": 20,
    }
    _install_event(
        monkeypatch,
        generation_id="evt-trace",
        generated_at="2026-10-08T00:00:00Z",
        facts=[{
            "fact_id": "fact_revenue_gaap",
            "metric": "revenue",
            "value": 1000.0,
            "unit": "USD",
            "source_span": event_span,
        }],
    )
    theme = _install_theme(monkeypatch, as_of="2026-10-11", leadership={"state": "narrow", "trailing_leader": {"id": "ai"}})
    monkeypatch.setenv("MACRO_CTE_DIR", str(root))

    page = integrated_answer._compose_page("AAPL")
    _assert_provenance_shape(page, membership=True)
    assert "fif-span-1" not in _canonical(page)
    assert "ew-span-doc-1" not in _canonical(page)
    assert _span_keys(page) == set()

    surfaced = [item for item in page["legs"] if item["status"] in {"ok", "stale"}]
    assert {item["leg"] for item in surfaced} >= {
        "financial_facts",
        "earnings_expectation",
        "publication_seam",
        "event_workspace",
        "theme_tape",
        "company_theme_exposure",
    }
    for item in page["legs"]:
        if item["status"] in {"ok", "stale"}:
            ref = item["ref"]
            assert ref["content_hash"] == integrated_answer._content_hash(item["payload"])
            assert ref["content_hash"] == _content_digest(item["payload"])
            route = ref["route"]
            assert route in ROUTE_ALLOWLIST or route == EVENT_ROUTE.format(ticker=page["ticker"])
        else:
            assert item["ref"] is None

    financial = _leg(page, "financial_facts")
    assert set(financial["payload"]) == {"request", "query_hash", "response_sha256", "replay_route"}
    assert financial["ref"]["owner_hash"] == result_sha

    earnings = _leg(page, "earnings_expectation")
    assert earnings["payload"]["capture_inspection"] == inspection
    assert earnings["payload"]["expectation_chip"]["pead_drift_20d"] == 0.2
    assert earnings["payload"]["expectation_chip"]["bad_news_absorption"] is True

    assert _leg(page, "theme_tape")["payload"]["leadership"] == theme["leadership"]

    gid = _leg(page, "company_theme_exposure")["ref"]["generation_id"]
    raw = json.loads(
        (root / "generations" / gid / "companies" / "AAPL.json").read_text(encoding="utf-8")
    )
    assert _leg(page, "company_theme_exposure")["payload"] == raw

    reported = _leg(page, "event_workspace")["payload"]["reported"]
    assert reported and reported[0]["receipt_state"] == event_span["receipt_state"]
    assert "document_id" not in reported[0]
    assert "start_byte" not in reported[0]
    assert "source_span" not in reported[0]


def test_price_derived_legs_follow_tape_and_chip(monkeypatch) -> None:
    """theme_tape joins whenever surfaced. earnings joins only when the chip is not None."""

    def _run(*, chip: str, theme: str, expect: list[str]) -> None:
        _silence(monkeypatch)
        if theme == "absent":
            monkeypatch.setattr(integrated_answer, "_theme_context", lambda: None)
        elif theme == "unparsed":
            _install_theme(monkeypatch, as_of="not-a-clock", leadership=[])
        else:
            _install_theme(monkeypatch, as_of="2026-10-11", leadership=[])
        if chip == "absent":
            monkeypatch.setattr(
                integrated_answer, "_k3e_source", lambda: (_ for _ in ()).throw(QueryRefusal("absent"))
            )
            monkeypatch.setattr(integrated_answer, "_expectation_chips", lambda _day: {})
        elif chip == "missing":
            _install_earnings(monkeypatch, query_identity="ab" * 32, chip=None, clock="2026-10-10T00:00:00Z")
        else:
            clock = None if chip == "stale" else "2026-10-10T00:00:00Z"
            payload: dict = {} if chip == "empty" else {"pead_drift_20d": 0.1, "bad_news_absorption": False}
            if chip == "stale":
                payload = {"pead_drift_20d": 1.0, "bad_news_absorption": True}
            _install_earnings(monkeypatch, query_identity=None, chip=payload, clock=clock)
        page = integrated_answer._compose_page("AAPL")
        assert page["provenance"]["price_derived_legs"] == expect

    _run(chip="present", theme="ok", expect=["earnings_expectation", "theme_tape"])
    _run(chip="missing", theme="ok", expect=["theme_tape"])
    _run(chip="present", theme="absent", expect=["earnings_expectation"])
    _run(chip="absent", theme="absent", expect=[])
    _run(chip="stale", theme="absent", expect=["earnings_expectation"])
    _run(chip="absent", theme="unparsed", expect=["theme_tape"])
    _run(chip="empty", theme="ok", expect=["earnings_expectation", "theme_tape"])

    _silence(monkeypatch)
    _install_theme(monkeypatch, as_of="not-a-clock", leadership=[])
    _install_earnings(
        monkeypatch,
        query_identity=None,
        chip={"pead_drift_20d": 1.0, "bad_news_absorption": True},
        clock=None,
    )
    both_stale = integrated_answer._compose_page("AAPL")
    assert _leg(both_stale, "theme_tape")["status"] == "stale"
    assert _leg(both_stale, "earnings_expectation")["status"] == "stale"
    assert both_stale["provenance"]["price_derived_legs"] == ["earnings_expectation", "theme_tape"]


@pytest.mark.parametrize(
    "banned",
    ["count", "score", "agreement", "consensus", "confidence"],
)
def test_banned_agreement_keys_cover_the_names(banned: str) -> None:
    """The walker itself fails when a banned key is introduced anywhere in the tree."""
    with pytest.raises(AssertionError):
        _assert_no_banned_keys({"provenance": {banned: 1}})
