
"""GMI research-review consumer: no taxonomy admission, security identity or signal authority."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from engine.theme_graph.membership_evidence import (
    build_microtheme_research_evidence,
    render_microtheme_research_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research/theme_graph/microtheme_membership_candidates_2026-10-08.json"
CLI = ROOT / "scripts/explain_theme_overlap.py"


@pytest.fixture(scope="module")
def source_document():
    return json.loads(RESEARCH.read_text(encoding="utf-8"))


@pytest.fixture
def document(source_document):
    return copy.deepcopy(source_document)


def test_micro_research_real_document_is_readable_and_nonauthoritative(document):
    result = build_microtheme_research_evidence(document)
    assert result["schema"] == "gmi.microtheme_membership_review/v1"
    assert result["availability"]["state"] == "STRUCTURALLY_REVIEWABLE_NOT_ADMITTED"
    assert result["counts"]["micro_definitions"] == 68
    assert result["counts"]["subtheme_definitions"] == 12
    assert result["counts"]["parent_relationships"] == 132
    assert result["counts"]["candidate_activity_records"] == 103
    assert result["counts"]["source_references"] == 100
    assert result["counts"]["negative_cases"] == 14
    assert result["counts"]["cpu_scope_reviews"] == 3
    assert result["counts"]["canonical_memberships_admitted"] == 0
    assert result["counts"]["dataos_identities_qualified"] == 0
    assert result["counts"]["measurement_cohorts_admitted"] == 0
    assert all(x is False for x in result["authority"].values())
    assert all(x["canonical_security_id"] is None for x in result["candidates"])
    assert all(x["admission_status"] == "UNADMITTED_RESEARCH" for x in result["candidates"])
    assert all(x["measurement_eligible"] is False for x in result["candidates"])
    assert any(x["micro_id"] == "theme:hbm_packaging" for x in result["candidates"])
    assert any(x["parent_subtheme_ids"] for x in result["microthemes"])


def test_micro_research_no_runtime_graph_or_provider_needed(document, monkeypatch):
    from engine.theme_graph import store
    def refuse(*args, **kwargs):
        raise AssertionError("unexpected graph/data read or write")
    for name in ("read_nodes", "read_edges", "write_nodes", "write_edges"):
        monkeypatch.setattr(store, name, refuse)
    assert build_microtheme_research_evidence(document)["counts"]["candidate_activity_records"] == 103


def test_micro_research_no_input_mutation(document):
    previous = json.dumps(document, sort_keys=True)
    result = build_microtheme_research_evidence(document)
    result["candidates"][0]["role"] = "changed in output only"
    assert json.dumps(document, sort_keys=True) == previous


def test_micro_research_crosswalk_byte_fence(document, tmp_path):
    # Date-scoped fence (2026-10-21 micro expansion): the pin describes the
    # frozen pre-expansion table named by source_pin.commit, so the fence is
    # exercised against a frozen projection of the live file — the same frozen
    # rows, different bytes — plus a nonsemantic trailing comment. Any local
    # table the pin does not describe byte-for-byte refuses. The expansion era
    # itself is fenced by frozen-projection reconciliation
    # (tests/test_theme_graph_micro_expansion_20261021.py).
    import yaml
    live = yaml.safe_load((ROOT / "config/theme_crosswalk.yml").read_text(encoding="utf-8"))
    frozen = {
        key: [row for row in live["hierarchy"][key]
              if str(row.get("asserted_on", "")) < "2026-10-21"]
        for key in ("categories", "sub_themes", "micro_themes", "parents")
    }
    target = tmp_path / "crosswalk.yml"
    target.write_text(
        yaml.safe_dump({"hierarchy": frozen}, allow_unicode=True, sort_keys=False)
        + "# nonsemantic but different bytes\n", encoding="utf-8")
    with pytest.raises(ValueError, match="crosswalk bytes differ"):
        build_microtheme_research_evidence(document, crosswalk_path=target)


@pytest.mark.parametrize("mutation", [
    lambda d: d["authority"].__setitem__("ranking", True),
    lambda d: d.__setitem__("runtime_member_map", {"AAPL": "theme:hbm_packaging"}),
    lambda d: d["microthemes"][0].__setitem__("admitted", True),
    lambda d: d["subthemes"][0].__setitem__("rank_weight", 1),
    lambda d: d["candidates"][0].__setitem__("rank_score", 1),
    lambda d: d["sources"]["S001"].__setitem__("public_display_allowed", True),
    lambda d: d["negative_cases"][0].__setitem__("reviewed_by", "human"),
    lambda d: d["population"].__setitem__("complete_global_membership", True),
    lambda d: d["population"].__setitem__("canonical_memberships_admitted", 1),
    lambda d: d["population"].__setitem__("candidate_activity_records", 99),
    lambda d: d["population"]["source_stage_counts"].__setitem__("OFFERED_PRODUCT", 1),
    lambda d: d["microthemes"][0].__setitem__("micro_id", "theme:invented_runtime_micro"),
    lambda d: d["microthemes"].append(copy.deepcopy(d["microthemes"][0])),
    lambda d: d["microthemes"][0].__setitem__("parent_theme_ids", ["theme:wrong_parent"]),
    lambda d: d["subthemes"][0].__setitem__("children", ["theme:fake_child"]),
    lambda d: d["candidates"][0].__setitem__("record_id", d["candidates"][1]["record_id"]),
    lambda d: d["candidates"][0].__setitem__("micro_id", "theme:invented_runtime_micro"),
    lambda d: d["candidates"][0].__setitem__("stage", "PROVEN_TRADING_SIGNAL"),
    lambda d: d["candidates"][0].__setitem__("admission_status", "RATIFIED"),
    lambda d: d["candidates"][0].__setitem__("proposed_by", "operator"),
    lambda d: d["candidates"][0].__setitem__("identity_status", "QUALIFIED"),
    lambda d: d["candidates"][0].__setitem__("canonical_security_id", "security:FAKE"),
    lambda d: d["candidates"][0].__setitem__("economic_share", 0.8),
    lambda d: d["candidates"][0].__setitem__("valid_from", "2025-01-01"),
    lambda d: d["candidates"][0].__setitem__("measurement_eligible", True),
    lambda d: d["candidates"][0].__setitem__("current_operation_asserted", True),
    lambda d: d["candidates"][0]["source_ids"].append("S999"),
    lambda d: d["negative_cases"][0].__setitem__("adjudication", "HUMAN_APPROVED"),
    lambda d: d["cpu_scope_review"][0].__setitem__("canonical_micro_id", "theme:cpu"),
    lambda d: d["sources"]["S001"].__setitem__("rights_use_qualification", "PUBLIC_GRANTED"),
    lambda d: d["sources"]["S001"].__setitem__("full_document_archived", True),
    lambda d: d["sources"]["S001"].__setitem__("url", "file:///etc/passwd"),
    lambda d: d["sources"]["S001"].__setitem__("url", "https://127.0.0.1/secret"),
    lambda d: d["sources"]["S001"].__setitem__("url", "https://localhost/private"),
    lambda d: d["sources"]["S001"].__setitem__("published_on", "2027-01-01"),
    lambda d: d["sources"]["S001"].__setitem__("publication_precision", "YEAR"),
    # Date-scoped (2026-10-21 micro expansion): a well-formed but wrong digest
    # can only be exercised against a byte-exact pre-expansion table, so this
    # param arms the digest-format fence, which holds in both regimes; the
    # value-level fence is covered by test_micro_research_crosswalk_byte_fence.
    lambda d: d["source_pin"].__setitem__("crosswalk_sha256", "not-a-digest"),
    lambda d: d.__setitem__("schema", "gmi.microtheme_membership_research/v2"),
])
def test_micro_research_adversarial_refusals(document, mutation):
    mutation(document)
    with pytest.raises(ValueError, match="microtheme research refused"):
        build_microtheme_research_evidence(document)


def test_micro_research_valid_undated_year_and_day_source_precision(document):
    result = build_microtheme_research_evidence(document)
    assert result["sources"]["S007"]["published_on"] is None
    assert result["sources"]["S006"]["publication_precision"] == "YEAR"
    assert result["sources"]["S033"]["publication_precision"] == "DAY"


def test_micro_research_markdown_escapes_untrusted_strings(document):
    document["candidates"][0]["entity_name"] = "<script>alert(1)</script>|Broken"
    result = build_microtheme_research_evidence(document)
    md = render_microtheme_research_markdown(result)
    assert "<script>" not in md
    assert "&lt;script&gt;" in md
    assert "&#124;Broken" in md
    assert "UNADMITTED RESEARCH" in md
    assert "https://" in md


def _run_cli(*args):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT, capture_output=True, text=True, timeout=15
    )


def test_micro_research_cli_json_markdown_and_nonoverwrite(tmp_path):
    before = hashlib.sha256(RESEARCH.read_bytes()).hexdigest()
    js = _run_cli("--microtheme-research", str(RESEARCH), "--format", "json")
    assert js.returncode == 0, js.stderr
    body = json.loads(js.stdout)
    assert body["counts"]["candidate_activity_records"] == 103
    assert body["counts"]["canonical_memberships_admitted"] == 0
    md_path = tmp_path / "review.md"
    md = _run_cli("--microtheme-research", str(RESEARCH),
                  "--format", "markdown", "--out", str(md_path))
    assert md.returncode == 0, md.stderr
    assert "UNADMITTED RESEARCH" in md_path.read_text()
    assert _run_cli("--microtheme-research", str(RESEARCH), "--out", str(md_path)).returncode == 2
    assert _run_cli("--microtheme-research", str(RESEARCH), "--out", str(RESEARCH)).returncode == 2
    assert hashlib.sha256(RESEARCH.read_bytes()).hexdigest() == before


def test_micro_research_cli_refuses_invalid_without_output(tmp_path, document):
    document["authority"]["ranking"] = True
    bad = tmp_path / "research.json"
    bad.write_text(json.dumps(document))
    result = tmp_path / "never_written.json"
    process = _run_cli("--microtheme-research", str(bad), "--out", str(result))
    assert process.returncode == 2
    assert not result.exists()
    body = json.loads(process.stderr)
    assert body["schema"] == "gmi.microtheme_membership_review_refusal/v1"


def test_legacy_review_cli_requirement_retained():
    process = _run_cli("--format", "json")
    assert process.returncode != 0
    assert "--review" in process.stderr


# Independent regression probes from the exact-head review. They test refusal
# of latent untrusted-input and render-injection mistakes without changing
# any canonical membership, source data, or historical owner behavior.
@pytest.mark.parametrize("mutate", [
    lambda d: d["source_pin"].__setitem__("initial_research_snapshot", "not-a-commit"),
    lambda d: d.__setitem__("compiled_at", "2099-01-01T00:00:00+00:00"),
    lambda d: d.__setitem__("commission_date", "2099-01-01"),
    lambda d: d.__setitem__("commission_date", "not-a-date"),
    lambda d: d.__setitem__("operation", ""),
    lambda d: d.__setitem__("operation", None),
    lambda d: d.__setitem__("limitations", [""]),
    lambda d: d.__setitem__("limitations", None),
    lambda d: d["sources"]["S001"].__setitem__("catalogued_at", "2099-01-01T00:00:00+00:00"),
    lambda d: d["sources"]["S001"].__setitem__("catalogued_at", "junk"),
    lambda d: d["sources"]["S001"].__setitem__("catalogued_at", None),
    lambda d: d["sources"]["S001"].__setitem__("limitation", {"unsafe": True}),
    lambda d: d["population"].__setitem__("definition", ["not a text"]),
    lambda d: d["microthemes"][0].__setitem__("parent_theme_ids", "theme:fake"),
    lambda d: d["microthemes"][0].__setitem__("parent_subtheme_ids", {"bad": True}),
    lambda d: d["microthemes"][0].__setitem__("activity_facets", [""]),
    lambda d: d["subthemes"][0].__setitem__("name", {"bad": True}),
    lambda d: d["subthemes"][0].__setitem__("children", "fake"),
    lambda d: d["negative_cases"][0].__setitem__("case_id", {"nonhashable": True}),
    lambda d: d["negative_cases"][0].__setitem__("research_disposition", ["bad"]),
    lambda d: d["cpu_scope_review"][0].__setitem__("label", {"bad": 1}),
    lambda d: d["candidates"][0].__setitem__("source_ids", [{"bad": 1}]),
])
def test_micro_review_hardening_fails_closed(document, mutate):
    mutate(document)
    with pytest.raises(ValueError, match="microtheme research refused"):
        build_microtheme_research_evidence(document)


def test_micro_review_markdown_links_escape_delimiters_quotes_and_parens(document):
    document["sources"]["S001"]["url"] = 'https://example.org/dossier/(case)|part?label="quote"'
    review = build_microtheme_research_evidence(document)
    md = render_microtheme_research_markdown(review)
    assert "%28case%29%7Cpart?label=%22quote%22" in md
    assert '](https://example.org/dossier/(case)|part?' not in md
    line = next(x for x in md.splitlines() if x.startswith("| theme:hbm_packaging") and "Micron" in x)
    assert line.count("|") == 7


def test_cli_json_never_calls_human_renderer(tmp_path, monkeypatch, capsys, document):
    from scripts import explain_theme_overlap as cli
    path = tmp_path / "input.json"
    path.write_text(json.dumps(document))
    def forbid(*args, **kwargs):
        raise AssertionError("JSON path must not render markdown")
    monkeypatch.setattr(cli, "render_microtheme_research_markdown", forbid)
    assert cli.main(["--microtheme-research", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["counts"]["candidate_activity_records"] == 103

    monkeypatch.setattr(cli, "render_markdown", forbid)
    monkeypatch.setattr(cli, "_load", lambda _: {"kind": "fixture"})
    monkeypatch.setattr(cli, "build_overlap_evidence", lambda _: {"legacy": "unchanged"})
    assert cli.main(["--review", str(path), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"legacy": "unchanged"}


def test_cli_mode_specific_refusal_code(tmp_path):
    result = _run_cli("--microtheme-research", str(tmp_path / "missing.json"))
    assert result.returncode == 2
    body = json.loads(result.stderr)
    assert body["schema"] == "gmi.microtheme_membership_review_refusal/v1"
    assert body["code"] == "MICROTHEME_RESEARCH_UNAVAILABLE"


# M1 next wave: Data OS CURRENT identity reference hints, not issuer admission.
from engine.theme_graph.membership_evidence import (
    build_microtheme_identity_preflight,
    render_microtheme_identity_preflight_markdown,
)


@pytest.fixture
def dataos_reference_rows():
    issuer_rows = [
        {"issuer_id": "ISS:US-XNAS-MU", "legal_name": "Micron Technology Inc", "status": "active"},
        {"issuer_id": "ISS:US-XNYS-PL", "legal_name": "Planet Labs PBC", "status": "active"},
        {"issuer_id": "ISS:US-XNYS-PLNT", "legal_name": "Planet Fitness Inc", "status": "active"},
        {"issuer_id": "ISS:US-XNYS-CPT", "legal_name": "Camden Property Trust", "status": "active"},
        {"issuer_id": "ISS:US-XNAS-DEL", "legal_name": "Micron obsolete", "status": "retired"},
    ]
    security_rows = [
        {
            "security_id": "SEC:" + x["issuer_id"].removeprefix("ISS:"),
            "issuer_id": x["issuer_id"],
            "issuer_state": "RESOLVED",
            "listing_key": x["issuer_id"].removeprefix("ISS:"),
            "security_state": None,
        }
        for x in issuer_rows if x["status"] == "active"
    ]
    return issuer_rows, security_rows


def _identity_report(document, rows):
    return build_microtheme_identity_preflight(
        document,
        issuer_rows=rows[0],
        security_rows=rows[1],
        issuer_snapshot_sha256="a" * 64,
        security_snapshot_sha256="b" * 64,
    )


def test_m1_current_reference_is_diagnostic_not_member_admission(document, dataos_reference_rows):
    out = _identity_report(document, dataos_reference_rows)
    assert out["schema"] == "gmi.microtheme_identity_preflight/v1"
    assert out["counts"]["activity_records"] == 103
    assert out["counts"]["micro_definitions"] == 68
    assert sum(out["counts"]["identity_hint_states"].values()) == 103
    assert out["counts"]["canonical_memberships_admitted"] == 0
    assert out["counts"]["dataos_identities_qualified_for_micro"] == 0
    assert out["counts"]["measurement_cohorts_admitted"] == 0
    assert out["reference"]["point_in_time_issuer_history_available"] is False
    assert all(not row["measurement_eligible"] and not row["canonical_membership_admitted"]
               for row in out["candidate_diagnostics"])
    assert all(row["legal_entity_qualification"] == "NOT_PERFORMED"
               for row in out["candidate_diagnostics"])


def test_m1_identity_prefix_planet_fitness_and_amd_counterexamples(document, dataos_reference_rows):
    by_id = {
        row["record_id"]: row for row in
        _identity_report(document, dataos_reference_rows)["candidate_diagnostics"]
    }
    assert by_id["M001"]["identity_hint_state"] == "POSSIBLE_ONE_CURRENT_ISSUER"
    assert [x["issuer_id"] for x in by_id["M001"]["possible_current_issuer_refs"]] == [
        "ISS:US-XNAS-MU",
    ]
    assert by_id["M073"]["identity_hint_state"] == "AMBIGUOUS_NAME_PREFIX"
    assert {x["issuer_id"] for x in by_id["M073"]["possible_current_issuer_refs"]} == {
        "ISS:US-XNYS-PL", "ISS:US-XNYS-PLNT",
    }
    assert by_id["M008"]["identity_hint_state"] == "NO_NAME_PREFIX_IN_REFERENCE"
    assert by_id["M008"]["possible_current_issuer_refs"] == []  # AMD != Camden.


def test_m1_identity_excludes_retired_or_orphaned_issuers(document, dataos_reference_rows):
    issuers, security = copy.deepcopy(dataos_reference_rows)
    # There is a real issuer name in the catalogue but no eligible owner security.
    security[:] = [row for row in security if row["issuer_id"] != "ISS:US-XNAS-MU"]
    report = _identity_report(document, (issuers, security))
    m001 = next(x for x in report["candidate_diagnostics"] if x["record_id"] == "M001")
    assert m001["identity_hint_state"] == "NO_NAME_PREFIX_IN_REFERENCE"


@pytest.mark.parametrize("alter", [
    lambda i, s: i.append(copy.deepcopy(i[0])),
    lambda i, s: i[0].__setitem__("issuer_id", "not-a-canonical-issuer"),
    lambda i, s: i[0].__setitem__("legal_name", 42),
    lambda i, s: s.clear(),
])
def test_m1_identity_bad_dataos_rows_refused(document, dataos_reference_rows, alter):
    issuer, security = copy.deepcopy(dataos_reference_rows)
    alter(issuer, security)
    with pytest.raises(ValueError, match="microtheme"):
        _identity_report(document, (issuer, security))


def test_m1_identity_digest_format_is_strict(document, dataos_reference_rows):
    with pytest.raises(ValueError, match="unbound identity reference digest"):
        build_microtheme_identity_preflight(
            document, issuer_rows=dataos_reference_rows[0],
            security_rows=dataos_reference_rows[1],
            issuer_snapshot_sha256="not-a-sha",
            security_snapshot_sha256="b" * 64,
        )


def test_m1_identity_cannot_upgrade_model_originated_canonical_id(document, dataos_reference_rows):
    document["candidates"][0]["canonical_security_id"] = "SEC:US-XNAS-MU"
    with pytest.raises(ValueError, match="candidate contains unadmitted identity"):
        _identity_report(document, dataos_reference_rows)


def test_m1_identity_output_is_deep_copy_and_markdown_escapes(document, dataos_reference_rows):
    before = json.dumps(document, sort_keys=True)
    out = _identity_report(document, dataos_reference_rows)
    out["candidate_diagnostics"][0]["entity_name"] = "changed"
    assert json.dumps(document, sort_keys=True) == before
    out["candidate_diagnostics"][0]["entity_name"] = "fake|unsafe<tag>"
    rendered = render_microtheme_identity_preflight_markdown(out)
    assert "fake&#124;unsafe&lt;tag&gt;" in rendered
    assert "qualified identities, memberships and weights: zero" in rendered


def test_m1_identity_cli_actual_parquet_fixture(document, tmp_path):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    issuer = tmp_path / "issuer_master.parquet"
    security = tmp_path / "security_master.parquet"
    pq.write_table(pa.Table.from_pylist([
        {"issuer_id": "ISS:US-XNAS-MU", "legal_name": "Micron Technology Inc", "status": "active"},
    ]), issuer)
    pq.write_table(pa.Table.from_pylist([{
        "security_id": "SEC:US-XNAS-MU", "issuer_id": "ISS:US-XNAS-MU",
        "issuer_state": "RESOLVED", "listing_key": "US-XNAS-MU",
        "security_state": None,
    }]), security)
    source = tmp_path / "research.json"
    source.write_text(json.dumps(document))
    result = subprocess.run(
        [sys.executable, str(CLI), "--microtheme-research", str(source),
         "--issuer-reference", str(issuer), "--security-reference", str(security)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed["counts"]["identity_hint_states"]["POSSIBLE_ONE_CURRENT_ISSUER"] >= 1
    assert observed["counts"]["canonical_memberships_admitted"] == 0


def test_m1_identity_cli_partial_or_nonresearch_arguments_refused(tmp_path):
    for args in (
        ["--review", "missing.json", "--issuer-reference", "some.parquet"],
        ["--microtheme-research", "missing.json", "--issuer-reference", "some.parquet"],
    ):
        result = subprocess.run([sys.executable, str(CLI), *args],
                                cwd=ROOT, text=True, capture_output=True, check=False)
        assert result.returncode == 2
        assert json.loads(result.stderr)["ok"] is False


def test_m1_current_reference_null_legal_name_is_reported_not_guessed(
    document, dataos_reference_rows
):
    issuers, securities = copy.deepcopy(dataos_reference_rows)
    issuers.append({
        "issuer_id": "ISS:US-XNAS-NONAME",
        "legal_name": None, "status": "active",
    })
    securities.append({
        "security_id": "SEC:US-XNAS-NONAME", "issuer_id": "ISS:US-XNAS-NONAME",
        "listing_key": "US-XNAS-NONAME", "issuer_state": "RESOLVED",
        "security_state": None,
    })
    report = _identity_report(document, (issuers, securities))
    assert report["reference"]["current_issuer_rows_without_legal_name"] == 1
    assert sum(report["counts"]["identity_hint_states"].values()) == 103
    assert not any(
        x["issuer_id"] == "ISS:US-XNAS-NONAME"
        for row in report["candidate_diagnostics"]
        for x in row["possible_current_issuer_refs"]
    )


def test_m1_cli_valid_legacy_input_refuses_identity_flag_before_loading(
    document, tmp_path
):
    path = tmp_path / "valid-source.json"
    path.write_text(json.dumps(document))
    result = subprocess.run(
        [sys.executable, str(CLI), "--review", str(path),
         "--issuer-reference", str(tmp_path / "issuer_master.parquet")],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 2
    error = json.loads(result.stderr)
    assert error["code"] == "OVERLAP_EVIDENCE_UNAVAILABLE"
    assert "requires both Data OS files" in error["message"]


def test_m1_parquet_digest_and_parser_use_the_same_captured_bytes(
    tmp_path, monkeypatch
):
    """Kill the path-reopened-after-hash mutation: provenance must cover parsed bytes."""
    from scripts import explain_theme_overlap as cli
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    source = tmp_path / "current-issuer.parquet"
    pq.write_table(pa.Table.from_pylist([{
        "issuer_id": "ISS:US-XNAS-MU", "legal_name": "Micron Technology Inc", "status": "active",
    }]), source)
    original_bytes = source.read_bytes()
    original_loader = pq.ParquetFile

    def mutate_live_path_after_snapshot(snapshot, *args, **kwargs):
        assert isinstance(snapshot, pa.BufferReader), "parquet parser reopened a path"
        pq.write_table(pa.Table.from_pylist([{
            "issuer_id": "ISS:US-XNYS-PL", "legal_name": "Planet Labs", "status": "active",
        }]), source)
        return original_loader(snapshot, *args, **kwargs)

    monkeypatch.setattr(pq, "ParquetFile", mutate_live_path_after_snapshot)
    records, sha = cli._read_bounded_reference(source)
    assert records[0]["issuer_id"] == "ISS:US-XNAS-MU"
    assert sha == hashlib.sha256(original_bytes).hexdigest()
    assert source.read_bytes() != original_bytes


def test_m1_source_reader_refuses_symlinks_oversize_and_invalid_parquet(tmp_path):
    from scripts import explain_theme_overlap as cli
    invalid = tmp_path / "corrupt.parquet"
    invalid.write_bytes(b"not a parquet file")
    link = tmp_path / "redirect.parquet"
    link.symlink_to(invalid)
    oversize = tmp_path / "large.parquet"
    oversize.write_bytes(b"X" * 4_000_001)
    for path in (invalid, link, oversize):
        with pytest.raises((ValueError, OSError)):
            cli._read_bounded_reference(path)
