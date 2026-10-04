"""Pass 05: local research arithmetic and pedagogical input-compatibility checks.

Run beside the report: python check_bulk_research.py
Standard library only; no network, product imports, orders or external effects.
These miniature examples are NOT production accounting, pricing or demand models.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal as D, localcontext
from pathlib import Path
import hashlib
import json
import re
from typing import Callable

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "MINING_BULK_FERTILIZER_ECONOMICS_2026-09-23.md"
RECEIPT = ROOT / "MINING_BULK_RESEARCH_CHECKS_2026-09-23.json"


@dataclass(frozen=True)
class Observation:
    """A teaching fixture, not an accepted native GMI observation contract."""
    value: D
    unit: str
    period: str
    definition: str
    delivery: str
    basis_resolved: bool = True


def change(a: Observation, b: Observation) -> D:
    """Compare only equal fixture bases; b is the earlier observation."""
    fields = ("unit", "period", "definition", "delivery")
    if not (a.basis_resolved and b.basis_resolved):
        raise ValueError("unresolved basis")
    if any(getattr(a, f) != getattr(b, f) for f in fields):
        raise ValueError("incompatible observation bases")
    if b.value <= 0:
        raise ValueError("comparison denominator must be positive")
    return (a.value / b.value - 1) * 100


def wet_to_dry(value: D, moisture: D | None, input_basis: str) -> D:
    if input_basis != "USD/wet_metric_tonne":
        raise ValueError("input is not a wet metric tonne quote")
    if moisture is None or not D("0") <= moisture < D("1"):
        raise ValueError("a bounded moisture assumption or measurement is required")
    return value / (1 - moisture)


def premium_interval(buyer_value: D | None, incremental_cost: D | None) -> tuple[D, D] | None:
    if buyer_value is None or incremental_cost is None:
        raise ValueError("both sides of the premium comparison are required")
    if buyer_value < 0 or incremental_cost < 0:
        raise ValueError("this simple fixture assumes non-negative gross amounts")
    if buyer_value < incremental_cost:
        return None
    return incremental_cost, buyer_value


def add_nonoverlap(items: list[tuple[D, str]]) -> D:
    """Only disjoint realized fixtures may be summed; no arbitrary period inference."""
    if any(kind != "disjoint_realized" for _, kind in items):
        raise ValueError("banked, annualized and target observations may overlap")
    return sum((v for v, _ in items), D("0"))


def nutrient_cost(price: D, phosphate_fraction: D, nitrogen_kg: D,
                  nitrogen_credit: D, usable: bool | None) -> D:
    if not D("0") < phosphate_fraction <= D("1"):
        raise ValueError("invalid phosphate fraction")
    if nitrogen_credit and usable is not True:
        raise ValueError("co-nutrient usefulness must be stipulated or established")
    return (price - nitrogen_kg * nitrogen_credit) / phosphate_fraction


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def run() -> dict[str, object]:
    raw = REPORT.read_bytes()
    text = raw.decode("utf-8")
    checks: list[dict[str, object]] = []

    def check(name: str, ok: bool, evidence: object) -> None:
        checks.append({"name": name, "passed": bool(ok), "evidence": evidence})

    def refuses(name: str, fn: Callable[[], object]) -> None:
        try:
            value = fn()
        except ValueError as exc:
            check(name, True, str(exc))
        else:
            check(name, False, {"unexpected_result": str(value)})

    def rounded(name: str, value: D, expected: str, source: str) -> None:
        check(name, value.quantize(D(expected)) == D(expected),
              {"value": str(value), "expected_rounded": expected, "scope": source})

    dossiers = re.findall(r"^### (D\d{2}) —", text, re.M)
    sources = re.findall(r"^- \*\*(S\d{2}) —", text, re.M)
    requirements = re.findall(r"^\| (MG-\d{2}) \|", text, re.M)
    personas = re.findall(r"^### (P\d{2}) —", text, re.M)
    examples = re.findall(r"^\*\*(H\d{2}) —", text, re.M)
    check("eleven_dossiers", dossiers == [f"D{i:02d}" for i in range(1, 12)], dossiers)
    check("sixteen_primary_source_records", sources == [f"S{i:02d}" for i in range(1, 17)], sources)
    check("twenty_eight_prospective_requirements", requirements == [f"MG-{i:02d}" for i in range(1, 29)], requirements)
    check("five_persona_workflows", personas == [f"P{i:02d}" for i in range(1, 6)], personas)
    check("five_hypothetical_examples", examples == [f"H{i:02d}" for i in range(1, 6)], examples)
    refs = set(re.findall(r"\bS\d{2}\b", text))
    check("source_identifiers_resolve", refs == set(sources), sorted(refs))
    urls = re.findall(r"https://\S+", text.split("## 9. Source register", 1)[1])
    check("unique_source_urls", len(urls) == len(set(urls)) == 16, len(urls))
    check("held_scope_explicit", "**Mission complete:** false" in text and "**Final Fable implementation handoff:** not created" in text, "research/HOLD; not implementation")
    check("procedure_and_carrier", "4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2" in text and "#7795" in text, "same protected pin and research carrier")
    check("research_not_product_tests", "not implemented application tests" in text, "prospective requirements, not executed product behavior")
    check("pellet_ambiguity_kept", "pellet basis remains conditional" in text, "S02/S03; no forced migration date")
    check("source_year_discrepancy_kept", "opening sentence says 2025" in text, "S14 conflict retained, not silently rewritten")

    with localcontext() as ctx:
        ctx.prec = 40
        check("Vale_reported_bridge", D("106.0") - D("2.5") - D("8.5") == D("95.0"), "S04: issuer transformation bridge, not homogeneous-unit subtraction")
        check("Vale_sustaining_inclusive_break_even", D("61.6") + D("8.5") == D("70.1"), "S04: USD/dry tonne")
        rounded("Jansen_capital_estimate_change", (D("6.9") / D("4.9") - 1) * 100, "40.82", "S07/S08; not isolated cause of IRR change")
        check("Rio_group_FCF", D("9173") - D("5037") - D("302") == D("3834"), "S09; USD millions; issuer-defined economic share")
        check("Rio_capital_adjustment", D("5947") - D("207") - D("703") == D("5037"), "S09; partner contributions due are not all cash received")
        old_margin = D("130.01") - D("101.17")
        new_margin = D("137.82") - D("92.53")
        check("Warrior_prior_unit_cash_contribution", old_margin == D("28.84"), "S10; USD/short ton, not GAAP margin")
        check("Warrior_current_unit_cash_contribution", new_margin == D("45.29"), "S10; USD/short ton")
        rounded("Warrior_contribution_change", (new_margin / old_margin - 1) * 100, "57.04", "S10; not causal attribution to engineering")
        check("Warrior_operating_cash_less_gross_capex", D("132.277") - D("28.923") == D("103.354"), "S10; USD millions")
        check("Warrior_net_investing_bridge", D("28.923") - D("10.579") - D("0.045") == D("18.299"), "S10; gross capex less disposal inflows")
        check("net_investing_is_not_capex", D("18.299") != D("28.923"), "Using net investment overstates this simple FCF by USD10.624m")
        rounded("Nutrien_phosphate_price_change", (D("781") / D("714") - 1) * 100, "9.38", "S11; same stated product price scope")
        rounded("Nutrien_phosphate_EBITDA_change", (D("23") / D("92") - 1) * 100, "-75.00", "S11; reported adjusted EBITDA")
        check("Nutrien_potash_margin_direction", D("154") > D("138"), "S11; not phosphate economics")
        old_mid = (D("630") + D("730")) / 2
        new_mid = (D("680") + D("760")) / 2
        check("KplusS_midpoints", (old_mid, new_mid) == (D("680"), D("720")), "S13/S14; EUR millions, FY2026 EBITDA")
        rounded("KplusS_guidance_midpoint_increase", (new_mid / old_mid - 1) * 100, "5.88", "S13/S14; management-range comparison")
        rounded("KplusS_midpoint_vs_stated_consensus", (new_mid / D("718") - 1) * 100, "0.28", "S14; July16-labeled consensus, reconstructed now")

        check("H01_no_jointly_feasible_premium", premium_interval(D("12"), D("17")) is None, "hypothetical; buyer value below incremental production cost")
        check("H01_buyer_seller_at_ten", (D("12") - 10, D("10") - 17) == (D("2"), D("-7")), "hypothetical; matched comparable units")
        check("H01_improved_cost_opens_interval", premium_interval(D("12"), D("6")) == (D("6"), D("12")) and D("10") - 6 == 4, "hypothetical; producer +4 and buyer +2")
        rounded("H02_moisture_example", wet_to_dry(D("18.74"), D("0.08"), "USD/wet_metric_tonne"), "20.3696", "reported cost with explicitly hypothetical 8% moisture")
        annual_cash = D("70")
        pv = sum((annual_cash / D("1.1") ** t for t in range(1, 11)), D("0"))
        rounded("H03_cash_margin", annual_cash / D("100") * 100, "70.0000", "hypothetical; stipulated cash basis")
        rounded("H03_simple_payback", D("500") / annual_cash, "7.1429", "hypothetical; years, not discounted payback")
        rounded("H03_present_value", pv, "430.1197", "hypothetical; ten annual cash flows discounted at 10%")
        rounded("H03_negative_NPV", pv - D("500"), "-69.8803", "hypothetical; excludes tax, reinvestment, working capital and terminal proceeds")
        old_receipts = D("200") * D("4.50")
        new_receipts = old_receipts * D("0.9")
        new_bill = D("210") * D("1.15")
        check("H04_receipts_and_bill", (old_receipts, new_receipts, new_bill) == (D("900"), D("810"), D("241.50")), "hypothetical; same area basis")
        rounded("H04_original_affordability_ratio", D("210") / old_receipts * 100, "23.3333", "hypothetical; fraction of gross receipts, not profit")
        rounded("H04_changed_affordability_ratio", new_bill / new_receipts * 100, "29.8148", "hypothetical; no elasticity estimate")
        check("H04_credit_is_separate_constraint", D("180") < D("210"), "hypothetical; financing constraint regardless of annual-profit assertion")
        a_gross = nutrient_cost(D("600"), D(".46"), D("180"), D("0"), None)
        b_gross = nutrient_cost(D("650"), D(".52"), D("110"), D("0"), None)
        a_net = nutrient_cost(D("600"), D(".46"), D("180"), D(".50"), True)
        b_net = nutrient_cost(D("650"), D(".52"), D("110"), D(".50"), True)
        rounded("H05_A_phosphate_only", a_gross, "1304.3478", "hypothetical USD/tonne available phosphate equivalent")
        rounded("H05_B_phosphate_only", b_gross, "1250.0000", "hypothetical; stipulated composition")
        rounded("H05_A_after_usable_nitrogen", a_net, "1108.6957", "hypothetical; USD90 stipulated usable credit")
        rounded("H05_B_after_usable_nitrogen", b_net, "1144.2308", "hypothetical; USD55 stipulated usable credit")
        check("H05_comparison_reverses", a_gross > b_gross and a_net < b_net, "not an actual agronomic or purchasing recommendation")

        refuses("missing_moisture_refused", lambda: wet_to_dry(D("18.74"), None, "USD/wet_metric_tonne"))
        refuses("invalid_moisture_refused", lambda: wet_to_dry(D("18.74"), D("1"), "USD/wet_metric_tonne"))
        refuses("second_dry_conversion_refused", lambda: wet_to_dry(D("18.74"), D(".08"), "USD/dry_metric_tonne"))
        now = Observation(D("106"), "USD/dry_metric_tonne", "illustrative_matched_period", "Fe61_impurity_version_A", "CFR")
        prev = replace(now, value=D("100"))
        check("compatible_fixture_comparison", change(now, prev) == D("6"), "hypothetical positive control, not actual benchmark history")
        refuses("benchmark_specification_mismatch", lambda: change(now, replace(prev, definition="Fe62_legacy_impurities")))
        refuses("unresolved_conditional_migration", lambda: change(now, replace(prev, basis_resolved=False)))
        refuses("wet_dry_mismatch", lambda: change(now, replace(prev, unit="USD/wet_metric_tonne")))
        refuses("long_short_ton_mismatch", lambda: change(replace(now, unit="USD/long_ton"), replace(prev, unit="USD/short_ton")))
        refuses("delivery_basis_mismatch", lambda: change(now, replace(prev, delivery="FOB")))
        refuses("period_mismatch", lambda: change(now, replace(prev, period="different_period")))
        refuses("zero_comparison_denominator", lambda: change(now, replace(prev, value=D("0"))))
        refuses("missing_producer_cost", lambda: premium_interval(D("12"), None))
        refuses("overlapping_productivity_sum", lambda: add_nonoverlap([(D("870"), "banked"), (D("1300"), "annualized"), (D("1800"), "target")]))
        check("disjoint_fixture_sum_allowed", add_nonoverlap([(D("2"), "disjoint_realized"), (D("3"), "disjoint_realized")]) == 5, "hypothetical positive control")
        refuses("unknown_nutrient_usefulness", lambda: nutrient_cost(D("600"), D(".46"), D("180"), D(".50"), None))
        refuses("unusable_nutrient_credit", lambda: nutrient_cost(D("600"), D(".46"), D("180"), D(".50"), False))
        refuses("zero_nutrient_denominator", lambda: nutrient_cost(D("600"), D("0"), D("180"), D("0"), None))

    script_raw = Path(__file__).read_bytes()
    receipt: dict[str, object] = {
        "operation": "gmi-mining-principal-research-20260923-sol-001",
        "classification": "LOCAL_RESEARCH_ARITHMETIC_DOCUMENT_AND_PEDAGOGICAL_COMPATIBILITY_ONLY",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "research_cutoff": "2026-09-23",
        "command": "python check_bulk_research.py",
        "document": REPORT.name,
        "document_words": len(text.split()),
        "document_bytes": len(raw),
        "document_sha256": hashlib.sha256(raw).hexdigest(),
        "document_git_blob_sha1": git_blob(raw),
        "script_git_blob_sha1": git_blob(script_raw),
        "total": len(checks),
        "passed": sum(bool(x["passed"]) for x in checks),
        "failed": sum(not bool(x["passed"]) for x in checks),
        "checks": checks,
        "not_claimed": ["application tests", "CI", "independent research review", "issuer-accounting reconciliation", "native benchmark normalization", "actual contract settlement", "customer or agronomic validation", "historical native retention", "source reuse rights", "Agent OS validator", "browser proof", "investment validation", "Fable dispatch"],
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    result = run()
    keys = ("run_utc", "document_words", "document_bytes", "document_sha256", "document_git_blob_sha1", "script_git_blob_sha1", "total", "passed", "failed")
    print(json.dumps({k: result[k] for k in keys}, indent=2))
    failures = [c for c in result["checks"] if not c["passed"]]
    if failures:
        print(json.dumps(failures, indent=2))
        raise SystemExit(1)
