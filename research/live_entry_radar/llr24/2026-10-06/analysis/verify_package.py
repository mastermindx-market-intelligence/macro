"""Validate LLR-24 report structure, not scientific efficacy. No network access."""
from pathlib import Path
import argparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = [
    "00_EXECUTIVE_RULING.md", "01_CURRENT_ESTATE_AND_COLLISION_CENSUS.md",
    "02_PRIOR_MASTERMIND_RESEARCH_SYNTHESIS.md", "03_EXTERNAL_LITERATURE_AND_MECHANISM_CENSUS.md",
    "04_24H_MARKET_CLOCK_AND_DATA_CONTRACT.md", "05_DATA_SOURCE_AND_STORAGE_ARCHITECTURE.md",
    "06_ECONOMIC_LOW_HIGH_LABEL_SPEC.md", "07_FEATURE_DEPENDENCY_AND_ABLATION_SPEC.md",
    "08_MODEL_TOURNAMENT_AND_PATH_INTELLIGENCE_ARCHITECTURE.md", "09_STATISTICAL_PREREGISTRATION_AND_EVALUATION.md",
    "10_LIVE_ENTRY_RADAR_INTEGRATION.md", "11_TECHNICAL_OPPORTUNITY_REVIVAL_AND_INTEGRATION.md",
    "12_OPTIONS_MICROSTRUCTURE_AND_RELATIVE_CONTEXT.md", "13_TERMINAL_TACTICAL_INTELLIGENCE_PRODUCT_SPEC.md",
    "14_MASTERMINDEX_PROPHET_ENTRY_AVAILABILITY_INTERFACE.md", "15_EXIT_AND_TOP_INTELLIGENCE_RESEARCH_PLAN.md",
    "16_END_TO_END_PROGRAM_MASTERPLAN.md", "17_ORCHESTRATOR_EXECUTION_HANDOFF.md",
    "SOURCE_REGISTER.md", "DECISION_LEDGER.md", "OPEN_QUESTIONS.md",
]
FIELDS = ["WAVE_ID", "CAPABILITY_UNLOCKED", "CANONICAL_OWNER", "REPO", "SOURCE_PATHS",
          "INPUT_CONTRACT", "OUTPUT_CONTRACT", "PREREQUISITES", "RESEARCH/IMPLEMENTATION",
          "ALLOWED_EFFECTS", "NON_GOALS", "ACCEPTANCE", "TESTS", "REAL_PATH_PROOF",
          "ROLLBACK", "KILL_CONDITION", "NEXT_DEPENDENCY"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write the structural validation receipt")
    args = parser.parse_args()
    errors = []
    missing = [name for name in CHAPTERS if not (ROOT / name).is_file()]
    errors.extend("missing file: " + name for name in missing)
    text = {name: (ROOT / name).read_text() for name in CHAPTERS if name not in missing}
    questions = re.findall(r"^\| (\d+) \|", text.get(CHAPTERS[0], ""), re.M)
    if questions != [str(i) for i in range(1, 31)]:
        errors.append("Executive table must answer questions1–30 exactly once in order")
    wave_sections = re.split(r"(?=^## \d+\. R\d+ —)", text.get(CHAPTERS[16], ""), flags=re.M)[1:]
    wave_fields = {}
    for section in wave_sections:
        match = re.search(r"^## \d+\. (R\d+) —", section)
        wave = match.group(1)
        section = re.split(r"^## \d+\. Role routing", section, flags=re.M)[0]
        fields = re.findall(r"^- \*\*([^*]+):\*\*", section, re.M)
        wave_fields[wave] = fields
        if fields != FIELDS:
            errors.append(wave + " fields differ from required17-field contract")
    if set(wave_fields) != {"R" + str(i) for i in range(12)}:
        errors.append("Wave set must be R0–R11")
    matrix = json.loads((ROOT / "appendices/TERMINAL_PRIMITIVE_MATRIX.json").read_text())
    variants = [r["id"] for r in matrix["rows"]]
    if variants != [f"F{i:02d}" for i in range(1, 41)]:
        errors.append("Primitive matrix must preserve F01–F40 exactly once")
    lit = re.findall(r"^\| \*\*([LMW]\d\d)\*\*", text.get(CHAPTERS[3], ""), re.M)
    expected_lit = {f"L{i:02d}" for i in range(1, 11)} | {f"M{i:02d}" for i in range(1, 13)} | {f"W{i:02d}" for i in range(17, 26)}
    if len(lit) != 31 or set(lit) != expected_lit:
        errors.append("Literature table set/uniqueness mismatch")
    index = json.loads((ROOT / "appendices/SOURCE_INDEX.json").read_text())
    source_ids = {r["id"] for key in ["internal_prior", "internal_terminal", "internal_radar_toi", "data_records", "external"] for r in index[key]}
    local_links = 0
    for path in ROOT.rglob("*.md"):
        if path.name == "LLR24_COMPLETE_REPORT.md":
            continue
        body = path.read_text()
        if len(re.findall(r"^```", body, re.M)) % 2:
            errors.append(str(path.relative_to(ROOT)) + ": unbalanced fenced block")
        for target in re.findall(r"\]\(([^)]+)\)", body):
            if re.match(r"(?:https?://|sandbox:|#|mailto:)", target):
                continue
            local_links += 1
            target = target.split("#", 1)[0]
            if not (path.parent / target).is_file():
                errors.append(str(path.relative_to(ROOT)) + ": unresolved local link " + target)
        for group in re.findall(r"\[([^]\n]+)\]", body):
            if re.search(r"(?:R|T|M|L):(?:D1|R1B|RVOL|intraday|ext-quote|TOI|live-cadence|DeepLOB|Gould|calibration|conformal|White|PBO|DSR)", group):
                errors.append(str(path.relative_to(ROOT)) + ": unresolved draft alias " + group)
            for source in re.findall(r"\b[PRTDLMW]\d{2}(?!\d)\b", group):
                if source not in source_ids:
                    errors.append(str(path.relative_to(ROOT)) + ": unknown source ID " + source)
    json_files = list(ROOT.rglob("*.json"))
    for path in json_files:
        try:
            json.loads(path.read_text())
        except (ValueError, UnicodeError) as exc:
            errors.append(str(path.relative_to(ROOT)) + ": invalid JSON " + str(exc))
    result = {
        "scope": "Report structural validation only; not an empirical market test or production acceptance",
        "status": "PASS" if not errors else "FAIL",
        "required_artifacts": len(CHAPTERS) - len(missing),
        "executive_questions": len(questions),
        "wave_contracts": len(wave_fields),
        "fields_per_wave": {k: len(v) for k, v in wave_fields.items()},
        "primitive_variants": len(variants), "literature_entries": len(lit),
        "registered_source_ids": len(source_ids), "json_files_parsed": len(json_files),
        "local_links_checked": local_links, "errors": errors,
    }
    if args.write:
        (ROOT / "appendices/PACKAGE_VALIDATION.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
