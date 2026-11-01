"""G0-S lane: the three E0 reference gaps, requalification receipts and the seal.

Lane G0-S (SPEC_G0 Rev 2 §3/§3.1): the reference pack is requalified to
capital-structure-reference-qualification/1.1.0 with two of the three E0 gaps
closed by deterministic selection from the served universe (foreign F-3
witness, held-out pattern witness) and the WHK replacement gap left open with
its failure list. The held-out expected answer is sealed OUT of the repository:
the pack's held-out gold entry carries the identity, the source packet and the
path id, and no expected number.
"""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from engine.capital_structure import reference_qualification as rq
from engine.capital_structure.rule_applicability import load_rule_applicability_pack

ROOT = Path(__file__).resolve().parents[1]
PACK_PATH = ROOT / rq.REFERENCE_PACK_RELPATH
G0_FIXTURE_DIR = ROOT / "tests/fixtures/capital_structure/reference/g0"
SELECTION_RECORD = ROOT / "research/capital_structure/e2e_20261013/reference/G0_SELECTION.md"
FETCH_DATE = "2026-10-19"
G0_GAPS = ("whk_replacement_issuer", "foreign_issuer_f3_witness", "held_out_pattern_witness")


@pytest.fixture(scope="module")
def raw() -> dict:
    return json.loads(PACK_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pack() -> rq.ReferencePack:
    return rq.load_reference_pack(PACK_PATH)


def parse_g0_fixture(path: Path) -> tuple[dict, list[dict]]:
    """Header keys plus spans (label, chars, start, end, sha256, text) of a g0 excerpt."""
    hdr: dict[str, str] = {}
    spans: list[dict] = []
    in_spans = False
    cur: dict | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue
        if line.strip() == "spans:":
            in_spans = True
            continue
        if not in_spans:
            m = re.match(r"^([a-z0-9_]+): (.*)$", line)
            if m:
                hdr[m.group(1)] = m.group(2)
            continue
        if line.startswith("span: "):
            _, label, chars, start, end, sha = line.split()
            cur = {"label": label, "chars": int(chars), "start": int(start), "end": int(end),
                   "sha256": sha, "text": ""}
            spans.append(cur)
        elif cur is not None and cur["text"] == "" and line.strip():
            cur["text"] = line
    return hdr, spans


def test_g0_pack_is_1_1_0_and_loads(pack):
    assert pack.version == rq.REFERENCE_PACK_VERSION == "capital-structure-reference-qualification/1.1.0"
    assert pack.qualified_on == FETCH_DATE
    assert pack.task == "G0-S"
    assert set(pack.acceptance_rows) >= {"A07", "A13", "A33", "A42"}


def test_g0_new_identities_resolve(pack):
    for archetype, cik, ticker in (("EDRY", "0001731388", "EDRY"), ("RPID", "0001380106", "RPID")):
        identity = rq.identity_for(pack, archetype)
        assert identity.cik == cik
        assert identity.issuer_id == f"sec:cik:{cik}"
        assert identity.ticker == ticker
        assert identity.ticker_as_of == FETCH_DATE
        assert set(identity.source_ids) == {"sec_company_tickers", f"sec_submissions_cik_{cik}"}
        for sid in identity.source_ids:
            source = pack.source(sid)
            assert source.source_class == "identity_registry"
            assert source.qualification == "qualified"


def test_g0_gold_fixtures_verify(pack):
    assert rq.verify_gold_fixtures(pack, ROOT) == {}
    for gold in pack.gold_cases:
        if gold.gold_id.startswith("gold:reference_g0:"):
            assert gold.allowed_source == "sec_edgar_public_filing"
            assert gold.provenance == "real_edgar_g0"
            assert "test_capital_structure_g0_reference.py" in gold.consumers


def test_g0_fixture_spans_respect_the_rights_cap():
    files = sorted(G0_FIXTURE_DIR.glob("*.txt"))
    assert files, "the g0 reference fixture directory must not be empty"
    for path in files:
        hdr, spans = parse_g0_fixture(path)
        assert re.fullmatch(r"[0-9a-f]{64}", hdr["full_document_sha256"]), path
        assert re.fullmatch(r"\d{10}-\d{2}-\d{6}", hdr["accession"]), path
        assert hdr["http_status"] == "200" and hdr["retrieved_at"].startswith("20"), path
        for span in spans:
            assert len(span["text"]) == span["chars"] <= rq.EXCERPT_CAP_CHARS, (path, span["label"])
            assert span["sha256"] == hashlib.sha256(span["text"].encode("utf-8")).hexdigest(), (path, span["label"])


def test_g0_each_e0_gap_is_closed_or_carries_its_failures(raw, pack):
    closed = {g["gap_id"]: g for g in raw["closed_gaps"]}
    open_gaps = {g["gap_id"]: g for g in raw["gaps"]}
    for gap_id in G0_GAPS:
        assert (gap_id in closed) != (gap_id in open_gaps), gap_id
    for gap_id in ("foreign_issuer_f3_witness", "held_out_pattern_witness"):
        entry = closed[gap_id]
        assert entry["closed_on"] == FETCH_DATE
        assert entry["selection_record"] == "research/capital_structure/e2e_20261013/reference/G0_SELECTION.md"
        identity = rq.identity_for(pack, entry["closed_by"])  # closed_by must resolve
        assert identity.cik and identity.issuer_id == f"sec:cik:{identity.cik}"
    whk = open_gaps["whk_replacement_issuer"]
    assert whk["note"].strip()
    assert "60 candidates tested" in whk["note"]
    assert "c4_operand_spans_exercisable_shares_terms=1" in whk["note"]


def test_g0_whk_is_a_historical_witness_with_replacement(raw, pack):
    whk = rq.identity_for(pack, "WHK")
    assert whk.case_supply == "unsupplied"
    assert whk.replacement_owed is True
    # the whk_replacement_issuer gap stayed open (budget stop, failure list in
    # the pack), so no replacement issuer is named and none is guessed
    assert whk.replacement is None
    assert any(g["gap_id"] == "whk_replacement_issuer" for g in raw["gaps"])


def test_g0_held_out_entry_carries_no_expected_number(raw):
    entry = next(g for g in raw["gold_cases"] if g["gold_id"] == "gold:reference_g0:held_out_ib6_headroom")
    assert entry["sealed"] is True

    def walk(node, path):
        if isinstance(node, dict):
            for key, val in node.items():
                assert key not in ("expected", "value", "amount"), (path, key)
                walk(val, f"{path}.{key}")
        elif isinstance(node, list):
            for i, val in enumerate(node):
                walk(val, f"{path}[{i}]")
        elif isinstance(node, str) and path.startswith("held_out.expectations"):
            assert not re.search(r"\d{4,}", node), (path, node)

    walk(entry, "held_out")
    # every numeric claim is bounded to at most three consecutive digits
    for expectation in entry["expectations"]:
        assert not re.search(r"\d{4,}", expectation["claim"])
        assert expectation["test"].startswith("tests/test_capital_structure_g0_reference.py::")


def test_g0_foreign_f3_gold_binds_exact_spans(raw):
    entry = next(g for g in raw["gold_cases"] if g["gold_id"] == "gold:reference_g0:foreign_f3_ib5_baby_shelf")
    assert entry["cik"] == "0001731388" and entry["form"] == "F-3" and entry["filed"] == "2026-08-27"
    assert entry["accession"] == "0000919574-26-005806"
    hdr, spans = parse_g0_fixture(ROOT / entry["path"])
    by_label = {s["label"]: s for s in spans}
    assert {"public_float", "ib5_trailing_sales"} <= set(by_label)
    case = next(i for i in raw["identities"] if i["archetype"] == "EDRY")["details"]["g0_case"]["numerical_path"]
    assert case["path_id"] == "foreign_f3.ib5_baby_shelf_cap"
    assert case["rule_id"] == "form_f3.I.B.5"
    operands = {o["name"]: o for o in case["operands"]}
    assert operands["public_float"]["span_text_sha256"] == by_label["public_float"]["sha256"]
    assert operands["sold_trailing_ib5"]["span_text_sha256"] == by_label["ib5_trailing_sales"]["sha256"]
    # exact arithmetic on the issuer's own stated figures
    limit = Decimal(65613529) / Decimal(3)
    cap = limit - Decimal(0)
    assert case["computed"]["exact"] == "65613529/3"
    assert Decimal(case["computed"]["cap"]) == cap.quantize(Decimal("0.01"))
    assert "65,613,529" in by_label["public_float"]["text"]
    assert "August 25, 2026" in by_label["public_float"]["text"]
    assert "General Instruction I.B.5" in by_label["ib5_trailing_sales"]["text"]


def test_g0_held_out_fixture_binds_the_sealed_operands(raw):
    entry = next(g for g in raw["gold_cases"] if g["gold_id"] == "gold:reference_g0:held_out_ib6_headroom")
    hdr, spans = parse_g0_fixture(ROOT / entry["path"])
    by_label = {s["label"]: s for s in spans}
    assert {"public_float_ib6", "ib6_trailing_sales", "atm_programme", "registered_direct"} == set(by_label)
    case = next(i for i in raw["identities"] if i["archetype"] == "RPID")["details"]["g0_case"]
    assert case["sealed"] is True and case["venue"] == "nasdaq" and case["foreign_private_issuer"] is False
    path = case["numerical_path"]
    assert path["path_id"] == "held_out.ib6_headroom" and path["rule_id"] == "form_s3.I.B.6"
    assert path["sealed"] is True and path["cutoff"] == entry["filed"] == "2026-05-19"
    operands = {o["name"]: o for o in path["operands"]}
    assert operands["public_float"]["span_text_sha256"] == by_label["public_float_ib6"]["sha256"]
    assert operands["sold_trailing"]["span_text_sha256"] == by_label["ib6_trailing_sales"]["sha256"]
    assert "held by non-affiliates" in by_label["public_float_ib6"]["text"]
    assert "12-calendar-month" in by_label["ib6_trailing_sales"]["text"]
    assert "sales agreement with TD Securities" in by_label["atm_programme"]["text"]
    assert "registered direct" in by_label["registered_direct"]["text"]


def test_g0_selection_record_lists_every_tested_candidate():
    text = SELECTION_RECORD.read_text(encoding="utf-8")
    for gap_id in G0_GAPS:
        assert f"## Gap: {gap_id}" in text, gap_id
    # chosen lines name the two chosen issuers and the open gap names its budget stop
    assert "EuroDry Ltd." in text and "EDRY" in text
    assert "Rapid Micro Biosystems" in text and "RPID" in text
    assert "not tested (budget)" in text
    # candidate tables carry CIK, accession, filing date and first failed criterion or PASS
    assert re.search(r"\| *# *\| *CIK *\| *accession *\| *filing date *\|", text)
    assert "c1_nasdaq_domestic_issuer" in text and "c4_operand_spans_exercisable_shares_terms" in text
    # the request ledger states the real count
    assert re.search(r"requests_made[\"']?\s*[:=]\s*297", text) or "297" in text


def test_g0_requalification_receipts(raw, pack):
    for archetype in ("AIR", "CLNN", "QNCX", "WHK", "LPTH", "EDBL"):
        identity = rq.identity_for(pack, archetype)
        receipt = identity.details["requalification_2026_10_19"]
        assert receipt["as_of"] == FETCH_DATE, archetype
    nasdaq = pack.source("nasdaq_rule_5600_series")
    rendered = nasdaq.details["rendered_receipt"]
    assert nasdaq.details["e0_rendered_receipt"]["page_text_sha256"] == \
        "25b336964180ff319bfc0f211a92951e81e0bf7ecc599cd9e7169b967938ee05"
    assert rendered["page_text_sha256"] == "adbee39938f63d9e7680d067398cabf1f1304845679746d0600fb68da7b465c3"
    assert rendered["rendered_at"].startswith("2026-10-19")
    assert rendered["section_5635_chars"] == 45650
    assert rendered["section_5635_sha256"] == "25c790344f44c97acedca33ac085c5ffae077172479d9db0c9208106d01d2030"
    assert nasdaq.edition_date == "2020-01-15"


def test_g0_qncx_rename_is_label_drift(raw, pack):
    identity = rq.identity_for(pack, "QNCX")
    assert identity.label_drift is True
    assert identity.registry_name == "IRulya Therapeutics Inc."
    assert identity.ticker == "IRLA"
    assert set(identity.details["all_tickers"]) == {"IRLA", "QNCX"}
    former = {n["name"] for n in identity.former_names}
    assert "Quince Therapeutics, Inc." in former
    assert any(n["to"] == "2026-10-09" for n in identity.former_names)
    assert "former" in identity.reason.casefold()
    assert identity.case_supply == "supplied" and identity.replacement_owed is False


def test_g0_l0_reference_pin_matches_the_pack():
    reference = rq.load_reference_pack(PACK_PATH)
    merged = load_rule_applicability_pack(reference_pack=reference)
    assert merged.reference.version == "capital-structure-reference-qualification/1.1.0"
    assert merged.file_sha256 == hashlib.sha256(
        (ROOT / "config/capital_structure_rule_applicability_pack.v1.json").read_bytes()).hexdigest()


def test_g0_no_float_or_network_in_this_test():
    source = Path(__file__).read_text(encoding="utf-8")
    for forbidden in ("flo" "at(", "re" "quests.", "url" "ib", "sec" ".gov"):
        assert forbidden not in source, forbidden
    assert "Decimal" in source  # exact arithmetic only
