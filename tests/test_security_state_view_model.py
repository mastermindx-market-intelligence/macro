"""Security State view model — `build_security_state()` against the contract.

The contract suite proves the compiler emits the right payload. This suite
proves the DOSSIER reads that payload: every assertion here names a field the
compiled `security_state.v1` object actually carries, so a projection that
quietly reads a field the contract never emits fails here rather than shipping
an empty panel.

Four things are pinned, all of them regressions this file exists to prevent:

1. Integration — a really compiled object, straight through the projection,
   reaching the view model with its real recipe/block ids, its real compilation
   denominator, its coverage counts, its R1..R9 receipts and its state leg.
2. The State axis renders from `legs.state`, never from the blob's own ladder.
3. `last_good` is read by the keys the contract writes.
4. An `ESTIMATED_WINDOW` observable renders as a window that says it is not an
   announced date.
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.build_ticker_pages import build_security_state  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})


class _HtmlNode:
    """One element in a stdlib-parsed tree (class tokens + descendant text)."""

    __slots__ = ("tag", "classes", "children", "text_parts")

    def __init__(self, tag: str, classes: frozenset[str]) -> None:
        self.tag = tag
        self.classes = classes
        self.children: list[_HtmlNode] = []
        self.text_parts: list[str] = []

    def get_text(self) -> str:
        bits = list(self.text_parts)
        for child in self.children:
            bits.append(child.get_text())
        return "".join(bits)

    def find_class(self, name: str) -> _HtmlNode | None:
        for child in self.children:
            if name in child.classes:
                return child
            found = child.find_class(name)
            if found is not None:
                return found
        return None

    def find_all_class(self, name: str) -> list[_HtmlNode]:
        out: list[_HtmlNode] = []
        if name in self.classes:
            out.append(self)
        for child in self.children:
            out.extend(child.find_all_class(name))
        return out


class _ClassTreeParser(HTMLParser):
    """Minimal class-aware tree. Sealed CI has no bs4; do not import it."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _HtmlNode("#root", frozenset())
        self._stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = frozenset((dict(attrs).get("class") or "").split())
        node = _HtmlNode(tag, classes)
        self._stack[-1].children.append(node)
        if tag not in _VOID_TAGS:
            self._stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                del self._stack[i:]
                return

    def handle_data(self, data: str) -> None:
        self._stack[-1].text_parts.append(data)


def _parse_class_tree(html: str) -> _HtmlNode:
    parser = _ClassTreeParser()
    parser.feed(html)
    parser.close()
    return parser.root


def _axis(view: dict, key: str) -> dict:
    for a in view["axes"]:
        if a["key"] == key:
            return a
    raise AssertionError(f"axis {key!r} missing from the view model")


def _k1_bundle(engine, subject, workspace, disposition: str, manifest_sha256: str | None) -> dict:
    from lib.evidence_foundation import compile_recipe

    recipe = engine._build_k1_recipe(subject=subject)
    empty = compile_recipe(recipe, blocks=[], references={})
    found = None
    if disposition == "found" and isinstance(workspace, dict):
        lifecycle = workspace.get("lifecycle") or {}
        reference = engine._build_k1_reference(
            subject=subject,
            generation_id=workspace["generation_id"], event_id=workspace["event_id"],
            manifest_sha256=manifest_sha256,
            source_available_at=lifecycle.get("source_available_at"),
            observed_at=lifecycle.get("observed_at"),
            generated_at=workspace.get("generated_at"),
        )
        block = engine._build_k1_block([reference], subject=subject)
        found = {
            "reference_id": reference["reference_id"],
            "block_id": block["evidence_block_id"],
            "compilation": compile_recipe(
                recipe, blocks=[block], references={reference["reference_id"]: reference},
            ),
        }
    return {
        "subject_cik": subject.issuer_cik,
        "recipe_id": recipe["recipe_id"],
        "empty_compilation": empty,
        "found": found,
    }


def _render_section(view: dict, lang: str = "en") -> str:
    """Render the dossier template far enough to read the section's own text.

    The section is server-rendered, so "does the value reach the page" is a
    question about HTML, not about a dict. Undefined page context is chainable
    so the rest of the dossier simply does not render.
    """
    import jinja2

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(REPO / "templates")),
        undefined=jinja2.ChainableUndefined,
    )
    html = env.get_template("ticker.html.j2").render(
        security_state=view, ticker="AAPL", name="Apple Inc.",
    )
    assert 'id="security-state"' in html, "the section did not render at all"
    if lang == "en":
        # Drop the Chinese twin of every bilingual pair so an assertion cannot
        # pass on the other language's copy.
        html = re.sub(r'<span class="l-zh">.*?</span>', "", html, flags=re.S)
    else:
        html = re.sub(r'<span class="l-en">.*?</span>', "", html, flags=re.S)
    return html


# ---------------------------------------------------------------------------
# 1 · integration — a really compiled object through the real projection
# ---------------------------------------------------------------------------

# Hand-carried golden inputs. Deliberately a copy rather than an import of the
# contract suite's fixture files: this suite must fail when the CONSUMER drifts
# from the contract, and a shared fixture that moves with the producer would
# hide exactly that.
GOLDEN_NOW = "2026-08-23T12:00:00Z"

GOLDEN_SECURITY_MASTER_ROW = {
    "security_id": "SEC:US-XNAS-AAPL",
    "issuer_id": "ISS:US-XNAS-AAPL",
    "issuer_state": "RESOLVED",
    "issuer_cik": "0000320193",
    "listing_key": "US-XNAS-AAPL",
    "country": "US",
    "mic": "XNAS",
    "inception_code": "AAPL",
    "security_state": None,
    "superseded_by": None,
}

GOLDEN_ISSUER_MASTER_ROWS = [{
    "issuer_id": "ISS:US-XNAS-AAPL",
    "cik": "0000320193",
    "legal_name": "Apple Inc.",
    "n_securities": 1,
    "status": "active",
    "era": "issuer_semantic_correction_v1",
}]

GOLDEN_WORKSPACE = {
    "schema": "event_workspace.v1",
    "event_id": "evt_cik0000320193_2026q3_results",
    "generation_id": "6d56c84a3ac23b8954e59ee7",
    "issuer": {
        "company_id": "cik:0000320193",
        "display_name": "Apple Inc.",
        "listings": [{
            "is_primary": True, "mic": "XNAS", "security_id": "xnas:AAPL",
            "share_class": "common", "ticker": "AAPL", "trading_currency": "USD",
            "valid_from": "1970-01-01", "valid_to": None,
        }],
    },
    "fiscal_period": {"calendar_end": "2026-06-27", "quarter": 3, "year": 2026},
    "lifecycle": {
        "observed_at": "2026-07-30T20:30:28Z",
        "source_available_at": "2026-07-30T20:30:28Z",
        "state": "complete",
    },
    "generated_at": "2026-07-30T20:30:28Z",
    "authority": "context_only",
    "prophet_flags": {"earnings_flagged": False},
    "claim_citations_pending": False,
    "qa_exchanges": [],
    "warnings": [
        "collector_filing_unjoinable", "consensus_unlicensed",
        "questions_count_unstructured", "reaction_not_joined",
        "slides_absent", "wire_record_not_found",
    ],
    "completeness": {"filing": {"filing_key": {
        "accession": "0000320193-26-000018", "cik": "0000320193"}}},
    "facts": [{"k": 1}, {"k": 2}, {"k": 3}],
    "deltas": [{"k": 1}],
    "guidance": [{"k": 1}, {"k": 2}],
    "claims": [], "sources": [], "aliases": {},
}

GOLDEN_BLOB = {
    "ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology",
    "asof": "2026-08-23", "history_days": 500,
    "tech": {"chg_1d": 0.5, "price": 230.1},
    "ladder": {"state": "watch", "dir": "up",
               "entry": {"text": "Watching for a pullback entry.",
                         "text_zh": "等待回调买点。"}},
    "entry_signal": {"score": 1, "state": "watch"},
    "conviction": {"cautions": [
        "Valuation is rich relative to trailing five-year multiples."]},
    "alerts": {"pinned": None, "timeline": [], "n_recent": 2, "n_total": 10},
    "view": {}, "basket_alloc": {}, "alpha": {"alpha": 0.1},
}


def _compile_golden() -> dict:
    """Compile the golden AAPL object with the real compiler."""
    engine = pytest.importorskip("engine.security_state")
    subject = engine.SecurityStateSubject(
        security_id="SEC:US-XNAS-AAPL",
        issuer_id="ISS:US-XNAS-AAPL",
        listing_key="US-XNAS-AAPL",
        ticker_display="AAPL",
        issuer_cik="0000320193",
        owner_evidence=(
            ("decision_date", "2026-09-04"),
            ("alias_reader", "VendorAliasTable.resolve(store)"),
            ("issuer_reader", "IssuerMaster.issuer_of_security"),
            ("cik_reader", "IssuerMaster.cik_of_issuer"),
        ),
    )
    return engine.compile_security_state(
        validator=engine.build_security_state_validator(
            json.loads(engine.SCHEMA_PATH.read_text(encoding="utf-8"))
        ),
        subject=subject,
        k1_bundle=_k1_bundle(
            engine, subject, GOLDEN_WORKSPACE, "found",
            "c3b9495028c07e6bf1eb385f520f0b3c57064b84ea430540ba9a0808cd2d14db",
        ),
        now=GOLDEN_NOW,
        security_master_row=dict(GOLDEN_SECURITY_MASTER_ROW),
        issuer_master_rows=[dict(r) for r in GOLDEN_ISSUER_MASTER_ROWS],
        issuer_security_ids=["SEC:US-XNAS-AAPL"],
        issuer_migration_matches=[],
        security_migration_matches=[],
        workspace=GOLDEN_WORKSPACE,
        workspace_disposition="found",
        blob=GOLDEN_BLOB,
        manifest_sha256="c3b9495028c07e6bf1eb385f520f0b3c57064b84ea430540ba9a0808cd2d14db",
    )


def test_compiled_msft_object_reaches_the_existing_view_model() -> None:
    engine = pytest.importorskip("engine.security_state")
    subject = engine.SecurityStateSubject(
        security_id="SEC:US-XNAS-MSFT",
        issuer_id="ISS:US-XNAS-MSFT",
        listing_key="US-XNAS-MSFT",
        ticker_display="MSFT",
        issuer_cik="0000789019",
        owner_evidence=(
            ("decision_date", "2026-09-04"),
            ("alias_reader", "VendorAliasTable.resolve(store)"),
            ("issuer_reader", "IssuerMaster.issuer_of_security"),
            ("cik_reader", "IssuerMaster.cik_of_issuer"),
        ),
    )
    row = {
        "security_id": subject.security_id, "issuer_id": subject.issuer_id,
        "issuer_state": "RESOLVED", "issuer_cik": subject.issuer_cik,
        "listing_key": subject.listing_key, "country": "US", "mic": "XNAS",
        "inception_code": "MSFT", "security_state": None, "superseded_by": None,
    }
    blob = {**GOLDEN_BLOB, "ticker": "MSFT", "name": "Microsoft Corp."}
    compiled = engine.compile_security_state(
        subject=subject,
        validator=engine.build_security_state_validator(
            json.loads(engine.SCHEMA_PATH.read_text(encoding="utf-8"))
        ),
        now=GOLDEN_NOW, security_master_row=row,
        k1_bundle=_k1_bundle(engine, subject, None, "not_published", None),
        issuer_master_rows=[{
            "issuer_id": subject.issuer_id, "cik": subject.issuer_cik,
            "status": "active",
        }],
        issuer_security_ids=[subject.security_id], issuer_migration_matches=[],
        security_migration_matches=[], workspace=None,
        workspace_disposition="not_published", blob=blob, manifest_sha256=None,
    )
    view = build_security_state({"security_state": compiled})
    assert view is not None
    assert view["ticker_display"] == "MSFT"
    assert view["security_id"] == "SEC:US-XNAS-MSFT"
    assert view["issuer_id"] == "ISS:US-XNAS-MSFT"
    assert view["listing_key"] == "US-XNAS-MSFT"


def test_compiled_golden_object_reaches_the_view_model() -> None:
    """A really compiled object keeps its receipts all the way to the page."""
    compiled = _compile_golden()
    if "state" not in (compiled.get("legs") or {}):
        pytest.skip("compiler does not yet emit legs.state (producer lane in flight)")

    view = build_security_state({"security_state": compiled})
    assert view is not None

    legs = compiled["legs"]
    ev_leg = legs["evidence"]

    # ── evidence: the real recipe, the real blocks, the real denominator ──
    assert view["evidence"]["recipe_id"] == ev_leg["recipe_id"]
    assert view["evidence"]["recipe_id"], "recipe_id must not be blank"
    for ref in ev_leg["evidence_block_refs"]:
        assert ref in view["evidence"]["refs"]

    comp = ev_leg["compilation"]
    assert view["evidence"]["compile_state"] is not None
    assert view["evidence"]["compile_state"]["code"] == str(comp["state"]).upper()
    rendered_counts = {r["v"] for r in view["evidence"]["counts"]}
    for key, value in comp["denominator"].items():
        assert any(r["v"] == value for r in view["evidence"]["counts"]), (
            f"denominator.{key}={value} never reached the view model")
    assert rendered_counts, "denominator rendered empty"

    # ── coverage: available and nonblocking are separate answers ──
    cov = compiled["coverage"]
    vc = view["coverage"]
    assert vc["req_total"] == cov["required_legs_total"]
    assert vc["req_avail"] == cov["required_legs_available"]
    assert vc["req_nonblock"] == cov["required_legs_nonblocking"]
    assert vc["opt_total"] == cov["optional_legs_total"]
    assert vc["opt_avail"] == cov["optional_legs_available"]
    assert vc["opt_nonblock"] == cov["optional_legs_nonblocking"]

    # ── identity: R1..R9 with the fields the contract emits ──
    contract_legs = compiled["identity_proof"]["legs"]
    assert contract_legs, "the golden object carries no identity legs"
    assert len(view["identity"]["legs"]) == len(contract_legs)
    from scripts.build_ticker_pages import (
        _SS_ARTIFACT, _SS_LEG_DESC, _SS_LEG_HOUSE_BY_DESC, _SS_READER,
    )

    for src, out in zip(contract_legs, view["identity"]["legs"]):
        assert out["check"] == src["check"]
        # h5: coded legs use (check, code); code-less legs use
        # (check, engine description). Unmapped legs render empty strings,
        # never engine text and never 暂不可用.
        code = out["code"] or ""
        desc_raw = src["description"] or ""
        if code:
            desc_house = _SS_LEG_DESC.get((out["check"], code))
            art_house = _SS_ARTIFACT.get((out["check"], code))
            rdr_house = _SS_READER.get((out["check"], code))
        else:
            triple = _SS_LEG_HOUSE_BY_DESC.get((out["check"], desc_raw)) or {}
            desc_house = _SS_LEG_DESC.get((out["check"], "")) or triple.get("desc")
            art_house = triple.get("artifact")
            rdr_house = triple.get("reader")
        if desc_house:
            assert out["desc_en"] == desc_house["en"]
            assert out["desc_zh"] == desc_house["zh"]
        else:
            assert out["desc_en"] == ""
            assert out["desc_zh"] == ""
        if art_house:
            assert out["artifact_en"] == art_house["en"]
            assert out["artifact_zh"] == art_house["zh"]
        else:
            assert out["artifact_en"] == ""
            assert out["artifact_zh"] == ""
        if rdr_house:
            assert out["reader_en"] == rdr_house["en"]
            assert out["reader_zh"] == rdr_house["zh"]
        else:
            assert out["reader_en"] == ""
            assert out["reader_zh"] == ""
        assert out["result"] == str(src["result"]).lower()
        assert len(out["reads"]) == len(src["values_read"])
        for pair, row in zip(src["values_read"], out["reads"]):
            assert row["k"] == pair["field"]
    checks = [lg["check"] for lg in view["identity"]["legs"]]
    assert checks[0] == "R1" and "R9" in checks

    # ── state: the contract's own axis ──
    assert _axis(view, "state")["ladder_state"] == legs["state"]["ladder_state"]


# ---------------------------------------------------------------------------
# shared fixture — a compiled object in the amended shapes
# ---------------------------------------------------------------------------

def _contract(**over) -> dict:
    ss = {
        "schema": "security_state.v1",
        "version": "1.0.0",
        "security_id": "SEC:US-XNAS-AAPL",
        "issuer_id": "ISS:US-XNAS-AAPL",
        "listing_key": "US-XNAS-AAPL",
        "ticker_display": "AAPL",
        "generated_at": "2026-08-23T12:00:00Z",
        "content_sha256": "cfecf1282d8c59f8d265529e040f9d04ed7e31caaa3b23d8ab22c88cd74c0138",
        "as_of": {
            "market_at": "2026-08-23",
            "source_frontier_at": "2026-07-30T20:30:28Z",
            "state_compiled_at": "2026-08-23T12:00:00Z",
        },
        "identity_proof": {
            "state": "PROVEN",
            "method": "owner_backed_chain.v1",
            "legs": [{
                "check": "R1",
                "description": "security_master row exists, security_state/superseded_by both null",
                "artifact": "data/reference/security_master.parquet",
                "reader": "scripts/security_state_producer.py::_read_security_state_identity_rows",
                "values_read": [
                    {"field": "row_present", "value": True},
                    {"field": "security_state", "value": None},
                ],
                "result": "pass",
                "code": None,
            }],
            "equalities": [], "refusals": [], "disclosures": [],
        },
        "coverage": {
            "overall_state": "PARTIAL",
            "required_legs_total": 2, "required_legs_available": 2,
            "required_legs_nonblocking": 2,
            "optional_legs_total": 5, "optional_legs_available": 3,
            "optional_legs_nonblocking": 5,
            "missing_legs": [], "stale_legs": [],
            "rights_blocked_legs": [], "conflicted_legs": [],
        },
        "dominant_degradation": "PARTIAL",
        "legs": {
            "state": {
                "deterministic_state_refs": ["ladder.state", "ladder.dir", "tech.chg_1d"],
                "ladder_state": "watch",
                "ladder_direction": "up",
                "values_read": [{"field": "tech.chg_1d", "value": 0.5}],
                "summary": {"en": "Ladder state: watch (up).",
                            "zh": "阶梯状态：watch（上行）。"},
                "coverage_state": "AVAILABLE",
            },
            "change": {
                "event_refs": ["evt_cik0000320193_2026q3_results"],
                "generation_id": "6d56c84a3ac23b8954e59ee7",
                "observed_at": "2026-07-30T20:30:28Z",
                "summary": {"en": "Q3 2026 results workspace is complete.",
                            "zh": "Q3 2026 财报工作区状态为完整。"},
                "correction_state": "none",
                "coverage_state": "AVAILABLE",
                "workspace_warnings": ["reaction_not_joined"],
            },
            "opportunity_context": {
                "prophet": {"ref": None, "state": "UNAVAILABLE",
                            "reason": "PROPHET_OWNER_OUTPUT_ABSENT"},
                "entry": {"state": "AVAILABLE", "available": True, "null_reason": None},
                "market_incorporation": {"ref": None, "state": "NOT_COVERED"},
                "dislocation": {"ref": None, "state": "NOT_COVERED"},
                "coverage_state": "AVAILABLE",
            },
            "risk": {
                "risk_refs": ["alerts_n_total:10"],
                "failed_gates": [],
                "strongest_unresolved_fact": {
                    "state": "workspace_warning", "leg": "change",
                    "code": "reaction_not_joined",
                    "en": "Market reaction data has not been joined to this release yet.",
                    "zh": "市场反应数据尚未与此次发布关联。",
                },
                "coverage_state": "AVAILABLE",
            },
            "catalyst": {
                "next_observables": [{
                    "kind": "ESTIMATED_WINDOW",
                    "window_start": "2026-09-19",
                    "window_end": "2026-10-03",
                    "authoritative": False,
                    "basis": "fiscal_period.calendar_end + ~1 fiscal quarter (91 days), "
                             "deterministic calendar arithmetic",
                }],
                "deadlines": [],
                "coverage_state": "PARTIAL",
            },
            "personal_impact": {
                "state": "NO_USER_CONTEXT",
                "user_exposure_overlay_ref": None,
                "coverage_state": "NOT_APPLICABLE",
            },
            "evidence": {
                "evidence_block_refs": ["ebl_5b86ed829a65b95f6f82bc5a856f8f74"],
                "recipe_id": "erp_5687f42d2acac8826110a5952a4d0ba0",
                "compilation": {
                    "schema": "evidence_foundation.recipe_compilation_receipt.v1",
                    "recipe_id": "erp_5687f42d2acac8826110a5952a4d0ba0",
                    "state": "partial",
                    "dominant_degradation": "unknown",
                    "block_ids": ["ebl_5b86ed829a65b95f6f82bc5a856f8f74"],
                    "denominator": {"total": 1, "included": 1, "excluded": 0,
                                    "missing": 0, "stale": 0, "rights_blocked": 0,
                                    "fallback": 0, "identity_unresolved": 0},
                },
                "conflicts": [],
                "coverage_state": "PARTIAL",
            },
        },
        "last_good": None,
    }
    ss.update(over)
    return ss


# ---------------------------------------------------------------------------
# 2 · the State axis renders from the contract, not from the blob
# ---------------------------------------------------------------------------

def test_state_axis_renders_the_contract_not_the_blob_ladder() -> None:
    """The blob's own ladder is loudly wrong; the card must not repeat it."""
    contract = _contract()
    contract["legs"]["state"]["ladder_state"] = "downtrend"
    contract["legs"]["state"]["ladder_direction"] = "down"
    contract["legs"]["state"]["summary"] = {
        "en": "Ladder state: downtrend (down).", "zh": "阶梯状态：downtrend（下行）。"}

    blob = {
        # The blob disagrees on purpose — this is the fallback the section used
        # to render before the contract carried a state leg.
        "ladder": {"state": "uptrend", "dir": "up"},
        "security_state": contract,
    }
    view = build_security_state(blob)
    assert view is not None

    state = _axis(view, "state")
    assert state["ladder_state"] == "downtrend"
    assert state["ladder_direction"] == "down"
    assert {"k": "ladder_state", "v": "downtrend"} in state["fields"]
    assert state["headline"]["en"] == "Below its long-term trend"

    html = _render_section(view)
    # The contract's reading ("Below its long-term trend") is on the page and
    # the blob's ("In an uptrend") is nowhere in the section.
    assert "Below its long-term trend" in html
    assert "In an uptrend" not in html
    assert "pointing down" in html
    assert "pointing up" not in html


def _card_region(html: str) -> str:
    """Just the always-visible grid — the dialogs live outside the section."""
    start = html.index('id="security-state"')
    return html[start:html.index("</section>", start)]


def test_the_state_card_never_prints_the_raw_state_name() -> None:
    """The contract's summary is a receipt; the glance tier gets plain words.

    `legs.state.summary` restates the fields it read ("Ladder state: watch
    (up).") — an internal state name, and an English one inside the Chinese
    page. It is quoted verbatim in the drilldown and never on the card.
    """
    view = build_security_state({"security_state": _contract()})
    card = _card_region(_render_section(view))
    assert "Worth monitoring" in card
    assert "Ladder state:" not in card

    zh_card = _card_region(_render_section(view, lang="zh"))
    assert "值得关注" in zh_card
    assert "阶梯状态" not in zh_card

    # …and it is still there, unchanged, where receipts belong.
    assert "Ladder state: watch (up)." in _render_section(view)


def test_state_axis_without_a_state_leg_claims_nothing() -> None:
    """No state leg is 'not available', never a borrowed reading."""
    contract = _contract()
    contract["legs"].pop("state")
    view = build_security_state({"ladder": {"state": "uptrend"},
                                 "security_state": contract})
    state = _axis(view, "state")
    assert state["cov"] == "UNAVAILABLE"
    assert not state.get("ladder_state")
    assert "In an uptrend" not in _render_section(view)


# ---------------------------------------------------------------------------
# 3 · last_good is read by the keys the contract writes
# ---------------------------------------------------------------------------

def test_last_good_renders_from_the_contract_keys() -> None:
    view = build_security_state({"security_state": _contract(last_good={
        "generated_at": "2026-08-22T12:00:00Z",
        "content_sha256": "aa11bb22cc33dd44ee55ff66aa77bb88cc99dd00ee11ff22aa33bb44cc55dd66",
        "dominant_degradation": "STALE",
        "reason": "current cycle could not reach the owner",
    })})
    lg = view["last_good"]
    assert lg["ok"] is True
    assert lg["at"] == "2026-08-22 12:00Z"
    assert lg["sha"].startswith("aa11bb22")
    assert lg["deg"]["code"] == "STALE"
    assert lg["reason"]["en"] == "current cycle could not reach the owner"

    html = _render_section(view)
    assert "Last complete read" in html
    assert "2026-08-22 12:00Z" in html
    assert "aa11bb22" in html


def test_last_good_is_never_cited_for_a_read_that_failed() -> None:
    """A recorded fallback whose own compile failed is not a fallback."""
    view = build_security_state({"security_state": _contract(
        dominant_degradation="COMPILER_FAILURE",
        last_good={
            "generated_at": "2026-08-22T12:00:00Z",
            "content_sha256": "deadbeef" * 8,
            "dominant_degradation": "COMPILER_FAILURE",
            "reason": "compiler_failure",
        },
    )})
    assert view["last_good"]["ok"] is False
    html = _render_section(view)
    assert "This read could not be built" in html
    assert "Last complete read" not in html
    assert "2026-08-22 12:00Z" not in html


def test_last_good_absent_renders_no_banner() -> None:
    view = build_security_state({"security_state": _contract()})
    assert view["last_good"]["ok"] is False
    assert "Last complete read" not in _render_section(view)


# ---------------------------------------------------------------------------
# 4 · an estimated window never reads as an announced date
# ---------------------------------------------------------------------------

def test_estimated_window_renders_as_a_window_that_says_it_is_estimated() -> None:
    view = build_security_state({"security_state": _contract()})
    obs = _axis(view, "catalyst")["observables"]
    assert len(obs) == 1
    row = obs[0]
    assert row["est"] is True
    assert row["when"] == "2026-09-19 – 2026-10-03"
    assert row["basis"].startswith("fiscal_period.calendar_end")

    html = _render_section(view)
    assert "2026-09-19 – 2026-10-03" in html
    assert "Estimated window — not an announced date" in html
    # Neither end of the window may appear as a lone dated claim.
    assert not re.search(r"(?<!\d)2026-09-19(?!\s*–)", html)

    zh = _render_section(view, lang="zh")
    assert "预计窗口 — 并非官方公布日期" in zh


def test_an_authoritative_observable_carries_no_estimate_qualifier() -> None:
    contract = _contract()
    contract["legs"]["catalyst"]["next_observables"] = [{
        "kind": "CONFIRMED_EARNINGS",
        "date": "2026-10-29",
        "authoritative": True,
        "basis": "issuer announcement",
    }]
    view = build_security_state({"security_state": contract})
    row = _axis(view, "catalyst")["observables"][0]
    assert row["est"] is False
    assert row["when"] == "2026-10-29"
    html = _render_section(view)
    assert "Confirmed results date" in html
    assert "not an announced date" not in html


# ---------------------------------------------------------------------------
# receipts that used to render blank
# ---------------------------------------------------------------------------

def test_evidence_ids_and_denominator_reach_the_page() -> None:
    view = build_security_state({"security_state": _contract()})
    html = _render_section(view)
    assert "erp_5687f42d2acac8826110a5952a4d0ba0" in html
    assert "ebl_5b86ed829a65b95f6f82bc5a856f8f74" in html
    assert "Partly compiled" in html
    assert "Records asked for" in html
    assert "Records not tied to this listing" in html


def test_coverage_counts_separate_available_from_nonblocking() -> None:
    view = build_security_state({"security_state": _contract()})
    html = _render_section(view)
    assert "Required reads, current" in html
    assert "Optional reads, not in the way" in html
    assert "3 / 5" in html   # optional available
    assert "5 / 5" in html   # optional nonblocking


def test_not_applicable_leg_is_not_displayed_as_available() -> None:
    view = build_security_state({"security_state": _contract()})
    personal = view["personal_impact"]
    assert personal["cov"] == "NOT_APPLICABLE"
    assert personal["ok"] is False
    assert personal["tone"] == "off"


def test_identity_receipts_render_their_actual_fields() -> None:
    from scripts.build_ticker_pages import _SS_LEG_DESC, _SS_LEG_HOUSE_BY_DESC

    view = build_security_state({"security_state": _contract()})
    html = _render_section(view)
    assert "R1" in html
    house = _SS_LEG_HOUSE_BY_DESC.get((
        "R1", "security_master row exists, security_state/superseded_by both null",
    ))
    assert house, "R1 code-less leg must have a house triple"
    packet_desc = _SS_LEG_DESC[("R1", "")]
    assert packet_desc["en"] in html
    assert house["artifact"]["en"] in html
    assert house["reader"]["en"] in html
    assert "security_master row exists" not in html
    assert "data/reference/security_master.parquet" not in html
    assert "_read_security_state_identity_rows" not in html
    assert "Master row found" in html
    assert "row_present" not in html
    panel_text = _identity_checks_panel(html).get_text()
    assert "yes" in panel_text
    assert "true" not in panel_text
    assert "Security status" in html
    assert "security_state</dt>" not in html
    assert "—" in panel_text
    assert "null" not in panel_text


def test_provenance_copy_is_two_register_and_bilingual() -> None:
    view = build_security_state({"security_state": _contract()})
    html = _render_section(view)
    # The absolutist claims are gone.
    assert "Nothing in this panel is calculated here" not in html
    assert "It does not calculate anything" not in html
    # Both registers are named, and the marker is on the page.
    assert "worked out here" in html
    assert "counted here" in html
    assert "quoted" in html
    zh = _render_section(view, lang="zh")
    assert "本页推算" in zh
    assert "本页统计" in zh


def test_absent_block_still_costs_only_the_section() -> None:
    assert build_security_state(None) is None
    assert build_security_state({}) is None
    assert build_security_state({"security_state": {}}) is None


# ---------------------------------------------------------------------------
# B-F06-1 · second issuer end to end — the golden MSFT compiled object renders
# with plain words, no raw enum codes, and both languages present
# ---------------------------------------------------------------------------

def test_view_model_renders_the_msft_state_with_plain_words() -> None:
    import jinja2

    fixture = REPO / "tests" / "fixtures" / "security_state" / "golden_msft_expected_output.json"
    state = json.loads(fixture.read_text(encoding="utf-8"))
    view = build_security_state({"security_state": state})
    assert view is not None
    assert view["ticker_display"] == "MSFT"

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(REPO / "templates")),
        undefined=jinja2.ChainableUndefined,
    )
    html = env.get_template("ticker.html.j2").render(
        security_state=view, ticker="MSFT", name="Microsoft Corp.",
    )
    assert 'id="security-state"' in html

    for code in (
        "COMPILER_FAILURE", "IDENTITY_UNRESOLVED", "BLOCKED_IDENTITY_BRIDGE",
        "NOT_COVERED", "UNAVAILABLE",
    ):
        assert code not in html, f"raw enum code {code!r} leaked into MSFT panel markup"

    # macro#6920 round-3 MINOR #1: the allowlist above excludes every code
    # the MSFT panel actually renders — the golden fixture's own
    # `identity_proof.disclosures` carry these four (the
    # `owner_read_completed=True` shared `DISCLOSURES` tuple). Those codes
    # ARE expected to appear, but only inside their own `ss-id` receipt chip
    # — never as the bare sentence itself (the actual MAJOR #2 failure mode).
    for code in (
        "CIK_LEG_OWNER_BACKED_CURRENT_ONLY", "OWNER_COMPOSED_SUBJECT_CURRENT_ONLY",
        "ISSUERMASTER_CURRENT_IDENTITY_ONLY", "ALIAS_EPOCH_VALID_FROM",
    ):
        assert f'<span class="c ss-id">{code}</span>' in html, (
            f"{code}: expected inside its ss-id receipt chip, not found"
        )
        assert f'<span class="l-en">{code}</span>' not in html, (
            f"{code}: raw code leaked as the bare EN sentence"
        )
        assert f'<span class="l-zh">{code}</span>' not in html, (
            f"{code}: raw code leaked as the bare ZH sentence"
        )

    import re
    section_match = re.search(r'id="security-state".*?(?=<section )', html, re.DOTALL)
    assert section_match is not None, "could not isolate the #security-state panel markup"
    section_html = section_match.group(0)
    assert '<span class="l-en">' in section_html
    assert '<span class="l-zh">' in section_html


def test_dfoot_c_chip_scoping_is_structural_not_a_grep_count() -> None:
    """The `.dfoot .c{margin-left:6px;...}` CSS rule (round-3 MAJOR #1 fix)
    applies to every `.c`-classed descendant of every `.dfoot` element on the
    page. A prior PR body argued this could not regress any other `.dfoot`
    usage by grepping `class="dfoot"` line counts in the `.j2` source and
    eyeballing which lines also mentioned `class="c"` — a text coincidence
    on the SOURCE template, not a structural check of what actually renders
    (round-3 review MINOR-3). A `.dfoot` spanning several lines, or a `.c`
    element nested inside conditional Jinja branches, would not show up in a
    single-line grep at all.

    This test instead parses the ACTUALLY RENDERED HTML with the standard
    library HTML parser and asks, for every `.dfoot` element, whether it
    has a `.c`-classed descendant — the exact question the CSS selector
    answers in a browser — for two renders that between them exercise every
    `.dfoot` line in the template, including both new `.c`-chip lines
    (identity refusals and identity disclosures). Sealed CI has no bs4;
    this assertion must stay stdlib-only.
    """
    import jinja2

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(REPO / "templates")),
        undefined=jinja2.ChainableUndefined,
    )
    tmpl = env.get_template("ticker.html.j2")

    # golden MSFT: identity.disclosures present (dfoot line ~1933), identity
    # PROVEN so identity.refusals is empty (dfoot line ~1932 does not render
    # at all — proving the `{% if %}` guard, not merely the CSS selector).
    fixture = REPO / "tests" / "fixtures" / "security_state" / "golden_msft_expected_output.json"
    msft_state = json.loads(fixture.read_text(encoding="utf-8"))
    msft_view = build_security_state({"security_state": msft_state})
    assert msft_view is not None

    # A BLOCKED shell with both refusals and disclosures present renders the
    # remaining `.c`-chip dfoot line (~1932) too.
    blocked_contract = _contract(identity_proof={
        "state": "BLOCKED_IDENTITY_BRIDGE", "method": "owner_backed_chain.v1",
        "legs": [], "equalities": [],
        "refusals": ["COMPILER_FAILURE"],
        "disclosures": ["CIK_LEG_OWNER_BACKED_CURRENT_ONLY: some technical description"],
    })
    blocked_view = build_security_state({"security_state": blocked_contract})
    assert blocked_view is not None

    for label, view, expect_refusals_dfoot in (
        ("msft (disclosures only, no refusals)", msft_view, False),
        ("blocked shell (refusals + disclosures)", blocked_view, True),
    ):
        html = tmpl.render(security_state=view, ticker="MSFT", name="Microsoft Corp.")
        tree = _parse_class_tree(html)
        dfoots = tree.find_all_class("dfoot")
        assert len(dfoots) >= 8, f"{label}: expected at least 8 static+dynamic .dfoot blocks, found {len(dfoots)}"

        carrying_ids = {id(d) for d in dfoots if d.find_class("c") is not None}
        carrying = [d for d in dfoots if id(d) in carrying_ids]

        found_refusals_dfoot = any("Held back" in d.get_text() or "暂不呈现" in d.get_text() for d in carrying)
        found_disclosures_dfoot = any(
            d.find_class("ss-id") is not None
            and "Held back" not in d.get_text() and "暂不呈现" not in d.get_text()
            for d in carrying
        )
        assert found_refusals_dfoot == expect_refusals_dfoot, (
            f"{label}: refusals .dfoot .c-chip presence = {found_refusals_dfoot}, expected {expect_refusals_dfoot}"
        )
        assert found_disclosures_dfoot, f"{label}: disclosures .dfoot .c-chip not found"
        # Structural scoping proof: every OTHER rendered .dfoot element (not
        # the refusals/disclosures lines just identified) carries NO
        # element with class "c" at all — so `.dfoot .c` cannot style them.
        expected_carrying_count = (1 if expect_refusals_dfoot else 0) + 1  # + disclosures
        assert len(carrying) == expected_carrying_count, (
            f"{label}: {len(carrying)} .dfoot blocks carry a .c descendant, "
            f"expected exactly {expected_carrying_count}: "
            f"{[d.get_text().strip()[:60] for d in carrying]!r}"
        )
        for d in dfoots:
            if id(d) not in carrying_ids:
                assert d.find_class("c") is None, (
                    f"{label}: an unaccounted .dfoot block unexpectedly carries a .c descendant: "
                    f"{d.get_text().strip()[:80]!r}"
                )


def test_compiler_failure_gate_renders_a_plain_bilingual_sentence() -> None:
    """A ``COMPILER_FAILURE`` failed-gate must render a real, DISTINCT EN/ZH
    sentence — never the raw enum code duplicated into both language slots
    (Chairman plain-language law, 2026-09-06, macro#6920 round-2 ruling).

    Before the fix, ``COMPILER_FAILURE`` had no ``_SS_GATES`` house-copy
    entry, so both ``en`` and ``zh`` fell back to ``_ss_prettify(code)`` —
    the SAME English words in the field the page treats as Chinese. The raw
    machine code may still appear, but only inside the receipt's own
    ``ss-id`` chip, never as the sentence itself.
    """
    contract = _contract(dominant_degradation="COMPILER_FAILURE")
    contract["legs"]["risk"]["failed_gates"] = [
        {"code": "COMPILER_FAILURE",
         "reason": "security_state compiler failed after owner identity was composed"},
    ]
    view = build_security_state({"security_state": contract})
    assert view is not None

    gate = next(g for a in view["axes"] for g in a["gates"] if g["code"] == "COMPILER_FAILURE")
    assert gate["en"] != gate["zh"], (
        f"ZH slot must be real Chinese, not the English fallback duplicated: {gate!r}"
    )
    assert gate["en"] not in ("COMPILER_FAILURE", "Compiler failure"), (
        "must be a house plain sentence, not the raw code or its bare prettification"
    )
    # A real Chinese sentence contains CJK characters — a prettified English
    # fallback never does.
    assert re.search(r"[一-鿿]", gate["zh"]), f"zh is not Chinese: {gate['zh']!r}"

    import jinja2
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(REPO / "templates")),
        undefined=jinja2.ChainableUndefined,
    )
    html = env.get_template("ticker.html.j2").render(
        security_state=view, ticker="AAPL", name="Apple Inc.",
    )
    # The plain sentence must appear as visible prose …
    assert gate["en"] in html
    assert gate["zh"] in html
    # … and wherever the raw code still appears, it must be inside the
    # receipt's machine-id chip, never as a bare bilingual prose span.
    assert '<span class="l-en">COMPILER_FAILURE</span>' not in html
    assert '<span class="l-zh">COMPILER_FAILURE</span>' not in html


def test_identity_refusal_renders_a_plain_bilingual_sentence_not_the_raw_code() -> None:
    """``identity_proof.refusals`` is the M1/M2 failure-shell path

    (``engine.security_state.compile_security_state_failure``) — a DIFFERENT
    rendering path from ``legs.risk.failed_gates`` covered by
    ``test_compiler_failure_gate_renders_a_plain_bilingual_sentence`` above.
    Before this fix the "Held back" line rendered the raw refusal code
    (``COMPILER_FAILURE`` / ``IDENTITY_UNRESOLVED``) as bare, language-
    identical text inside a plain ``<div class="dfoot">`` — no ``ss-id``
    chip, no ``data-`` attribute — byte-identical in the EN and ZH views
    (macro#6920 round-2 MAJOR #2: the PR body's claim that the raw code
    "only appears inside the receipt's own ss-id machine-id chip" was false
    for this path).
    """
    for code in ("COMPILER_FAILURE", "IDENTITY_UNRESOLVED"):
        contract = _contract(identity_proof={
            "state": "BLOCKED_IDENTITY_BRIDGE", "method": "owner_backed_chain.v1",
            "legs": [], "equalities": [], "refusals": [code], "disclosures": [],
        })
        view = build_security_state({"security_state": contract})
        assert view is not None

        refusal = next(r for r in view["identity"]["refusals"] if r["code"] == code)
        assert refusal["en"] != refusal["zh"], (
            f"{code}: ZH slot must be real Chinese, not the English fallback duplicated: {refusal!r}"
        )
        assert refusal["en"] not in (code, _prettify_words(code)), (
            f"{code}: must be a house plain sentence, not the raw code or its bare prettification"
        )
        assert re.search(r"[一-鿿]", refusal["zh"]), f"{code}: zh is not Chinese: {refusal['zh']!r}"

        import jinja2
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(REPO / "templates")),
            undefined=jinja2.ChainableUndefined,
        )
        html = env.get_template("ticker.html.j2").render(
            security_state=view, ticker="MSFT", name="Microsoft Corp.",
        )  # both languages present, un-filtered
        # The plain sentence must appear as visible prose in BOTH languages.
        assert refusal["en"] in html, f"{code}: EN plain sentence missing from render"
        assert refusal["zh"] in html, f"{code}: ZH plain sentence missing from render"

        # The raw machine code, wherever it appears, must be inside the
        # receipt's own ss-id chip — never as bare, bilingual-identical text
        # sitting directly in the "Held back" line (what the PR body's round-2
        # claim asserted but did not test).
        m = re.search(r'Held back</span>.*?:(.*?)</div>', html, re.S)
        assert m is not None, f"{code}: 'Held back' line not found in render"
        held_back_html = m.group(1)
        assert f'<span class="c ss-id">{code}</span>' in held_back_html, (
            f"{code}: raw code must be inside the ss-id chip: {held_back_html!r}"
        )
        stripped = re.sub(r'<span class="c ss-id">.*?</span>', "", held_back_html)
        assert code not in stripped, (
            f"{code}: raw code leaked outside the ss-id chip: {stripped!r}"
        )
        # And explicitly: the raw code must never sit as its own bare
        # bilingual-label span (the exact failure the round-2 PR body missed).
        assert f'<span class="l-en">{code}</span>' not in html
        assert f'<span class="l-zh">{code}</span>' not in html


def test_identity_disclosure_renders_a_plain_bilingual_sentence_not_the_raw_code() -> None:
    """``identity_proof.disclosures`` is stored engine-side as "CODE:
    technical description" (see ``engine.security_state.DISCLOSURES`` and the
    M1 failure shell's own local list). Before this fix
    ``templates/ticker.html.j2`` rendered each raw string verbatim —
    machine-code prefix and all — identically in the EN and ZH views (macro
    #6920 round-3 MAJOR #2). The code must render only inside the receipt's
    ``ss-id`` chip, and the sentence must be real, distinct EN/ZH prose.
    """
    for code in (
        "PINNED_IDENTITY_NOT_OWNER_READ_THIS_CYCLE",
        "IDENTITY_BRIDGE_UNRESOLVED_THIS_CYCLE",
        "CIK_LEG_OWNER_BACKED_CURRENT_ONLY",
    ):
        contract = _contract(identity_proof={
            "state": "BLOCKED_IDENTITY_BRIDGE", "method": "owner_backed_chain.v1",
            "legs": [], "equalities": [], "refusals": [],
            "disclosures": [f"{code}: some technical description that must never reach the page"],
        })
        view = build_security_state({"security_state": contract})
        assert view is not None

        disclosure = next(d for d in view["identity"]["disclosures"] if d["code"] == code)
        assert disclosure["en"] != disclosure["zh"], (
            f"{code}: ZH slot must be real Chinese, not the English fallback duplicated: {disclosure!r}"
        )
        assert re.search(r"[一-鿿]", disclosure["zh"]), f"{code}: zh is not Chinese: {disclosure['zh']!r}"
        assert "some technical description" not in disclosure["en"], (
            f"{code}: the raw engine description must be replaced by house copy, not passed through"
        )

        import jinja2
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(REPO / "templates")),
            undefined=jinja2.ChainableUndefined,
        )
        html = env.get_template("ticker.html.j2").render(
            security_state=view, ticker="MSFT", name="Microsoft Corp.",
        )
        assert disclosure["en"] in html, f"{code}: EN plain sentence missing from render"
        assert disclosure["zh"] in html, f"{code}: ZH plain sentence missing from render"
        assert "some technical description" not in html, (
            f"{code}: raw engine disclosure text leaked into rendered markup"
        )

        # The raw machine code, wherever it appears, must be inside the
        # receipt's own ss-id chip — never as bare text sitting directly in
        # the disclosures line, and never duplicated into the ZH view.
        m = re.search(
            r'<div class="dfoot">((?:(?!</div>).)*?' + re.escape(code) + r'(?:(?!</div>).)*?)</div>',
            html, re.S,
        )
        assert m is not None, f"{code}: disclosure line containing the code not found in render"
        line_html = m.group(1)
        assert f'<span class="c ss-id">{code}</span>' in line_html, (
            f"{code}: raw code must be inside the ss-id chip: {line_html!r}"
        )
        stripped = re.sub(r'<span class="c ss-id">.*?</span>', "", line_html)
        assert code not in stripped, f"{code}: raw code leaked outside the ss-id chip: {stripped!r}"


def test_every_compile_path_refusal_code_has_house_copy_with_no_prettify_fallback() -> None:
    """`engine/security_state.py` emits nine distinct refusal codes on its
    compile path (`identity_proof.refusals`, both `compile_security_state`'s
    R1..R8 gates and `compile_security_state_failure`'s M1/M2 shells). Every
    one of them must have a `_SS_GATES` house-copy entry carrying a REAL,
    distinct EN/ZH sentence. The code set is extracted from the engine
    source by regex, not hand-copied, so this test cannot go stale silently
    if a new refusal code is added there without a matching entry here
    (macro#6920 round-3 review MAJOR-1; heal-round h2 adds OWNER_IDENTITY_UNREAD).

    Before this fix, only two of the eight then-known codes (`COMPILER_FAILURE`,
    `IDENTITY_UNRESOLVED`) had a `_SS_GATES` entry; the other six
    (`SECURITY_SUPERSEDED`, `ISSUER_GROUP_AMBIGUOUS`,
    `LISTING_KEY_INCOHERENT`, `IDENTITY_CORRECTED`,
    `SUBJECT_NATIVE_PARITY_FAILED`, `IDENTITY_BRIDGE_DISAGREEMENT`) fell
    through to `_ss_prettify(code)` for BOTH slots — the same English words
    duplicated into the field the page treats as Chinese. Main later added
    `OWNER_IDENTITY_UNREAD`; without a ninth house-copy entry the same
    prettify fallback would print English slug words in EN and ZH.
    """
    from scripts.build_ticker_pages import _SS_GATES, _ss_prettify

    engine_src = (REPO / "engine" / "security_state.py").read_text()
    codes = set(re.findall(r'refusals\.append\("([A-Z][A-Z0-9_]*)"\)', engine_src))
    codes |= set(re.findall(r'"refusals":\s*\["([A-Z][A-Z0-9_]*)"\]', engine_src))

    # macro#6920 round-4 review MINOR-2: the two `re.findall` calls above only
    # recognise `refusals.append("LITERAL")` and `"refusals": ["LITERAL"]` —
    # a future `refusals.extend([...])`, `refusals += [...]`, or an appended
    # variable (`refusals.append(code_var)`) would add a ninth code that
    # slips past both regexes and leaves this test's coverage claim silently
    # stale. This walks every line mentioning `refusals` and fails loudly on
    # any shape that is neither one of the two recognised literal forms nor
    # one of the three known non-mutating/benign references (the `list[str]`
    # initializer, the `if refusals:` guard, and `"refusals": refusals` final
    # assembly) — so an unrecognised shape is a test failure, not a gap.
    _benign = re.compile(
        r'^\s*refusals:\s*list\[str\]\s*=\s*\[\]\s*$'
        r'|^\s*if refusals:\s*$'
        r'|^\s*"refusals":\s*refusals,\s*$'
    )
    _literal_append = re.compile(r'^\s*refusals\.append\("[A-Z][A-Z0-9_]*"\)\s*$')
    _literal_dict = re.compile(r'^\s*"refusals":\s*\["[A-Z][A-Z0-9_]*"\],?\s*$')
    for lineno, line in enumerate(engine_src.splitlines(), start=1):
        if "refusals" not in line:
            continue
        if _benign.match(line) or _literal_append.match(line) or _literal_dict.match(line):
            continue
        pytest.fail(
            f"engine/security_state.py:{lineno}: `refusals` is used in a shape this "
            f"test's code-coverage extraction does not recognise ({line.strip()!r}) — "
            "a `.extend(`, `+=`, or a non-literal `.append(var)` would add a code "
            "this test's regex cannot see, going stale silently. Update the "
            "extraction regexes above (and this allow-list) together with whatever "
            "new code this line adds."
        )

    assert codes == {
        "SECURITY_SUPERSEDED", "IDENTITY_UNRESOLVED", "ISSUER_GROUP_AMBIGUOUS",
        "LISTING_KEY_INCOHERENT", "IDENTITY_CORRECTED", "SUBJECT_NATIVE_PARITY_FAILED",
        "IDENTITY_BRIDGE_DISAGREEMENT", "COMPILER_FAILURE", "OWNER_IDENTITY_UNREAD",
    }, (
        f"engine/security_state.py's emitted refusal-code set changed: {sorted(codes)} — "
        "this test's extraction regex and its house-copy coverage below must be updated together"
    )

    for code in sorted(codes):
        assert code in _SS_GATES, f"{code}: no _SS_GATES house-copy entry — falls through to _ss_prettify"
        entry = _SS_GATES[code]
        assert entry.get("en") and entry.get("zh"), f"{code}: house-copy entry has an empty slot: {entry!r}"
        assert entry["en"] != entry["zh"], (
            f"{code}: ZH slot is not real Chinese (duplicates the EN fallback): {entry!r}"
        )
        assert re.search(r"[一-鿿]", entry["zh"]), f"{code}: zh is not Chinese: {entry['zh']!r}"
        pretty = _ss_prettify(code)
        assert entry["en"] != pretty, (
            f"{code}: house copy is just the bare prettification of the code, not a real sentence"
        )

        # Exercise the real production mapping site
        # (`(_SS_GATES.get(code) or {}).get("en") or _ss_prettify(code)`) end
        # to end for every code, not just the dict — a present, non-empty
        # `_SS_GATES` entry makes the `_ss_prettify` branch unreachable for
        # this code, and this proves it by observing the actual output.
        contract = _contract(identity_proof={
            "state": "BLOCKED_IDENTITY_BRIDGE", "method": "owner_backed_chain.v1",
            "legs": [], "equalities": [], "refusals": [code], "disclosures": [],
        })
        view = build_security_state({"security_state": contract})
        assert view is not None
        refusal = next(r for r in view["identity"]["refusals"] if r["code"] == code)
        assert refusal["en"] == entry["en"] and refusal["zh"] == entry["zh"], (
            f"{code}: rendered refusal does not match its _SS_GATES house copy: {refusal!r}"
        )
        assert refusal["en"] != pretty, f"{code}: rendered refusal fell back to the bare prettification"


def _iter_leg_house_copy_slots():
    """Walk every user-facing string in the identity-leg house tables."""
    from scripts.build_ticker_pages import (
        _SS_ARTIFACT, _SS_LEG_DESC, _SS_LEG_HOUSE_BY_DESC, _SS_READER,
        _SS_READ_KEY_VALUE, _SS_READ_VALUE,
    )
    for key, entry in _SS_LEG_DESC.items():
        for slot, text in entry.items():
            yield f"_SS_LEG_DESC[{key!r}][{slot!r}]", str(text)
    for key, entry in _SS_ARTIFACT.items():
        for slot, text in entry.items():
            yield f"_SS_ARTIFACT[{key!r}][{slot!r}]", str(text)
    for key, entry in _SS_READER.items():
        for slot, text in entry.items():
            yield f"_SS_READER[{key!r}][{slot!r}]", str(text)
    for key, triple in _SS_LEG_HOUSE_BY_DESC.items():
        for field, entry in triple.items():
            if not isinstance(entry, dict):
                continue
            for slot, text in entry.items():
                yield (
                    f"_SS_LEG_HOUSE_BY_DESC[{key!r}][{field!r}][{slot!r}]",
                    str(text),
                )
    for key, entry in _SS_READ_VALUE.items():
        for slot, text in entry.items():
            yield f"_SS_READ_VALUE[{key!r}][{slot!r}]", str(text)
    for key, entry in _SS_READ_KEY_VALUE.items():
        for slot, text in entry.items():
            yield f"_SS_READ_KEY_VALUE[{key!r}][{slot!r}]", str(text)


def test_ss_gates_and_leg_desc_user_facing_copy_has_no_batch_machine_words() -> None:
    """macro#6920 heal-round h2 R3: user-facing `_SS_GATES` / `_SS_LEG_DESC`
    strings must not say "batch" / "批处理". Those are pipeline nouns, not
    what the reader is looking at. RED at 3ac3bb2f because IDENTITY_UNRESOLVED
    clear_en/clear_zh and the R8 IDENTITY_UNRESOLVED leg description used both.
    Heal-round h5: also walk `_SS_LEG_HOUSE_BY_DESC`, `_SS_ARTIFACT`, and
    `_SS_READER`.
    """
    from scripts.build_ticker_pages import _SS_GATES

    banned_ascii = ("batch",)
    banned_zh = ("批处理",)
    for code, entry in _SS_GATES.items():
        for slot, text in entry.items():
            hay = str(text)
            for word in banned_ascii:
                assert word not in hay.lower(), (
                    f"_SS_GATES[{code!r}][{slot!r}] contains {word!r}: {hay!r}"
                )
            for word in banned_zh:
                assert word not in hay, (
                    f"_SS_GATES[{code!r}][{slot!r}] contains {word!r}: {hay!r}"
                )
    for label, hay in _iter_leg_house_copy_slots():
        for word in banned_ascii:
            assert word not in hay.lower(), f"{label} contains {word!r}: {hay!r}"
        for word in banned_zh:
            assert word not in hay, f"{label} contains {word!r}: {hay!r}"


def test_unmapped_disclosure_code_keeps_the_engine_description_not_a_prettified_slug() -> None:
    """macro#6920 round-3 ruling MAJOR-1 (binding): "the `_ss_prettify`
    fallback stays only as a last resort that ALSO keeps the engine's
    description text." Round-4's `_ss_disclosure_rows` still discarded the
    description whenever a code prefix was present but unmapped, replacing
    it with `_ss_prettify(code)` in BOTH language slots (round-4 review
    MAJOR-1). This is the reviewer's own literal repro command, pinned.
    """
    from scripts.build_ticker_pages import _ss_disclosure_rows, _ss_prettify

    rows = _ss_disclosure_rows([
        "FUTURE_UNMAPPED_CODE: alias epoch valid_from 2026-01-01, owner batch skipped",
    ])
    assert len(rows) == 1
    row = rows[0]
    assert row["code"] == "FUTURE_UNMAPPED_CODE"
    # The engine's own description text must survive — never thrown away in
    # favor of a slug-derived pseudo-word.
    assert row["en"] == "alias epoch valid_from 2026-01-01, owner batch skipped"
    assert row["zh"] == "alias epoch valid_from 2026-01-01, owner batch skipped"
    assert row["en"] != _ss_prettify("FUTURE_UNMAPPED_CODE")

    # A code with NO description text at all (defensive path) still falls
    # back to the prettified code rather than rendering blank.
    blank_rows = _ss_disclosure_rows(["FUTURE_UNMAPPED_CODE_NO_TEXT:   "])
    assert blank_rows[0]["en"] == _ss_prettify("FUTURE_UNMAPPED_CODE_NO_TEXT")


def test_m1_shell_gate_description_renders_a_real_bilingual_sentence() -> None:
    """macro#6920 round-4 review MAJOR-2: `identity_proof.legs[].description`
    (the gate sentence under `.ss-chk-d`, e.g. "Identity checks") was passed
    to the template as `lg.desc` with no `t()` call — a NEW string this PR's
    own M1 failure shell (`engine.security_state.compile_security_state_failure`,
    `owner_read_completed=False`) added rendered in English even on the ZH
    page, and it was the LARGEST text in that panel. The PR body had argued
    this was "cosmetic ... not user-facing" because the disclosures line
    next to it is bilingual — the review found the body's own committed ZH
    screenshot proved the gate sentence itself was not. Fixed via
    `_SS_LEG_DESC`, keyed on (check, code) so it cannot collide with the
    OTHER "R8" leg descriptions (the normal AAPL-reachable path and the
    owner-composed COMPILER_FAILURE shell) that are unrelated pre-existing
    text.
    """
    from scripts.build_ticker_pages import _SS_LEG_DESC

    contract = _contract(identity_proof={
        "state": "BLOCKED_IDENTITY_BRIDGE", "method": "owner_backed_chain.v1",
        "legs": [{
            "check": "R8",
            "description": "owner-identity batch was unavailable this cycle; subject is the "
            "frozen pinned allowlist mapping for this ticker, never a live owner read",
            "artifact": "SecurityStateSubject (frozen pinned allowlist config, not a producer owner receipt)",
            "reader": "scripts/security_state_producer.py::_read_security_state_identity_rows",
            "values_read": [{"field": "subject_ticker_display", "value": "MSFT"}],
            "result": "fail", "code": "IDENTITY_UNRESOLVED",
        }],
        "equalities": [], "refusals": ["IDENTITY_UNRESOLVED"], "disclosures": [],
    })
    view = build_security_state({"security_state": contract})
    assert view is not None
    leg = view["identity"]["legs"][0]

    house = _SS_LEG_DESC[("R8", "IDENTITY_UNRESOLVED")]
    assert leg["desc_en"] == house["en"] and leg["desc_zh"] == house["zh"]
    assert leg["desc_en"] != leg["desc_zh"], "ZH slot must be real Chinese, not the English duplicated"
    assert re.search(r"[一-鿿]", leg["desc_zh"]), f"desc_zh is not Chinese: {leg['desc_zh']!r}"
    # The raw engine sentence must not leak through unmapped.
    assert "owner-identity batch was unavailable this cycle" not in leg["desc_en"] or leg["desc_en"] == house["en"]

    import jinja2
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(REPO / "templates")),
        undefined=jinja2.ChainableUndefined,
    )
    html = env.get_template("ticker.html.j2").render(
        security_state=view, ticker="MSFT", name="Microsoft Corp.",
    )
    assert house["en"] in html
    assert house["zh"] in html
    # The raw engine-only English sentence (pre-fix behaviour) is gone.
    assert "owner-identity batch was unavailable this cycle" not in html

    # A DIFFERENT code-less "R8" leg with no house-copy entry: all six slots
    # are empty. The EN slot never receives engine text and the ZH slot never
    # receives 暂不可用. The proven-path R8 sentence is a mapped key and must
    # not be used here.
    other_contract = _contract(identity_proof={
        "state": "PROVEN", "method": "owner_backed_chain.v1",
        "legs": [{
            "check": "R8",
            "description": "some future unmapped engine sentence",
            "artifact": "x", "reader": "y", "values_read": [], "result": "pass", "code": None,
        }],
        "equalities": [], "refusals": [], "disclosures": [],
    })
    other_view = build_security_state({"security_state": other_contract})
    assert other_view is not None
    other_leg = other_view["identity"]["legs"][0]
    assert other_leg["desc_en"] == ""
    assert other_leg["desc_zh"] == ""
    assert other_leg["artifact_en"] == ""
    assert other_leg["artifact_zh"] == ""
    assert other_leg["reader_en"] == ""
    assert other_leg["reader_zh"] == ""


def test_unread_disclosures_have_house_copy_with_no_english_into_zh_leak() -> None:
    """macro#6920 round-2/2 review MAJOR: engine UNREAD_DISCLOSURES
    (CIK_LEG_OWNER_UNREAD, OWNER_COMPOSED_SUBJECT_UNREAD,
    ISSUER_LINEAGE_UNREAD, ALIAS_EPOCH_UNREAD) had no `_SS_DISCLOSURES`
    entries. `_ss_disclosure_rows` then duplicated the English engine
    description — including machine field names — into both language slots.

    RED at 59933d1a: OWNER_COMPOSED_SUBJECT_UNREAD rendered
    `security_id, issuer_id, listing_key and ticker_display are the frozen
    pinned fallback values; ...` in EN and ZH.
    """
    from engine.security_state import UNREAD_DISCLOSURES
    from scripts.build_ticker_pages import _SS_DISCLOSURES, _ss_disclosure_rows, _ss_split_disclosure

    rows = _ss_disclosure_rows(list(UNREAD_DISCLOSURES))
    assert len(rows) == 4, rows
    machine_tokens = (
        "security_id", "issuer_id", "listing_key", "ticker_display",
        "VendorAliasTable", "IssuerMaster",
    )
    for raw, row in zip(UNREAD_DISCLOSURES, rows):
        code, _desc = _ss_split_disclosure(raw)
        assert row["code"] == code
        assert code in _SS_DISCLOSURES, (
            f"{code}: no _SS_DISCLOSURES house-copy entry — EN leaks into ZH"
        )
        house = _SS_DISCLOSURES[code]
        assert row["en"] == house["en"] and row["zh"] == house["zh"], (
            f"{code}: rendered disclosure does not match house copy: {row!r}"
        )
        assert row["en"] != row["zh"], (
            f"{code}: ZH slot duplicates English: {row!r}"
        )
        assert re.search(r"[一-鿿]", row["zh"]), f"{code}: zh is not Chinese: {row['zh']!r}"
        hay = f"{row['en']} {row['zh']}"
        for tok in machine_tokens:
            assert tok not in hay, (
                f"{code}: machine token {tok!r} in user-facing copy: {hay!r}"
            )

        contract = _contract(identity_proof={
            "state": "BLOCKED_IDENTITY_BRIDGE", "method": "owner_backed_chain.v1",
            "legs": [], "equalities": [], "refusals": [],
            "disclosures": [raw],
        })
        view = build_security_state({"security_state": contract})
        assert view is not None
        rendered = next(d for d in view["identity"]["disclosures"] if d["code"] == code)
        assert rendered["en"] == house["en"] and rendered["zh"] == house["zh"]


def test_ss_leg_desc_identity_unresolved_is_plain_words_not_allowlist_jargon() -> None:
    """macro#6920 round-2/2 review MINOR-1: `_SS_LEG_DESC[('R8','IDENTITY_UNRESOLVED')]`
    still said 'frozen pinned-allowlist mapping' / '冻结准入映射' after the
    batch/批处理 rewrite. Those are pipeline nouns, not what the reader is
    looking at. RED at 59933d1a. Heal-round h5: also walk the by-description
    table and the artifact/reader tables.
    """
    from scripts.build_ticker_pages import _SS_GATES

    banned = (
        "allowlist", "pinned-allowlist", "pinned allowlist",
        "准入映射", "SecurityStateSubject",
    )
    for code, entry in _SS_GATES.items():
        for slot, text in entry.items():
            hay = str(text)
            for word in banned:
                if word.isascii():
                    assert word.lower() not in hay.lower(), (
                        f"_SS_GATES[{code!r}][{slot!r}] contains {word!r}: {hay!r}"
                    )
                else:
                    assert word not in hay, (
                        f"_SS_GATES[{code!r}][{slot!r}] contains {word!r}: {hay!r}"
                    )
    for label, hay in _iter_leg_house_copy_slots():
        for word in banned:
            if word.isascii():
                assert word.lower() not in hay.lower(), (
                    f"{label} contains {word!r}: {hay!r}"
                )
            else:
                assert word not in hay, f"{label} contains {word!r}: {hay!r}"


def test_m1_shell_artifact_and_reader_are_plain_bilingual_not_machine_paths() -> None:
    """macro#6920 round-2/2 review MINOR-2: the M1 Identity checks panel
    printed `artifact` and `reader` as raw English on the ZH page
    (`SecurityStateSubject (frozen pinned allowlist config, ...)` and
    `scripts/security_state_producer.py::_read_security_state_identity_rows`)
    via the pass-through at build_ticker_pages.py. RED at 59933d1a.
    """
    from scripts.build_ticker_pages import _SS_ARTIFACT, _SS_READER

    contract = _contract(identity_proof={
        "state": "BLOCKED_IDENTITY_BRIDGE", "method": "owner_backed_chain.v1",
        "legs": [{
            "check": "R8",
            "description": "owner-identity batch was unavailable this cycle; subject is the "
            "frozen pinned allowlist mapping for this ticker, never a live owner read",
            "artifact": "SecurityStateSubject (frozen pinned allowlist config, not a producer owner receipt)",
            "reader": "scripts/security_state_producer.py::_read_security_state_identity_rows",
            "values_read": [{"field": "subject_ticker_display", "value": "MSFT"}],
            "result": "fail", "code": "IDENTITY_UNRESOLVED",
        }],
        "equalities": [], "refusals": ["IDENTITY_UNRESOLVED"], "disclosures": [],
    })
    view = build_security_state({"security_state": contract})
    assert view is not None
    leg = view["identity"]["legs"][0]

    art = _SS_ARTIFACT[("R8", "IDENTITY_UNRESOLVED")]
    rdr = _SS_READER[("R8", "IDENTITY_UNRESOLVED")]
    assert leg["artifact_en"] == art["en"] and leg["artifact_zh"] == art["zh"]
    assert leg["reader_en"] == rdr["en"] and leg["reader_zh"] == rdr["zh"]
    assert leg["artifact_en"] != leg["artifact_zh"]
    assert leg["reader_en"] != leg["reader_zh"]
    assert re.search(r"[一-鿿]", leg["artifact_zh"])
    assert re.search(r"[一-鿿]", leg["reader_zh"])
    blob = " ".join([
        leg["artifact_en"], leg["artifact_zh"],
        leg["reader_en"], leg["reader_zh"],
    ])
    assert "SecurityStateSubject" not in blob
    assert "scripts/" not in blob
    assert "allowlist" not in blob.lower()
    assert "准入映射" not in blob

    import jinja2
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(REPO / "templates")),
        undefined=jinja2.ChainableUndefined,
    )
    html = env.get_template("ticker.html.j2").render(
        security_state=view, ticker="MSFT", name="Microsoft Corp.",
    )
    assert art["en"] in html and art["zh"] in html
    assert rdr["en"] in html and rdr["zh"] in html
    assert "SecurityStateSubject" not in html
    assert "scripts/security_state_producer.py::_read_security_state_identity_rows" not in html


def _prettify_words(code: str) -> str:
    words = re.sub(r"[^0-9A-Za-z]+", " ", code).strip().lower()
    return (words[:1].upper() + words[1:]) if words else ""


def test_m1_subread_reason_is_house_copy_never_english_on_zh_page() -> None:
    """REQUIRED 2: M1 public_reason is a CODE; the page maps it through
    `_SS_REASON` and never renders the raw code or the false compiler
    sentence. Unmapped codes render `_SS_COVERAGE_FALLBACK`, never the code.
    """
    from engine.security_state import MSFT_SUBJECT, compile_security_state_failure
    from jsonschema import Draft202012Validator, FormatChecker
    from scripts.build_ticker_pages import _SS_COVERAGE_FALLBACK, _SS_REASON

    schema_path = REPO / "contracts" / "market_os" / "security_state.v1.schema.json"
    validator = Draft202012Validator(
        json.loads(schema_path.read_text(encoding="utf-8")),
        format_checker=FormatChecker(),
    )
    state = compile_security_state_failure(
        subject=MSFT_SUBJECT, validator=validator, now="2026-01-01T00:00:00Z",
        prior_state=None, owner_read_completed=False,
    )
    view = build_security_state({"security_state": state})
    assert view is not None
    entry = next(s for s in _axis(view, "opportunity_context")["subreads"] if s["en"] == "Entry read")
    house = _SS_REASON["OWNER_IDENTITY_BATCH_UNAVAILABLE"]
    assert entry["reason_en"] == house["en"]
    assert entry["reason_zh"] == house["zh"]
    assert entry["reason_en"] != entry["reason_zh"]
    assert re.search(r"[一-鿿]", entry["reason_zh"])

    zh_html = _render_section(view, lang="zh")
    assert house["zh"] in zh_html
    assert house["en"] not in zh_html
    # REQUIRED 3 puts this code on M1 failed_gates, so the raw identifier may
    # appear inside an ss-id chip. It must not appear as the reason sentence.
    stripped = re.sub(r'<span class="(?:c )?ss-id">.*?</span>', "", zh_html)
    assert "OWNER_IDENTITY_BATCH_UNAVAILABLE" not in stripped
    assert "compiler failed" not in zh_html
    assert "security_state compiler" not in zh_html

    unmapped = _contract(legs={
        **_contract()["legs"],
        "opportunity_context": {
            "prophet": {"ref": None, "state": "UNAVAILABLE", "reason": "SOME_FUTURE_REASON_CODE"},
            "entry": {"state": "UNAVAILABLE", "available": False, "null_reason": None},
            "market_incorporation": {"ref": None, "state": "NOT_COVERED"},
            "dislocation": {"ref": None, "state": "NOT_COVERED"},
            "coverage_state": "UNAVAILABLE",
        },
    })
    unmapped_view = build_security_state({"security_state": unmapped})
    assert unmapped_view is not None
    prophet = next(s for s in _axis(unmapped_view, "opportunity_context")["subreads"] if s["en"] == "Prophet outlook")
    assert prophet["reason_en"] == _SS_COVERAGE_FALLBACK["en"]
    assert prophet["reason_zh"] == _SS_COVERAGE_FALLBACK["zh"]
    unmapped_zh = _render_section(unmapped_view, lang="zh")
    assert "SOME_FUTURE_REASON_CODE" not in unmapped_zh
    assert _SS_COVERAGE_FALLBACK["zh"] in unmapped_zh


def test_pinned_identity_not_owner_read_house_copy_is_the_frozen_pair() -> None:
    """REQUIRED 4: PINNED_IDENTITY_NOT_OWNER_READ_THIS_CYCLE is a frozen
    EN/ZH pair at parity, not pipeline jargon.
    """
    from scripts.build_ticker_pages import _SS_DISCLOSURES, _ss_disclosure_rows

    house = _SS_DISCLOSURES["PINNED_IDENTITY_NOT_OWNER_READ_THIS_CYCLE"]
    assert house["en"] == (
        "This cycle used the last known identity for this security; the identity sources were not re-read."
    )
    assert house["zh"] == (
        "本周期使用该证券上次已知的身份记录；未重新读取身份来源。"
    )
    rows = _ss_disclosure_rows([
        "PINNED_IDENTITY_NOT_OWNER_READ_THIS_CYCLE: frozen allowlist mapping must never reach the page",
    ])
    assert rows[0]["en"] == house["en"]
    assert rows[0]["zh"] == house["zh"]
    assert "allowlist" not in rows[0]["en"].lower()
    assert "frozen" not in rows[0]["en"].lower()
    assert re.search(r"[一-鿿]", rows[0]["zh"])


def _identity_checks_panel(html: str) -> _HtmlNode:
    """The Identity-checks `.dpanel` from a language-stripped ticker render."""
    root = _parse_class_tree(html)
    for panel in root.find_all_class("dpanel"):
        for child in panel.children:
            if child.tag == "h3" and (
                "Identity checks" in child.get_text() or "身份核对" in child.get_text()
            ):
                return panel
    raise AssertionError("Identity checks panel not found")


def _without_ss_id(node: _HtmlNode) -> _HtmlNode:
    """Drop ``ss-id`` / ``c ss-id`` subtrees (receipt chips and identifiers).

    `_HtmlNode` has no subtree-exclusion of its own. The receipt code chip is
    the sanctioned home for a machine code; the ALL_CAPS_SNAKE and ZH Latin-run
    rules apply to what remains after those spans are removed.
    """
    clone = _HtmlNode(node.tag, node.classes)
    clone.text_parts = list(node.text_parts)
    for child in node.children:
        if "ss-id" in child.classes:
            continue
        clone.children.append(_without_ss_id(child))
    return clone


def _spaced_text(node: _HtmlNode) -> str:
    """Visible text with a gap between child elements so labels do not glue to values."""
    bits = [part for part in node.text_parts if part.strip()]
    for child in node.children:
        child_text = _spaced_text(child)
        if child_text:
            bits.append(child_text)
    return " ".join(bits)


def _visible_page_text(html: str) -> str:
    """Tag-stripped text with style/script dropped, for field-name leakage."""
    html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", html)


def test_golden_msft_proven_path_zh_page_has_no_raw_engine_english() -> None:
    """Heal-round h5: every golden-MSFT identity leg is mapped to house copy.
    The ZH Identity-checks panel never receives engine English and never
    receives `_SS_COVERAGE_FALLBACK` ('暂不可用') on a passing row.
    """
    from scripts.build_ticker_pages import (
        _SS_ARTIFACT, _SS_COVERAGE_FALLBACK, _SS_LEG_DESC, _SS_LEG_HOUSE_BY_DESC,
        _SS_READER,
    )

    fixture = REPO / "tests" / "fixtures" / "security_state" / "golden_msft_expected_output.json"
    state = json.loads(fixture.read_text(encoding="utf-8"))
    view = build_security_state({"security_state": state})
    assert view is not None
    missing_house: list[tuple[str, str]] = []
    for src, lg in zip(state["identity_proof"]["legs"], view["identity"]["legs"]):
        code = lg["code"] or ""
        desc_raw = src["description"] or ""
        if code:
            desc_house = _SS_LEG_DESC.get((lg["check"], code))
            art_house = _SS_ARTIFACT.get((lg["check"], code))
            rdr_house = _SS_READER.get((lg["check"], code))
        else:
            triple = _SS_LEG_HOUSE_BY_DESC.get((lg["check"], desc_raw)) or {}
            desc_house = _SS_LEG_DESC.get((lg["check"], "")) or triple.get("desc")
            art_house = triple.get("artifact")
            rdr_house = triple.get("reader")
        if not (desc_house and desc_house.get("en") and desc_house.get("zh")):
            missing_house.append((lg["check"], code))
        else:
            assert lg["desc_en"] == desc_house["en"]
            assert lg["desc_zh"] == desc_house["zh"]
            assert lg["desc_zh"] != _SS_COVERAGE_FALLBACK["zh"]
        if art_house:
            assert lg["artifact_en"] == art_house["en"]
            assert lg["artifact_zh"] == art_house["zh"]
        if rdr_house:
            assert lg["reader_en"] == rdr_house["en"]
            assert lg["reader_zh"] == rdr_house["zh"]
    assert not missing_house, (
        f"golden-MSFT identity legs missing house description: {missing_house}"
    )

    zh_html = _render_section(view, lang="zh")
    assert "scripts/security_state_producer.py" not in zh_html
    assert "data/reference/security_master.parquet" not in zh_html

    panel_text = _identity_checks_panel(zh_html).get_text()
    assert _SS_COVERAGE_FALLBACK["zh"] not in panel_text
    assert "{" not in panel_text, panel_text
    assert "}" not in panel_text, panel_text
    assert "':" not in panel_text, panel_text
    visible = _visible_page_text(zh_html)
    for name in ("left_value", "right_value", "values_read", "artifact", "reader", "check"):
        assert not re.search(rf"\b{name}\b", visible), (
            f"{name!r} leaked as visible text on the ZH page"
        )
    for name in (
        "owner_alias_reader", "security_set", "workspace_native_cik",
        "subject_ticker_display",
    ):
        assert name not in panel_text, (
            f"{name!r} leaked as visible text on the ZH Identity-checks panel"
        )


_PANEL_CUSTOMER_TOKENS = frozenset({
    "ISS", "SEC", "XNAS", "XNYS", "MSFT", "AAPL", "cik", "evt", "results",
    "CIK", "ISIN", "CUSIP", "NYSE", "NASDAQ",
})
_IDENTITY_CHECKS_MACHINE_TOKENS = (
    ".parquet", "::", "scripts/", "engine/", "data/",
    "lib.dataos", "engine.neuralweb", "parse_listing_key",
    "load_workspace_with_disposition", "event_workspace.v1",
    "SecurityStateSubject", "_read_security_state_identity_rows",
    "security_master", "issuer_master", "issuer_migrations",
    "security_migrations",
)
_CAMEL_RE = re.compile(r"\b[A-Z][a-z]+[A-Z][A-Za-z]+\b")
_DOTTED_MODULE_RE = re.compile(
    r"[A-Za-z_]+\.[A-Za-z_]+\.[A-Za-z_]+|[A-Za-z_]+\.[a-z_]+\("
)
_CALL_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\(")
_ALL_CAPS_SNAKE_RE = re.compile(r"\b[A-Z]{3,}(?:_[A-Z0-9]+)*\b")
_BARE_LITERAL_RE = re.compile(r"\b(?:true|false|null|None)\b")
_ZH_LATIN_RUN_RE = re.compile(r"[A-Za-z]{3,}")
# h7 REQUIRED (5): `.py` cannot join the substring tuple (consumed by
# `if token in text`). Word-boundary regex, never the bare substring "py".
_PY_RE = re.compile(r"\.py\b")

# h7 REQUIRED (3): discovery extractor over engine/security_state.py.
# Single-capture r'(\w*(?:state|status))\W{1,4}["\']([A-Za-z_]+)["\']' finds
# UNAVAILABLE at :681 and DIVERGENT at the :703/:704 comparisons (addendum:
# :691 is `= "AVAILABLE" if agrees else "DIVERGENT"` and the first literal
# wins). Identity-row assertion (c) uses a separate assignment/== scan of
# the four values_read keys so :691's DIVERGENT is still in the reachable set.
_ENGINE_STATE_STATUS_ASSIGN_RE = re.compile(
    r"""(\w*(?:state|status))\W{1,4}['"]([A-Za-z_]+)['"]"""
)
_QUOTED_TOKEN_RE = re.compile(r"""['"]([A-Za-z_]+)['"]""")
_IDENTITY_ROW_STATE_STATUS_KEYS = frozenset({
    "security_state", "issuer_state", "status", "corroboration_state",
})
_IDENTITY_ROW_ASSIGN_RE = re.compile(
    r"\b(?:security_state|issuer_state|corroboration_state|status)\b\s*(?:=|==)\s*(.+)$"
)


def _identity_checks_machine_hits(text: str, *, lang: str) -> list[str]:
    """Collect machine-text hits in Identity-checks visible text (ss-id stripped)."""
    hits: list[str] = []
    for token in _IDENTITY_CHECKS_MACHINE_TOKENS:
        if token in text:
            hits.append(token)
    for m in _PY_RE.finditer(text):
        hits.append(".py")
    for rx, label in (
        (_CAMEL_RE, "CamelCase"),
        (_DOTTED_MODULE_RE, "dotted-path"),
        (_CALL_RE, "call"),
        (_BARE_LITERAL_RE, "literal"),
        (_ALL_CAPS_SNAKE_RE, "ALL_CAPS"),
    ):
        for m in rx.finditer(text):
            tok = m.group(0)
            if tok in _PANEL_CUSTOMER_TOKENS:
                continue
            hits.append(f"{label}:{tok}")
    if "::" in text and "::" not in hits:
        hits.append("::")
    if lang == "zh":
        for m in _ZH_LATIN_RUN_RE.finditer(text):
            tok = m.group(0)
            if tok in _PANEL_CUSTOMER_TOKENS:
                continue
            hits.append(f"zh-latin:{tok}")
    return hits


def _extract_engine_state_status_tokens(src: str) -> set[str]:
    """Discovery (3)(a): group-2 of every *state/*status-then-quoted pair."""
    return {m.group(2) for m in _ENGINE_STATE_STATUS_ASSIGN_RE.finditer(src)}


def _walk_json_state_status_values(obj: object, *, keys: frozenset[str] | None) -> set[str]:
    """Collect string values of keys ending in state/status, optionally filtered."""
    found: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k.endswith(("state", "status")):
                if keys is None or k in keys:
                    if isinstance(v, str) and v:
                        found.add(v)
            found |= _walk_json_state_status_values(v, keys=keys)
    elif isinstance(obj, list):
        for item in obj:
            found |= _walk_json_state_status_values(item, keys=keys)
    return found


def _extract_engine_identity_row_tokens(src: str) -> set[str]:
    """Quoted literals assigned to (or ``==``-compared with) the four identity keys."""
    out: set[str] = set()
    for line in src.splitlines():
        m = _IDENTITY_ROW_ASSIGN_RE.search(line)
        if not m:
            continue
        for qm in _QUOTED_TOKEN_RE.finditer(m.group(1)):
            tok = qm.group(1)
            if tok not in _IDENTITY_ROW_STATE_STATUS_KEYS:
                out.add(tok)
    return out


def _identity_checks_panel_html(html: str) -> str:
    """The Identity-checks ``<section>`` HTML, ss-id spans included."""
    for m in re.finditer(r'<section class="dpanel">.*?</section>', html, flags=re.S):
        blob = m.group(0)
        if "Identity checks" in blob or "身份核对" in blob:
            return blob
    raise AssertionError("Identity checks panel HTML not found")


def _inject_identity_read_values(state: dict, updates: dict[str, object]) -> dict:
    """Copy *state* and overwrite matching ``values_read`` fields. Never writes disk."""
    clone = json.loads(json.dumps(state))
    remaining = dict(updates)
    for leg in clone.get("identity_proof", {}).get("legs") or []:
        for item in leg.get("values_read") or []:
            if isinstance(item, dict) and item.get("field") in remaining:
                item["value"] = remaining.pop(item["field"])
    assert not remaining, (
        "golden-MSFT values_read missing fields to inject: "
        + ", ".join(sorted(str(k) for k in remaining))
    )
    return clone


def test_identity_checks_panel_has_no_machine_text_on_golden_msft_and_m1() -> None:
    """Heal-round h6 REQUIRED 2: panel-wide machine-text guard.

    Renders golden-MSFT and M1 Identity-checks in EN and ZH, strips ``ss-id``
    subtrees (receipt chips and customer identifiers), and fails on CamelCase
    identifiers, dotted paths, parenthesised calls, ``::``, ``.parquet`` /
    ``.py``, ``scripts/`` / ``engine/`` / ``data/``, bare ``true`` / ``false``
    / ``null`` / ``None``, and ALL_CAPS_SNAKE of three or more letters.
    ZH additionally fails on a Latin run of three or more letters outside
    `_PANEL_CUSTOMER_TOKENS`. Supersedes
    ``test_golden_msft_identity_checks_panel_has_no_machine_text``.
    RED at b53b05b8 on reads values (VendorAliasTable.resolve(store),
    IssuerMaster.cik_of_issuer, IssuerMaster.issuer_of_security, true, null,
    RESOLVED, AVAILABLE, active).
    """
    from engine.security_state import MSFT_SUBJECT, compile_security_state_failure
    from jsonschema import Draft202012Validator, FormatChecker
    from scripts.build_ticker_pages import _SS_ARTIFACT, _SS_COVERAGE_FALLBACK

    pages: list[tuple[str, dict]] = []
    fixture = REPO / "tests" / "fixtures" / "security_state" / "golden_msft_expected_output.json"
    golden = json.loads(fixture.read_text(encoding="utf-8"))
    golden_view = build_security_state({"security_state": golden})
    assert golden_view is not None
    pages.append(("golden-msft", golden_view))

    schema_path = REPO / "contracts" / "market_os" / "security_state.v1.schema.json"
    validator = Draft202012Validator(
        json.loads(schema_path.read_text(encoding="utf-8")),
        format_checker=FormatChecker(),
    )
    m1 = compile_security_state_failure(
        subject=MSFT_SUBJECT, validator=validator, now="2026-01-01T00:00:00Z",
        prior_state=None, owner_read_completed=False,
    )
    m1_view = build_security_state({"security_state": m1})
    assert m1_view is not None
    pages.append(("m1", m1_view))

    failures: list[str] = []
    for label, view in pages:
        for lang in ("en", "zh"):
            html = _render_section(view, lang=lang)
            panel = _identity_checks_panel(html)
            scanned = _spaced_text(_without_ss_id(panel))
            hits = _identity_checks_machine_hits(scanned, lang=lang)
            for hit in hits:
                failures.append(f"{label}/{lang}: {hit}")
            for chk in panel.find_all_class("ss-chk"):
                chk_text = chk.get_text()
                passed = ("passed" in chk_text) if lang == "en" else ("通过" in chk_text)
                if passed:
                    assert _SS_COVERAGE_FALLBACK["zh"] not in chk_text, (
                        f"{label}/{lang} PASS row still has 暂不可用: {chk_text}"
                    )
    assert not failures, (
        "Identity-checks panel still prints machine text: " + "; ".join(failures)
    )

    m1_en = _identity_checks_panel(_render_section(pages[1][1], lang="en")).get_text()
    artifact_en = _SS_ARTIFACT[("R8", "IDENTITY_UNRESOLVED")]["en"]
    assert "(not a live owner record)" in artifact_en
    assert "(not a live owner record)" in m1_en, (
        "M1 EN artifact sentence missing from Identity-checks: " + m1_en
    )
    # h7 REQUIRED (5): \.py\b must not false-positive on the captured panels.
    for label, view in pages:
        for lang in ("en", "zh"):
            scanned = _spaced_text(_without_ss_id(
                _identity_checks_panel(_render_section(view, lang=lang))
            ))
            assert _PY_RE.search(scanned) is None, (
                f"{label}/{lang} false-positive on .py: {scanned}"
            )
            assert ".py" not in scanned


def test_identity_row_state_status_tokens_have_house_pairs() -> None:
    """h7 REQUIRED (3): every identity-row state/status token has a house pair.

    Discovery walks engine/security_state.py and tests/fixtures/security_state/*.json.
    The assertion is scoped to values reachable under the four identity
    values_read keys ending in state/status (addendum 2026-09-10 23:05Z):
    security_state, issuer_state, status, corroboration_state.
    RED-first at h6 head 9990a4a9: UNAVAILABLE, DIVERGENT,
    SUPERSEDED_DUPLICATE_MINT, NO_ISSUER_EVIDENCE missing from _SS_READ_VALUE.
    ``inactive`` is defensive vocabulary (not in either extractor half) and is
    guarded only by the injection test.
    """
    from scripts.build_ticker_pages import _SS_READ_KEY_VALUE, _SS_READ_VALUE

    engine_src = (REPO / "engine" / "security_state.py").read_text(encoding="utf-8")
    engine_tokens = _extract_engine_state_status_tokens(engine_src)
    assert "UNAVAILABLE" in engine_tokens, (
        "extractor missed UNAVAILABLE (expected at engine/security_state.py:681)"
    )
    assert "DIVERGENT" in engine_tokens, (
        "extractor missed DIVERGENT (expected at engine/security_state.py:703/:704; "
        "the :691 assignment yields AVAILABLE first under the single-capture regex)"
    )

    fixture_dir = REPO / "tests" / "fixtures" / "security_state"
    fixture_tokens: set[str] = set()
    fixture_identity: set[str] = set()
    for path in sorted(fixture_dir.glob("*.json")):
        blob = json.loads(path.read_text(encoding="utf-8"))
        fixture_tokens |= _walk_json_state_status_values(blob, keys=None)
        fixture_identity |= _walk_json_state_status_values(
            blob, keys=_IDENTITY_ROW_STATE_STATUS_KEYS,
        )

    engine_identity = _extract_engine_identity_row_tokens(engine_src)
    reachable = engine_identity | fixture_identity

    missing = sorted(
        tok for tok in reachable
        if tok not in _SS_READ_VALUE and tok not in _SS_READ_KEY_VALUE
    )
    assert not missing, (
        "identity-row state/status tokens missing a house pair: "
        + ", ".join(missing)
        + f" (discovery engine={sorted(engine_tokens)}; "
        f"fixtures={sorted(fixture_tokens)}; reachable={sorted(reachable)})"
    )


def test_identity_checks_injected_unmapped_state_tokens_render_as_house_copy() -> None:
    """h7 REQUIRED (4): inject UNAVAILABLE / SUPERSEDED_DUPLICATE_MINT / inactive
    into golden-MSFT at render time. The whole Identity-checks panel subtree
    (ss-id included) must show the house phrases and none of the three raw
    tokens, and the panel-wide machine scan must stay empty.
    RED-first at h6 head 9990a4a9: all three raw tokens printed inside ss-id.
    """
    # Frozen house phrases from REQUIRED (2) / addendum (6). Looked up as
    # literals so the RED-first run on the h6 mapper fails on the raw tokens
    # rather than KeyErroring on a table that does not yet contain them.
    house = {
        "UNAVAILABLE": {"en": "not available", "zh": "暂不可用"},
        "SUPERSEDED_DUPLICATE_MINT": {
            "en": "superseded (duplicate record)",
            "zh": "已被取代（重复记录）",
        },
        "inactive": {"en": "not active", "zh": "无效"},
    }

    fixture = REPO / "tests" / "fixtures" / "security_state" / "golden_msft_expected_output.json"
    golden = json.loads(fixture.read_text(encoding="utf-8"))
    injected = _inject_identity_read_values(golden, {
        "corroboration_state": "UNAVAILABLE",
        "security_state": "SUPERSEDED_DUPLICATE_MINT",
        "status": "inactive",
    })
    view = build_security_state({"security_state": injected})
    assert view is not None

    raw_tokens = ("UNAVAILABLE", "SUPERSEDED_DUPLICATE_MINT", "inactive")

    failures: list[str] = []
    for lang in ("en", "zh"):
        html = _render_section(view, lang=lang)
        panel = _identity_checks_panel(html)
        panel_html = _identity_checks_panel_html(html)
        slot = "en" if lang == "en" else "zh"
        for token in raw_tokens:
            if token in panel_html or token in panel.get_text():
                failures.append(f"{lang} still prints raw {token!r}")
            phrase = house[token][slot]
            if phrase not in panel_html:
                failures.append(f"{lang} missing house phrase {phrase!r}")
        scanned = _spaced_text(_without_ss_id(panel))
        hits = _identity_checks_machine_hits(scanned, lang=lang)
        for hit in hits:
            failures.append(f"{lang} machine-hit {hit}")
    assert not failures, (
        "injected identity-row tokens still leak or lack house copy: "
        + "; ".join(failures)
    )
    from scripts.build_ticker_pages import _SS_READ_VALUE
    for tok, pair in house.items():
        assert _SS_READ_VALUE[tok] == pair


def test_ss_id_is_only_reached_through_id_shapes() -> None:
    """h7 REQUIRED (1): ss-id only for `_SS_ID_SHAPES` (plus key-gated ticker/CUSIP).

    ALL_CAPS_SNAKE and bare lowercase never receive ss-id. DIVERGENT/AVAILABLE
    match the ungated CUSIP shape and STALE matches the ungated ticker shape;
    the key gates must hold or HOLE A returns. A code identifier with no
    house pair keeps the row as the dash pair.
    """
    from scripts.build_ticker_pages import (
        _SS_READ_ABSENT, _ss_is_id_shape, _ss_map_identity_read_value,
    )

    assert _ss_is_id_shape("XNAS:MSFT", "") is True
    assert _ss_is_id_shape("ISS:US-XNAS-MSFT", "") is True
    assert _ss_is_id_shape("US-XNAS-MSFT", "") is True
    assert _ss_is_id_shape("2026-09-04", "owner_decision_date") is True
    assert _ss_is_id_shape("MSFT", "subject_ticker_display") is True
    assert _ss_is_id_shape("MSFT", "status") is False
    assert _ss_is_id_shape("DIVERGENT", "corroboration_state") is False
    assert _ss_is_id_shape("AVAILABLE", "corroboration_state") is False
    assert _ss_is_id_shape("STALE", "corroboration_state") is False
    assert _ss_is_id_shape("UNAVAILABLE", "corroboration_state") is False
    assert _ss_is_id_shape("inactive", "status") is False

    for token, key in (
        ("UNAVAILABLE", "corroboration_state"),
        ("DIVERGENT", "corroboration_state"),
        ("SUPERSEDED_DUPLICATE_MINT", "security_state"),
        ("inactive", "status"),
        ("NO_ISSUER_EVIDENCE", "issuer_state"),
    ):
        mapped = _ss_map_identity_read_value(key, token, True)
        assert mapped is not None
        assert mapped["is_id"] is False, token
        assert mapped["en"] not in ("", "—") or token == "never", token

    dropped = _ss_map_identity_read_value(
        "unknown_reader", "VendorAliasTable.resolve(store)", True,
    )
    assert dropped is not None
    assert dropped["is_id"] is False
    assert dropped["en"] == _SS_READ_ABSENT["en"]


def test_identity_leg_house_copy_covers_golden_msft_m1_and_compile_failed_shell() -> None:
    """REQUIRED 1 (ii): every captured-path identity leg has a house
    description. Walks golden-MSFT, the M1 shell, and the :1805
    COMPILE_FAILED_AFTER_OWNER_CONFIRMED shell.
    """
    from engine.security_state import (
        MSFT_CIK, MSFT_ISSUER_ID, MSFT_LISTING_KEY, MSFT_SECURITY_ID,
        MSFT_SUBJECT, SecurityStateSubject, compile_security_state_failure,
    )
    from jsonschema import Draft202012Validator, FormatChecker
    from scripts.build_ticker_pages import _SS_LEG_DESC, _SS_LEG_HOUSE_BY_DESC

    def _desc_house(check: str, code: str | None, description: str):
        code = code or ""
        if code:
            return _SS_LEG_DESC.get((check, code))
        entry = _SS_LEG_HOUSE_BY_DESC.get((check, description or ""))
        if not entry:
            return None
        return _SS_LEG_DESC.get((check, "")) or entry.get("desc")

    missing: list[tuple[str, str, str]] = []

    def _walk(label: str, legs) -> None:
        for lg in legs:
            house = _desc_house(lg.get("check") or "", lg.get("code"), lg.get("description") or "")
            if not (house and house.get("en") and house.get("zh")):
                missing.append((label, lg.get("check") or "", lg.get("code") or ""))

    fixture = REPO / "tests" / "fixtures" / "security_state" / "golden_msft_expected_output.json"
    golden = json.loads(fixture.read_text(encoding="utf-8"))
    _walk("golden-msft", golden["identity_proof"]["legs"])

    schema_path = REPO / "contracts" / "market_os" / "security_state.v1.schema.json"
    validator = Draft202012Validator(
        json.loads(schema_path.read_text(encoding="utf-8")),
        format_checker=FormatChecker(),
    )
    m1 = compile_security_state_failure(
        subject=MSFT_SUBJECT, validator=validator, now="2026-01-01T00:00:00Z",
        prior_state=None, owner_read_completed=False,
    )
    _walk("m1", m1["identity_proof"]["legs"])

    owner_subject = SecurityStateSubject(
        security_id=MSFT_SECURITY_ID,
        issuer_id=MSFT_ISSUER_ID,
        listing_key=MSFT_LISTING_KEY,
        ticker_display="MSFT",
        issuer_cik=MSFT_CIK,
        owner_evidence=(
            ("decision_date", "2026-09-04"),
            ("alias_reader", "VendorAliasTable.resolve(store)"),
            ("issuer_reader", "IssuerMaster.issuer_of_security"),
            ("cik_reader", "IssuerMaster.cik_of_issuer"),
        ),
    )
    shell = compile_security_state_failure(
        subject=owner_subject, validator=validator, now="2026-01-01T00:00:00Z",
        prior_state=None, owner_read_completed=True,
    )
    assert shell["legs"]["opportunity_context"]["entry"]["null_reason"] == (
        "COMPILE_FAILED_AFTER_OWNER_CONFIRMED"
    )
    assert any(
        (lg.get("check") == "R8" and not lg.get("code"))
        for lg in shell["identity_proof"]["legs"]
    ), "expected the :1805 code-less R8 PASS shell"
    _walk("compile-failed-after-owner-confirmed", shell["identity_proof"]["legs"])

    assert not missing, f"identity legs missing house description: {missing}"


def test_golden_msft_identity_checks_equalities_are_labeled_rows_not_dict_reprs() -> None:
    """Heal-round h4 REQUIRED 1: equalities are view-model rows with a frozen
    label, the two values, and a match/differ verdict — never a Python dict
    repr. EN and ZH Identity-checks sections contain no dict-repr markers,
    and every equality row carries a label.
    """
    from scripts.build_ticker_pages import _SS_EQUALITY

    fixture = REPO / "tests" / "fixtures" / "security_state" / "golden_msft_expected_output.json"
    state = json.loads(fixture.read_text(encoding="utf-8"))
    view = build_security_state({"security_state": state})
    assert view is not None
    rows = view["identity"]["equalities"]
    assert rows, "golden MSFT carries equality receipts"
    emitted = {e["check"] for e in state["identity_proof"]["equalities"]}
    missing = emitted - set(_SS_EQUALITY)
    assert not missing, f"_SS_EQUALITY missing engine checks: {sorted(missing)}"
    for row in rows:
        assert isinstance(row, dict), f"equality must be a row dict, got {row!r}"
        assert row["label_en"], f"{row.get('check')!r}: missing EN label"
        assert row["label_zh"], f"{row.get('check')!r}: missing ZH label"
        assert re.search(r"[一-鿿]", row["label_zh"])
        assert row["label_en"] != row["label_zh"]
        assert row["verdict_en"] in ("match", "differ")
        assert row["verdict_zh"] in ("一致", "不一致")
        assert "{" not in row["label_en"] and "{" not in row["label_zh"]
    for lang in ("en", "zh"):
        html = _render_section(view, lang=lang)
        panel = _identity_checks_panel(html)
        text = panel.get_text()
        notes = panel.find_all_class("dnotes")
        assert notes, f"{lang} Identity-checks missing equalities list"
        # REQUIRED 1 RED-first: the whole Identity-checks *section* (not just
        # the equalities list) contains no dict-repr / set-repr markers.
        # Pinning only `.dnotes` left `{SEC:…}` in the R4 description green.
        assert "{" not in text, f"{lang} Identity-checks still has '{{': {text}"
        assert "}" not in text, f"{lang} Identity-checks still has '}}': {text}"
        assert "':" not in text, f"{lang} Identity-checks still has dict-repr \"'\": {text}"
        for row in rows:
            label = row["label_en"] if lang == "en" else row["label_zh"]
            assert label in text, f"{lang} Identity-checks missing label {label!r}"


def test_golden_msft_identity_checks_read_fields_are_plain_labels() -> None:
    """Round-2 review MINOR 2: Identity-checks `values_read` keys render as
    frozen EN/ZH labels, never as engine field names (`owner_alias_reader`,
    `security_set`, `workspace_native_cik`, `subject_ticker_display`).
    """
    from scripts.build_ticker_pages import _SS_READ_FIELD

    fixture = REPO / "tests" / "fixtures" / "security_state" / "golden_msft_expected_output.json"
    state = json.loads(fixture.read_text(encoding="utf-8"))
    view = build_security_state({"security_state": state})
    assert view is not None
    emitted: set[str] = set()
    for lg in state["identity_proof"]["legs"]:
        for pair in lg.get("values_read") or []:
            emitted.add(pair["field"])
    missing = emitted - set(_SS_READ_FIELD)
    assert not missing, f"_SS_READ_FIELD missing engine fields: {sorted(missing)}"
    for lg in view["identity"]["legs"]:
        for row in lg["reads"]:
            assert row["label_en"], f"{row['k']!r}: missing EN label"
            assert row["label_zh"], f"{row['k']!r}: missing ZH label"
            assert re.search(r"[一-鿿]", row["label_zh"]), row["label_zh"]
            assert row["label_en"] != row["label_zh"]
    banned = (
        "owner_alias_reader", "security_set", "workspace_native_cik",
        "subject_ticker_display",
    )
    for lang in ("en", "zh"):
        html = _render_section(view, lang=lang)
        panel_text = _identity_checks_panel(html).get_text()
        for name in banned:
            assert name not in panel_text, (
                f"{lang} Identity-checks still shows engine field {name!r}"
            )
        for lg in view["identity"]["legs"]:
            for row in lg["reads"]:
                label = row["label_en"] if lang == "en" else row["label_zh"]
                assert label in panel_text, (
                    f"{lang} Identity-checks missing field label {label!r}"
                )


def test_unknown_equality_check_falls_back_to_ss_id_never_a_repr() -> None:
    """Heal-round h4 REQUIRED 1: an unknown `check` key renders inside
    `<span class="ss-id">`, never as a Python dict repr.
    """
    contract = _contract()
    contract["identity_proof"]["equalities"] = [{
        "check": "R99",
        "left": "left.field",
        "left_value": "1",
        "right": "right.field",
        "right_value": "2",
        "equal": False,
    }]
    view = build_security_state({"security_state": contract})
    assert view is not None
    row = view["identity"]["equalities"][0]
    assert row["check"] == "R99"
    assert row["label_en"] == ""
    assert row["label_zh"] == ""
    assert row["verdict_en"] == "differ"
    assert row["verdict_zh"] == "不一致"
    html = _render_section(view, lang="en")
    assert '<span class="ss-id">R99</span>' in html
    assert "{'check'" not in html
    assert '"check":' not in html


def test_m1_zh_page_reason_text_has_no_latin_letters() -> None:
    """Heal-round h4 REQUIRED 2: M1 ZH reason slots are house copy, never
    English prose and never a Latin-letter reason.
    """
    from engine.security_state import MSFT_SUBJECT, compile_security_state_failure
    from jsonschema import Draft202012Validator, FormatChecker
    from scripts.build_ticker_pages import _SS_REASON

    schema_path = REPO / "contracts" / "market_os" / "security_state.v1.schema.json"
    validator = Draft202012Validator(
        json.loads(schema_path.read_text(encoding="utf-8")),
        format_checker=FormatChecker(),
    )
    state = compile_security_state_failure(
        subject=MSFT_SUBJECT, validator=validator, now="2026-01-01T00:00:00Z",
        prior_state=None, owner_read_completed=False,
    )
    view = build_security_state({"security_state": state})
    assert view is not None
    prophet_house = _SS_REASON["PROPHET_OWNER_OUTPUT_ABSENT"]
    owner_house = _SS_REASON["OWNER_IDENTITY_BATCH_UNAVAILABLE"]
    for s in _axis(view, "opportunity_context")["subreads"]:
        if s["reason_zh"]:
            assert not re.search(r"[A-Za-z]", s["reason_zh"]), (
                f"M1 ZH reason still has Latin letters: {s['reason_zh']!r}"
            )
    zh_html = _render_section(view, lang="zh")
    assert prophet_house["zh"] in zh_html
    assert owner_house["zh"] in zh_html
    assert prophet_house["en"] not in zh_html
    assert "no current Prophet US owner output" not in zh_html
    assert "PROPHET_OWNER_OUTPUT_ABSENT" not in zh_html
    assert "subject_ticker_display" not in _identity_checks_panel(zh_html).get_text()


def test_ss_map_subread_reason_prose_keeps_en_and_falls_back_zh() -> None:
    """Heal-round h4 REQUIRED 2: the mapper's last branch keeps engine prose
    in EN and never copies it into ZH.
    """
    from scripts.build_ticker_pages import _SS_COVERAGE_FALLBACK, _ss_map_subread_reason

    en, zh = _ss_map_subread_reason("some unmapped engine sentence")
    assert en == "some unmapped engine sentence"
    assert zh == _SS_COVERAGE_FALLBACK["zh"]
    assert en != zh


def test_m1_failed_gate_is_owner_identity_not_compiler_failure() -> None:
    """Heal-round h4 REQUIRED 3: M1 failed_gates carries
    OWNER_IDENTITY_BATCH_UNAVAILABLE, never COMPILER_FAILURE's
    'Read could not be built' false cause.
    """
    from engine.security_state import MSFT_SUBJECT, compile_security_state_failure
    from jsonschema import Draft202012Validator, FormatChecker
    from scripts.build_ticker_pages import _SS_GATES

    schema_path = REPO / "contracts" / "market_os" / "security_state.v1.schema.json"
    validator = Draft202012Validator(
        json.loads(schema_path.read_text(encoding="utf-8")),
        format_checker=FormatChecker(),
    )
    state = compile_security_state_failure(
        subject=MSFT_SUBJECT, validator=validator, now="2026-01-01T00:00:00Z",
        prior_state=None, owner_read_completed=False,
    )
    gate = state["legs"]["risk"]["failed_gates"][0]
    assert gate["code"] == "OWNER_IDENTITY_BATCH_UNAVAILABLE"
    assert gate["reason"] == "OWNER_IDENTITY_BATCH_UNAVAILABLE"
    house = _SS_GATES["OWNER_IDENTITY_BATCH_UNAVAILABLE"]
    assert house["en"] == "Owner-identity read did not run"
    assert house["zh"] == "未执行所有者身份读取"
    view = build_security_state({"security_state": state})
    assert view is not None
    rendered = next(
        g for a in view["axes"] for g in a["gates"]
        if g["code"] == "OWNER_IDENTITY_BATCH_UNAVAILABLE"
    )
    assert rendered["en"] == house["en"]
    assert rendered["zh"] == house["zh"]
    zh_html = _render_section(view, lang="zh")
    assert house["zh"] in zh_html
    # Dominant degradation stays COMPILER_FAILURE (the shell still did not
    # compile). The false-cause residue was the failed_gates CODE, which
    # must render this house pair and not the compiler-failure sentence.
    assert f'<span class="c ss-id">{gate["code"]}</span>' in zh_html
    risk_panel = next(
        (p for p in _parse_class_tree(zh_html).find_all_class("ss-gate")
         if house["zh"] in p.get_text()),
        None,
    )
    assert risk_panel is not None, "M1 failed-gate house copy missing from the gate receipt"
    assert "读数无法生成" not in risk_panel.get_text()
    assert "Read could not be built" not in risk_panel.get_text()


# ---------------------------------------------------------------------------
# B-F06-3 · second-issuer cockpit — eight B1B panels, personal_impact refolded
# ---------------------------------------------------------------------------

# Freeze §3 panel names in the freeze's own order. Overview and Owner & model
# receipts use the packet copy table; Evidence is the freeze panel name;
# the five remaining axis cards keep the titles #6920 shipped and map 1:1
# onto freeze panels 4, 3, 5, 6, 7. Visible document order is Overview, then
# those five axis cards in `_SS_AXES` order, then Evidence, then Owner &
# model receipts — the packet spec pins Overview before `.ss-grid`.
_B1B_HEADINGS_EN = (
    "Overview",
    "Where it stands",
    "What changed",
    "Opportunity context",
    "What could go wrong",
    "What to watch next",
    "Evidence",
    "Owner & model receipts",
)
_FREEZE_NOT_APPLICABLE_EN = "This does not apply to you right now."
_FREEZE_NOT_APPLICABLE_ZH = "这暂不适用于你。"


def _heading_label(node: _HtmlNode) -> str:
    """The panel name, never the coverage chip sitting in the same heading."""
    for child in node.children:
        if "ss-chip" in child.classes:
            continue
        text = " ".join(child.get_text().split())
        if text:
            return text
    return " ".join(node.get_text().split())


def _visible_b1b_headings(html: str) -> list[str]:
    """Named B1B panel headings inside `#security-state`, never dialog chrome."""
    section = _card_region(html)
    wrapped = "<section " + section[section.find("id="):]
    tree = _parse_class_tree(wrapped)
    return [_heading_label(node) for node in tree.find_all_class("ss-b1b-h") if _heading_label(node)]


def test_personal_impact_is_no_longer_rendered_as_a_sixth_axis_card() -> None:
    view = build_security_state({"security_state": _contract()})
    assert view is not None
    assert len(view["axes"]) == 5
    assert [a["key"] for a in view["axes"]] == [
        "state", "change", "opportunity_context", "risk", "catalyst",
    ]
    assert all(a["key"] != "personal_impact" for a in view["axes"])


def test_overview_carries_only_state_summary() -> None:
    """Overview keeps only `state_summary`. The template reads coverage,
    degradation, and the personal-impact row from the top-level view.
    """
    view = build_security_state({"security_state": _contract()})
    assert view is not None
    assert set(view["overview"]) == {"state_summary"}
    assert view["personal_impact"]["key"] == "personal_impact"


def test_personal_impact_not_applicable_prints_the_freeze_registered_sentence() -> None:
    contract = _contract()
    assert contract["legs"]["personal_impact"]["coverage_state"] == "NOT_APPLICABLE"
    view = build_security_state({"security_state": contract})
    assert view is not None
    row = view["personal_impact"]
    assert row["headline"]["en"] == _FREEZE_NOT_APPLICABLE_EN
    assert row["headline"]["zh"] == _FREEZE_NOT_APPLICABLE_ZH
    assert "NOT_APPLICABLE" not in row["headline"]["en"]
    assert "NOT_APPLICABLE" not in row["headline"]["zh"]

    en_card = _card_region(_render_section(view, lang="en"))
    zh_card = _card_region(_render_section(view, lang="zh"))
    assert _FREEZE_NOT_APPLICABLE_EN in en_card
    assert _FREEZE_NOT_APPLICABLE_ZH in zh_card
    assert "NOT_APPLICABLE" not in en_card
    assert "NOT_APPLICABLE" not in zh_card


def test_owner_model_receipts_surfaces_identity_legs_asof_and_content_sha256() -> None:
    view = build_security_state({"security_state": _contract()})
    assert view is not None
    receipts = view["owner_receipts"]
    assert receipts["legs"] is view["identity"]["legs"]
    assert receipts["generated_at"] == view["generated_at"]
    assert receipts["compiled_at"] == view["compiled_at"]
    assert receipts["content_sha256"] == view["content_sha256"]
    assert receipts["content_sha256"]
    assert receipts["generated_at"]
    assert receipts["compiled_at"]


def test_owner_receipts_glance_uses_bilingual_house_copy_not_engine_prose() -> None:
    """B-F06-3 round-2 review MAJOR-1.

    The always-visible Owner & model receipts panel printed English engine
    prose (`security_master row exists…`) and machine identifiers (python
    paths, parquet paths, field slugs) at glance, including on the ZH page.
    Spec MAJOR: EN==ZH on a sentence that should differ. Glance copy must be
    a registered bilingual sentence; artifact/reader/reads stay in the
    evidence dialog.
    """
    from scripts.build_ticker_pages import _SS_LEG_DESC, _SS_LEG_HOUSE_BY_DESC

    fixture = REPO / "tests" / "fixtures" / "security_state" / "golden_msft_expected_output.json"
    state = json.loads(fixture.read_text(encoding="utf-8"))
    view = build_security_state({"security_state": state})
    assert view is not None
    legs = view["identity"]["legs"]
    assert [lg["check"] for lg in legs] == [f"R{i}" for i in range(1, 10)]
    fixture_legs = state["identity_proof"]["legs"]
    assert len(fixture_legs) == len(legs)
    for src, lg in zip(fixture_legs, legs):
        house = _SS_LEG_DESC[(lg["check"], lg["code"] or "")]
        raw = src["description"]
        assert lg["desc_en"] == house["en"]
        assert lg["desc_zh"] == house["zh"]
        assert lg["desc_en"] != lg["desc_zh"]
        assert lg["desc_en"] != raw
        assert lg["desc_zh"] != raw
        assert re.search(r"[一-鿿]", lg["desc_zh"]), lg["desc_zh"]

    zh_card = _card_region(_render_section(view, lang="zh"))
    en_card = _card_region(_render_section(view, lang="en"))
    # The reader value the receipt carries, and the bare module path inside it.
    # Spelled through the reference form on purpose: a bare repo-path literal is
    # recorded as a CI trigger-closure read (scripts/ci_scope_dependencies.py:588
    # -600), and this suite never imports that module — the path is a STRING
    # RENDERED INTO THE PAGE that these assertions search for, not a dependency.
    reader_ref = "scripts/build_stock_library.py::_read_security_state_identity_rows"
    reader_module = reader_ref.split("::", 1)[0]
    engine_leaks = (
        "security_master row exists",
        "security_state/superseded_by",
        reader_module,
        "data/reference/security_master.parquet",
        "VendorAliasTable.resolve",
        "row_present",
        "lib.dataos.identity.parse_listing_key",
        "issuer_migrations.parquet",
        "event_workspace.v1",
        "owner-composed",
    )
    for leak in engine_leaks:
        assert leak not in zh_card, leak
        assert leak not in en_card, leak
    for lg in legs:
        assert lg["desc_zh"] in zh_card
        assert lg["desc_en"] in en_card
        assert lg["desc_en"] not in zh_card
    assert "The panels below" in en_card
    assert "以下面板" in zh_card
    assert "八个面板" not in zh_card
    assert "eight panels" not in en_card
    assert "Eight reads on this listing" not in en_card
    assert "Eight separate reads" not in en_card
    assert "八项读数" not in zh_card

    # Artifact/reader rows are house sentences, never the engine paths.
    # Field values stay in the receipt dialog. After #6920 h7, the owner-alias
    # reader value is projected through `_SS_READ_KEY_VALUE` as house copy
    # ("the vendor alias table" / "供应商别名表"), not the raw token.
    full_en = _render_section(view, lang="en")
    full_zh = _render_section(view, lang="zh")
    assert "data/reference/security_master.parquet" not in full_en
    assert reader_module not in full_en
    assert "the vendor alias table" in full_en
    assert "供应商别名表" in full_zh
    r1 = _SS_LEG_HOUSE_BY_DESC[(
        "R1", "security_master row exists, security_state/superseded_by both null",
    )]
    assert r1["artifact"]["en"] in full_en
    assert r1["reader"]["en"] in full_en


def test_ticker_page_renders_all_eight_b1b_panel_headings_for_msft() -> None:
    fixture = REPO / "tests" / "fixtures" / "security_state" / "golden_msft_expected_output.json"
    state = json.loads(fixture.read_text(encoding="utf-8"))
    view = build_security_state({"security_state": state})
    assert view is not None
    html = _render_section(view)
    headings = _visible_b1b_headings(html)
    assert headings == list(_B1B_HEADINGS_EN), headings


def test_aapl_page_still_renders_five_axis_cards_after_the_personal_impact_extraction() -> None:
    fixture = REPO / "tests" / "fixtures" / "security_state" / "golden_aapl_expected_output.json"
    state = json.loads(fixture.read_text(encoding="utf-8"))
    view = build_security_state({"security_state": state})
    assert view is not None
    html = _render_section(view)
    tree = _parse_class_tree(html)
    grid = tree.find_class("ss-grid")
    assert grid is not None
    # `.ss-cell` descendants of the grid — the grid itself is not an ss-cell.
    cards = grid.find_all_class("ss-cell")
    assert len(cards) == 5, [c.find_class("ss-axis").get_text() if c.find_class("ss-axis") else "?" for c in cards]
    texts = [c.get_text() for c in cards]
    assert all("Your position" not in t and "你的持仓" not in t for t in texts)


def test_subhead_does_not_assert_a_count_the_page_contradicts() -> None:
    """Lead copy must not name a read-count the same screen contradicts
    (5 axis cards, 8 freeze panels, 7 coverage legs). The section hint
    names the panel count the page actually renders — see
    test_section_hint_counts_the_panels_the_page_renders — as
    ``f"{n} panels"`` / ``f"{n} 个面板"``. Numeral "reads" forms stay banned.
    """
    fixture = REPO / "tests" / "fixtures" / "security_state" / "golden_msft_expected_output.json"
    state = json.loads(fixture.read_text(encoding="utf-8"))
    view = build_security_state({"security_state": state})
    assert view is not None
    en_card = _card_region(_render_section(view, lang="en"))
    zh_card = _card_region(_render_section(view, lang="zh"))
    for banned in (
        "Eight separate reads",
        "Eight reads on this listing",
        "eight panels",
        "Eight panels",
        "8 reads",
    ):
        assert banned not in en_card, banned
    for banned in ("八项独立读数", "八项读数", "八个面板", "8 项读数"):
        assert banned not in zh_card, banned
    assert "The panels below" in en_card
    assert "以下面板" in zh_card


def test_state_sentence_prints_once_on_the_surface() -> None:
    """Overview always carries the state headline; the grid's state card drops
    it whenever the card has its own explanatory clause to print, so the
    sentence appears once on the surface (design system §9.5, printed once).

    The one case where the card does reprint it is a stance that yields no
    clause, where the alternative is a card of heading and chip with no prose
    at all — see test_state_card_prints_its_headline_when_it_has_no_clause.
    """
    view = build_security_state({"security_state": _contract()})
    assert view is not None
    en_card = _card_region(_render_section(view, lang="en"))
    zh_card = _card_region(_render_section(view, lang="zh"))
    assert en_card.count("Worth monitoring") == 1
    assert zh_card.count("值得关注") == 1
    wrapped = "<section " + en_card[en_card.find("id="):]
    tree = _parse_class_tree(wrapped)
    grid = tree.find_class("ss-grid")
    assert grid is not None
    state_card = grid.find_all_class("ss-cell")[0]
    assert "Worth monitoring" not in state_card.get_text()


def test_personal_impact_failed_gates_reach_the_tally_and_receipt_dialog() -> None:
    """The Overview refold must not drop personal_impact gates from the
    aggregated tally or retire its receipt dialog.
    """
    contract = _contract()
    contract["legs"]["personal_impact"]["failed_gates"] = [{"code": "RIGHTS_WITHHELD"}]
    view = build_security_state({"security_state": contract})
    assert view is not None
    assert any(g["code"] == "RIGHTS_WITHHELD" for g in view["gates"])
    html = _render_section(view)
    assert 'id="dlg-ss-personal-impact"' in html
    glance = _card_region(html)
    assert "dsrOpenDlg('dlg-ss-personal-impact')" in glance
    assert len(view["axes"]) == 5
    assert all(a["key"] != "personal_impact" for a in view["axes"])


def test_no_new_panel_reads_a_rank_score_size_or_gate_field() -> None:
    """New cockpit code may only read the frozen object. It must not assign
    any `can_*` authority key to true, and it must not mint a rank, score,
    size or gate value of its own (DNR:KILL-CAUSAL-DAG-ALPHA).
    """
    py_src = (REPO / "scripts" / "build_ticker_pages.py").read_text(encoding="utf-8")
    j2_src = (REPO / "templates" / "ticker.html.j2").read_text(encoding="utf-8")
    # Restrict the Python scan to the security-state projection — the rest of
    # the dossier builder already talks about scores on other surfaces.
    start = py_src.index("# Security State (security_state.v1)")
    end = py_src.index("# Main context builder", start)
    ss_py = py_src[start:end]
    for key in (
        "can_rank", "can_gate", "can_size",
        "can_originate_signal", "can_execute",
    ):
        for label, src in (("build_ticker_pages.py", ss_py), ("ticker.html.j2", j2_src)):
            assert f"{key}=True" not in src.replace(" ", ""), (
                f"{label} assigns {key} to true"
            )
            assert f"{key} = True" not in src, f"{label} assigns {key} to true"
            assert f'"{key}": True' not in src and f"'{key}': True" not in src, (
                f"{label} sets {key} true in a literal"
            )
    for banned in ("rank_score", "size_score", "gate_score", "llm_confidence"):
        assert banned not in ss_py, f"new authority field {banned!r} in the projection"
        assert banned not in j2_src, f"new authority field {banned!r} in the template"



# ---------------------------------------------------------------------------
# B-F06-3 round 3 — an empty leg code is not a synonym for "this check proved
# out". These three pin the guard that keeps the affirmative empty-code copy
# off the legs the engine passed vacuously or carried through a failure shell.
# ---------------------------------------------------------------------------

_SCREAMING_SNAKE = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")

_CARRIED_OVER_EN = "Carried over from the owner read; not re-verified in this read."
_CARRIED_OVER_ZH = "沿用所有者读数中的识别码，本次读数未重新核对。"
_R9_UNAVAILABLE_EN = "No workspace listing was available to compare this cycle."
_R9_UNAVAILABLE_ZH = "本周期没有可比对的工作区上市记录。"


def _owner_receipts_article(html: str) -> _HtmlNode:
    """The always-visible `Owner & model receipts` panel, never the dialog."""
    section = _card_region(html)
    tree = _parse_class_tree("<section " + section[section.find("id="):])
    for node in tree.find_all_class("ss-cell"):
        head = node.find_class("ss-axis")
        if head is not None and _heading_label(head) in (
            "Owner & model receipts", "所有者与模型凭证",
        ):
            return node
    raise AssertionError("the Owner & model receipts panel did not render")


def _compiler_failure_shell(*, owner_read_completed: bool = True) -> dict:
    """The producer's own containment shell, compiled by the real engine."""
    from jsonschema import Draft202012Validator

    from engine import security_state as ss_engine

    schema = json.loads(
        (REPO / "contracts" / "market_os" / "security_state.v1.schema.json")
        .read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    subject = ss_engine.SecurityStateSubject(
        security_id="SEC:US-XNAS-MSFT", issuer_id="ISS:US-XNAS-MSFT",
        listing_key="US-XNAS-MSFT", ticker_display="MSFT", issuer_cik="0000789019",
        owner_evidence=(
            ("decision_date", "2026-09-04"),
            ("alias_reader", "VendorAliasTable.resolve(store)"),
            ("issuer_reader", "IssuerMaster.issuer_of_security"),
            ("cik_reader", "IssuerMaster.cik_of_issuer"),
        ),
    )
    return ss_engine.compile_security_state_failure(
        subject=subject, validator=Draft202012Validator(schema),
        now="2026-08-23T12:00:00Z", prior_state=None,
        owner_read_completed=owner_read_completed,
    )


def test_compiler_failure_shell_r8_never_claims_a_check_this_read_did_not_run() -> None:
    """The default failure path emits one R8 leg with result "pass" and a null
    code, and says in its own words that it does NOT claim a full identity
    chain. The affirmative empty-code house sentence must never print there —
    it would be a bilingual verification claim on the page whose own banner
    says the read could not be built.
    """
    from scripts.build_ticker_pages import _SS_LEG_DESC

    state = _compiler_failure_shell(owner_read_completed=True)
    assert state["identity_proof"]["state"] == "BLOCKED_IDENTITY_BRIDGE"
    raw_legs = state["identity_proof"]["legs"]
    assert [lg["check"] for lg in raw_legs] == ["R8"]
    assert raw_legs[0]["result"] == "pass" and raw_legs[0]["code"] is None

    view = build_security_state({"security_state": state})
    assert view is not None
    leg = view["identity"]["legs"][0]
    affirmative = _SS_LEG_DESC[("R8", "")]
    assert leg["desc_en"] != affirmative["en"]
    assert leg["desc_zh"] != affirmative["zh"]
    assert leg["desc_en"] == _CARRIED_OVER_EN
    assert leg["desc_zh"] == _CARRIED_OVER_ZH
    assert leg["result_en"] not in ("passed",) and leg["result_zh"] not in ("通过",)
    assert leg["result_en"] == "carried over" and leg["result_zh"] == "沿用"
    assert leg["ok"] is False
    # The engine's own verdict is reported, never edited.
    assert leg["result"] == "pass"

    en_html = _render_section(view, lang="en")
    zh_html = _render_section(view, lang="zh")
    assert 'data-ss-result="pass"' in en_html
    en_glance = " ".join(_owner_receipts_article(en_html).get_text().split())
    zh_glance = " ".join(_owner_receipts_article(zh_html).get_text().split())
    assert affirmative["en"] not in en_glance
    assert affirmative["zh"] not in zh_glance
    assert _CARRIED_OVER_EN in en_glance
    assert _CARRIED_OVER_ZH in zh_glance
    assert "passed" not in en_glance
    assert "通过" not in zh_glance
    # The engine's hedged machine sentence never reaches the glance surface.
    assert "without claiming" not in en_glance


def test_blocked_identity_bridge_hedges_every_empty_code_leg() -> None:
    """The guard is on the receipt's identity-proof state, not on one check id."""
    from scripts.build_ticker_pages import _SS_LEG_DESC

    contract = _contract(identity_proof={
        "state": "BLOCKED_IDENTITY_BRIDGE", "method": "owner_backed_chain.v1",
        "legs": [
            {"check": check, "description": "engine machine sentence",
             "artifact": "a", "reader": "b",
             "values_read": [{"field": "row_present", "value": True}],
             "result": "pass", "code": None}
            for check in ("R1", "R5", "R8")
        ],
        "equalities": [], "refusals": ["COMPILER_FAILURE"], "disclosures": [],
    })
    view = build_security_state({"security_state": contract})
    assert view is not None
    for leg in view["identity"]["legs"]:
        assert leg["desc_en"] == _CARRIED_OVER_EN, leg["check"]
        assert leg["desc_zh"] == _CARRIED_OVER_ZH, leg["check"]
        assert leg["desc_en"] != _SS_LEG_DESC[(leg["check"], "")]["en"]
        assert leg["result_en"] == "carried over" and leg["result_zh"] == "沿用"


def test_r9_vacuous_pass_reports_that_no_workspace_listing_was_compared() -> None:
    """`corroboration_state: UNAVAILABLE` is a pass with nothing compared. The
    panel says so instead of asserting an agreement that was never checked.
    """
    from scripts.build_ticker_pages import _SS_LEG_DESC

    def _r9(corroboration: str | None) -> dict:
        values_read = ([] if corroboration is None
                       else [{"field": "corroboration_state", "value": corroboration}])
        return _contract(identity_proof={
            "state": "PROVEN", "method": "owner_backed_chain.v1",
            "legs": [{
                "check": "R9",
                "description": "corroboration: workspace primary alias agrees with the "
                               "owner subject's current alias and listing venue",
                "artifact": "event_workspace.v1 issuer.listings[]",
                "reader": "engine.neuralweb.company_intelligence_reader."
                          "load_workspace_with_disposition",
                "values_read": values_read, "result": "pass", "code": None,
            }],
            "equalities": [], "refusals": [], "disclosures": [],
        })

    affirmative = _SS_LEG_DESC[("R9", "")]

    view = build_security_state({"security_state": _r9("UNAVAILABLE")})
    assert view is not None
    leg = view["identity"]["legs"][0]
    assert leg["desc_en"] == _R9_UNAVAILABLE_EN
    assert leg["desc_zh"] == _R9_UNAVAILABLE_ZH
    assert leg["desc_en"] != affirmative["en"]
    assert leg["result_en"] == "not checked" and leg["result_zh"] == "未核对"
    assert leg["result_en"] != "passed" and leg["result_zh"] != "通过"
    assert leg["result"] == "pass"
    en_glance = " ".join(_owner_receipts_article(_render_section(view, "en")).get_text().split())
    zh_glance = " ".join(_owner_receipts_article(_render_section(view, "zh")).get_text().split())
    assert _R9_UNAVAILABLE_EN in en_glance and affirmative["en"] not in en_glance
    assert _R9_UNAVAILABLE_ZH in zh_glance and affirmative["zh"] not in zh_glance
    assert "passed" not in en_glance and "通过" not in zh_glance

    # A receipt that records no corroboration state at all cannot tell a real
    # comparison from a vacuous one, so the sentence is presence-hedged.
    silent = build_security_state({"security_state": _r9(None)})
    assert silent is not None
    silent_leg = silent["identity"]["legs"][0]
    assert silent_leg["desc_en"].startswith("The workspace primary listing, when present,")
    assert silent_leg["desc_zh"].startswith("若有工作区上市记录")
    assert silent_leg["desc_en"] != silent_leg["desc_zh"]

    # A real comparison still earns the affirmative sentence and the real label.
    available = build_security_state({"security_state": _r9("AVAILABLE")})
    assert available is not None
    available_leg = available["identity"]["legs"][0]
    assert available_leg["desc_en"] == affirmative["en"]
    assert available_leg["desc_zh"] == affirmative["zh"]
    assert available_leg["result_en"] == "passed"


def test_no_screaming_snake_token_reaches_the_owner_receipts_glance_panel() -> None:
    """No SCREAMING_SNAKE machine token — refusal code, field slug, store or
    reader name — reaches the always-visible glance tier; the raw refusal code
    chip stays inside `dlg-ss-evidence`.

    That is the whole of it, and the name says so. It does NOT establish that
    the glance tier carries no machine-looking string at all: each row's short
    label is the leg's own check id (R1…R9), which is the frozen spec's leg
    numbering, identical in EN and ZH, already shown in the base's drilldown,
    and deliberately kept — and no underscore-requiring regex could catch it.
    A later round must not lean on this test for more than its assertion.
    """
    codes = ("IDENTITY_UNRESOLVED", "IDENTITY_BRIDGE_DISAGREEMENT",
             "LISTING_KEY_INCOHERENT", "SUBJECT_NATIVE_PARITY_FAILED")
    contract = _contract(identity_proof={
        "state": "BLOCKED_IDENTITY_BRIDGE", "method": "owner_backed_chain.v1",
        "legs": [{
            "check": f"R{i}", "description": "engine machine sentence",
            "artifact": "data/reference/security_master.parquet",
            "reader": "scripts/build_stock_library.py::_read_security_state_identity_rows",
            "values_read": [], "result": "fail", "code": code,
        } for i, code in enumerate(codes, start=5)],
        "equalities": [], "refusals": list(codes), "disclosures": [],
    })
    view = build_security_state({"security_state": contract})
    assert view is not None
    for lang in ("en", "zh"):
        html = _render_section(view, lang=lang)
        glance = " ".join(_owner_receipts_article(html).get_text().split())
        assert not _SCREAMING_SNAKE.findall(glance), (lang, glance)
        for code in codes:
            assert code not in glance, (lang, code)
            # …and it is still on the page, in the receipt dialog.
            assert code in html, (lang, code)


# ---------------------------------------------------------------------------
# B-F06-3 round 5 — the always-visible receipts panel must say something true,
# in both languages, on every path the engine can actually produce; and the
# section's own copy must count what the page really renders.
# ---------------------------------------------------------------------------

_R8_PROVEN_EN = ("The master company identifier matches the owner read; "
                 "if a workspace is present, it agrees too.")
_R8_PROVEN_ZH = "主数据中的公司识别码与所有者读数一致；若有工作区，工作区亦一致。"

# Every (check, code) pair the identity chain can emit, read off the engine's
# own leg receipts (engine/security_state.py R1…R9 plus the containment
# shell's R8). ISSUER_GROUP_AMBIGUOUS is carried by two different checks and
# each gets its own sentence, because "not exactly one issuer row" and "the
# issuer holds more than this security" are different facts.
_ENGINE_LEG_FAILURE_CODES = (
    ("R1", "SECURITY_SUPERSEDED"),
    ("R2", "IDENTITY_UNRESOLVED"),
    ("R3", "ISSUER_GROUP_AMBIGUOUS"),
    ("R4", "ISSUER_GROUP_AMBIGUOUS"),
    ("R5", "LISTING_KEY_INCOHERENT"),
    ("R6", "IDENTITY_CORRECTED"),
    ("R7", "SUBJECT_NATIVE_PARITY_FAILED"),
    ("R8", "IDENTITY_BRIDGE_DISAGREEMENT"),
    ("R8", "IDENTITY_UNRESOLVED"),
    ("R8", "OWNER_IDENTITY_UNREAD"),
    ("R9", "CORROBORATION_DIVERGENT"),
)

_ELSE_FAIL_CODE = re.compile(r'else\s+"([A-Z][A-Z0-9_]+)"')
_BARE_FAIL_CODE = re.compile(r'"fail",\s+"([A-Z][A-Z0-9_]+)"')


def _balanced_call_body(src: str, open_at: int) -> str:
    """Return the text inside the ``(… )`` that opens at ``open_at``."""
    depth = 0
    for i in range(open_at, len(src)):
        ch = src[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return src[open_at + 1:i]
    return src[open_at + 1:]


def _engine_leg_failure_codes_emitted_in_src(src: str) -> set[str]:
    """Failure codes the engine actually puts on a leg receipt.

    Matches the engine's emission forms: every ``else "<SCREAMING_SNAKE>"``
    argument inside a ``legs.append(_leg_receipt(`` call, plus the bare
    ``"fail", "<CODE>"`` shell form. Codes added outside those two forms
    are not visible to this scan.
    """
    found: set[str] = set()
    needle = "legs.append(_leg_receipt("
    start = 0
    while True:
        idx = src.find(needle, start)
        if idx < 0:
            break
        open_at = idx + len("legs.append")
        body = _balanced_call_body(src, open_at)
        found.update(_ELSE_FAIL_CODE.findall(body))
        start = idx + len(needle)
    found.update(_BARE_FAIL_CODE.findall(src))
    return found


def _msft_golden_view() -> dict:
    fixture = REPO / "tests" / "fixtures" / "security_state" / "golden_msft_expected_output.json"
    state = json.loads(fixture.read_text(encoding="utf-8"))
    view = build_security_state({"security_state": state})
    assert view is not None
    return view


def test_r8_proven_copy_hedges_the_workspace_clause_the_way_r7_does() -> None:
    """Round-4 MAJOR. `r8_pass` is `master_cik == subject.issuer_cik and (not
    workspace_available or filing_cik_ok)` — the workspace conjunct is vacuous
    whenever no workspace was loaded this cycle, and on that same panel the R9
    row says no workspace listing was available to compare. So the R8 sentence
    may not assert that an existing workspace agreed. R7 already carries the
    conditional; R8 now carries the same one, in both languages.
    """
    from scripts.build_ticker_pages import _SS_LEG_DESC

    pair = _SS_LEG_DESC[("R8", "")]
    assert pair["en"] == _R8_PROVEN_EN
    assert pair["zh"] == _R8_PROVEN_ZH
    assert "现有" not in pair["zh"], pair["zh"]
    assert "也一致" not in pair["zh"], pair["zh"]
    assert "若有工作区" in pair["zh"], pair["zh"]

    view = _msft_golden_view()
    assert view["identity"]["legs"][7]["check"] == "R8"
    en = " ".join(_owner_receipts_article(_render_section(view, "en")).get_text().split())
    zh = " ".join(_owner_receipts_article(_render_section(view, "zh")).get_text().split())
    assert _R8_PROVEN_EN in en
    assert _R8_PROVEN_ZH in zh


def test_every_engine_failure_code_a_leg_can_carry_prints_a_house_sentence() -> None:
    """A named failure code with no house copy renders a sentence-less row —
    an id and a status word — on the always-visible panel, which is exactly
    where the reader most needs the explanation. Every code the engine can put
    on a leg now carries a plain bilingual sentence, and none of them leaks a
    machine token onto the glance tier.
    """
    from scripts.build_ticker_pages import _SS_LEG_DESC

    engine_src = (REPO / "engine" / "security_state.py").read_text(encoding="utf-8")
    for check, code in _ENGINE_LEG_FAILURE_CODES:
        assert f'"{code}"' in engine_src, (check, code)

    scanned = _engine_leg_failure_codes_emitted_in_src(engine_src)
    known = {code for _check, code in _ENGINE_LEG_FAILURE_CODES}
    missing = scanned - known
    assert not missing, (
        "engine emits a failure code this tuple does not name: " + ", ".join(sorted(missing))
    )

    contract = _contract(identity_proof={
        "state": "BLOCKED_IDENTITY_BRIDGE", "method": "owner_backed_chain.v1",
        "legs": [{
            "check": check,
            "description": "engine machine sentence",
            "artifact": "data/reference/security_master.parquet",
            "reader": "scripts/build_stock_library.py::_read_security_state_identity_rows",
            "values_read": [], "result": "fail", "code": code,
        } for check, code in _ENGINE_LEG_FAILURE_CODES],
        "equalities": [],
        "refusals": sorted({code for _check, code in _ENGINE_LEG_FAILURE_CODES}),
        "disclosures": [],
    })
    view = build_security_state({"security_state": contract})
    assert view is not None
    en = " ".join(_owner_receipts_article(_render_section(view, "en")).get_text().split())
    zh = " ".join(_owner_receipts_article(_render_section(view, "zh")).get_text().split())

    for check, code in _ENGINE_LEG_FAILURE_CODES:
        pair = _SS_LEG_DESC.get((check, code))
        assert pair, f"no house sentence for {(check, code)}"
        assert pair["en"] and pair["zh"] and pair["en"] != pair["zh"], (check, code)
        assert not _SCREAMING_SNAKE.findall(pair["en"]), (check, code)
        assert not _SCREAMING_SNAKE.findall(pair["zh"]), (check, code)
        assert pair["en"] in en, (check, code)
        assert pair["zh"] in zh, (check, code)
        assert code not in en and code not in zh, (check, code)

    assert not _SCREAMING_SNAKE.findall(en), en
    assert not _SCREAMING_SNAKE.findall(zh), zh
    # No row collapses to an id plus a status word in either language.
    for leg in view["identity"]["legs"]:
        assert leg["desc_en"] and leg["desc_zh"], leg["check"]
        assert leg["desc_en"] != leg["desc_zh"], leg["check"]
        assert leg["desc_en"] != "engine machine sentence", leg["check"]


def test_corroboration_state_recorded_with_no_value_is_treated_as_not_recorded() -> None:
    """`_ss_read_value` returns "" for a receipt that NAMES `corroboration_state`
    without echoing its value. "Recorded as empty" is still nothing the page
    can compare, so it takes the presence-hedged sentence "not recorded" takes
    — never the affirmative agreement copy.
    """
    from scripts.build_ticker_pages import _SS_LEG_DESC, _ss_read_value

    assert _ss_read_value([{"field": "corroboration_state"}], "corroboration_state") == ""

    contract = _contract(identity_proof={
        "state": "PROVEN", "method": "owner_backed_chain.v1",
        "legs": [{
            "check": "R9",
            "description": "corroboration: workspace primary alias agrees with the "
                           "owner subject's current alias and listing venue",
            "artifact": "event_workspace.v1 issuer.listings[]",
            "reader": "engine.neuralweb.company_intelligence_reader."
                      "load_workspace_with_disposition",
            "values_read": [{"field": "corroboration_state"}],
            "result": "pass", "code": None,
        }],
        "equalities": [], "refusals": [], "disclosures": [],
    })
    view = build_security_state({"security_state": contract})
    assert view is not None
    leg = view["identity"]["legs"][0]
    affirmative = _SS_LEG_DESC[("R9", "")]
    assert leg["desc_en"] != affirmative["en"]
    assert leg["desc_zh"] != affirmative["zh"]
    assert leg["desc_en"].startswith("The workspace primary listing, when present,")
    assert leg["desc_zh"].startswith("若有工作区上市记录")
    en = " ".join(_owner_receipts_article(_render_section(view, "en")).get_text().split())
    zh = " ".join(_owner_receipts_article(_render_section(view, "zh")).get_text().split())
    assert affirmative["en"] not in en
    assert affirmative["zh"] not in zh


def test_section_hint_counts_the_panels_the_page_renders() -> None:
    """The eyebrow names the panel count the page renders, as
    ``f"{n} panels"`` / ``f"{n} 个面板"`` (ratified at n = 8). It is not a
    "reads" count — that word is reserved for the coverage row.
    """
    view = _msft_golden_view()
    for lang, form in (("en", "{n} panels"), ("zh", "{n} 个面板")):
        html = _render_section(view, lang=lang)
        panels = len(_visible_b1b_headings(html))
        assert panels == 8, panels
        assert view["panel_count"] == panels
        section = _card_region(html)
        tree = _parse_class_tree("<section " + section[section.find("id="):])
        hint = tree.find_class("hint")
        assert hint is not None, lang
        assert " ".join(hint.get_text().split()) == form.format(n=panels), lang
        assert "The panels below." not in " ".join(hint.get_text().split())
        assert "以下面板。" not in " ".join(hint.get_text().split())


def test_overview_coverage_row_reads_as_two_parallel_sentences() -> None:
    """Round-4 minor. The row printed comma-joined label-ese in EN ("2 / 2
    required, current") against a full ZH noun phrase. Both languages now
    print the same two sentences, from the same counts.
    """
    view = _msft_golden_view()
    cov = view["coverage"]
    assert (cov["req_avail"], cov["req_total"]) == (2, 2)
    assert (cov["opt_avail"], cov["opt_total"]) == (2, 5)
    en = " ".join(_card_region(_render_section(view, "en")).split())
    zh = " ".join(_card_region(_render_section(view, "zh")).split())
    assert "2 of 2 required reads are current." in en
    assert "2 of 5 optional reads are current." in en
    assert "2 项必需读数中，2 项为当前数据。" in zh
    assert "5 项可选读数中，2 项为当前数据。" in zh
    for gone in ("required, current", "optional, current"):
        assert gone not in en, gone
    for gone in ("项必需读数（当前）", "项可选读数（当前）"):
        assert gone not in zh, gone


def test_state_card_prints_its_headline_when_it_has_no_clause() -> None:
    """A stance whose house sentence has no explanation half ("mixed") leaves
    the card with no clause, and the state card suppresses its headline so the
    sentence prints once. Without a clause that leaves heading + chip and no
    prose at all — so the exclusion applies only when a clause exists.
    """
    contract = _contract()
    contract["legs"]["state"]["ladder_state"] = "mixed"
    contract["legs"]["state"]["summary"] = {"en": "Ladder state: mixed.",
                                            "zh": "阶梯状态：mixed。"}
    view = build_security_state({"security_state": contract})
    assert view is not None
    state = _axis(view, "state")
    assert state["clause"] is None
    assert state["headline"]["en"] == "Signals point in different directions right now"
    assert state["headline"]["zh"] == "当前信号方向不一"

    for lang, sentence in (("en", "Signals point in different directions right now"),
                           ("zh", "当前信号方向不一")):
        tree = _parse_class_tree(_render_section(view, lang=lang))
        grid = tree.find_class("ss-grid")
        assert grid is not None
        card = grid.find_all_class("ss-cell")[0]
        text = " ".join(card.get_text().split())
        assert _heading_label(card.find_class("ss-axis")) in ("Where it stands", "当前位置")
        assert sentence in text, (lang, text)


def test_owner_receipts_panel_renders_from_the_owner_receipts_view_key() -> None:
    """The spec names `owner_receipts` as the panel's path. It was a dead key —
    the template read `identity.legs` and the top-level clocks instead. The
    panel now renders from `owner_receipts`, and the identity between the two
    reads stays pinned by
    test_owner_model_receipts_surfaces_identity_legs_asof_and_content_sha256.
    """
    j2_src = (REPO / "templates" / "ticker.html.j2").read_text(encoding="utf-8")
    assert "ss.owner_receipts.legs" in j2_src
    assert "ss.owner_receipts.generated_at" in j2_src
    assert "ss.owner_receipts.compiled_at" in j2_src
    assert "ss.owner_receipts.content_sha256" in j2_src

    view = _msft_golden_view()
    en = " ".join(_owner_receipts_article(_render_section(view, "en")).get_text().split())
    assert view["owner_receipts"]["content_sha256"] in en
    assert view["owner_receipts"]["generated_at"] in en
    assert len(view["owner_receipts"]["legs"]) == 9


def test_id_legs_carry_artifact_and_reader_keys_and_m1_failure_renders_them() -> None:
    """Heal-round h6 REQUIRED 1. Every identity leg the projection emits
    carries ``artifact_en`` / ``artifact_zh`` / ``reader_en`` / ``reader_zh``
    so the template's ``{% if lg.artifact_en %}`` / ``{% if lg.reader_en %}``
    rows can fire. On the M1 failure path those four slots hold the house
    sentences, and both languages of the rendered ticker page print them.
    """
    keys = ("artifact_en", "artifact_zh", "reader_en", "reader_zh")
    view = build_security_state({"security_state": _contract()})
    assert view is not None
    for leg in view["identity"]["legs"]:
        for key in keys:
            assert key in leg, (leg.get("check"), sorted(leg))

    from scripts.build_ticker_pages import _SS_ARTIFACT, _SS_READER

    m1_code = (
        "OWNER_IDENTITY_UNREAD"
        if ("R8", "OWNER_IDENTITY_UNREAD") in _SS_ARTIFACT
        else "IDENTITY_UNRESOLVED"
    )
    art = _SS_ARTIFACT[("R8", m1_code)]
    rdr = _SS_READER[("R8", m1_code)]
    contract = _contract(identity_proof={
        "state": "BLOCKED_IDENTITY_BRIDGE", "method": "owner_backed_chain.v1",
        "legs": [{
            "check": "R8",
            "description": "owner-identity batch was unavailable this cycle; subject is the frozen "
                           "pinned allowlist mapping for this ticker, never a live owner read",
            "artifact": "SecurityStateSubject (frozen pinned allowlist config, not a producer owner receipt)",
            "reader": "scripts/build_stock_library.py::_read_security_state_identity_rows",
            "values_read": [{"field": "subject_ticker_display", "value": "AAPL"}],
            "result": "fail", "code": m1_code,
        }],
        "equalities": [], "refusals": [m1_code], "disclosures": [],
    })
    m1 = build_security_state({"security_state": contract})
    assert m1 is not None
    leg = m1["identity"]["legs"][0]
    for key in keys:
        assert key in leg, (key, sorted(leg))
    assert leg["artifact_en"] == art["en"]
    assert leg["artifact_zh"] == art["zh"]
    assert leg["reader_en"] == rdr["en"]
    assert leg["reader_zh"] == rdr["zh"]
    assert art["en"] and art["zh"] and art["en"] != art["zh"]
    assert rdr["en"] and rdr["zh"] and rdr["en"] != rdr["zh"]

    en = _render_section(m1, "en")
    zh = _render_section(m1, "zh")
    assert art["en"] in en
    assert art["zh"] in zh
    assert rdr["en"] in en
    assert rdr["zh"] in zh


def test_overview_coverage_row_is_absent_when_both_sentences_are_none() -> None:
    """The coverage row (label and values) is gated on at least one sentence,
    matching the clocks' rule on the receipts panel. Both sentences None
    means the row is not rendered at all.
    """
    contract = _contract()
    contract["coverage"] = {
        "overall_state": "PARTIAL",
        "required_legs_total": None, "required_legs_available": None,
        "required_legs_nonblocking": None,
        "optional_legs_total": None, "optional_legs_available": None,
        "optional_legs_nonblocking": None,
        "missing_legs": [], "stale_legs": [],
        "rights_blocked_legs": [], "conflicted_legs": [],
    }
    view = build_security_state({"security_state": contract})
    assert view is not None
    assert view["coverage"]["req_sentence"] is None
    assert view["coverage"]["opt_sentence"] is None
    en = _card_region(_render_section(view, "en"))
    zh = _card_region(_render_section(view, "zh"))
    assert "Reads available" not in en
    assert "可用读数" not in zh



# ---------------------------------------------------------------------------
# F06-ZH-CARD-1 · the change card's workspace lifecycle state
#
# `engine/security_state.py:1219-1223` composes the change card's sentence and
# interpolates the owner's raw lifecycle value into BOTH language slots, so the
# Chinese page reads `Q4 2026 财报工作区状态为 complete：…` — an engine token
# inside customer Chinese (Chairman plain-language law 2026-09-06). The engine
# and the compiled goldens are truth and are never edited; the projection layer
# in `scripts/build_ticker_pages.py` translates.

_F06_CARD_TITLE = {"en": "What changed", "zh": "有何变化"}
#: Any Latin run of three or more. Every `EVENT_STATES` member
#: (`engine/company_intelligence/events.py:43`) is one, and so is every other
#: shape an out-of-contract owner could send.
_F06_LATIN_RUN_RE = re.compile(r"[A-Za-z_]{3,}")
_F06_GOLDENS = ("golden_msft_expected_output.json", "golden_aapl_expected_output.json")


def _f06_golden(name: str) -> dict:
    path = REPO / "tests" / "fixtures" / "security_state" / name
    return json.loads(path.read_text(encoding="utf-8"))


def _f06_axis_card(html: str, *, lang: str) -> _HtmlNode:
    """The one `ss-cell` article whose axis heading is the change card's."""
    want = _F06_CARD_TITLE[lang]
    for card in _parse_class_tree(_card_region(html)).find_all_class("ss-cell"):
        heading = card.find_class("ss-axis")
        if heading is not None and want in heading.get_text():
            return card
    raise AssertionError(f"the {want!r} card did not render in {lang!r}")


def _f06_card_sentence(view: dict, *, lang: str) -> str:
    head = _f06_axis_card(_render_section(view, lang=lang), lang=lang).find_class("ss-head")
    assert head is not None, f"the change card printed no sentence in {lang!r}"
    return head.get_text()


def _f06_with_state(golden: dict, state: str, *, quarter: object = 4) -> dict:
    """Golden with its change-card sentence recomposed for *state*.

    Rebuilt with the engine's own two frames (`engine/security_state.py:1219-1223`)
    so the test exercises a real engine sentence, not a shape of its own
    invention. The golden on disk is never written.
    """
    import copy

    out = copy.deepcopy(golden)
    label = f"Q{quarter} 2026" if quarter else "the latest period"
    out["legs"]["change"]["summary"] = {
        "en": f"{label} results workspace is {state}: "
              "2 fact(s), 1 delta(s), 1 guidance item(s).",
        "zh": f"{label} 财报工作区状态为 {state}："
              "2 项事实、1 项变动、1 项指引。",
    }
    return out


@pytest.mark.parametrize("golden_name", _F06_GOLDENS)
def test_change_card_sentence_carries_no_engine_state_token(golden_name: str) -> None:
    """F06-ZH-CARD-1 scope (3): render a golden and read the change card.

    RED-first at main 961a9c3d, both goldens: the Chinese sentence printed
    `… 财报工作区状态为 complete：…` — the lifecycle token verbatim inside
    Chinese copy.
    """
    view = build_security_state({"security_state": _f06_golden(golden_name)})
    assert view is not None

    zh_sentence = _f06_card_sentence(view, lang="zh")
    assert "财报工作区" in zh_sentence, (
        f"the change card sentence is not the workspace sentence: {zh_sentence!r}"
    )
    hits = _F06_LATIN_RUN_RE.findall(zh_sentence)
    assert not hits, (
        "engine state token(s) reached the Chinese change card sentence: "
        f"{hits} in {zh_sentence!r}"
    )
    # No ASCII space may sit against a CJK character where the value was.
    assert "状态为 " not in zh_sentence, (
        f"the projection left the engine's ASCII space against CJK: {zh_sentence!r}"
    )


@pytest.mark.parametrize(
    ("state", "en_words", "zh_words"),
    [
        ("completed_partial", "partly complete", "部分完成"),
        ("derived_ready", "ready to read", "可供查阅"),
        ("discovered", "first seen", "已发现"),
    ],
)
def test_change_card_projects_both_languages_end_to_end(
    state: str, en_words: str, zh_words: str,
) -> None:
    """The EN slot is projected too, and `complete` is the one value that hides
    it: the token happens to be an English word, so an EN assertion on the MSFT
    golden alone passes byte-identically without any projection at all. These
    three tokens have house words that DIFFER from the token, so the English
    half of the table is exercised on the real render path.
    """
    view = build_security_state(
        {"security_state": _f06_with_state(_f06_golden(_F06_GOLDENS[0]), state)},
    )
    assert view is not None

    en_sentence = _f06_card_sentence(view, lang="en")
    assert f"results workspace is {en_words}:" in en_sentence, en_sentence
    assert state not in en_sentence, f"raw {state!r} survived in English: {en_sentence!r}"

    zh_sentence = _f06_card_sentence(view, lang="zh")
    assert f"状态为{zh_words}：" in zh_sentence, zh_sentence
    assert not _F06_LATIN_RUN_RE.findall(zh_sentence), zh_sentence


def test_change_card_annual_period_label_is_not_english_in_chinese() -> None:
    """`engine/security_state.py:1218` labels a workspace with no fiscal quarter
    `"the latest period"` and puts that English into the CHINESE frame as well.
    Projecting the state and leaving this would swap one Latin run out of the
    sentence and leave another in.
    """
    view = build_security_state({
        "security_state": _f06_with_state(
            _f06_golden(_F06_GOLDENS[0]), "complete", quarter=None,
        ),
    })
    assert view is not None

    zh_sentence = _f06_card_sentence(view, lang="zh")
    assert "the latest period" not in zh_sentence, zh_sentence
    assert "最近一期" in zh_sentence, zh_sentence
    assert not _F06_LATIN_RUN_RE.findall(zh_sentence), zh_sentence
    # English keeps the engine's own label — it is house English there.
    assert "the latest period" in _f06_card_sentence(view, lang="en")


def test_change_card_state_table_covers_the_whole_engine_vocabulary() -> None:
    """F06-ZH-CARD-1 scope (3), extending macro#6920 h7's completeness rule.

    Discovery walks `EVENT_STATES` in the engine source, so a vocabulary that
    GROWS reds here instead of silently reaching the page as a raw token.
    """
    from scripts.build_ticker_pages import _SS_CHANGE_STATE, _SS_CHANGE_STATE_UNREADABLE

    events_src = (
        REPO / "engine" / "company_intelligence" / "events.py"
    ).read_text(encoding="utf-8")
    block = re.search(
        r"EVENT_STATES:\s*frozenset\[str\]\s*=\s*frozenset\(\{(.*?)\}\)",
        events_src, re.S,
    )
    assert block is not None, "EVENT_STATES no longer parses at its declaration site"
    engine_states = set(re.findall(r'"([a-z_]+)"', block.group(1)))
    assert "complete" in engine_states and "completed_partial" in engine_states, (
        f"the EVENT_STATES extractor is not reading the docket set: {sorted(engine_states)}"
    )
    # The reader's own sentinel when the owner states no lifecycle state
    # (`engine/security_state.py:1198`: `... or "unknown"`).
    engine_src = (REPO / "engine" / "security_state.py").read_text(encoding="utf-8")
    assert 'lifecycle.get("state")) or "unknown"' in engine_src, (
        "the reader's lifecycle-state fallback moved; re-derive the sentinel"
    )
    reachable = engine_states | {"unknown"}

    missing = sorted(tok for tok in reachable if tok not in _SS_CHANGE_STATE)
    assert not missing, f"_SS_CHANGE_STATE missing engine lifecycle states: {missing}"

    failures: list[str] = []
    for token, pair in _SS_CHANGE_STATE.items():
        for slot in ("en", "zh"):
            text = str(pair.get(slot) or "")
            if not text:
                failures.append(f"{token}[{slot}] is empty")
            if text == _SS_CHANGE_STATE_UNREADABLE[slot]:
                failures.append(f"{token}[{slot}] is the unreadable-value fallback")
        # An EN pair may legitimately BE the token when the token is already an
        # ordinary English word (`complete`, `cancelled`) — `_SS_READ_VALUE`
        # does the same for `AVAILABLE`. What it may never be is a machine
        # word: an underscore is the shape that gives a snake_case token away.
        en = str(pair.get("en") or "")
        if "_" in en:
            failures.append(f"{token}['en'] is still a machine word: {en!r}")
        zh = str(pair.get("zh") or "")
        if " " in zh:
            failures.append(f"{token}['zh'] carries an ASCII space: {zh!r}")
        if _F06_LATIN_RUN_RE.search(zh):
            failures.append(f"{token}['zh'] carries a Latin run: {zh!r}")
    assert not failures, "; ".join(failures)

    # The drilldown's `correction_state` row reads the SAME vocabulary, so the
    # completeness rule covers that path too: the reader DERIVES that field from
    # the lifecycle state through one literal map
    # (`engine/security_state.py:1199-1201`), and every value the map can
    # produce — its own default included — must reach house words or be the
    # recognised "nothing recorded" sentinel. A vocabulary that grows reds here
    # instead of printing a token into the row.
    from scripts.build_ticker_pages import (
        _SS_CHANGE_STATE_UNMAPPED, _SS_CORRECTION_ABSENT,
        _ss_project_correction_state,
    )

    derivation = re.search(
        r'correction_state = \{(?P<body>[^}]*)\}\.get\(\s*'
        r'str\(lifecycle_state\),\s*"(?P<default>[a-z_]+)"',
        engine_src, re.S,
    )
    assert derivation is not None, (
        "the change leg's correction_state derivation no longer parses at its "
        "declaration site; re-derive the reachable vocabulary"
    )
    reachable_corrections = set(
        re.findall(r'"[a-z_]+"\s*:\s*"([a-z_]+)"', derivation.group("body"))
    ) | {derivation.group("default")}
    assert {"corrected", "superseded"} <= reachable_corrections, (
        f"the correction extractor is not reading the map: {sorted(reachable_corrections)}"
    )

    recorded_before = set(_SS_CHANGE_STATE_UNMAPPED)
    corr_failures: list[str] = []
    for token in sorted(reachable_corrections):
        projected = _ss_project_correction_state(token)
        if token in _SS_CORRECTION_ABSENT:
            if projected is not None:
                corr_failures.append(
                    f"{token} is the absence sentinel but projected {projected!r}"
                )
            continue
        if token not in _SS_CHANGE_STATE:
            corr_failures.append(f"_SS_CHANGE_STATE missing correction state: {token}")
            continue
        assert projected is not None
        for slot in ("en", "zh"):
            text = str(projected.get(slot) or "")
            if not text:
                corr_failures.append(f"{token}[{slot}] is empty")
            if text == _SS_CHANGE_STATE_UNREADABLE[slot]:
                corr_failures.append(f"{token}[{slot}] is the unreadable-value fallback")
        projected_zh = str(projected.get("zh") or "")
        if " " in projected_zh:
            corr_failures.append(f"{token}['zh'] carries an ASCII space: {projected_zh!r}")
        if _F06_LATIN_RUN_RE.search(projected_zh):
            corr_failures.append(f"{token}['zh'] carries a Latin run: {projected_zh!r}")
    assert not corr_failures, "; ".join(corr_failures)
    assert set(_SS_CHANGE_STATE_UNMAPPED) == recorded_before, (
        "a contract correction state was recorded as unmapped: "
        f"{sorted(set(_SS_CHANGE_STATE_UNMAPPED) - recorded_before)}"
    )


def test_change_card_projection_is_a_fixpoint_for_every_token() -> None:
    """Projecting an already-projected sentence must change nothing and record
    nothing. Without this, a house word that is itself a bare lowercase word
    (`discovered` → `found`) is re-read as an unrecognised value on any second
    pass: the sentence degrades AND a false operator line names a value the
    engine never sent.
    """
    from scripts.build_ticker_pages import (
        _SS_CHANGE_STATE, _SS_CHANGE_STATE_UNMAPPED, _ss_project_change_state,
    )

    before = set(_SS_CHANGE_STATE_UNMAPPED)
    failures: list[str] = []
    for token in _SS_CHANGE_STATE:
        once = _ss_project_change_state({
            "en": f"Q4 2026 results workspace is {token}: 2 fact(s).",
            "zh": f"Q4 2026 财报工作区状态为 {token}：2 项事实。",
        })
        assert once is not None
        twice = _ss_project_change_state(dict(once))
        if twice != once:
            failures.append(f"{token}: {once!r} -> {twice!r}")
    assert not failures, "; ".join(failures)
    assert set(_SS_CHANGE_STATE_UNMAPPED) == before, (
        "a contract token was recorded as unmapped: "
        f"{sorted(set(_SS_CHANGE_STATE_UNMAPPED) - before)}"
    )


@pytest.mark.parametrize(
    "raw",
    ["Complete", "COMPLETE", "in-progress", "ok", "v2_ready", "complete2",
     "future_owner_state", "5"],
)
def test_change_card_out_of_contract_state_is_recorded_not_printed(
    raw: str, capsys: pytest.CaptureFixture[str],
) -> None:
    """F06-ZH-CARD-1 scope (2): a value outside the docket vocabulary takes a
    readable house pair AND is recorded for the operator.

    The reader does not re-validate `lifecycle.state` against `EVENT_STATES`
    (only the producer does, `engine/company_intelligence/events.py:239`) and
    the workspace arrives over the wire, so EVERY shape is reachable — not only
    the snake_case one that happens to look like a contract token. A matcher
    gated on the token's shape lets exactly the values that most need catching
    walk past; this parametrisation is the guard against that.
    """
    from scripts.build_ticker_pages import (
        _SS_CHANGE_STATE_UNMAPPED, _SS_CHANGE_STATE_UNREADABLE,
        _ss_project_change_state,
    )

    _SS_CHANGE_STATE_UNMAPPED.discard(raw)
    try:
        projected = _ss_project_change_state({
            "en": f"Q4 2026 results workspace is {raw}: 2 fact(s).",
            "zh": f"Q4 2026 财报工作区状态为 {raw}：2 项事实。",
        })
        assert projected is not None
        assert raw not in projected["en"], projected["en"]
        assert raw not in projected["zh"], projected["zh"]
        assert _SS_CHANGE_STATE_UNREADABLE["en"] in projected["en"]
        assert _SS_CHANGE_STATE_UNREADABLE["zh"] in projected["zh"]
        assert "状态为 " not in projected["zh"], projected["zh"]
        assert raw in _SS_CHANGE_STATE_UNMAPPED, "the value was not recorded"
        assert f"change card lifecycle state unmapped: {raw}" in capsys.readouterr().err, (
            "the operator never heard about it"
        )
    finally:
        _SS_CHANGE_STATE_UNMAPPED.discard(raw)


def test_change_card_out_of_contract_state_never_reaches_the_page() -> None:
    """The same guarantee on the real render path, not just the projector."""
    from scripts.build_ticker_pages import _SS_CHANGE_STATE_UNMAPPED

    _SS_CHANGE_STATE_UNMAPPED.discard("Complete")
    try:
        view = build_security_state({
            "security_state": _f06_with_state(_f06_golden(_F06_GOLDENS[0]), "Complete"),
        })
        assert view is not None
        zh_sentence = _f06_card_sentence(view, lang="zh")
        assert "Complete" not in zh_sentence, zh_sentence
        assert not _F06_LATIN_RUN_RE.findall(zh_sentence), zh_sentence
        assert "Complete" not in _card_region(_render_section(view, lang="zh"))
    finally:
        _SS_CHANGE_STATE_UNMAPPED.discard("Complete")


def test_change_card_prints_its_sentence_once() -> None:
    """The projection returns a NEW dict, so `headline is summary` — which
    decides whether the card prints a second paragraph — has to be established
    after it, not before. If that identity breaks the card prints the same
    sentence twice.
    """
    view = build_security_state({"security_state": _f06_golden(_F06_GOLDENS[0])})
    assert view is not None
    change = _axis(view, "change")
    assert change["clause"] is None, (
        f"the change card grew a second paragraph: {change['clause']!r}"
    )
    card = _f06_axis_card(_render_section(view, lang="zh"), lang="zh")
    sentences = [p for p in card.find_all_class("ss-head") + card.find_all_class("ss-body")]
    assert len(sentences) == 1, [s.get_text() for s in sentences]


#: The drilldown row the change card's dialog prints the lifecycle-derived
#: correction value in (`templates/ticker.html.j2:1822`).
_F06_CORRECTION_LABEL = {"en": "Correction state", "zh": "更正状态"}
_F06_NOT_RECORDED = {"en": "None recorded", "zh": "无记录"}
#: `engine/security_state.py:1199-1201`: the change leg's `correction_state` is
#: DERIVED from the lifecycle state through exactly this map, so a fixture that
#: names a lifecycle state receives the correction value the engine would have
#: sent. A state the map does not name is carried through unchanged — the reader
#: re-validates this field no more than it re-validates the lifecycle one, and
#: the workspace arrives over the wire, so any value is reachable.
_F06_ENGINE_CORRECTION = {
    "complete": "none", "corrected": "corrected", "superseded": "superseded",
}


def _f06_with_correction(golden: dict, state: str) -> dict:
    out = _f06_with_state(golden, state)
    out["legs"]["change"]["correction_state"] = _F06_ENGINE_CORRECTION.get(state, state)
    return out


def _f06_correction_row(view: dict, *, lang: str) -> str:
    """What the change card's drilldown prints for `Correction state` in *lang*."""
    want_title = _F06_CARD_TITLE[lang]
    want_label = _F06_CORRECTION_LABEL[lang]
    for dlg in _parse_class_tree(_render_section(view, lang=lang)).find_all_class("dsr-dlg"):
        title = dlg.find_class("dsr-dlg-title")
        if title is None or want_title not in title.get_text():
            continue
        for row in dlg.find_all_class("r6d"):
            key = row.find_class("k")
            val = row.find_class("vv")
            if key is not None and val is not None and want_label in key.get_text():
                return val.get_text().strip()
        raise AssertionError(f"the change drilldown has no {want_label!r} row in {lang!r}")
    raise AssertionError(f"the change drilldown did not render in {lang!r}")


@pytest.mark.parametrize("golden_name", _F06_GOLDENS)
@pytest.mark.parametrize(
    ("state", "en_words", "zh_words"),
    [("corrected", "corrected", "已更正"), ("superseded", "superseded", "已被取代")],
)
def test_change_drilldown_correction_state_carries_no_engine_token(
    golden_name: str, state: str, en_words: str, zh_words: str,
) -> None:
    """Same defect class on the same card: the drilldown's correction row.

    RED-first at e65cc264 (the card's sentence already projected, this row not),
    both goldens: the row printed the lifecycle token verbatim into BOTH
    language slots, so the Chinese page read `更正状态 superseded`.

    What is load-bearing here is the CHINESE half plus the Latin-run and
    ASCII-space rules. `corrected` and `superseded` are the only two values the
    engine's derivation can emit besides the absence sentinel, and both are
    ordinary English words whose house EN is the token itself — so the English
    equality below is byte-identical with and without the projection and proves
    nothing on its own. `test_change_drilldown_correction_state_projects_the_
    english_half` is where the English half is actually exercised, on values
    that are reachable over the wire rather than from today's derivation.
    """
    view = build_security_state(
        {"security_state": _f06_with_correction(_f06_golden(golden_name), state)},
    )
    assert view is not None

    zh_value = _f06_correction_row(view, lang="zh")
    assert zh_value == zh_words, f"the Chinese row reads {zh_value!r}"
    assert state not in zh_value, f"raw {state!r} survived in Chinese: {zh_value!r}"
    assert not _F06_LATIN_RUN_RE.findall(zh_value), (
        f"an engine state token reached the Chinese correction row: {zh_value!r}"
    )
    # The row prints a bare value, so the CJK-adjoining-space rule is the whole
    # string: no ASCII space may sit anywhere in it.
    assert " " not in zh_value, f"the row left an ASCII space against CJK: {zh_value!r}"
    assert _f06_correction_row(view, lang="en") == en_words


@pytest.mark.parametrize(
    ("state", "en_words", "zh_words"),
    [
        ("completed_partial", "partly complete", "部分完成"),
        ("derived_ready", "ready to read", "可供查阅"),
        ("discovered", "first seen", "已发现"),
    ],
)
def test_change_drilldown_correction_state_projects_the_english_half(
    state: str, en_words: str, zh_words: str,
) -> None:
    """`corrected` and `superseded` are ordinary English words, so an English
    assertion on them passes byte-identically with no projection at all. These
    three have house words that DIFFER from the token, so the English half of
    the row is exercised on the real render path.
    """
    view = build_security_state(
        {"security_state": _f06_with_correction(_f06_golden(_F06_GOLDENS[0]), state)},
    )
    assert view is not None

    en_value = _f06_correction_row(view, lang="en")
    assert en_value == en_words, f"the English row reads {en_value!r}"
    assert state not in en_value, f"raw {state!r} survived in English: {en_value!r}"

    zh_value = _f06_correction_row(view, lang="zh")
    assert zh_value == zh_words, f"the Chinese row reads {zh_value!r}"
    assert not _F06_LATIN_RUN_RE.findall(zh_value), zh_value


@pytest.mark.parametrize("golden_name", _F06_GOLDENS)
def test_change_drilldown_none_correction_keeps_the_not_recorded_copy(
    golden_name: str, capsys: pytest.CaptureFixture[str],
) -> None:
    """`"none"` is the derivation's own default, not a lifecycle state.

    Both goldens ship it. It means absence, so the row keeps the house copy it
    already had — never the unreadable-value words — and no operator line is
    filed for the commonest real value on the surface.
    """
    from scripts.build_ticker_pages import (
        _SS_CHANGE_STATE_UNMAPPED, _SS_CHANGE_STATE_UNREADABLE,
    )

    golden = _f06_golden(golden_name)
    assert golden["legs"]["change"]["correction_state"] == "none", (
        "the golden no longer ships the absence sentinel; re-derive this guard"
    )
    recorded_before = set(_SS_CHANGE_STATE_UNMAPPED)
    view = build_security_state({"security_state": golden})
    assert view is not None

    for lang in ("en", "zh"):
        value = _f06_correction_row(view, lang=lang)
        assert value == _F06_NOT_RECORDED[lang], f"{lang}: {value!r}"
        assert value != _SS_CHANGE_STATE_UNREADABLE[lang]
    assert set(_SS_CHANGE_STATE_UNMAPPED) == recorded_before
    assert "unmapped: none" not in capsys.readouterr().err, (
        "the absence sentinel was filed as an out-of-contract value"
    )


def test_change_drilldown_out_of_contract_correction_never_reaches_the_page(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A wrong-case value is the shape a token-shaped matcher lets past. It
    takes readable house words in both slots AND is recorded for the operator.

    The value is planted in the correction field ALONE, with the card's own
    sentence left on a contract state: the operator line is deduped on the
    VALUE, so a token carried by both fields would be reported once under
    whichever field reached it first and this row's label would never show.
    """
    from scripts.build_ticker_pages import (
        _SS_CHANGE_STATE_UNMAPPED, _SS_CHANGE_STATE_UNREADABLE,
    )

    _SS_CHANGE_STATE_UNMAPPED.discard("Superseded")
    try:
        planted = _f06_with_state(_f06_golden(_F06_GOLDENS[0]), "complete")
        planted["legs"]["change"]["correction_state"] = "Superseded"
        view = build_security_state({"security_state": planted})
        assert view is not None
        for lang in ("en", "zh"):
            value = _f06_correction_row(view, lang=lang)
            assert value == _SS_CHANGE_STATE_UNREADABLE[lang], f"{lang}: {value!r}"
            assert "Superseded" not in value, value
        assert not _F06_LATIN_RUN_RE.findall(_f06_correction_row(view, lang="zh"))
        assert "Superseded" in _SS_CHANGE_STATE_UNMAPPED, "the value was not recorded"
        # The operator line names the field the value arrived in, not the
        # sentence's field: the two read the same vocabulary out of two
        # different contract fields.
        assert "change card correction state unmapped: Superseded" in capsys.readouterr().err
    finally:
        _SS_CHANGE_STATE_UNMAPPED.discard("Superseded")


@pytest.mark.parametrize("raw", [" none ", " None ", "NONE", " null ", "nat", 0, False, []])
def test_change_drilldown_padded_or_falsy_correction_is_absence_not_unreadable(
    raw: object, capsys: pytest.CaptureFixture[str],
) -> None:
    """Absence written badly is still absence.

    `_clean_str` empties its placeholder literals only when one IS the whole
    value, so `" None "` survives it; and the line this amendment replaced
    collapsed falsy non-strings with `or ""`. Either gap would print
    `not recognised` on a page that has nothing to report AND file an operator
    line for a value no owner ever stated.
    """
    from scripts.build_ticker_pages import (
        _SS_CHANGE_STATE_UNMAPPED, _ss_project_correction_state,
    )

    recorded_before = set(_SS_CHANGE_STATE_UNMAPPED)
    golden = _f06_golden(_F06_GOLDENS[0])
    golden["legs"]["change"]["correction_state"] = raw
    view = build_security_state({"security_state": golden})
    assert view is not None

    assert _ss_project_correction_state(raw or "") is None
    for lang in ("en", "zh"):
        assert _f06_correction_row(view, lang=lang) == _F06_NOT_RECORDED[lang]
    assert set(_SS_CHANGE_STATE_UNMAPPED) == recorded_before, (
        f"{raw!r} was filed as an out-of-contract value"
    )
    assert "correction state unmapped" not in capsys.readouterr().err
