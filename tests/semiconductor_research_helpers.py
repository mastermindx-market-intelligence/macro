"""tests/semiconductor_research_helpers.py — shared loader for the
semiconductor theme research synthetic fixture corpus.

Every fixture file under ``tests/fixtures/semiconductor_theme_research/`` is
strictly synthetic. No native paid data, no real company identities, no real
URLs — these fixtures exist so the input contract can be tested before the
Data OS and Earnings owners are wired up (T04 / T05). Any helper function here
MUST refuse to hand back a value whose ``synthetic`` flag is not explicitly
``True``; that refusal is what keeps a future native fixture from being
mistakenly loaded in tests that promise "synthetic only".
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE_ROOT = Path(__file__).parent / 'fixtures' / 'semiconductor_theme_research'


def load_case(name: str) -> dict:
    """Load a synthetic fixture case by file stem.

    Raises ``ValueError`` if the name is not a safe alphanumeric slug, and
    raises ``ValueError`` if the loaded payload is not explicitly marked
    ``{"synthetic": true}``. Both refusals are loud on purpose: a real
    fixture whose ``synthetic`` flag is missing or false is a contract
    violation, not a soft warning.
    """
    if not name.replace('_', '').isalnum():
        raise ValueError('invalid test case name')
    value = json.loads((FIXTURE_ROOT / (name + '.json')).read_text())
    if not isinstance(value, dict) or value.get('synthetic') is not True:
        raise ValueError('fixture must explicitly be synthetic')
    return value


def load_bundle_case(name: str):
    """Load a synthetic bundle-bearing fixture and build the F04 objects.

    The lazy import inside the function body is intentional — the
    ``engine.market_ontology.semiconductor_theme_research`` module is owned
    by a later task (F04) and does not yet exist. Tests that only exercise
    the JSON shape should call :func:`load_case` instead.
    """
    from engine.market_ontology.semiconductor_theme_research import ResearchQuery, OwnerBundle
    value = load_case(name)
    source = value['bundle']
    bundle = OwnerBundle(
        revision_tuple=tuple(tuple(x) for x in source['revision_tuple']),
        rights_revision=source['rights_revision'],
        assertions=tuple(source['assertions']),
        identity_results=tuple(source['identity_results']),
        event_workspaces=tuple(source['event_workspaces']),
        financial_packets=tuple(source['financial_packets']),
        interpretation_blocks=tuple(source['interpretation_blocks']),
        native_refs=tuple(source['native_refs']),
        omissions=tuple(source['omissions']),
    )
    return ResearchQuery(**value['query']), bundle


# ---------------------------------------------------------------------------
# T08c-2 — a synthetic Company Intelligence nest for the two witnesses, built
# with the PRODUCTION writer from the real-metadata payloads the intake
# integration suite discovers (production identity + profile + closed release
# grammars; only the network is replaced; exhibit bodies are the integration
# module's synthetic look-alikes with invented numbers — never a real body).
# ---------------------------------------------------------------------------

#: The origin the reader is pinned to in tests (RFC 2606 ``.example``); the
#: production default is never resolved and no public-hostname DNS check runs.
WITNESS_NEST_BASE = "https://company-intelligence.example/company_intelligence"


def witness_workspace_payloads(*, tickers=("TSM", "ON"), periods=(1, 2)) -> dict:
    """``{event_id: workspace payload}`` for the witnesses' fiscal periods.

    The payloads come from the earnings intake's own discovery over real
    issuer metadata and synthetic exhibit bodies — nothing here hand-writes a
    workspace. Split out of :func:`build_witness_nest` so a caller can write
    MORE THAN ONE generation from the same payloads (the publication-primitive
    proofs need a chained successor).
    """
    import pytest  # noqa: PLC0415 — test-only helper
    from engine.company_intelligence.issuer_profiles import ON_CIK, TSM_CIK  # noqa: PLC0415
    from tests import test_semiconductor_earnings_intake_integration as intake  # noqa: PLC0415

    recipes = {
        "TSM": dict(ticker="TSM", cik=TSM_CIK, rows=intake.TSM_ROWS + [intake.TSM_Q1_ROW],
                    manifests={**intake.TSM_MANIFESTS, **intake.TSM_Q1_MANIFEST},
                    bodies={intake.TSM_RESULTS_ACCESSION: intake.TSM_SYNTHETIC_EXHIBIT,
                            intake.TSM_Q1_RESULTS_ACCESSION: intake.TSM_Q1_SYNTHETIC_EXHIBIT}),
        "ON": dict(ticker="ON", cik=ON_CIK, rows=intake.ON_ROWS + intake.ON_Q2_ROWS,
                   manifests={**intake.ON_MANIFESTS, **intake.ON_Q2_MANIFESTS},
                   bodies={intake.ON_RESULTS_ACCESSION: intake.ON_SYNTHETIC_EXHIBIT,
                           intake.ON_Q2_RESULTS_ACCESSION: intake.ON_Q2_SYNTHETIC_EXHIBIT}),
    }
    workspaces = {}
    with pytest.MonkeyPatch.context() as mp:
        for ticker in tickers:
            revisions, _fetched = intake._discover(mp, **recipes[ticker])
            for event_id, payload in revisions:
                if (payload.get("fiscal_period") or {}).get("quarter") in periods:
                    workspaces[event_id] = payload
    return workspaces


def nest_files(out_dir) -> dict:
    """``{url: bytes}`` for every object under a written nest directory."""
    out = Path(out_dir)
    return {
        f"{WITNESS_NEST_BASE}/{path.relative_to(out).as_posix()}": path.read_bytes()
        for path in out.rglob("*.json")
    }


def build_witness_nest(tmp_dir, *, tickers=("TSM", "ON"), periods=(1, 2)) -> dict:
    """Return ``{url: bytes}`` for a one-generation ``event_workspaces/`` nest
    holding the requested witnesses' fiscal periods (Q1/Q2 2026), written by
    :func:`engine.company_intelligence.event_workspace.write_workspace_generation`
    under ``tmp_dir`` so marker, immutable manifest and per-object sha256/byte
    receipts are the producer's own."""
    from engine.company_intelligence.event_workspace import write_workspace_generation  # noqa: PLC0415

    workspaces = witness_workspace_payloads(tickers=tickers, periods=periods)
    out = Path(tmp_dir) / "company_intelligence"
    write_workspace_generation(out, workspaces, generated_at="2026-09-24T15:00:00Z", status="ready")
    return nest_files(out)


def wire_witness_nest(monkeypatch, files: dict) -> list:
    """Pin the reader to :data:`WITNESS_NEST_BASE` and serve ``files`` through
    its byte fetcher (the reader's own test seam, ``_wire_remote``). Returns the
    list of URLs fetched, in order. Nothing else is patched: marker →
    immutable generation → receipt verification → contract validation all run
    for real."""
    from engine.neuralweb import company_intelligence_reader as reader  # noqa: PLC0415

    calls: list = []
    reader.clear_company_intelligence_cache()
    monkeypatch.setattr(reader, "_public_base_url", lambda: WITNESS_NEST_BASE)

    def fetch(url: str, *, limit: int) -> bytes:
        calls.append(url)
        if url not in files:
            raise reader.CompanyIntelligenceReadError("Company Intelligence public source unavailable")
        assert len(files[url]) <= limit
        return files[url]

    monkeypatch.setattr(reader, "_fetch_bytes", fetch)
    return calls
