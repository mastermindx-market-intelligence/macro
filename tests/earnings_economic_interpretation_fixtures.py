"""Synthetic cases for the bounded economic interpretation builder."""
from __future__ import annotations

from engine.company_intelligence.event_workspace_build import build_event_workspace
from engine.company_intelligence.pg_profile import PG_METRIC_KEYS, pg_private_registry, pg_profile
from engine.earnings_narrative.economic_interpretation import (
    CODE_REVISION,
    SEMANTIC_REVISION,
    build_economic_interpretation,
)
from tests.earnings_economic_fixtures import (
    ACCEPTANCE,
    FISCAL_PERIOD,
    FISCAL_SCOPE,
    _filing,
    pg_bound_case,
)


_EPS_ROW = "<tr><td>Diluted Net Earnings per Common Share</td><td>$3.07</td><td>$2.93</td></tr>"
_CORE_ROW = "<tr><td>Core EPS</td><td>$3.11</td><td>$2.97</td></tr>"


def _base_body() -> str:
    return pg_bound_case("annual_first").source


def _body(case: str) -> str:
    body = _base_body()
    if case == "headline_positive_organic_flat":
        return body.replace("<td>3.0%</td><td>1.0%</td>", "<td>3.0%</td><td>0.0%</td>", 1)
    if case == "reported_core_opposite_direction":
        return body.replace(
            _CORE_ROW, "<tr><td>Core EPS</td><td>$2.91</td><td>$2.97</td></tr>"
        )
    if case == "negative_prior_eps":
        return body.replace(_EPS_ROW, "<tr><td>Diluted Net Earnings per Common Share</td><td>$3.07</td><td>($2.93)</td></tr>")
    if case == "zero_prior_eps":
        return body.replace(_EPS_ROW, "<tr><td>Diluted Net Earnings per Common Share</td><td>$3.07</td><td>$0.00</td></tr>")
    if case == "reported_negative_organic_positive":
        return body.replace("<td>3.0%</td><td>1.0%</td>", "<td>(2.0)%</td><td>3.0%</td>", 1)
    if case == "eps_flat_core_rises":
        return body.replace(_EPS_ROW, "<tr><td>Diluted Net Earnings per Common Share</td><td>$2.93</td><td>$2.93</td></tr>")
    if case == "missing_demand_context":
        return body.replace("<td>Price</td>", "<td>Unrecognized</td>", 1)
    if case == "unlocated_outcome":
        return body.replace("<p>全球品牌 demand was stable before 3.07 units of synthetic EPS.</p>", "<p>全球品牌 demand was stable before synthetic EPS.</p>")
    if case == "refused_document_outcome":
        return "<DOCUMENT>\n<TYPE>EX-99.2\n<TITLE>synthetic refused document\n<TEXT>\n</TEXT>\n</DOCUMENT>\n"
    if case == "segment_and_reconciliation_absent":
        body = body.replace("<p>Core EPS excludes an incremental charge of 0.20 and dilution of 0.05.</p>", "")
        return body[:body.find("<h2>Organic Sales Change by Segment</h2>")] + body[body.find("</body></html>"):]
    if case == "conflict_outcome":
        return body.replace("</body></html>", '<h2>Segment Results</h2><table><tr><td></td><td>Total Volume</td><td>Organic Sales Growth</td></tr><tr><td>Total P&amp;G</td><td>4.0%</td><td>1.0%</td></tr></table></body></html>')
    return body


def _workspace(
    case: str, *, body: str | None = None, fiscal_period=FISCAL_PERIOD,
    source_sha256: str | None = None,
):
    kind = "combined_volume_only" if case == "combined_volume_mix" else case
    if body is None:
        body = _body(case) if case in {
            "headline_positive_organic_flat", "reported_core_opposite_direction",
            "negative_prior_eps", "zero_prior_eps", "reported_negative_organic_positive",
            "eps_flat_core_rises", "missing_demand_context", "unlocated_outcome",
            "segment_and_reconciliation_absent", "conflict_outcome", "refused_document_outcome",
        } else pg_bound_case(kind).source if kind in {
            "annual_first", "combined_volume_only", "columns_reordered", "hostile_markup",
            "blank_dash", "dash_without_convention", "eps_unit_mismatch",
        } else _base_body()
    filing = _filing()
    filing["exhibit_url"] = f"https://synthetic.invalid/{case}.htm"
    return build_event_workspace(
        registry=pg_private_registry(),
        ticker="PG",
        asof=FISCAL_PERIOD.calendar_end,
        fiscal_period=fiscal_period,
        exhibit_body=body,
        filing=filing,
        transcript=None,
        observed_at="2026-07-29T17:01:00Z",
        source_available_at=ACCEPTANCE,
        prior_source_sha256=source_sha256,
        profile=pg_profile(fiscal_scope=FISCAL_SCOPE),
    )


def _case_body(case: str) -> str:
    return _body(case) if case in {
            "headline_positive_organic_flat", "reported_core_opposite_direction",
            "negative_prior_eps", "zero_prior_eps", "reported_negative_organic_positive",
            "eps_flat_core_rises", "missing_demand_context", "unlocated_outcome",
            "segment_and_reconciliation_absent", "conflict_outcome", "refused_document_outcome",
    } else pg_bound_case("combined_volume_only" if case == "combined_volume_mix" else "annual_first").source


def _texts(case: str, body: str | None = None) -> dict[str, str]:
    actual = body if body is not None else _case_body(case)
    document_id = next(
        source["document_id"]
        for source in _workspace(case, body=actual)["sources"]
        if source.get("kind") == "issuer_release"
    )
    return {document_id: actual}


def _selection(case: str):
    if case == "fake_fact_selector":
        return {"facts": [{"workspace_generation_id": "0" * 24, "event_id": "evt_wrong", "fact_id": "fact_wrong"}], "currentness": None}
    if case == "twenty_five_comparisons":
        return {"facts": [{"metric": metric, "include": True} for metric in (*PG_METRIC_KEYS, *(PG_METRIC_KEYS[:5]))], "currentness": None}
    return {"facts": None, "currentness": None}


def _case(case: str, *, fiscal_period=FISCAL_PERIOD, body: str | None = None):
    body = _case_body(case) if body is None else body
    build_kind = "eps_unit_mismatch" if case == "refused_document_outcome" else case
    workspace = _workspace(build_kind, body=body, fiscal_period=fiscal_period)
    document_id = next(
        source["document_id"]
        for source in workspace["sources"]
        if source.get("kind") == "issuer_release"
    )
    texts = {document_id: body}
    return workspace, texts


def build_case_interpretation(case: str, **overrides):
    workspace, texts = _case(case)
    return build_economic_interpretation(
        workspace,
        source_texts=texts,
        fiscal_scope=FISCAL_SCOPE,
        selection=overrides.pop("selection", _selection(case)),
        semantic_revision=SEMANTIC_REVISION,
        code_revision=overrides.pop("code_revision", CODE_REVISION),
        **overrides,
    )
