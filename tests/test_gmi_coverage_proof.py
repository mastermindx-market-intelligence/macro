"""Fixture-only tests for the GMI step-7 coverage proof CLI (measurement only).

Every input is built under ``tmp_path``; ``data/`` is never read. The real repo
crosswalk is used only for the scope-version parity test and the real recovery doc
only for the verbatim-threshold test, exactly as the commission requires. The
expected activity-gate verdict on these fixtures is FAIL, and the tests hold FAIL
to FAIL.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import yaml

from engine.theme_graph import membership_evidence as me
from engine.theme_graph import probation, store
from scripts import gmi_coverage_proof as gcp

REPO = Path(__file__).resolve().parents[1]
CODE_VERSION = "0" * 40
CREATED = "2026-10-19T06:00:00Z"
DECIDED = "2026-10-19T07:00:00Z"
COMPUTED = "2026-10-18T11:03:21Z"
BELIEF = "2026-10-18T12:00:00Z"
STALE_HASH = "f" * 64
MICROS = ("theme:fixture_micro_a", "theme:fixture_micro_b", "theme:fixture_micro_c")


def _row_of(columns, **values):
    row = {column: None for column in columns}
    row.update(values)
    return row


def _node(node_id, *, kind="company", market="us", external_ids=None):
    return _row_of(store.NODE_COLUMNS, node_id=node_id, kind=kind, name_en=node_id,
                   market_scope=market, status="canonical", identity_epoch=1,
                   birth_date="2026-10-01",
                   external_ids=json.dumps(external_ids or {}),
                   computed_at=COMPUTED, engine_version=store.ENGINE_VERSION)


def _identity(node_id, market, state, *, security_id=None, issuer_id=None,
              computed_at=COMPUTED):
    return _row_of(store.IDENTITY_RESOLUTION_COLUMNS, schema="gmi.identity_resolution/v1",
                   node_id=node_id, graph_kind="company", market_scope=market,
                   graph_identity_epoch=1, resolution_asof="2026-10-18",
                   resolution_state=state, issuer_id=issuer_id, security_id=security_id,
                   computed_at=computed_at, engine_version=store.ENGINE_VERSION)


def _lifecycle(node_id, status, computed_at):
    return _row_of(store.NODE_LIFECYCLE_COLUMNS, schema="gmi.node_lifecycle/v1",
                   node_id=node_id, status=status,
                   retire_date="2026-10-05" if status in store.RETIRED_LIKE_STATUSES else None,
                   ratified_by="fixture", computed_at=computed_at,
                   engine_version=store.ENGINE_VERSION)


def _edge(edge_id, type_, src, dst, **overrides):
    row = _row_of(store.EDGE_COLUMNS, edge_id=edge_id, type=type_, src=src, dst=dst,
                  valid_from="2026-10-01", belief_time=BELIEF, era="current",
                  source_class="vendor", computed_at=COMPUTED,
                  engine_version=store.ENGINE_VERSION)
    row.update(overrides)
    return row


def _master(security_id, issuer_id, issuer_state, country, mic, inception,
            security_state=None):
    return _row_of(("security_id", "issuer_id", "issuer_state", "issuer_cik",
                    "issuer_evidence_snapshot", "listing_key", "country", "mic",
                    "inception_code", "effective_at", "ingested_at", "security_state",
                    "superseded_by"), security_id=security_id, issuer_id=issuer_id,
                   issuer_state=issuer_state, listing_key=inception, country=country,
                   mic=mic, inception_code=inception, effective_at="2026-01-01",
                   ingested_at="2026-10-18T00:00:00Z", security_state=security_state)


US_RESOLVED = (("MU", "XNAS"), ("MSFT", "XNAS"), ("AVGO", "XNAS"), ("QCOM", "XNAS"),
               ("TXN", "XNAS"), ("AMD", "XNAS"), ("RTD", "XNAS"))
DIRECTORY_ROWS = [("MU", False, False, False, "XNAS"), ("SPY", True, False, False, "ARC"),
                  ("AAp", False, False, True, "NYSE"), ("TESTLTR", False, True, False, "XNAS")]


def _master_rows():
    rows = [_master(f"SEC:US-XNAS-{sym}", f"ISS:US-XNAS-{sym}", "RESOLVED", "US", mic, sym)
            for sym, mic in US_RESOLVED]
    rows += [_master("SEC:US-ARC-SPY", "ISS:US-ARC-SPY", "RESOLVED", "US", "ARC", "SPY"),
             _master("SEC:US-NYSE-AAp", "ISS:US-NYSE-AA", "RESOLVED", "US", "NYSE", "AAp"),
             _master("SEC:US-XNAS-DUP", "ISS:US-XNAS-DUP", "RESOLVED", "US", "NAS", "DUP",
                     security_state="SUPERSEDED_DUPLICATE_MINT"),
             _master("SEC:US-ARC-ETFN", "ISS:US-ARC-ETFN", "RESOLVED", "US", "ARC", "ETFN"),
             _master("SEC:US-XNAS-ZZT", "ISS:US-XNAS-ZZT", "NO_ISSUER_EVIDENCE", "US",
                     "XNAS", "ZZT"),
             _master("SEC:US-XNAS-CFT", "ISS:US-XNAS-CFT", "EVIDENCE_CONFLICT", "US",
                     "XNAS", "CFT"),
             _master("SEC:US-XNAS-DIE", "ISS:US-XNAS-DIE", "DEFERRED_IDENTITY_EXCEPTION",
                     "US", "XNAS", "DIE"),
             _master("SEC:CN-SSE-600000", "ISS:CN-600000", "RESOLVED", "CN", "SSE", "600000"),
             _master("SEC:CN-SZSE-000001", "ISS:CN-000001", "NO_ISSUER_EVIDENCE", "CN",
                     "SZSE", "000001"),
             _master("SEC:CN-SSE-600519", "ISS:CN-600519", "RESOLVED", "CN", "SSE", "600519"),
             _master("SEC:CN-SZSE-300750", "ISS:CN-300750", "RESOLVED", "CN", "SZSE", "300750"),
             _master("SEC:HK-00700", "ISS:HK-00700", "RESOLVED", "HK", "HKEX", "00700"),
             _master("SEC:CA-TSX-CCR", "ISS:CA-CCR", "NO_ISSUER_EVIDENCE", "CA", "TSX", "CCR"),
             _master("SEC:DE-XETR-SAP", "ISS:DE-SAP", "RESOLVED", "DE", "XETR", "SAP")]
    return rows


def _identity_rows():
    rows = [_identity(f"co:us:{sym}", "us", "RESOLVED",
                      security_id=f"SEC:US-XNAS-{sym}", issuer_id=f"ISS:US-XNAS-{sym}")
            for sym, _ in US_RESOLVED]
    rows += [_identity("co:us:MU", "us", "RESOLVED", security_id="SEC:US-OLD",
                       issuer_id="ISS:US-OLD", computed_at="2026-10-17T09:00:00Z"),
             _identity("co:us:MU2", "us", "RESOLVED", security_id="SEC:US-XNAS-MU",
                       issuer_id="ISS:US-XNAS-MU"),
             _identity("co:us:GHOST", "us", "NOT_IN_MASTER"),
             _identity("co:us:ORPH", "us", "RESOLVED", security_id="SEC:US-GRAPHONLY",
                       issuer_id="ISS:US-GRAPHONLY"),
             _identity("co:cn:600000", "cn", "RESOLVED", security_id="SEC:CN-SSE-600000",
                       issuer_id="ISS:CN-600000"),
             _identity("co:cn:600519.SH", "cn", "ENTITY_TYPE_CONFLICT"),
             _identity("co:cn:300750.SZ", "cn", "DEFERRED_IDENTITY_EXCEPTION"),
             _identity("co:ca:CCR", "ca", "NOT_IN_MASTER"),
             _identity("co:hk:00700", "hk", "RESOLVED", security_id="SEC:HK-00700",
                       issuer_id="ISS:HK-00700")]
    return rows


def _hierarchy_yaml():
    entry = lambda id_, name: {"id": id_, "name_en": name, "name_zh": name,
                               "asserted_on": "2026-10-08"}
    return {
        "hierarchy": {
            "categories": [entry("theme:fixture_cat_a", "Cat A"),
                           entry("theme:fixture_cat_b", "Cat B")],
            "sub_themes": [entry("theme:fixture_sub", "Sub")],
            "micro_themes": [entry(MICROS[0], "Micro A"), entry(MICROS[1], "Micro B"),
                             entry(MICROS[2], "Micro C")],
            "parents": [
                {"parent": "theme:fixture_cat_a", "child": "theme:fixture_sub",
                 "asserted_on": "2026-10-08"},
                {"parent": "theme:fixture_cat_a", "child": MICROS[0], "asserted_on": "2026-10-08"},
                {"parent": "theme:fixture_cat_a", "child": MICROS[2], "asserted_on": "2026-10-08"},
                {"parent": "theme:fixture_sub", "child": MICROS[1], "asserted_on": "2026-10-08"},
                {"parent": "theme:fixture_sub", "child": MICROS[2], "asserted_on": "2026-10-08"},
            ],
        }
    }


_DISCLOSURE = None


def _disclosure():
    """The REAL disclosure owner's qualified snapshot, read once from the repo
    (research/, config/ — never data/). Only its fact is re-subjected per row."""
    global _DISCLOSURE
    if _DISCLOSURE is None:
        _DISCLOSURE = me._default_activity_disclosure(REPO, CODE_VERSION)
    return _DISCLOSURE


def _a1_row(root: Path, node_id: str, security_id: str, issuer_id: str, theme_id: str,
            *, definition_override: str | None = None) -> dict:
    """A fully valid A1 proposal built through the real owners: the real disclosure
    snapshot (fact re-subjected to the fixture issuer), a fixture identity row, and
    the fixture crosswalk as the target definition."""
    spec = copy.deepcopy(_disclosure().spec)
    spec["fact"]["subject_id"] = issuer_id
    identity = {"schema": "gmi.identity_resolution/v1", "node_id": node_id,
                "graph_kind": "company", "market_scope": "us", "resolution_asof": "2026-10-18",
                "resolution_state": "RESOLVED", "issuer_id": issuer_id,
                "security_id": security_id, "join_method": "master_inception_exact"}
    evidence = me.build_activity_membership_evidence(
        issuer_node_id=node_id, target_theme_id=theme_id, role="component_supplier",
        knowledge_cutoff="2026-10-19T00:00:00Z", code_version=CODE_VERSION, root=root,
        identity_reader=lambda node: dict(identity),
        disclosure_reader=lambda _root, _code: SimpleNamespace(
            spec=spec, bindings=dict(_disclosure().bindings)))
    if definition_override is not None:
        evidence["target_definition"]["definition_sha256"] = definition_override
    # A construction is a PROPOSED row; only an explicit named curation below turns
    # one into RATIFIED.
    return probation.make_activity_membership_proposal(evidence, created=CREATED)


def _curated(row, *, status="RATIFIED", decision="ACCEPT"):
    out = copy.deepcopy(row)
    out["status"] = status
    out["curation"] = {"curator": "curator:gmi-desk", "decision": decision,
                       "decided_at": DECIDED,
                       "receipt_sha256": hashlib.sha256(b"curation").hexdigest()}
    return out


def _stale(row):
    out = copy.deepcopy(row)
    out["evidence"]["target_definition"]["definition_sha256"] = STALE_HASH
    out["proposal_id"] = probation.activity_proposal_id(out["evidence"])
    assert probation.validate_activity_membership_proposal(out) == []
    return out


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                    encoding="utf-8")


def _build(tmp_path: Path, queue: str = "current") -> SimpleNamespace:
    root = tmp_path / "repo"
    (root / "config").mkdir(parents=True)
    hierarchy = _hierarchy_yaml()
    (root / "config" / "theme_crosswalk.yml").write_text(
        yaml.safe_dump(hierarchy, allow_unicode=True), encoding="utf-8")

    store_dir = root / "store"
    (store_dir / "probation").mkdir(parents=True)
    nodes = [_node("co:us:MU"), _node("co:us:MU2"), _node("co:us:MSFT"), _node("co:us:AVGO"),
             _node("co:us:QCOM"), _node("co:us:TXN"), _node("co:us:AMD"), _node("co:us:RTD"),
             _node("co:us:GHOST"), _node("co:us:ORPH"),
             _node("co:us:ETFNODE", kind="etf", external_ids={"symbol": "ETFN.N"}),
             _node("co:cn:600000", market="cn"), _node("co:cn:600519.SH", market="cn"),
             _node("co:cn:300750.SZ", market="cn"),
             _node("basket:baskets:ai", kind="basket"),
             _node(MICROS[0], kind="local_theme"), _node(MICROS[1], kind="local_theme"),
             _node("co:ca:CCR", market="ca"), _node("co:hk:00700", market="hk")]
    pd.DataFrame(nodes).to_parquet(store_dir / "nodes.parquet", index=False)
    pd.DataFrame(_identity_rows()).to_parquet(store_dir / "identity_resolution.parquet",
                                              index=False)
    pd.DataFrame([_lifecycle("co:us:RTD", "retired", "2026-10-18T12:30:00Z")]
                 ).to_parquet(store_dir / "node_lifecycle.parquet", index=False)
    edges = [_edge("e1", "MEMBER_OF", "co:us:MU", "basket:baskets:ai"),
             _edge("e1", "MEMBER_OF", "co:us:MU", "basket:baskets:ai",
                   valid_to="2026-10-10", belief_time="2026-10-10T00:00:00Z",
                   computed_at="2026-10-10T00:00:00Z"),
             _edge("e2", "MEMBER_OF", "co:us:MSFT", "basket:baskets:ai"),
             _edge("e4", "EXPRESSES", "basket:baskets:ai", MICROS[0]),
             _edge("e5", "EXPRESSES", "basket:baskets:ai", MICROS[1])]
    pd.DataFrame(edges).to_parquet(store_dir / "edges.parquet", index=False)
    (store_dir / "_meta.json").write_text(json.dumps(
        {"computed_at": COMPUTED, "belief_time": BELIEF, "counts": {"nodes": len(nodes)}}),
        encoding="utf-8")

    rows = []
    if queue != "none":
        mu = _curated(_a1_row(root, "co:us:MU", "SEC:US-XNAS-MU", "ISS:US-XNAS-MU",
                              MICROS[0]))
        qcom = _curated(_a1_row(root, "co:us:QCOM", "SEC:US-XNAS-QCOM", "ISS:US-XNAS-QCOM",
                                MICROS[0]))
        if queue == "stale":
            # Both ratifications predate the current definition: nothing is current.
            mu, qcom = _stale(mu), _stale(qcom)
        else:
            qcom = _stale(qcom)  # QCOM's ratification predates the current definition
        amd = _curated(_a1_row(root, "co:us:AMD", "SEC:US-XNAS-AMD", "ISS:US-XNAS-AMD",
                               MICROS[2]), status="REJECTED", decision="REJECT")
        avgo = _a1_row(root, "co:us:AVGO", "SEC:US-XNAS-AVGO", "ISS:US-XNAS-AVGO",
                       MICROS[1])  # stays PROPOSED: never admitted
        rows = [mu, qcom, amd, avgo]
    _write_jsonl(store_dir / "probation" / "proposals.jsonl", rows)

    reference = root / "reference"
    reference.mkdir()
    master = pd.DataFrame(_master_rows())
    master_path = reference / "security_master.parquet"
    master.to_parquet(master_path, index=False)
    receipt_path = reference / "_receipt.json"
    receipt_path.write_text(json.dumps({
        "generated_at": "2026-10-18T06:00:00Z", "symbol_directory_snapshot": "2026-10-17",
        "code_version": CODE_VERSION, "cik_map_snapshot": "2026-10-17"}), encoding="utf-8")

    snapshots = root / "snapshots"
    snapshots.mkdir()
    directory_path = snapshots / "2026-10-17.parquet"
    pd.DataFrame(DIRECTORY_ROWS, columns=["symbol", "etf", "test_issue", "is_preferred",
                                          "exchange"]).to_parquet(directory_path, index=False)
    directory_manifest_path = snapshots.parent / "directory_manifest.json"
    directory_manifest_path.write_text(json.dumps(
        {"last_snapshot_date": "2026-10-17", "n_symbols": len(DIRECTORY_ROWS),
         "_display_only": True, "_version": "v1"}), encoding="utf-8")

    research_path = root / "research_candidates.json"
    research_path.write_text(json.dumps({
        "candidates": [{"micro_id": MICROS[0]}, {"micro_id": "fixture_micro_b"}],
        "negative_cases": [{"micro_id": "theme:unknown_micro"}], "scope_holds": []}),
        encoding="utf-8")
    return SimpleNamespace(
        root=root, store=store_dir, master=master_path, receipt=receipt_path,
        directory=directory_path, directory_manifest=directory_manifest_path,
        hierarchy=root / "config" / "theme_crosswalk.yml", research=research_path,
        out=root / "out")


def _argv(fixture: SimpleNamespace, out: Path | None = None, extra: list[str] | None = None):
    argv = ["--master", str(fixture.master), "--receipt", str(fixture.receipt),
            "--symbol-directory", str(fixture.directory),
            "--symbol-directory-manifest", str(fixture.directory_manifest),
            "--store", str(fixture.store), "--hierarchy", str(fixture.hierarchy),
            "--research-records", str(fixture.research),
            "--out", str(out or fixture.out), "--repo-root", str(fixture.root)]
    return argv + (extra or [])


def _outputs(out: Path) -> tuple[dict, dict, str]:
    report = json.loads((out / "coverage_report.json").read_text(encoding="utf-8"))
    manifest = json.loads((out / "UNIVERSE_MANIFEST.json").read_text(encoding="utf-8"))
    return report, manifest, (out / "COVERAGE_REPORT.md").read_text(encoding="utf-8")


def _run(fixture: SimpleNamespace, out: Path | None = None, extra: list[str] | None = None):
    assert gcp.main(_argv(fixture, out, extra)) == 0
    return _outputs(out or fixture.out)


def _gate(report: dict, dimension: str, market: str | None = None) -> dict:
    return next(g for g in report["gates"] if g["dimension"] == dimension
                and (market is None or g["measured"].get("market") == market))


# --- 1 -----------------------------------------------------------------------
def test_us_and_cn_denominators_are_separate_and_never_summed(tmp_path):
    fixture = _build(tmp_path)
    report, manifest, _ = _run(fixture)
    assert set(manifest["core_markets"]) == {"us", "cn"}
    us = manifest["core_markets"]["us"]["securities_total"]
    cn = manifest["core_markets"]["cn"]["securities_total"]
    assert (us, cn) == (14, 4) and us != cn

    def sweep(value, path=""):
        if isinstance(value, dict):
            for key, item in value.items():
                assert str(key).lower() not in {"total", "all_markets", "combined",
                                                "overall", "core_total"}, f"{path}.{key}"
                sweep(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                sweep(item, f"{path}[{index}]")

    sweep(manifest)
    sweep(report)
    assert manifest["provenance_only_counts"]["master_rows"] == 21
    assert manifest["provenance_only_counts"]["note"].endswith("never a denominator")
    assert gcp.CORE_MARKETS == ("us", "cn") and gcp.WIDER_MARKETS == ("ca", "hk", "intl")


# --- 2 -----------------------------------------------------------------------
def test_issuer_and_security_counts_are_separate(tmp_path):
    fixture = _build(tmp_path)
    _, manifest, _ = _run(fixture)
    us = manifest["core_markets"]["us"]
    assert us["securities_total"] == 14
    assert us["issuers_resolved_distinct"] == 11 != us["securities_total"]
    assert us["issuers_resolved_distinct_eligible"] == 7
    unresolved = us["eligible_securities_without_resolved_issuer"]
    assert unresolved == {"NO_ISSUER_EVIDENCE": 1, "EVIDENCE_CONFLICT": 1,
                          "DEFERRED_IDENTITY_EXCEPTION": 1}
    cn = manifest["core_markets"]["cn"]
    assert cn["issuers_resolved_distinct"] == 3
    assert cn["issuers_resolved_distinct_eligible"] == 2


# --- 3 -----------------------------------------------------------------------
def test_vendor_member_of_never_enters_activity_numerator(tmp_path):
    fixture = _build(tmp_path)
    (fixture.store / "probation" / "proposals.jsonl").unlink()  # no activity rows at all
    report, manifest, _ = _run(fixture)
    vendor = report["vendor_membership_not_principal_activity"]["us"]
    assert vendor == {"eligible_issuers_with_current_member_of": 2,
                      "eligible_securities_with_current_member_of": 2,
                      "member_of_edges_by_dst_kind": {"basket": 2},
                      "member_of_edges_by_source_class": {"vendor": 2}}
    activity = report["activity"]["us"]
    assert activity["numerator_issuers"] == 0
    assert activity["denominator"]["eligible_issuers_resolved"] == 7
    # MU and MSFT both carry a current vendor MEMBER_OF and nothing else.
    assert activity["remainder_by_reason"]["VENDOR_MEMBERSHIP_ONLY"] == 2
    assert activity["remainder_by_reason"]["NO_ACTIVITY_EVIDENCE"] == 4
    assert _gate(report, "Principal activity coverage", "us")["verdict"] == "FAIL"


# --- 4 -----------------------------------------------------------------------
def test_gate2_tokens_are_never_activity_labels(tmp_path):
    fixture = _build(tmp_path)
    base_report, _, _ = _run(fixture)
    assert base_report["activity"]["us"]["numerator_issuers"] == 1
    assert base_report["activity"]["us"]["proposals_seen"]["forbidden_label_rows"] == 0

    out = tmp_path / "out_forbidden"
    forbidden = [_curated(_a1_row(fixture.root, "co:us:TXN", "SEC:US-XNAS-TXN",
                                  "ISS:US-XNAS-TXN", MICROS[0])),
                 _curated(_a1_row(fixture.root, "co:us:TXN", "SEC:US-XNAS-TXN",
                                  "ISS:US-XNAS-TXN", MICROS[1]))]
    for row, target in zip(forbidden, ("basket:baskets_china_ths:x", "ltheme:finviz:x")):
        row["evidence"]["target_definition"]["theme_id"] = target
        row["evidence"]["endpoints"]["target_node_id"] = target
        row["proposal_id"] = probation.activity_proposal_id(row["evidence"])
    proposals_file = tmp_path / "extra_proposals.jsonl"
    _write_jsonl(proposals_file, forbidden)
    report, _, _ = _run(fixture, out=out, extra=["--activity-proposals", str(proposals_file)])
    seen = report["activity"]["us"]["proposals_seen"]
    assert seen["forbidden_label_rows"] == 2 and seen["total_rows"] == 6
    assert report["activity"]["us"]["numerator_issuers"] == 1
    for name in ("UNIVERSE_MANIFEST.json", "coverage_report.json", "COVERAGE_REPORT.md"):
        text = (out / name).read_text(encoding="utf-8")
        assert "basket:baskets_china_ths:x" not in text
        assert "ltheme:finviz:x" not in text
        assert "basket:" not in text and "ltheme:" not in text


# --- 5 -----------------------------------------------------------------------
def test_ratified_a1_row_enters_numerator(tmp_path):
    fixture = _build(tmp_path)
    report, _, _ = _run(fixture)
    activity = report["activity"]["us"]
    # The RATIFIED A1 row was built through the real owners; its
    # target_definition.definition_sha256 equals the fixture hierarchy scope_version.
    assert activity["proposals_seen"]["ratified_valid"] == 2
    assert activity["proposals_seen"]["scope_stale"] == 1
    assert activity["numerator_issuers"] == 1
    # QCOM's RATIFIED row predates the current definition: named remainder, not numerator.
    assert activity["remainder_by_reason"]["ADMITTED_SCOPE_STALE"] == 1

    stale_fixture = _build(tmp_path / "stale", queue="stale")
    stale_report, _, _ = _run(stale_fixture)
    stale = stale_report["activity"]["us"]
    assert stale["numerator_issuers"] == 0
    # Both stale RATIFIED rows (MU and QCOM) land on the same named remainder.
    assert stale["remainder_by_reason"]["ADMITTED_SCOPE_STALE"] == 2
    assert stale["proposals_seen"]["scope_stale"] == 2
    assert _gate(stale_report, "Principal activity coverage", "us")["verdict"] == "FAIL"


# --- 6 -----------------------------------------------------------------------
def test_closed_enums_are_enforced(tmp_path):
    fixture = _build(tmp_path)
    master = pd.read_parquet(fixture.master)
    master = pd.concat([master, pd.DataFrame([_master("SEC:US-XNAS-WEIRD", "ISS:US-WEIRD",
                                                      "WEIRD", "US", "XNAS", "WEIRD")])])
    bad_master = tmp_path / "bad_master.parquet"
    master.to_parquet(bad_master, index=False)
    out = tmp_path / "out_never"
    argv = _argv(fixture, out=out)
    argv[argv.index("--master") + 1] = str(bad_master)
    assert gcp.main(argv) == 2
    assert not out.exists()
    with pytest.raises(gcp.CoverageProofRefusal):
        gcp._reason_owner("TOTALLY_UNKNOWN_REASON", "us")
    with pytest.raises(gcp.CoverageProofRefusal):
        gcp._reason_owner("GRAPH_ONLY", "ca")  # a ledger state with no owner row refuses


# --- 7 -----------------------------------------------------------------------
def test_micro_count_discrepancy_is_reported_not_forced(tmp_path):
    fixture = _build(tmp_path)  # the fixture hierarchy carries exactly 3 micros
    report, _, markdown = _run(fixture)
    taxonomy = report["taxonomy"]
    assert taxonomy["observed_micro_count"] == 3
    assert taxonomy["declared_micro_count"] == 68
    assert taxonomy["discrepancy"] == "observed 3 != declared 68"
    gate = _gate(report, "Taxonomy coverage")
    assert gate["verdict"] == "FAIL"
    assert gate["measured"]["owner_reviewed"] is False
    assert "observed 3 != declared 68" in markdown
    assert taxonomy["unknown_research_micro_ids"] == ["theme:unknown_micro"]


# --- 8 -----------------------------------------------------------------------
def test_manifest_version_is_stable_across_runs(tmp_path):
    fixture = _build(tmp_path)
    out_one, out_two = tmp_path / "run_one", tmp_path / "run_two"
    _run(fixture, out=out_one)
    _run(fixture, out=out_two)
    names = ("UNIVERSE_MANIFEST.json", "coverage_report.json", "COVERAGE_REPORT.md")
    for name in names:
        assert (out_one / name).read_bytes() == (out_two / name).read_bytes(), name
    report, manifest, _ = _outputs(out_one)
    expect_manifest = hashlib.sha256(json.dumps(
        {k: v for k, v in manifest.items()
         if k not in ("manifest_version", "source_commit")},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert manifest["manifest_version"] == expect_manifest == report["manifest_version"]


# --- 9 -----------------------------------------------------------------------
@pytest.mark.parametrize("guarded", ["data", "site"])
def test_out_under_data_or_site_is_refused(tmp_path, guarded):
    fixture = _build(tmp_path)
    out = fixture.root / guarded / "proof"
    assert gcp.main(_argv(fixture, out=out)) == 2
    assert not out.exists()
    exact = fixture.root / guarded
    assert gcp.main(_argv(fixture, out=exact)) == 2
    assert not (exact / "coverage_report.json").exists()


# --- 10 ----------------------------------------------------------------------
def test_thresholds_are_verbatim_substrings_of_the_recovery_doc():
    doc = (REPO / "research/theme_graph/GMI_PROGRAM_RECOVERY_2026-10-16.md").read_text(
        encoding="utf-8")
    assert set(gcp.THRESHOLDS) == {
        "Denominator honesty", "Principal activity coverage", "Taxonomy coverage",
        "Correctness", "Automatic admission", "Freshness", "Corrections",
        "Product usefulness", "Predictive claims"}
    for dimension, threshold in gcp.THRESHOLDS.items():
        assert threshold in doc, dimension


# --- 11 ----------------------------------------------------------------------
def test_activity_gate_fail_stays_fail(tmp_path):
    fixture = _build(tmp_path)
    report, _, markdown = _run(fixture)
    for market, numerator, upper in (("us", 1, 10), ("cn", 0, 3)):
        gate = _gate(report, "Principal activity coverage", market)
        measured = gate["measured"]
        assert measured["numerator_issuers"] == numerator
        assert measured["denominator_upper_bound"] == upper
        assert numerator * 100 < 95 * upper  # the integer compare the gate must use
        assert gate["verdict"] == "FAIL"
    assert [g["verdict"] for g in report["gates"]].count("NOT_IN_THIS_LANE") == 6
    assert "FAIL stays FAIL: this report never rounds a failing gate into a pass." in markdown


# --- 12 ----------------------------------------------------------------------
def test_replicated_collapses_equal_store_readers(tmp_path, monkeypatch):
    fixture = _build(tmp_path)
    monkeypatch.setattr(store, "store_dir", lambda: fixture.store)
    identity_raw = pd.read_parquet(fixture.store / "identity_resolution.parquet")
    lifecycle_raw = pd.read_parquet(fixture.store / "node_lifecycle.parquet")
    nodes_raw = pd.read_parquet(fixture.store / "nodes.parquet")
    edges_raw = pd.read_parquet(fixture.store / "edges.parquet")
    pd.testing.assert_frame_equal(gcp._latest_by_node(identity_raw),
                                  store.read_identity_resolution(latest=True))
    pd.testing.assert_frame_equal(gcp._latest_by_node(lifecycle_raw),
                                  store.read_node_lifecycle(latest=True))
    pd.testing.assert_frame_equal(
        gcp._overlay_lifecycle(nodes_raw, gcp._latest_by_node(lifecycle_raw)),
        store.read_nodes(current=True))
    pd.testing.assert_frame_equal(gcp._latest_belief_edges(edges_raw),
                                  store.read_edges(latest_belief=True))


# --- 13 ----------------------------------------------------------------------
def test_scope_version_equals_activity_target_definition():
    crosswalk = REPO / "config/theme_crosswalk.yml"
    hierarchy = gcp._hierarchy(crosswalk)
    for theme_id in ("theme:hbm_packaging", "theme:gpu_merchant_accelerators",
                     "theme:liquid_cooling_thermal"):
        expected = me._activity_target_definition(REPO, theme_id)["definition_sha256"]
        assert gcp._entry_scope_version(hierarchy["micros"][theme_id]) == expected


# --- 14 ----------------------------------------------------------------------
def test_retired_node_is_not_qualified(tmp_path):
    fixture = _build(tmp_path)
    report, manifest, _ = _run(fixture)
    statuses = manifest["core_markets"]["us"]["securities_by_identity_status"]
    assert statuses["QUALIFIED"] == 6
    assert "SEC:US-XNAS-RTD|ISS:US-XNAS-RTD|RESOLVED|XNAS|RTD|ELIGIBLE|NOT_IN_GRAPH" \
        in manifest["core_markets"]["us"]["securities"]["rows"]
    assert manifest["core_markets"]["us"]["securities_by_identity_status"].get(
        "NOT_IN_GRAPH") == 1
    assert report["identity_coverage"]["us"]["qualified_securities"] == 6
    alias = report["alias_groups"]
    assert alias == [{"security_id": "SEC:US-XNAS-MU",
                      "node_ids": ["co:us:MU", "co:us:MU2"]}]
    ledger = report["graph_side_ledger"]["us"]
    assert ledger["RESOLVED/retired"] == 1 and ledger["GRAPH_ONLY/canonical"] == 1
    assert ledger["NOT_IN_MASTER/canonical"] == 1
