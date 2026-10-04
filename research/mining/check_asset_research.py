"""Reproduce Pass 02 research arithmetic; no product imports, trading or network I/O.

This checks illustrative calculations and selected transcription. It does not
reconcile issuer accounting, prove source rights, or implement a production model.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import hashlib
import json
import re
from typing import Callable

D = Decimal
ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "MINING_COPPER_PRECIOUS_ASSET_DOSSIERS_2026-09-23.md"
RECEIPT = ROOT / "MINING_ASSET_RESEARCH_CHECKS_2026-09-23.json"


def pct(actual: D, baseline: D) -> D:
    if not actual.is_finite() or not baseline.is_finite() or baseline <= 0:
        raise ValueError("Finite observations and a positive baseline are required")
    return (actual / baseline - 1) * 100


def display(value: D, places: str = "0.001") -> str:
    return format(value.quantize(D(places), rounding=ROUND_HALF_UP), "f")


def apply_interest(quantity: D, interest: D, reporting_basis: str) -> D:
    """Hypothetical attribution check, NOT an accepted accounting policy."""
    if quantity < 0 or not D(0) <= interest <= D(1):
        raise ValueError("Invalid quantity or interest")
    if reporting_basis != "gross":
        raise ValueError("Do not apply ownership again; reporting basis is not gross")
    return quantity * interest


def stream_illustration(gross: D, pre: D, post: D, payable: D,
                        remaining_pre_deliveries: D | None) -> D:
    """Synthetic common-gross stream, with a threshold measured in delivered ounces.

    Actual contracts can contain further terms. None are inferred here. Unknown
    cumulative-delivery state is deliberately not converted into pre-threshold.
    """
    if remaining_pre_deliveries is None:
        raise ValueError("Unknown threshold state")
    if gross < 0 or remaining_pre_deliveries < 0:
        raise ValueError("Negative production or threshold balance")
    if not D(0) < payable <= D(1) or not D(0) <= post <= pre <= D(1) or pre == 0:
        raise ValueError("Invalid contractual fraction")
    high_gross = min(gross, remaining_pre_deliveries / (pre * payable))
    return high_gross * pre * payable + (gross - high_gross) * post * payable


@dataclass(frozen=True)
class Comparison:
    subject: str
    metric: str
    period: str
    currency: str
    scale: str
    value: D


def compare(actual: Comparison, expected: Comparison) -> D:
    keys = ("subject", "metric", "period", "currency", "scale")
    if any(getattr(actual, key) != getattr(expected, key) for key in keys):
        raise ValueError("Incompatible expectation comparison")
    return pct(actual.value, expected.value)


def main() -> int:
    raw = REPORT.read_bytes()
    text = raw.decode("utf-8")
    checks: list[dict[str, object]] = []

    def check(name: str, ok: bool, evidence: object) -> None:
        checks.append({"name": name, "passed": bool(ok), "evidence": evidence})

    def rejects(name: str, action: Callable[[], object]) -> None:
        try:
            action()
        except ValueError as exc:
            check(name, True, str(exc))
        else:
            check(name, False, "Invalid input was accepted")

    sources = re.findall(r"^- \*\*(A\d{2}) —", text, re.M)
    requirements = re.findall(r"^\| (MA-\d{2}) \|", text, re.M)
    check("source_index_21_unique", sources == [f"A{i:02d}" for i in range(1, 22)], sources)
    check("source_references_resolve", set(re.findall(r"\bA\d{2}\b", text)) == set(sources), "All A references resolve")
    check("twenty_prospective_requirements", requirements == [f"MA-{i:02d}" for i in range(1, 21)], requirements)
    urls = re.findall(r"https://\S+", text.split("## 13. Source register", 1)[1])
    check("21_unique_primary_source_urls", len(urls) == len(set(urls)) == 21, len(urls))
    check("seven_dossiers", len(re.findall(r"^## \d+\. Dossier \d+", text, re.M)) == 7, "Seven case groups")
    check("research_only_and_handoff_held", "**Mission complete:** false" in text and "**Fable implementation handoff:** not created" in text, "No implementation acceptance")
    check("procedure_pin_and_same_carrier", "bf764f494b9cd0ecede6234bb472c3344c8e77cc" in text and "#7795" in text, "Pinned existing carrier")

    cu = D("10984") * D(".0108") * D(".92")
    zn = D("3572") * D(".0173") * D(".843")
    wrong_zn = D("10984") * D(".0173") * D(".843")
    check("ore_domains_sum", D("7412") + D("3572") == D("10984"), "A05, thousand tonnes")
    check("copper_reconstruction", cu == D("109.137024"), str(cu))
    check("zinc_correct_domain", zn == D("52.0936908"), str(zn))
    check("wrong_domain_counterexample", wrong_zn == D("160.1895576") and wrong_zn / zn > 3, str(wrong_zn / zn))
    check("zinc_reported_residual_preserved", zn != D("54") and "NOT_RECONCILED" in text, str(pct(zn, D("54"))))
    zn_bounds = (D("3571.5") * D(".01725") * D(".8425"),
                 D("3572.5") * D(".01735") * D(".8435"))
    check("hypothetical_rounding_intervals_do_not_reconcile", zn_bounds[1] < D("53.95"),
          {"model": "independent nearest rounding, NOT issuer-confirmed", "reconstruction_kt": [str(x) for x in zn_bounds], "reported_rounding_interval_kt": ["53.95", "54.05"]})
    check("Teck_illustrative_share", D("108.5") * D(".225") == D("24.4125"), "A05: gross production times interest, not a cash entitlement")
    check("Morenci_double_attribution_counterexample", D("117") * D(".72") == D("84.24"), "Wrong second multiplication; not the reported value")
    rejects("reject_second_attribution", lambda: apply_interest(D("117"), D(".72"), "already_attributable"))
    check("gross_attribution_example", apply_interest(D("100"), D(".72"), "gross") == D("72"), "Synthetic quantity")
    check("portfolio_attribution_reconciliation", D("786") - D("218") == D("568"), "A02: million recoverable pounds")

    pre_g, post_g, pre_b, post_b = D(".3375"), D(".225"), D(".3375") * D(".9"), D(".225") * D(".9")
    conditional = [pre_g + pre_b, pre_g + post_b, post_g + pre_b, post_g + post_b]
    check("four_conditional_stream_states", conditional == [D(".64125"), D(".54"), D(".52875"), D(".4275")], [str(x) for x in conditional])
    crossed = stream_illustration(D("1000000"), D(".3375"), D(".225"), D(".9"), D("100000"))
    check("within_period_threshold_split", abs(crossed - D("235833.3333333333333333333333")) < D(".000000001"), str(crossed))
    check("zero_threshold_uses_post_rate", stream_illustration(D("1000"), D(".3375"), D(".225"), D(".9"), D("0")) == D("202.5"), "Synthetic delivered ounces")
    check("all_high_rate_when_balance_suffices", stream_illustration(D("1000"), D(".3375"), D(".225"), D(".9"), D("1000")) == D("303.75"), "Conditional only")
    rejects("unknown_threshold_is_not_pre_threshold", lambda: stream_illustration(D("1000"), D(".3375"), D(".225"), D(".9"), None))
    rejects("invalid_payability_rejected", lambda: stream_illustration(D("1000"), D(".3375"), D(".225"), D("1.1"), D("1000")))
    check("Tia_progress_percentage_points", D("42") - D("32.5") == D("9.5"), "A11/A12; not a schedule extrapolation")
    check("Tia_unspent_budget_not_funding_gap", D("1802") - D("693") == D("1109"), "A12/A13; USD millions, selected observations")
    check("company_bond_simple_coupon", D("1250") * D(".0535") == D("66.875"), "A14; USD millions/year, not Tia-specific")
    mi_ex = D("13.685") + D("3.472")
    mi_inc = mi_ex + D(".534")
    inf_ex = D("2.290") + D("3.878")
    inf_inc = inf_ex + D(".136")
    check("Detour_MI_boundaries", [mi_ex, mi_inc] == [D("17.157"), D("17.691")], "A16; million ounces, excluding/including Zone58N")
    check("Detour_inferred_boundaries", [inf_ex, inf_inc] == [D("6.168"), D("6.304")], "A16; no reserve addition")
    check("Detour_headline_rounding", [display(v, ".1") for v in (mi_ex, mi_inc, inf_ex, inf_inc)] == ["17.2", "17.7", "6.2", "6.3"], "Same source date, different component boundary")
    check("hypothetical_displaced_feed", D("400") * (D("50") - D("30")) == D("8000"), "Synthetic USD/day, no actual mine forecast")
    dcf = D("100") / D("1.1") ** 5 - D("100") / D("1.1") ** 10
    check("hypothetical_cash_timing", display(dcf) == "23.538", str(dcf))
    actual = Comparison("Aurubis group", "operating EBT", "2025-10-01/2026-06-30", "EUR", "million", D("374"))
    expected = Comparison("Aurubis group", "operating EBT", "2025-10-01/2026-06-30", "EUR", "million", D("363"))
    check("matched_expectation_difference", display(compare(actual, expected), ".01") == "3.03", "A20/A21; presently reconstructed, not native PIT")
    check("year_on_year_growth", display(pct(D("374"), D("286")), ".01") == "30.77", "A20; a different denominator")
    check("result_below_sample_high", D("374") < D("377"), "A21; not a probability statement")
    rejects("mismatched_metric_rejected", lambda: compare(Comparison("Aurubis group", "IFRS EBT", actual.period, "EUR", "million", D("1272")), expected))
    rejects("mismatched_period_rejected", lambda: compare(actual, Comparison(expected.subject, expected.metric, "FY2025/26", "EUR", "million", D("523"))))
    rejects("mismatched_currency_rejected", lambda: compare(actual, Comparison(expected.subject, expected.metric, expected.period, "USD", "million", D("363"))))
    rejects("nonpositive_comparator_rejected", lambda: pct(D("374"), D("0")))
    check("historical_retrieval_limit_preserved", "not a contemporaneously captured historical snapshot" in text, "Publisher as-of != native archived knowledge")
    check("report_copper_rounding", display(cu) in text, display(cu))
    check("report_zinc_rounding", display(zn) in text, display(zn))
    check("report_wrong_domain_rounding", display(wrong_zn) in text, display(wrong_zn))
    check("report_DCF_rounding", display(dcf) in text, display(dcf))

    receipt = {
        "operation": "gmi-mining-principal-research-20260923-sol-001",
        "date": "2026-09-23",
        "command": "python /mnt/data/mining_research/check_asset_research.py",
        "classification": "RESEARCH_ARITHMETIC_AND_DOCUMENT_INTEGRITY_ONLY",
        "document": REPORT.name,
        "document_words": len(text.split()),
        "document_bytes": len(raw),
        "document_sha256": hashlib.sha256(raw).hexdigest(),
        "document_git_blob_sha1": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
        "total": len(checks),
        "passed": sum(bool(c["passed"]) for c in checks),
        "failed": sum(not bool(c["passed"]) for c in checks),
        "checks": checks,
        "prepublication_corrections": {"initial_result": "41/44; three draft-rounding text checks failed", "cause": "Manually transcribed approximate results did not match Decimal round-half-up calculations", "corrected_report_values": ["52.094 thousand zinc tonnes", "160.190 thousand wrong-domain zinc tonnes", "23.538 million hypothetical timing value"], "issuer_inputs_changed": False, "checks_weakened": False},
        "known_unresolved": ["Antamina reported zinc production residual", "actual stream threshold balances", "full reserve/resource overlap convention", "native historical consensus retention"],
        "not_claimed": ["product tests", "CI", "independent review", "issuer accounting reconciliation", "investment validation", "source-rights acceptance", "Agent OS validation", "browser proof", "implementation", "Fable dispatch"],
    }
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: receipt[key] for key in ("document_words", "document_bytes", "document_sha256", "document_git_blob_sha1", "total", "passed", "failed")}, indent=2))
    for c in checks:
        if not c["passed"]:
            print("FAIL", c["name"], c["evidence"])
    return 1 if receipt["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
