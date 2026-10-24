"""M3 descriptive renderer: "if X, the filing says" + correction demo.

Pins the frozen REL-M3-DESCRIBE-BUILD behaviour: the sha-pinned premise table
and its drift refusal, every sentence coming from a frozen template, the
no-inference rule, condition quotes re-derived from pinned bytes (verified,
outside-span refused, tampered excerpt suppressed), conflict rendering of
both values, the undisclosed sentence, the always-present rights line, the
data//site/ out-dir refusal, byte-identical reruns, the real committed M1
SWKS->AAPL render, the point-in-time correction demo (an April belief is not
rewritten by a later filing) and the never-synthesized restatement census.

No network anywhere; the only subprocess the CLI may spawn is the repo's own
producer script.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.company_intelligence.relationships import describe  # noqa: E402

PREMISES_PATH = REPO_ROOT / describe.PREMISES_RELPATH
SOURCES_DIR = REPO_ROOT / "research/theme_graph/gmi_relationships_20261021/sources"
ACC_24 = "0000004127-24-000131"
ACC_25 = "0000004127-25-000085"
ACC_26 = "0000004127-26-000003"
SWKS = "ISS:US-XNAS-SWKS"
AAPL = "ISS:US-XNAS-AAPL"
ALPHA = "ISS:TEST-ALPHA"
BETA = "ISS:TEST-BETA"
REL_KEY = "rel:2dddc958720e18bf0275"
T1 = "2025-06-30T00:00:00Z"
T2 = "2025-12-31T00:00:00Z"
T3 = "2026-10-21T00:00:00Z"
COND_TEXT = (
    "If the agreement is terminated by the customer, the supplier may sell "
    "its components to other customers."
)
SYN_ACC = "0000000000-99-000001"

pytestmark = pytest.mark.data_gate


# --- helpers -----------------------------------------------------------------


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["TZ"] = "UTC"
    return subprocess.run(
        [sys.executable, "scripts/relationship_m3_describe.py", *args],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def _real_excerpt(acc: str) -> dict:
    return json.loads((SOURCES_DIR / f"{acc}.json").read_text("utf-8"))


def _synthetic_excerpt(
    prefix: bytes = b"X" * 10,
    middle: bytes = COND_TEXT.encode("utf-8"),
    suffix: bytes = b"Y" * 5,
    span_start: int = 1000,
) -> tuple:
    """A valid excerpt whose span carries `middle` at a known inner offset."""
    from engine.company_intelligence.relationships import normalize_span

    raw = prefix + middle + suffix
    inner_start = span_start + len(prefix)
    inner_end = inner_start + len(middle)
    normalized = normalize_span(raw)
    return {
        "accession": SYN_ACC,
        "form": "10-K",
        "url": "https://www.sec.gov/example/" + SYN_ACC,
        "span": {
            "byte_start": span_start,
            "byte_end": span_start + len(raw),
            "raw": raw.decode("utf-8"),
            "raw_sha256": _sha_bytes(raw),
            "normalized": normalized,
            "normalized_sha256": _sha_bytes(normalized.encode("utf-8")),
        },
        "xbrl_contexts": [],
    }, inner_start, inner_end


def _condition(excerpt: dict, inner_start: int, inner_end: int,
               kind: str = "termination_right", text: str = COND_TEXT) -> dict:
    return {
        "kind": kind,
        "text": text,
        "byte_start": inner_start,
        "byte_end": inner_end,
        "span_sha256": _sha_bytes(text.encode("utf-8")),
        "accession": SYN_ACC,
    }


def _revision(
    label: str,
    value: float,
    seq: int,
    revision_kind: str,
    accession: str,
    known_at: str,
    kind: str = "seller_revenue_share",
    party: str = SWKS,
    start: str = "2022-10-01",
    end: str = "2023-09-29",
) -> dict:
    return {
        "revision_id": f"rev:{label}:{seq}",
        "relationship_key": "rel:test",
        "kind": kind,
        "value": value,
        "value_high": None,
        "unit": "ratio",
        "precision": "exact",
        "period": {"start": start, "end": end, "label": label},
        "numerator_scope": "NUM",
        "denominator_scope": "DEN",
        "asserting_party": party,
        "revision_seq": seq,
        "revision_kind": revision_kind,
        "supersedes": f"rev:{label}:{seq - 1}" if seq > 1 else None,
        "known_at": known_at,
        "source_ref": {
            "accession": accession,
            "form": "10-K",
            "byte_start": 1,
            "byte_end": 2,
            "span_sha256": "s" * 64,
        },
    }


def _edge(**overrides) -> dict:
    edge = {
        "relationship_key": "rel:test",
        "species": "supplier_customer",
        "direction": {
            "from_issuer_id": SWKS,
            "to_issuer_id": AAPL,
            "from_role": "supplier",
            "to_role": "customer",
        },
        "from": {"issuer_id": SWKS, "security_ids": ["SEC:US-XNAS-SWKS"]},
        "to": {"issuer_id": AAPL, "security_ids": ["SEC:US-XNAS-AAPL"]},
        "magnitude_state": "disclosed",
        "freshness_state": "fresh",
        "asserted_period": {"start": "2022-10-01", "end": "2025-10-03"},
        "current_magnitudes": [],
        "magnitude_history": [],
        "conflicts": [],
        "conditions": [],
        "source_refs": [],
        "correction_lineage": [],
        "rights": {
            "public_display": "unknown",
            "excerpt_display": "unknown",
            "magnitude_display": "unknown",
        },
    }
    edge.update(overrides)
    return edge


def _render(edge: dict, excerpts: dict, sec_names: dict = None):
    premises = describe.load_premises_file(PREMISES_PATH)
    entries, counters = describe.describe_edges(
        [edge], excerpts, premises, sec_names or {}
    )
    return entries[0], counters


def _classes(entry: dict, klass: str) -> list:
    return [line for line in entry["lines"] if line["display_class"] == klass]


def _tamper_real_excerpt(tmp_path: Path, acc: str = ACC_25) -> Path:
    """A tmp sources dir whose one excerpt fails offline verification."""
    doc = _real_excerpt(acc)
    doc["span"]["raw"] = doc["span"]["raw"] + " tampered tail"
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / f"{acc}.json").write_bytes(
        json.dumps(doc, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8")
        + b"\n"
    )
    return sources


# --- premises pin ----------------------------------------------------------------


def test_premises_bytes_pinned_and_drift_refused(tmp_path):
    data = PREMISES_PATH.read_bytes()
    assert describe.PREMISES_SHA256 == (
        "0394589fe14e92a7f9c3963a9b8adb8fa6477cc4fc66bd1a7c5f40ecadba6786"
    )
    assert _sha_bytes(data) == describe.PREMISES_SHA256
    premises = describe.load_premises(data)
    assert premises["schema"] == "orch_rel.m3_describe_premises/v1"
    assert set(premises["premises"]) >= {
        "termination_right", "pricing", "volume_commitment", "exclusivity",
        "concentration_risk", "contractual_term", "other",
    }
    with pytest.raises(describe.PremisesDrift):
        describe.load_premises(data + b" ")
    with pytest.raises(describe.PremisesDrift):
        describe.load_premises(b"{}")
    # The CLI refuses missing or drifting premise bytes with rc 2
    # PREMISES_DRIFT (a missing premise file is unreadable bytes).
    proc = _run_cli(
        "describe", "--out", str(tmp_path / "never"),
        "--premises", str(tmp_path / "nonexistent_premises.json"),
    )
    assert proc.returncode == 2
    assert "PREMISES_DRIFT" in proc.stdout
    tampered = tmp_path / "tampered_premises.json"
    tampered.write_bytes(data.replace(b"the filing says", b"the paper says"))
    proc = _run_cli(
        "describe", "--out", str(tmp_path / "never2"), "--premises", str(tampered)
    )
    assert proc.returncode == 2
    assert "PREMISES_DRIFT" in proc.stdout
    assert not (tmp_path / "never").exists()
    assert not (tmp_path / "never2").exists()


# --- template-only prose -----------------------------------------------------------


def test_every_sentence_comes_from_a_template():
    premises = describe.load_premises_file(PREMISES_PATH)
    excerpt = _real_excerpt(ACC_25)
    synth, inner_start, inner_end = _synthetic_excerpt()
    excerpts = {
        **describe.load_excerpt_map(SOURCES_DIR, {ACC_25}, base=REPO_ROOT)[0],
        (SYN_ACC, synth["span"]["raw_sha256"]): synth,
        SYN_ACC: synth,
    }
    edge = _edge(
        current_magnitudes=[
            {
                "kind": "seller_revenue_share",
                "value": 0.67,
                "value_high": None,
                "unit": "ratio",
                "precision": "exact",
                "period": {"start": "2024-09-28", "end": "2025-10-03",
                           "label": "FY2025"},
                "numerator_scope": "NUM",
                "denominator_scope": "DEN",
                "asserting_party": SWKS,
                "source_ref": {
                    "accession": ACC_25,
                    "form": "10-K",
                    "byte_start": 1,
                    "byte_end": 2,
                    "span_sha256": "s" * 64,
                },
            }
        ],
        source_refs=[
            {
                "observation_id": "obs:x",
                "accession": ACC_25,
                "form": "10-K",
                "url": excerpt["url"],
                "byte_start": excerpt["span"]["byte_start"],
                "byte_end": excerpt["span"]["byte_end"],
                "span_sha256": excerpt["span"]["raw_sha256"],
            }
        ],
        conditions=[_condition(synth, inner_start, inner_end)],
        magnitude_history=[
            _revision("FY2023", 0.66, 1, "new_period", ACC_24,
                      "2024-11-15T21:37:43Z"),
            _revision("FY2023", 0.66, 2, "reassertion", ACC_25,
                      "2025-11-07T21:08:12Z"),
        ],
        correction_lineage=[
            {
                "accession": ACC_26,
                "amends_accession": ACC_25,
                "assessment": "not_restated",
                "reason": "part_iii_only_amendment",
            }
        ],
    )
    entry, counters = _render(edge, excerpts)

    # With no resolver and no name_as_filed, names are the ticker suffixes.
    mag = premises["magnitude"]["seller_revenue_share"]
    lead_en = premises["lead_in"]["en"]
    lead_zh = premises["lead_in"]["zh"]
    expected = [
        (
            "derived_fact",
            mag["en"].format(party="SWKS", numerator_scope="NUM",
                             denominator_scope="DEN", pct="67",
                             period="FY2025"),
            mag["zh"].format(party="SWKS", period="FY2025",
                             numerator_scope="NUM", denominator_scope="DEN",
                             pct="67"),
            {"party": "SWKS", "numerator_scope": "NUM",
             "denominator_scope": "DEN", "pct": "67", "period": "FY2025"},
        ),
        (
            "verbatim_excerpt",
            f"{lead_en} {excerpt['span']['normalized']}",
            f"{lead_zh}{excerpt['span']['normalized']}",
            {},
        ),
        (
            "verbatim_excerpt",
            (
                premises["premises"]["termination_right"]["en"].format(
                    counterparty="AAPL"
                )
                + f", {lead_en} {COND_TEXT}"
            ),
            (
                premises["premises"]["termination_right"]["zh"].format(
                    counterparty="AAPL"
                )
                + f"，{lead_zh}{COND_TEXT}"
            ),
            {"counterparty": "AAPL"},
        ),
        (
            "first_published",
            premises["corrections"]["first_published"]["en"].format(
                party="SWKS", value="66%", period="FY2023", form="10-K",
                accession=ACC_24, date="2024-11-15",
            ),
            premises["corrections"]["first_published"]["zh"].format(
                party="SWKS", value="66%", period="FY2023", form="10-K",
                accession=ACC_24, date="2024-11-15",
            ),
            {"party": "SWKS", "value": "66%", "period": "FY2023",
             "form": "10-K", "accession": ACC_24, "date": "2024-11-15"},
        ),
        (
            "reassertion",
            premises["corrections"]["reassertion"]["en"].format(
                form="10-K", accession=ACC_25, date="2025-11-07", value="66%",
            ),
            premises["corrections"]["reassertion"]["zh"].format(
                form="10-K", accession=ACC_25, date="2025-11-07", value="66%",
            ),
            {"form": "10-K", "accession": ACC_25, "date": "2025-11-07",
             "value": "66%"},
        ),
        (
            "amendment_not_restated",
            premises["corrections"]["amendment_not_restated"]["en"].format(
                accession=ACC_26, amends_accession=ACC_25,
                reason="part_iii_only_amendment",
            ),
            premises["corrections"]["amendment_not_restated"]["zh"].format(
                accession=ACC_26, amends_accession=ACC_25,
                reason="part_iii_only_amendment",
            ),
            {"accession": ACC_26, "amends_accession": ACC_25,
             "reason": "part_iii_only_amendment"},
        ),
        (
            "footer",
            premises["footer"]["en"],
            premises["footer"]["zh"],
            {},
        ),
        (
            "rights",
            describe.RIGHTS_LINE_EN.format(state="unknown"),
            describe.RIGHTS_LINE_ZH.format(state="unknown"),
            {"state": "unknown"},
        ),
    ]
    assert len(entry["lines"]) == len(expected)
    for line, (klass, exp_en, exp_zh, slots) in zip(entry["lines"], expected):
        assert line["display_class"] == klass, (klass, line["en"])
        assert line["en"] == exp_en, (klass, line["en"], exp_en)
        assert line["zh"] == exp_zh, (klass, line["zh"], exp_zh)
        # Blanked form: with every slot value removed, the line collapses to
        # the template rendered with empty slots — nothing else was added.
        blanked_en = line["en"]
        blanked_zh = line["zh"]
        template_en = exp_en
        template_zh = exp_zh
        for value in sorted(slots.values(), key=len, reverse=True):
            if not value:
                continue
            blanked_en = blanked_en.replace(value, "")
            blanked_zh = blanked_zh.replace(value, "")
            template_en = template_en.replace(value, "")
            template_zh = template_zh.replace(value, "")
        assert blanked_en == template_en, (klass, blanked_en, template_en)
        assert blanked_zh == template_zh, (klass, blanked_zh, template_zh)
    assert counters["lines_by_class"] == {
        "derived_fact": 1,
        "verbatim_excerpt": 2,
        "first_published": 1,
        "reassertion": 1,
        "amendment_not_restated": 1,
        "footer": 1,
        "rights": 1,
    }
    assert counters["reassertions_found"] == 1
    assert counters["restatements_found"] == 0
    assert counters["quote_verified"] == 2
    assert counters["quote_unverified_by_kind"] == {}
    assert counters["conditions_by_kind"] == {"termination_right": 1}


# --- no inference --------------------------------------------------------------------


def test_no_inference_words(tmp_path):
    banned_en = re.compile(r"\b(will|likely|expect)\b", re.IGNORECASE)
    banned_substrings = ("risk score", "probability", "预计", "可能会")

    def _check(text: str) -> None:
        assert not banned_en.search(text), banned_en.search(text).group()
        for substring in banned_substrings:
            assert substring not in text, substring

    # Synthetic render, including a verbatim condition quote.
    synth, inner_start, inner_end = _synthetic_excerpt()
    excerpts = {(SYN_ACC, synth["span"]["raw_sha256"]): synth, SYN_ACC: synth}
    edge = _edge(
        conditions=[_condition(synth, inner_start, inner_end)],
    )
    entry, _counters = _render(edge, excerpts)
    _check(describe.report_text([entry]))
    # The real committed M1 render (json + txt + stdout).
    out = tmp_path / "no_inf"
    proc = _run_cli("describe", "--out", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    _check(proc.stdout)
    _check((out / "describe_report.json").read_text("utf-8"))


# --- condition quotes ----------------------------------------------------------------


def test_condition_quote_verified_from_pinned_bytes(tmp_path):
    synth, inner_start, inner_end = _synthetic_excerpt()
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / f"{SYN_ACC}.json").write_bytes(
        json.dumps(synth, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8")
        + b"\n"
    )
    excerpts, inputs = describe.load_excerpt_map(
        sources, {SYN_ACC}, base=tmp_path
    )
    assert inputs[f"sources/{SYN_ACC}.json"] == _sha_bytes(
        (sources / f"{SYN_ACC}.json").read_bytes()
    )
    edge = _edge(conditions=[_condition(synth, inner_start, inner_end)])
    entry, counters = _render(edge, excerpts)
    lines = _classes(entry, "verbatim_excerpt")
    assert len(lines) == 1
    citation = lines[0]["citation"]
    assert citation["accession"] == SYN_ACC
    assert citation["byte_start"] == inner_start
    assert citation["byte_end"] == inner_end
    assert citation["span_sha256"] == _sha_bytes(COND_TEXT.encode("utf-8"))
    assert COND_TEXT in lines[0]["en"]
    assert counters["quote_verified"] == 1
    assert counters["quote_unverified_by_kind"] == {}
    assert counters["conditions_by_kind"] == {"termination_right": 1}


def test_condition_quote_outside_span_refused_not_paraphrased(tmp_path):
    synth, inner_start, inner_end = _synthetic_excerpt()
    excerpts = {(SYN_ACC, synth["span"]["raw_sha256"]): synth, SYN_ACC: synth}
    span = synth["span"]
    # (a) byte range beyond the span end — refused, not paraphrased.
    outside = _condition(
        synth, inner_start, inner_end,
        kind="pricing",
        text=COND_TEXT,
    )
    outside = dict(outside, byte_end=span["byte_end"] + 5)
    # (b) a range inside the span whose pinned slice hash does not match.
    wrong_hash = _condition(
        synth, inner_start, inner_end, kind="exclusivity", text=COND_TEXT
    )
    wrong_hash = dict(wrong_hash, span_sha256="0" * 64)
    edge = _edge(conditions=[outside, wrong_hash])
    entry, counters = _render(edge, excerpts)
    assert _classes(entry, "verbatim_excerpt") == []
    assert counters["quote_verified"] == 0
    assert counters["quote_unverified_by_kind"] == {"pricing": 1,
                                                    "exclusivity": 1}
    assert counters["conditions_by_kind"] == {"pricing": 1, "exclusivity": 1}
    # The unverified text is never printed in any form.
    text = describe.report_text([entry])
    assert COND_TEXT not in text


def test_tampered_excerpt_suppresses_quote(tmp_path):
    sources = _tamper_real_excerpt(tmp_path)
    excerpts, _inputs = describe.load_excerpt_map(sources, {ACC_25}, base=tmp_path)
    real = _real_excerpt(ACC_25)
    edge = _edge(
        source_refs=[
            {
                "observation_id": "obs:x",
                "accession": ACC_25,
                "form": "10-K",
                "url": real["url"],
                "byte_start": real["span"]["byte_start"],
                "byte_end": real["span"]["byte_end"],
                "span_sha256": real["span"]["raw_sha256"],
            }
        ],
    )
    entry, counters = _render(edge, excerpts)
    assert _classes(entry, "verbatim_excerpt") == []
    assert counters["quote_verified"] == 0
    assert counters["quote_unverified_by_kind"] == {"source_ref": 1}


# --- magnitudes, conflicts, rights -----------------------------------------------------


def test_conflict_renders_both_values():
    premises = describe.load_premises_file(PREMISES_PATH)
    rev_alpha = _revision("FY2024", 0.6, 1, "new_period", ACC_24,
                          "2024-11-15T21:37:43Z", party=ALPHA)
    rev_beta = _revision("FY2024", 0.7, 1, "new_period", ACC_25,
                         "2025-11-07T21:08:12Z", party=BETA)
    edge = _edge(
        magnitude_state="conflicted",
        magnitude_history=[rev_alpha, rev_beta],
        current_magnitudes=[dict(rev_alpha, value=None, asserting_party=ALPHA)],
        conflicts=[
            {
                "kind": "seller_revenue_share",
                "period": dict(rev_alpha["period"]),
                "values": [
                    {"asserting_party": ALPHA, "value": 0.6,
                     "revision_id": rev_alpha["revision_id"]},
                    {"asserting_party": BETA, "value": 0.7,
                     "revision_id": rev_beta["revision_id"]},
                ],
            }
        ],
    )
    entry, counters = _render(edge, {})
    conflicts = _classes(entry, "conflict")
    assert len(conflicts) == 1
    template = premises["corrections"]["conflict"]
    assert conflicts[0]["en"] == template["en"].format(
        period="FY2024", party_a="ALPHA", value_a="60%",
        party_b="BETA", value_b="70%",
    )
    assert conflicts[0]["zh"] == template["zh"].format(
        period="FY2024", party_a="ALPHA", value_a="60%",
        party_b="BETA", value_b="70%",
    )
    # No value is chosen for the conflicted kind: no derived fact at all.
    assert _classes(entry, "derived_fact") == []
    assert counters["restatements_found"] == 0
    assert counters["reassertions_found"] == 0


def test_undisclosed_magnitude_sentence():
    premises = describe.load_premises_file(PREMISES_PATH)
    edge = _edge(magnitude_state="undisclosed")
    entry, _counters = _render(edge, {})
    facts = _classes(entry, "derived_fact")
    assert len(facts) == 1
    template = premises["magnitude"]["undisclosed"]
    assert facts[0]["en"] == template["en"].format(party="SWKS")
    assert facts[0]["zh"] == template["zh"].format(party="SWKS")


def test_rights_line_always_present():
    premises = describe.load_premises_file(PREMISES_PATH)
    for state in ("unknown", "derived_facts_permitted"):
        entry, _counters = _render(
            _edge(rights={"public_display": state}), {}
        )
        rights = _classes(entry, "rights")
        assert len(rights) == 1
        assert rights[0]["en"] == describe.RIGHTS_LINE_EN.format(state=state)
        assert rights[0]["zh"] == describe.RIGHTS_LINE_ZH.format(state=state)
        # The footer rides along on every entry.
        assert len(_classes(entry, "footer")) == 1


# --- CLI refusals and determinism --------------------------------------------------------


def test_out_dir_under_data_refused():
    for guard in ("data", "site"):
        target = f"{guard}/m3_describe_should_not_exist"
        proc = _run_cli("describe", "--out", target)
        assert proc.returncode == 2, proc.stdout + proc.stderr
        assert "OUT_REFUSED" in proc.stdout
        assert not (REPO_ROOT / target).exists()
    demo = _run_cli(
        "correction-demo", "--out", "data/m3_demo_should_not_exist",
        "--relationship-key", REL_KEY, "--as-of", T1,
    )
    assert demo.returncode == 2
    assert "OUT_REFUSED" in demo.stdout
    assert not (REPO_ROOT / "data/m3_demo_should_not_exist").exists()


@pytest.mark.needs_full_checkout("data")
def test_describe_rerun_byte_identical(tmp_path):
    out1, out2 = tmp_path / "d1", tmp_path / "d2"
    proc1 = _run_cli("describe", "--out", str(out1))
    proc2 = _run_cli("describe", "--out", str(out2))
    assert proc1.returncode == 0, proc1.stdout + proc1.stderr
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    assert proc1.stdout == proc2.stdout
    for name in ("describe_report.json", "describe_report.txt"):
        assert (out1 / name).read_bytes() == (out2 / name).read_bytes(), name


# --- the real committed M1 render -----------------------------------------------------------


@pytest.mark.needs_full_checkout("data")
def test_real_m1_describe(tmp_path):
    out = tmp_path / "d"
    proc = _run_cli("describe", "--out", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads((out / "describe_report.json").read_text("utf-8"))
    assert report["schema"] == describe.REPORT_SCHEMA
    assert report["as_of"] == T3
    assert report["premises_sha256"] == describe.PREMISES_SHA256
    assert report["counters"]["edges"] == 1
    entry = report["entries"][0]
    assert entry["relationship_key"] == REL_KEY
    assert entry["from"] == {"issuer_id": SWKS, "name": "SKYWORKS SOLUTIONS, INC."}
    assert entry["to"] == {"issuer_id": AAPL, "name": "Apple Inc."}
    assert entry["from_role"] == "supplier" and entry["to_role"] == "customer"
    assert entry["rights"]["public_display"] == "unknown"

    # One derived fact per committed current_magnitudes entry (the committed
    # artifact carries exactly one: FY2025 at 67%).
    facts = _classes(entry, "derived_fact")
    assert len(facts) == 1
    assert facts[0]["en"] == (
        "SKYWORKS SOLUTIONS, INC. disclosed that net revenue from Apple in "
        "aggregate, through distributors, contract manufacturers and direct "
        "sales was 67% of Skyworks consolidated net revenue for FY2025."
    )
    assert facts[0]["citation"]["accession"] == ACC_25

    # Both committed source_refs render as verified verbatim quotes.
    verbatims = _classes(entry, "verbatim_excerpt")
    assert len(verbatims) == 2
    assert {line["citation"]["accession"] for line in verbatims} == {ACC_24, ACC_25}
    for line in verbatims:
        assert line["en"].startswith("the filing says: ")
        assert line["citation"]["url"].startswith("https://www.sec.gov/")

    # The full FY2022..FY2025 history rides the correction chains: four
    # first_published lines, two reassertions, no restatement.
    firsts = _classes(entry, "first_published")
    assert [line["en"].split("for ")[1].split(" in ")[0] for line in firsts] == [
        "FY2022", "FY2023", "FY2024", "FY2025",
    ]
    assert [line["citation"]["accession"] for line in firsts] == [
        ACC_24, ACC_24, ACC_24, ACC_25,
    ]
    reassertions = _classes(entry, "reassertion")
    assert len(reassertions) == 2
    for line in reassertions:
        assert line["citation"]["accession"] == ACC_25
    assert _classes(entry, "restatement") == []
    amendment = _classes(entry, "amendment_not_restated")
    assert len(amendment) == 1
    assert amendment[0]["en"] == (
        f"{ACC_26} amends {ACC_25}; it does not restate this figure "
        "(part_iii_only_amendment)."
    )
    assert len(_classes(entry, "footer")) == 1
    assert len(_classes(entry, "rights")) == 1

    counters = report["counters"]
    assert counters["quote_verified"] == 2
    assert counters["quote_unverified_by_kind"] == {}
    assert counters["conditions_by_kind"] == {}
    assert counters["restatements_found"] == 0
    assert counters["reassertions_found"] == 2
    assert "research/theme_graph/gmi_relationships_20261021/"
    "m3/describe_premises_v1.json" in report["inputs"]


# --- the point-in-time correction demo --------------------------------------------------------


@pytest.mark.needs_full_checkout("data")
def test_correction_demo_pit(tmp_path):
    out = tmp_path / "demo"
    proc = _run_cli(
        "correction-demo",
        "--out", str(out),
        "--relationship-key", REL_KEY,
        "--as-of", T2, "--as-of", T1, "--as-of", T3,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    demo = json.loads((out / "correction_demo.json").read_text("utf-8"))
    assert demo["schema"] == describe.DEMO_SCHEMA
    assert demo["as_ofs"] == [T1, T2, T3]  # sorted, not invocation order
    assert demo["reproducible"] is True
    assert demo["relationship_key"] == REL_KEY

    by_as_of = {view["as_of"]: view for view in demo["views"]}

    # T1: FY2022/FY2023/FY2024 first published from 24-000131; NO 25-000085
    # line anywhere; no lineage visible yet.
    t1 = by_as_of[T1]
    assert len(t1["new_revisions"]) == 3
    assert t1["correction_lineage"] == []
    for line in t1["entry"]["lines"]:
        citation = line["citation"] or {}
        assert citation.get("accession") != ACC_25, line
    classes_t1 = [line["display_class"] for line in t1["entry"]["lines"]]
    assert "reassertion" not in classes_t1
    assert "amendment_not_restated" not in classes_t1
    assert len([c for c in classes_t1 if c == "first_published"]) == 3

    # T2: FY2023 and FY2024 reasserted by 25-000085; FY2025 first published;
    # still no lineage.
    t2 = by_as_of[T2]
    classes_t2 = [line["display_class"] for line in t2["entry"]["lines"]]
    assert classes_t2.count("first_published") == 4
    assert classes_t2.count("reassertion") == 2
    reasserted = [
        line for line in t2["entry"]["lines"]
        if line["display_class"] == "reassertion"
    ]
    assert {line["citation"]["accession"] for line in reasserted} == {ACC_25}
    fy2025_first = [
        line for line in t2["entry"]["lines"]
        if line["display_class"] == "first_published"
        and "FY2025" in line["en"]
    ]
    assert len(fy2025_first) == 1
    assert fy2025_first[0]["citation"]["accession"] == ACC_25
    assert t2["correction_lineage"] == []
    assert len(t2["new_revisions"]) == 3

    # T3: additionally the amendment_not_restated line for 26-000003; no new
    # revisions (all six were already visible at T2).
    t3 = by_as_of[T3]
    classes_t3 = [line["display_class"] for line in t3["entry"]["lines"]]
    assert "amendment_not_restated" in classes_t3
    assert t3["new_revisions"] == []
    assert len(t3["correction_lineage"]) == 1

    # Every first appearance carries extraction latency, labelled backfill:
    # the rows were ingested 2026-10-21, years after publication.
    for view in (t1, t2):
        for row in view["new_revisions"]:
            assert row["backfill"] is True
            assert row["correction_latency_hours"] > 24 * 30
    assert "backfill latency (not natural-operations latency)" in proc.stdout

    # The current package has no restatement revision anywhere — ABSENT is
    # printed, never synthesized.
    assert demo["current_package_restatements"] == []
    assert "ABSENT" in proc.stdout


@pytest.mark.needs_full_checkout("data")
def test_restatement_absent_is_printed_not_synthesized(tmp_path):
    # The committed package really carries no restatement revision.
    package = json.loads(
        (REPO_ROOT / "data/company_intelligence/relationships/"
         "observation_package.v2.json").read_text("utf-8")
    )
    kinds = {row["revision_kind"] for row in package["magnitude_revisions"]}
    assert "restatement" not in kinds

    out = tmp_path / "d"
    proc = _run_cli("describe", "--out", str(out))
    assert proc.returncode == 0
    report = json.loads((out / "describe_report.json").read_text("utf-8"))
    assert report["counters"]["restatements_found"] == 0
    assert "restatement" not in proc.stdout.replace("restatements_found", "")

    demo_out = tmp_path / "demo"
    demo = _run_cli(
        "correction-demo", "--out", str(demo_out),
        "--relationship-key", REL_KEY, "--as-of", T3,
    )
    assert demo.returncode == 0
    assert "ABSENT" in demo.stdout
    demo_json = json.loads((demo_out / "correction_demo.json").read_text("utf-8"))
    assert demo_json["current_package_restatements"] == []


# --- purity ---------------------------------------------------------------------------------


def test_no_network_import():
    for rel in (
        "engine/company_intelligence/relationships/describe.py",
        "scripts/relationship_m3_describe.py",
    ):
        source = (REPO_ROOT / rel).read_text("utf-8")
        for banned in ("urllib", "urlopen", "requests", "http.client", "socket"):
            assert banned not in source, (rel, banned)
    engine_source = (
        REPO_ROOT / "engine/company_intelligence/relationships/describe.py"
    ).read_text("utf-8")
    for banned in ("datetime.now", "utcnow", "time.time", "date.today"):
        assert banned not in engine_source, banned
