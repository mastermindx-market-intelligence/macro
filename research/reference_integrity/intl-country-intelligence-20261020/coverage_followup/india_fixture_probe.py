"""Exercise the real acquired India fixture and targeted in-memory mutations."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from india_fixture_parser import parse_reviewed_pdf, parse_reviewed_texts

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "primary_artifacts"
blob = (ARTIFACTS / "mospi_q1_fy2026_27_20260831.pdf").read_bytes()
receipt = json.loads((ARTIFACTS / "in_acquisition_receipt.json").read_text())
pages = [page["text"] for page in json.loads((ARTIFACTS / "in_extracted_pages.json").read_text())["pages"]]
as_of = datetime.now(timezone.utc)
result = parse_reviewed_pdf(blob, receipt, as_of=as_of)
candidate = result["observation_candidate"]
assert candidate["value"] == 7.8 and candidate["period"] == "2026-Q2"
assert candidate["native_levels"][1]["value"] == 7546230
assert candidate["native_levels"][2]["value"] == 8136153
assert candidate["source_physical_page"] == 9 and candidate["source_printed_page"] == 8
assert candidate["seasonal_adjustment"] == "not_stated" and result["production_admitted"] is False
checks = [{"case": "actual_reviewed_pdf_and_receipt", "status": "passed"}]


def rejected(name, operation, expected_reason):
    try:
        operation()
    except ValueError as error:
        assert str(error) == expected_reason, (name, str(error), expected_reason)
        checks.append({"case": name, "status": "passed", "rejection": str(error)})
    else:
        raise AssertionError(name + " unexpectedly accepted")


def changed_page(index, old, new, count=-1):
    output = list(pages)
    assert old in output[index]
    output[index] = output[index].replace(old, new, count)
    return output


rejected("changed_wire_bytes", lambda: parse_reviewed_pdf(blob + b" ", receipt, as_of=as_of), "unreviewed_source_payload")
rejected("html_instead_of_pdf", lambda: parse_reviewed_pdf(b"<html>7.8</html>", receipt, as_of=as_of), "invalid_pdf_bytes")
rejected("wrong_source_url", lambda: parse_reviewed_pdf(blob, {**receipt, "final_url": "https://example.gov/gdp"}, as_of=as_of), "source_url_mismatch")
rejected("wrong_receipt_hash", lambda: parse_reviewed_pdf(blob, {**receipt, "source_sha256": "0" * 64}, as_of=as_of), "source_receipt_hash_or_length_mismatch")
rejected("naive_retrieval_clock", lambda: parse_reviewed_pdf(blob, {**receipt, "retrieved_at": "2026-10-20T21:04:50"}, as_of=as_of), "retrieval_clock_must_be_aware")
rejected("retrieved_before_publication", lambda: parse_reviewed_pdf(blob, {**receipt, "retrieved_at": "2026-08-01T00:00:00+00:00"}, as_of=as_of), "retrieval_clock_out_of_order")
rejected("future_retrieval_clock", lambda: parse_reviewed_pdf(blob, {**receipt, "retrieved_at": "2099-01-01T00:00:00+00:00"}, as_of=as_of), "retrieval_clock_out_of_order")
rejected("forecast_wording", lambda: parse_reviewed_texts(changed_page(2, "has been estimated to grow", "is predicted to grow")), "observed_real_headline_not_unique")
rejected("nominal_headline", lambda: parse_reviewed_texts(changed_page(2, "Real GDP", "Nominal GDP")), "observed_real_headline_not_unique")
rejected("old_price_base", lambda: parse_reviewed_texts(changed_page(1, "Constant (2022-23)", "Constant (2011-12)")), "price_base_mismatch")
rejected("wrong_native_quarter", lambda: parse_reviewed_texts(changed_page(1, "(Q1, April-June)", "(Q2, July-September)")), "native_period_mismatch")
rejected("wrong_table_columns", lambda: parse_reviewed_texts(changed_page(8, "2024-25 2025-26 2026-27 2025-26 2026-27", "2024-25 2026-27 2025-26 2025-26 2026-27")), "column_order_mismatch")
rejected("sequential_growth_basis", lambda: parse_reviewed_texts(changed_page(8, "Previous Year", "Previous Quarter")), "growth_basis_mismatch")
rejected("conflicting_statements", lambda: parse_reviewed_texts(changed_page(8, "GDP 70,61,843 75,46,230 81,36,153 6.9 7.8", "GDP 70,61,843 75,46,230 81,36,154 6.9 7.8", 1)), "gdp_statements_disagree")
rejected("level_growth_disagrees", lambda: parse_reviewed_texts(changed_page(8, "GDP 70,61,843 75,46,230 81,36,153 6.9 7.8", "GDP 70,61,843 75,46,230 91,36,153 6.9 7.8")), "current_level_rate_disagreement")
rejected("wrong_native_units", lambda: parse_reviewed_texts(changed_page(8, "₹ Crore", "USD Million")), "native_unit_mismatch")
rejected("new_seasonal_claim", lambda: parse_reviewed_texts([pages[0] + " Seasonally adjusted", *pages[1:]]), "seasonal_label_requires_new_review")

(ARTIFACTS / "in_parser_result_research_only.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
execution = {
    "scope": "research-only actual source fixture and targeted in-memory rejection cases; no production admission",
    "run_at": as_of.isoformat(), "checks_passed": len(checks), "checks": checks,
    "source_sha256": sha256(blob).hexdigest(),
    "parser_sha256": sha256((ROOT / "india_fixture_parser.py").read_bytes()).hexdigest(),
    "probe_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
}
(ARTIFACTS / "in_fixture_probe_receipt.json").write_text(json.dumps(execution, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(execution, ensure_ascii=False, indent=2))
