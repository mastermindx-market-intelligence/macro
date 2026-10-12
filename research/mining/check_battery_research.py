"""Reproduce Pass 03 research arithmetic and pedagogical counterexamples.

Run beside the report: python check_battery_research.py
Standard library only. No product imports, network I/O or trading output.
These examples are NOT a production contract engine or accounting reconciliation.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal as D, localcontext
from pathlib import Path
import hashlib
import json
import re
from typing import Callable

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "MINING_BATTERY_RARE_EARTH_ECONOMICS_2026-09-23.md"
RECEIPT = ROOT / "MINING_BATTERY_RESEARCH_CHECKS_2026-09-23.json"


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def same_basis(left: tuple[str, ...], right: tuple[str, ...]) -> None:
    """Illustrative refusal only; not a native Mastermind validation contract."""
    if left != right:
        raise ValueError("Incompatible measurement or accounting basis")


def unique_designations(groups: list[set[str]]) -> None:
    """Synthetic batch IDs illustrate nonduplication; no live batch records."""
    seen: set[str] = set()
    for group in groups:
        if seen & group:
            raise ValueError("A synthetic batch was designated more than once")
        seen.update(group)


def mp_upside(kg: D, benchmark: D, capacity_condition: bool | None) -> D | None:
    """Partial hypothetical formula, not a settlement estimate or legal opinion."""
    if capacity_condition is None:
        return None
    if not capacity_condition:
        return D(0)
    return kg * max(benchmark - D(110), D(0)) * D("0.30")


def jare_sharing(kg: D, achieved_price: D, used_cap: D | None) -> D | None:
    """Calendar-year toy calculation; missing consumed cap stays unknown."""
    if used_cap is None:
        return None
    if not D(0) <= used_cap <= D("10000000"):
        raise ValueError("Consumed cap is outside the assumed annual limit")
    raw = kg * max(achieved_price - D(150), D(0)) * D("0.30")
    return min(raw, D("10000000") - used_cap)


def rejects(fn: Callable[[], object]) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


def main() -> int:
    raw = REPORT.read_bytes()
    text = raw.decode("utf-8")
    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, evidence: object, kind: str = "ARITHMETIC") -> None:
        checks.append({"check": name, "passed": bool(passed), "kind": kind, "evidence": evidence})

    def shown(value: D, digits: str, literal: str) -> bool:
        return value.quantize(D(digits)) == D(literal.replace(",", "")) and literal in text

    sources = re.findall(r"^- \*\*(S3-\d{2}) —", text, re.M)
    check("source_index", sources == [f"S3-{i:02d}" for i in range(1, 18)], sources, "DOCUMENT")
    check("source_references_resolve", set(re.findall(r"\bS3-\d{2}\b", text)) == set(sources), "Index/reference identity, not source authentication", "DOCUMENT")
    check("nine_dossiers", re.findall(r"^### (B\d{2}) —", text, re.M) == [f"B{i:02d}" for i in range(1, 10)], "B01..B09", "DOCUMENT")
    check("twenty_four_prospective_requirements", re.findall(r"^\| (MB-\d{2}) \|", text, re.M) == [f"MB-{i:02d}" for i in range(1, 25)], "MB-01..MB-24 are NOT executed application tests", "DOCUMENT")
    persona_section = text.split("## 7.", 1)[1].split("## 8.", 1)[0]
    check("six_persona_tasks", len(re.findall(r"^\*\*[^*]+\*\*", persona_section, re.M)) == 6, "Six proposed user tasks", "DOCUMENT")
    urls = re.findall(r"https://\S+", text.split("## 12.", 1)[1])
    check("seventeen_source_urls", len(urls) == len(set(urls)) == 17, "Unique URLs within Pass03 only", "DOCUMENT")
    check("explicit_hold", "**Mission complete:** false" in text and "**Final Fable implementation handoff:** not created" in text, "Research remains incomplete", "DOCUMENT")
    check("exact_carrier_and_pin", all(x in text for x in ["#7795", "gmi-mining-principal-research-20260923-sol-001", "4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2"]), "Same research carrier; current procedure pin", "DOCUMENT")

    with localcontext() as ctx:
        ctx.prec = 36
        alb_fcf = D("709.997") - D("71.731")
        check("albemarle_q2_reported_cash_arithmetic", shown(alb_fcf, ".001", "638.266"), {"USD_millions": str(alb_fcf), "source": "S3-01"})
        naive_income = D("461.155") * D(".49")
        residual = naive_income - D("165.835")
        check("windfield_naive_share_and_unresolved_residual", shown(naive_income, ".00001", "225.96595") and shown(residual, ".00001", "60.13095") and "NOT_RECONCILED" in text, {"naive_USD_m": str(naive_income), "unexplained_USD_m": str(residual), "source": "S3-02", "not_accounting_reconciliation": True})
        check("reject_unlike_period_bridge", rejects(lambda: same_basis(("USD", "Q2 2026"), ("USD", "H1 2026"))), "Synthetic period mismatch; do not force six-month deferral change into quarter residual", "COUNTEREXAMPLE")

        total = D(882) + D(2679)
        weighted = (D(882)*D(".99") + D(2679)*D(".98")) / total * 100
        check("ppls_weighted_grade_conformity", shown(weighted, ".01", "98.25"), {"total_tonnes": str(total), "implied_percent": str(weighted), "source": "S3-03", "rounded_inputs": True, "not_recovery_or_customer_acceptance": True})
        check("ppls_simple_average_is_different", (D(99)+D(98))/2 != weighted, "98.5% unweighted versus approximately 98.25% weighted", "COUNTEREXAMPLE")
        margins = [D(15000)-D("7.5")*D(1000)-D(4000), D(15000)-D("7.5")*D(1600)-D(4000), D(18000)-D("7.5")*D(1600)-D(4000)]
        check("hypothetical_converter_margin_regimes", margins == [D(3500), D(-1000), D(2000)] and all(x in text for x in ["$3,500", "minus $1,000", "$2,000"]), [str(x) for x in margins], "HYPOTHETICAL")
        check("reject_incompatible_mass_bases", rejects(lambda: same_basis(("tonnes", "concentrate", "quarter"), ("tonnes", "hydroxide", "year"))), "Synthetic gross concentrate versus final-product/period mismatch", "COUNTEREXAMPLE")

        floor_below = D(1000000) * max(D(110)-D(80), D(0))
        check("hypothetical_mp_floor_below", floor_below == D(30000000) and "$30 million" in text, str(floor_below), "HYPOTHETICAL")
        check("hypothetical_mp_floor_above_zero", D(1000000)*max(D(110)-D(170), D(0)) == 0, "No shortfall above threshold in simplified example", "HYPOTHETICAL")
        check("hypothetical_mp_upside_trigger", mp_upside(D(1000000), D(170), True) == D(18000000) and "$18 million" in text and mp_upside(D(1000000), D(170), False) == 0, "Capacity condition changes partial illustrative formula", "HYPOTHETICAL")
        check("unknown_mp_trigger_stays_unknown", mp_upside(D(1000000), D(170), None) is None, "Unknown does not silently become zero or true", "COUNTEREXAMPLE")
        check("duplicate_designation_rejected", rejects(lambda: unique_designations([{"toy-batch-1"}, {"toy-batch-1"}])), "Synthetic duplicate across categories; no native records", "COUNTEREXAMPLE")

        reo_growth = (D(3481)/D(3233)-1)*100
        ndpr_growth = (D(1857)/D(1996)-1)*100
        check("lynas_product_directions", shown(reo_growth, ".01", "7.67") and (-ndpr_growth).quantize(D(".01")) == D("6.96") and "minus 6.96%" in text, {"REO_percent": str(reo_growth), "NdPr_percent": str(ndpr_growth), "source": "S3-08"})
        capex_change = (D(294)/D(180)-1)*100
        check("lynas_budget_revision", shown(capex_change, ".01", "63.33"), {"percent": str(capex_change), "source": "S3-08", "not_wholly_same_scope_overrun": True})
        check("firm_quantity_is_subset", D(5000) <= D(7200) and D(5000)+D(7200) != D(7200), "Do not add firm quantity to its containing availability envelope", "COUNTEREXAMPLE")
        check("hypothetical_jare_annual_cap", jare_sharing(D(5000000), D(170), D(0)) == D(10000000), "Raw sharing $30m; assumed unused annual cap $10m", "HYPOTHETICAL")
        check("hypothetical_jare_remaining_cap", jare_sharing(D(5000000), D(170), D(7000000)) == D(3000000), "Earlier $7m consumes part of annual cap", "HYPOTHETICAL")
        check("unknown_jare_cap_stays_unknown", jare_sharing(D(5000000), D(170), None) is None, "Missing cumulative settlement is not unused cap", "COUNTEREXAMPLE")
        check("invalid_jare_cap_rejected", rejects(lambda: jare_sharing(D(5000000), D(170), D(11000000))), "Synthetic consumed cap exceeds assumed limit", "COUNTEREXAMPLE")

        check("neo_release_chronology", date(2026,6,30) < date(2026,7,8) < date(2026,8,11) < date(2026,9,14) <= date(2026,9,23), "Period end, guidance change, results, commercial update, retrieval; not PIT retention", "CHRONOLOGY")
        guide_change = (D(145)/D(105)-1)*100
        check("neo_guidance_midpoint_change", shown(guide_change, ".01", "38.10"), {"percent": str(guide_change), "source": "S3-16", "not_consensus_surprise": True})
        neo_reported = D("93.264") - D("5.154")
        neo_cash = D("-49.645") - D("16.559")
        check("neo_reported_metric_arithmetic", shown(neo_reported, ".001", "88.110"), {"USD_m": str(neo_reported), "source": "S3-12", "definition": "Adjusted EBITDA less capex net recognized JTF grant"})
        check("neo_operating_cash_less_gross_spending", (-neo_cash).quantize(D(".001")) == D("66.204") and "minus $66.204 million" in text, {"USD_m": str(neo_cash), "source": "S3-13", "definition": "Our OCF less gross PPE/intangible cash spending"})
        check("neo_definitions_not_interchangeable", rejects(lambda: same_basis(("USD", "H1 2026", "EBITDA less adjusted capex"), ("USD", "H1 2026", "OCF less gross investing spend"))) and neo_reported > 0 > neo_cash, "Definition refusal, not accusation of issuer arithmetic error", "COUNTEREXAMPLE")
        investing = D("-16.559") + D(".660") - D(".125")
        cash_change = D("-49.645") + investing + D("125.900") - D("2.367")
        check("neo_cash_statement_bridge", investing == D("-16.024") and shown(cash_change, ".001", "57.864") and D("38.360")+cash_change == D("96.224"), {"change_USD_m": str(cash_change), "source": "S3-13", "not_self_funded_growth": True})

        recycled = D(1000)*D(".20")*D(".90")*D(".90")
        check("hypothetical_single_cycle_recycling", recycled == D(162) and D(1000)-recycled == D(838) and "162 kilograms" in text and "838 kilograms" in text, "Single cycle and one element-equivalent basis, not issuer recovery", "HYPOTHETICAL")
        physical = min(D(100),D(80),D(70))
        commercial = min(physical,D(60))
        economic = min(commercial,D(45))
        check("hypothetical_serial_and_commercial_bounds", (physical,commercial,economic) == (D(70),D(60),D(45)) and physical != sum([D(100),D(80),D(70)]), "Compatible units, steady state, no inventory; not a predictive score", "HYPOTHETICAL")
        check("forecast_horizon_not_current_mix", rejects(lambda: same_basis(("MP Magnetics mix", "forecast 2030"), ("MP Magnetics mix", "actual 2026"))), "S3-17 estimates do not establish current revenue weights", "COUNTEREXAMPLE")
        check("unresolveds_and_access_limits_preserved", all(x in text for x in ["NOT_RECONCILED", "screenshot/local-byte retrieval failed", "No specific P-PLS current utilization", "unaudited interim statements"]), "Missing evidence is retained, not filled by arithmetic", "DOCUMENT")

    result = {
        "operation": "gmi-mining-principal-research-20260923-sol-001",
        "classification": "RESEARCH_ARITHMETIC_DOCUMENT_AND_PEDAGOGICAL_COUNTEREXAMPLES_ONLY",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "command": "python check_battery_research.py",
        "document": REPORT.name,
        "document_words": len(text.split()),
        "document_bytes": len(raw),
        "document_sha256": hashlib.sha256(raw).hexdigest(),
        "document_git_blob_sha1": git_blob(raw),
        "script_git_blob_sha1": git_blob(Path(__file__).read_bytes()),
        "total": len(checks),
        "passed": sum(bool(c["passed"]) for c in checks),
        "failed": sum(not bool(c["passed"]) for c in checks),
        "checks": checks,
        "not_claimed": ["application tests", "accepted native contract engine", "CI", "independent research review", "issuer accounting reconciliation", "canonical Agent OS validation", "customer confirmation", "data rights/admission", "historical PIT retention", "browser proof", "investment validation", "Fable handoff or dispatch"]
    }
    RECEIPT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ["document_words", "document_bytes", "document_sha256", "document_git_blob_sha1", "script_git_blob_sha1", "total", "passed", "failed"]}, indent=2))
    for item in checks:
        if not item["passed"]:
            print("FAIL:", json.dumps(item, ensure_ascii=False))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
