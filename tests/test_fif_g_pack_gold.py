"""Hermetic gold tests for the FIF G packs (G_PACK_BUILD_SPEC.md section 4).

Generic over issuers: packs are discovered under
``tests/fixtures/fundamental_forensics/g_pack/*/`` and every identity fact
(ticker, CIK, legal name, accession) is read from the pack manifests, the
committed g_src manifests and the D0 coverage contract -- this file carries no
issuer literal (a self-test below re-checks its own source against exactly that
data). Everything hermetic runs over committed bytes plus the repo's own
formula/mapping config; the one byte-level re-check of the staged filing bytes
is ``data_gate`` and skips unless ``FIF_GSRC_STAGE_ROOT`` is set.

Negative coverage: every pin type and every hermetic rule has a unit test over
a small synthetic in-memory pack (invented identity, no real issuer), so a pin
type this pack set does not yet use is still proven to refuse bad input.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import defaultdict
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

_REPO = Path(__file__).resolve().parents[1]
_G_PACK = _REPO / "tests" / "fixtures" / "fundamental_forensics" / "g_pack"
_G_SRC = _REPO / "tests" / "fixtures" / "fundamental_forensics" / "g_src"
_D0_PATH = _REPO / "config" / "fundamental_forensics" / "coverage" / "five_issuer_v1.json"
_FORMULAS_PATH = (
    _REPO / "config" / "fundamental_forensics" / "metrics" / "v1" / "formulas" / "core.yaml"
)
_METRIC_CATALOG_PATH = (
    _REPO / "config" / "fundamental_forensics" / "metrics" / "v1" / "metric_catalog.yaml"
)
_ISSUER_GROUPS_PATH = _REPO / "config" / "issuer_group_allowlist.yml"

PACK_FILES = {
    "pack_manifest.json",
    "gold_cells.jsonl",
    "expected_run_v1.json",
    "expected_financial_intelligence_packet_v1.json",
    "GOLD_SHEET.md",
}
NOT_GOLD = "kernel_minted_not_gold"
DRAFT_PLACEHOLDER = "PENDING" + "_G_PR"
NOT_APPLICABLE_CODE = "NOT_APPLICABLE"
_FORBIDDEN_WORD = "vali" + "dated"
_HISTORICAL_ATTESTATION = "unavailable_until_d2_admission"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ACCESSION_RE = re.compile(r"\d{10}-\d{2}-\d{6}")

# The R-G1 decimal contract the gold engine recorded on every formula row.
_RG1_CONTEXT = Context(
    prec=34,
    rounding=ROUND_HALF_EVEN,
    Emin=-6143,
    Emax=6144,
    capitals=1,
    clamp=0,
)

# Keys under which the kernel-minted not-gold placeholder may appear. Closed
# set: every id/digest field the kernel canonicalisation would mint.
_IDENTITY_KEYS = frozenset(
    {
        "canonical_bytes",
        "canonical_sha256",
        "run_id",
        "packet_id",
        "content_sha256",
        "governance_bundle_id",
        "packet_builder_digest",
        "companyfacts_witness_sha256",
        "filing_package_fixture_sha256",
        "query_request_digest",
        "submissions_witness_sha256",
        "cell_id",
        "source_digest",
        "mapping_rule_digest",
        "formula_rule_digest",
        "source_occurrence_ids",
        "dependency_cell_ids",
        "occurrence_id",
    }
)

PIN_TYPES = frozenset(
    {
        "kpi_vintages",
        "decimals_precision",
        "segment_as_filed",
        "negative_mapping",
        "scope_label",
        "errata_absence",
        "not_applicable_class",
        "dual_listing",
    }
)

TRACE_FIELDS = (
    "accession",
    "member_file",
    "member_sha256",
    "concept",
    "contextRef",
    "unitRef",
    "decimals",
)


# ---------------------------------------------------------------------------
# Data loading (issuer identity enters only through data)
# ---------------------------------------------------------------------------


def _pack_dirs() -> list[Path]:
    if not _G_PACK.is_dir():
        return []
    return sorted(p for p in _G_PACK.iterdir() if p.is_dir())


def _load_pack(pack_dir: Path) -> dict:
    return {
        "dir": pack_dir,
        "manifest": json.loads((pack_dir / "pack_manifest.json").read_text(encoding="utf-8")),
        "rows": _load_jsonl(pack_dir / "gold_cells.jsonl"),
        "run": json.loads((pack_dir / "expected_run_v1.json").read_text(encoding="utf-8")),
        "packet": json.loads(
            (pack_dir / "expected_financial_intelligence_packet_v1.json").read_text(
                encoding="utf-8"
            )
        ),
        "sheet": (pack_dir / "GOLD_SHEET.md").read_text(encoding="utf-8"),
    }


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _gsrc_issuer(cik10: str) -> dict:
    root = _G_SRC / cik10
    capture_index = json.loads((root / "capture_index.json").read_text(encoding="utf-8"))
    manifests = {
        row["accession"]: json.loads(
            (root / row["accession"] / "package_manifest.json").read_text(encoding="utf-8")
        )
        for row in capture_index
        if row.get("manifest_sha256")
    }
    return {"capture_index": capture_index, "manifests": manifests}


def _d0() -> dict:
    return json.loads(_D0_PATH.read_text(encoding="utf-8"))


def _d0_issuer_rows() -> list[dict]:
    return list(_d0()["issuers"])


def _issuer_group_members() -> dict[str, list[str]]:
    """Committed multi-listing issuer groups: cik10 -> listing keys (data, never literals)."""
    raw = yaml.safe_load(_ISSUER_GROUPS_PATH.read_text(encoding="utf-8")) or {}
    return {
        str(g.get("cik")).zfill(10): sorted(g.get("members") or [])
        for g in raw.get("groups") or []
    }


def _formulas() -> dict[str, dict]:
    raw = yaml.safe_load(_FORMULAS_PATH.read_text(encoding="utf-8"))
    return {f["metric_id"]: f for f in raw["formulas"]}


def _absence_vocabulary() -> frozenset[str]:
    """Closed no-result vocabulary from the shipped catalog (not a hand list)."""
    raw = yaml.safe_load(_METRIC_CATALOG_PATH.read_text(encoding="utf-8"))
    codes: set[str] = set()
    for metric in raw["metrics"]:
        codes.update(metric.get("no_result", {}).get("codes", []))
    # The unmapped refusal the packet builder emits for metrics outside the
    # governed catalog (engine/fundamental_forensics/financial_intelligence_packet.py:893).
    codes.add("unsupported_metric")
    return frozenset(codes)


def _metric_applicability() -> dict[str, dict[str, list[str]]]:
    """Per-metric issuer-class policy from the shipped catalog (not a hand list)."""
    raw = yaml.safe_load(_METRIC_CATALOG_PATH.read_text(encoding="utf-8"))
    out: dict[str, dict[str, list[str]]] = {}
    for metric in raw["metrics"]:
        policy = metric.get("applicability") or {}
        out[metric["metric_id"]] = {
            "applicable_classes": [str(c) for c in policy.get("applicable_classes") or []],
            "excluded_classes": [str(c) for c in policy.get("excluded_classes") or []],
        }
    return out


def _class_refuses(policy: dict[str, list[str]] | None, issuer_class: str | None) -> bool:
    """Mirror of the kernel applicability gate (metric_registry.py:397-399)."""
    if not policy or issuer_class is None:
        return False
    if issuer_class in policy["excluded_classes"]:
        return True
    return bool(policy["applicable_classes"]) and issuer_class not in policy["applicable_classes"]


def _metric_statement_families() -> dict[str, str]:
    raw = yaml.safe_load(_METRIC_CATALOG_PATH.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for metric in raw["metrics"]:
        constraints = metric.get("presentation_constraints") or {}
        if "statement" in constraints:
            out[metric["metric_id"]] = str(constraints["statement"])
    return out


# ---------------------------------------------------------------------------
# Hermetic rule checks (pure functions returning problem lists)
# ---------------------------------------------------------------------------


def check_closed_inventory(pack_dir: Path) -> list[str]:
    problems: list[str] = []
    files = sorted(p.name for p in pack_dir.iterdir() if p.is_file())
    for name in files:
        if name not in PACK_FILES:
            problems.append(f"unexpected file in pack: {name}")
    for name in sorted(PACK_FILES - set(files)):
        problems.append(f"missing pack file: {name}")
    for child in pack_dir.iterdir():
        if child.is_dir():
            problems.append(f"unexpected directory in pack: {child.name}")
    return problems


def check_identity(pack: dict, gsrc: dict, d0_rows: list[dict] | None = None) -> list[str]:
    problems: list[str] = []
    manifest = pack["manifest"]
    packet_entity = pack["packet"].get("entity", {})
    admitted = manifest.get("admitted_accessions") or []
    sampled = [gsrc["manifests"][a] for a in admitted if a in gsrc["manifests"]]
    if not sampled:
        problems.append("no admitted g_src manifest found for the pack identity check")
        return problems
    for field, packet_field in (
        ("entity_id", "entity_id"),
        ("legal_name", "name"),
    ):
        values = {m.get(field) for m in sampled}
        if len(values) != 1:
            problems.append(f"g_src manifests disagree on {field}")
        elif manifest.get(field) != values.pop():
            problems.append(f"manifest {field} differs from the g_src manifests")
        if packet_entity.get(packet_field) != manifest.get(field):
            problems.append(f"packet entity {packet_field} differs from the manifest")
    for field in ("security_ids", "listing_keys"):
        want = {m.get("security_id" if field == "security_ids" else "listing_key") for m in sampled}
        got = set(manifest.get(field) or [])
        if got != want:
            problems.append(f"manifest {field} {sorted(got)} != g_src {sorted(want)}")
    if packet_entity.get("cik") != manifest.get("cik10"):
        problems.append("packet entity cik differs from the manifest cik10")
    if pack["dir"].name.isdigit() and manifest.get("cik10") != pack["dir"].name:
        problems.append("pack directory name is not the cik10")
    rows = _d0_issuer_rows() if d0_rows is None else d0_rows
    d0_row = next(
        (r for r in rows if str(r.get("cik")).zfill(10) == manifest.get("cik10")),
        None,
    )
    if d0_row is None:
        problems.append("issuer is not in the D0 coverage contract")
    else:
        if manifest.get("issuer_class") != d0_row.get("issuer_class"):
            problems.append("manifest issuer_class differs from the D0 coverage contract")
        if manifest.get("legal_name") != d0_row.get("legal_name"):
            problems.append("manifest legal_name differs from the D0 coverage contract")
    return problems


def check_admitted_set(manifest: dict, gsrc: dict) -> list[str]:
    problems: list[str] = []
    admitted_rows = [
        row for row in gsrc["capture_index"] if row.get("admission") == "ADMITTED"
    ]
    expected = [
        row["accession"]
        for row in sorted(
            admitted_rows,
            key=lambda row: gsrc["manifests"][row["accession"]]["source_accepted_at"],
            reverse=True,
        )
    ]
    if list(manifest.get("admitted_accessions") or []) != expected:
        problems.append(
            "admitted_accessions != g_src capture_index ADMITTED rows newest first: "
            f"{manifest.get('admitted_accessions')} vs {expected}"
        )
    return problems


def check_view_a_admitted(rows: list[dict], manifest: dict) -> list[str]:
    admitted = set(manifest.get("admitted_accessions") or [])
    problems = []
    for row in rows:
        if row.get("view") == "as_filed" and row.get("source_accession") not in admitted:
            problems.append(
                f"View A row {row.get('metric_id')}/{row.get('period_label')} cites a "
                f"non-admitted accession {row.get('source_accession')}"
            )
    return problems


def check_direct_traces(rows: list[dict], gsrc: dict) -> list[str]:
    problems: list[str] = []
    member_digests: dict[tuple[str, str], str] = {}
    for accession, gman in gsrc["manifests"].items():
        for member in gman.get("members", []):
            if member.get("state") == "stored":
                member_digests[(accession, member["name"])] = member["content_sha256"]
    for row in rows:
        if row.get("verification_state") != "verified_from_bytes" or "trace" not in row:
            continue
        trace = row["trace"]
        for field in TRACE_FIELDS:
            if field not in trace or trace[field] in (None, ""):
                problems.append(
                    f"direct cell {row.get('metric_id')}/{row.get('period_label')} "
                    f"trace misses {field}"
                )
        digest = member_digests.get((trace.get("accession"), trace.get("member_file")))
        if digest is None:
            problems.append(
                f"direct cell {row.get('metric_id')} cites member "
                f"{trace.get('member_file')} not stored in the g_src manifest"
            )
        elif trace.get("member_sha256") != digest:
            problems.append(
                f"direct cell {row.get('metric_id')} member_sha256 differs from the "
                "g_src manifest digest"
            )
    return problems


def _row_join_index(rows: list[dict]) -> dict[tuple, dict]:
    index: dict[tuple, dict] = {}
    for row in rows:
        if row.get("view") == "as_filed":
            key = (
                "as_filed",
                row.get("source_accession") or "",
                row.get("metric_id"),
                tuple(row.get("period_key") or ()),
            )
        else:
            key = (
                row.get("view"),
                row.get("metric_id"),
                tuple(row.get("period_key") or ()),
            )
        if key in index:
            raise AssertionError(f"gold cell join key is not unique: {key}")
        index[key] = row
    return index


def _dependency_row(formula_row: dict, dep: str, index: dict[tuple, dict]) -> dict | None:
    dep_period = (
        formula_row.get("dep_periods", {}).get(dep, {}).get("dep_period")
        or formula_row.get("period_key")
    )
    if formula_row.get("view") == "as_filed":
        key = (
            "as_filed",
            formula_row.get("source_accession") or "",
            dep,
            tuple(dep_period or ()),
        )
    else:
        key = (formula_row.get("view"), dep, tuple(dep_period or ()))
    row = index.get(key)
    if row is not None:
        return row
    # A dependency the gold verified only inside the formula row (no standalone
    # cell exists for that period) counts only as an unvalued absence for the
    # exact expected period; a value always needs its own traced cell.
    embedded = (formula_row.get("dependency_cells") or {}).get(dep)
    if not isinstance(embedded, dict):
        return None
    if (
        embedded.get("metric_id") == dep
        and embedded.get("view") == formula_row.get("view")
        and list(embedded.get("period_key") or []) == list(dep_period or [])
        and (
            formula_row.get("view") != "as_filed"
            or (embedded.get("source_accession") or "")
            == (formula_row.get("source_accession") or "")
        )
        and embedded.get("verification_state")
        in ("typed_absence_verified", "not_applicable_verified")
        and embedded.get("value_exact") is None
        and embedded.get("code") in _absence_vocabulary()
    ):
        return embedded
    return None


def _rg1_evaluate(expression: str, values: dict[str, Decimal]) -> Decimal:
    """Left-to-right evaluation of the catalog's binary/ternary expressions."""
    tokens = expression.split()
    if not tokens or len(tokens) % 2 == 0:
        raise ValueError(f"unsupported expression shape: {expression!r}")
    with localcontext(_RG1_CONTEXT) as ctx:
        acc = ctx.plus(Decimal(str(values[tokens[0]])))
        for i in range(1, len(tokens), 2):
            op, operand = tokens[i], tokens[i + 1]
            rhs = ctx.plus(Decimal(str(values[operand])))
            if op == "+":
                acc = acc + rhs
            elif op == "-":
                acc = acc - rhs
            elif op == "/":
                acc = acc / rhs
            else:
                raise ValueError(f"unsupported operator {op!r} in {expression!r}")
        return ctx.plus(acc)


def check_formulas(rows: list[dict], formulas: dict[str, dict]) -> list[str]:
    problems: list[str] = []
    index = _row_join_index(rows)
    for row in rows:
        if "formula_rule_id" not in row:
            continue
        metric = row.get("metric_id")
        spec = formulas.get(metric)
        if spec is None:
            problems.append(f"formula metric {metric} has no repo formula definition")
            continue
        if row.get("formula_rule_id") != spec["rule"]["rule_id"]:
            problems.append(f"formula row {metric} rule id differs from the repo config")
        if list(row.get("dependencies") or []) != list(spec["dependencies"]):
            problems.append(f"formula row {metric} dependencies differ from the repo config")
        if row.get("dependency_period_alignment") != spec.get("dependency_period_alignment"):
            problems.append(
                f"formula row {metric} dependency_period_alignment differs from the repo config"
            )
        dep_values: dict[str, Decimal] = {}
        dep_absent: list[str] = []
        for dep in spec["dependencies"]:
            dep_row = _dependency_row(row, dep, index)
            if dep_row is None:
                problems.append(
                    f"formula row {metric}/{row.get('period_label')} dependency {dep} "
                    "has no gold cell"
                )
                continue
            if dep_row.get("verification_state") != "verified_from_bytes" or "value_exact" not in dep_row:
                dep_absent.append(dep)
            else:
                dep_values[dep] = Decimal(dep_row["value_exact"])
        valued = row.get("verification_state") == "verified_from_bytes" and "value_exact" in row
        if dep_absent:
            # E2: a formula is never derived from a partial input set.
            if valued:
                problems.append(
                    f"E2 violation: formula row {metric}/{row.get('period_label')} is "
                    f"valued while dependencies are absent: {sorted(dep_absent)}"
                )
            elif row.get("code") != "missing_dependency":
                problems.append(
                    f"formula absence {metric}/{row.get('period_label')} must carry "
                    f"code missing_dependency, got {row.get('code')!r}"
                )
            continue
        if not valued:
            continue
        try:
            result = _rg1_evaluate(spec["expression"], dep_values)
        except ZeroDivisionError:
            if row.get("code") != "division_by_zero":
                problems.append(
                    f"formula row {metric}/{row.get('period_label')} divides by zero but "
                    f"carries code {row.get('code')!r}"
                )
            continue
        if Decimal(row["value_exact"]) != result:
            problems.append(
                f"formula row {metric}/{row.get('period_label')} value "
                f"{row['value_exact']} does not recompute ({result}) under the R-G1 contract"
            )
    return problems


def check_absences(rows: list[dict], issuer_class: str | None = None) -> list[str]:
    problems: list[str] = []
    vocabulary = _absence_vocabulary()
    applicability = _metric_applicability()
    for row in rows:
        state = row.get("verification_state")
        if state in ("typed_absence_verified", "not_applicable_verified"):
            if row.get("value_exact") is not None:
                problems.append(
                    f"absence row {row.get('metric_id')}/{row.get('period_label')} carries "
                    f"a value {row.get('value_exact')!r}"
                )
            code = row.get("code")
            if code == NOT_APPLICABLE_CODE:
                # The issuer-class refusal (query.py:2822 CellState.NOT_APPLICABLE):
                # admitted only where the catalog policy refuses the manifest class.
                if state != "not_applicable_verified" or not _class_refuses(
                    applicability.get(row.get("metric_id")), issuer_class
                ):
                    problems.append(
                        f"absence row {row.get('metric_id')}/{row.get('period_label')} code "
                        f"{code!r} needs not_applicable_verified and a catalog applicability "
                        f"refusal of issuer class {issuer_class!r}"
                    )
            elif code not in vocabulary:
                problems.append(
                    f"absence row {row.get('metric_id')}/{row.get('period_label')} code "
                    f"{code!r} is outside the repo no-result vocabulary"
                )
            if code == "0" or row.get("value_exact") == "0":
                problems.append(
                    f"absence row {row.get('metric_id')}/{row.get('period_label')} is a "
                    "zero stand-in, not a typed absence"
                )
        elif state == "verified_from_bytes":
            if row.get("value_exact") in (None, "") and "trace" in row:
                problems.append(
                    f"valued row {row.get('metric_id')}/{row.get('period_label')} has no value"
                )
    return problems


def check_attestation(pack: dict) -> list[str]:
    problems: list[str] = []
    if pack["manifest"].get("attested") is not False:
        problems.append("manifest attested is not false")
    if pack["manifest"].get("historical_attestation") != _HISTORICAL_ATTESTATION:
        problems.append("manifest historical_attestation is not the D2-until string")
    for name, doc in (("run", pack["run"]), ("packet", pack["packet"])):
        if doc.get("attested") is not False:
            problems.append(f"{name} attested is not false")
        if doc.get("historical_attestation") != _HISTORICAL_ATTESTATION:
            problems.append(f"{name} historical_attestation is not the D2-until string")
    for row in pack["rows"]:
        if row.get("attested") is not False:
            problems.append("a gold cell row carries attested != false")
            break
        if row.get("historical_attestation") != _HISTORICAL_ATTESTATION:
            problems.append("a gold cell row carries the wrong historical_attestation")
            break
    if pack["dir"].is_dir():
        for path in pack["dir"].iterdir():
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                if _FORBIDDEN_WORD in text:
                    problems.append(f"forbidden word present in {path.name}")
    return problems


def check_no_specialist(pack: dict) -> list[str]:
    problems: list[str] = []

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "specialist_pack_result":
                    problems.append(f"specialist_pack_result envelope at {path}")
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")

    for name, doc in (("manifest", pack["manifest"]), ("run", pack["run"]), ("packet", pack["packet"])):
        walk(doc, name)
    if "specialist_pack_result" in pack["sheet"]:
        for line in pack["sheet"].splitlines():
            if (
                "specialist_pack_result" in line
                and not re.search(r"\bno\b|\bnot\b|never|absence|without", line, re.I)
            ):
                problems.append("GOLD_SHEET.md asserts a specialist_pack_result envelope")
                break
    return problems


def _check_not_gold_placement(node, path: str, problems: list[str], key: str | None = None) -> None:
    if isinstance(node, dict):
        for child_key, value in node.items():
            if value == NOT_GOLD and child_key not in _IDENTITY_KEYS:
                problems.append(
                    f"kernel-minted placeholder under non-identity key {path}.{child_key}"
                )
            _check_not_gold_placement(value, f"{path}.{child_key}", problems, child_key)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            if item == NOT_GOLD and key not in _IDENTITY_KEYS:
                problems.append(
                    f"kernel-minted placeholder under non-identity key {path}[{i}]"
                )
            _check_not_gold_placement(item, f"{path}[{i}]", problems, key)


def check_pending_and_not_gold(pack: dict) -> list[str]:
    problems: list[str] = []

    def walk_strings(node, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk_strings(value, f"{path}.{key}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk_strings(item, f"{path}[{i}]")
        elif isinstance(node, str) and node == DRAFT_PLACEHOLDER:
            problems.append(f"draft placeholder remains at {path}")

    for name, doc in (
        ("manifest", pack["manifest"]),
        ("run", pack["run"]),
        ("packet", pack["packet"]),
    ):
        walk_strings(doc, name)
    if pack["dir"].is_dir():
        for path in pack["dir"].iterdir():
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                if DRAFT_PLACEHOLDER in text:
                    problems.append(f"draft placeholder remains in {path.name}")
    for name, doc in (("run", pack["run"]), ("packet", pack["packet"])):
        _check_not_gold_placement(doc, name, problems)
    return problems


def check_pins(pack: dict, metric_families: dict[str, str]) -> list[str]:
    problems: list[str] = []
    manifest = pack["manifest"]
    rows = pack["rows"]
    index = _row_join_index(rows)
    for pin in manifest.get("pins") or []:
        kind = pin.get("type")
        if kind not in PIN_TYPES:
            problems.append(f"unknown pin type {kind!r}")
            continue
        if not pin.get("ruling"):
            problems.append(f"pin {kind} carries no ruling reference")
        problems.extend(_check_pin(kind, pin, manifest, rows, index, metric_families))
    return problems


def _check_pin(
    kind: str,
    pin: dict,
    manifest: dict,
    rows: list[dict],
    index: dict[tuple, dict],
    metric_families: dict[str, str],
    issuer_groups: dict[str, list[str]] | None = None,
) -> list[str]:
    problems: list[str] = []
    if kind == "kpi_vintages":
        if pin.get("splice_refused") is not True:
            problems.append("kpi_vintages pin does not refuse splicing")
        vintages = pin.get("vintages") or []
        for vintage in vintages:
            for field in ("accession", "member_file", "member_sha256", "byte_offset", "row_label", "value"):
                if vintage.get(field) in (None, ""):
                    problems.append(f"kpi_vintages entry misses {field}")
            if not _HEX64.fullmatch(str(vintage.get("member_sha256") or "")):
                problems.append("kpi_vintages member_sha256 is not a sha256 hex digest")
        admitted_values = [
            v["value"] for v in vintages if v.get("admitted") is True
        ]
        if len(admitted_values) < 2 or len(set(admitted_values)) < 2:
            problems.append(
                "kpi_vintages gate needs >=2 admitted vintages with different values"
            )
        if not pin.get("metric_label"):
            problems.append("kpi_vintages pin misses metric_label")
    elif kind == "decimals_precision":
        for field in (
            "concept",
            "period_key",
            "source_accession",
            "contextRef",
            "value_exact",
            "decimals",
            "member_file",
            "member_sha256",
            "byte_offset",
        ):
            if pin.get(field) in (None, ""):
                problems.append(f"decimals_precision pin misses {field}")
        if not _HEX64.fullmatch(str(pin.get("member_sha256") or "")):
            problems.append("decimals_precision member_sha256 is not a sha256 hex digest")
        if str(pin.get("decimals", "x")).lstrip("-").isdigit() is False:
            problems.append("decimals_precision decimals is not an integer string")
    elif kind == "segment_as_filed":
        consolidated = pin.get("consolidated") or {}
        if not consolidated.get("trace"):
            # The consolidated value must be the filing's own fact, never the sum.
            problems.append("segment_as_filed consolidated value lacks its own trace")
        for segment in pin.get("segments") or []:
            for field in ("member", "value", "trace"):
                if segment.get(field) in (None, ""):
                    problems.append(f"segment_as_filed segment misses {field}")
        if not (pin.get("period_key") and pin.get("source_accession")):
            problems.append("segment_as_filed pin misses period_key/source_accession")
    elif kind == "negative_mapping":
        metric = pin.get("metric_id")
        forbidden = pin.get("forbidden_concept")
        if not metric or not forbidden:
            problems.append("negative_mapping pin misses metric_id/forbidden_concept")
            return problems
        for row in rows:
            trace = row.get("trace") or {}
            if row.get("metric_id") == metric and trace.get("concept") == forbidden:
                problems.append(
                    f"negative_mapping violated: a gold cell for {metric} cites {forbidden}"
                )
    elif kind == "scope_label":
        families = set(pin.get("statement_families") or [])
        label = pin.get("label")
        if not families or not label:
            problems.append("scope_label pin misses statement_families/label")
            return problems
        for row in rows:
            family = metric_families.get(row.get("metric_id", ""))
            if family in families and row.get("scope_label") != label:
                problems.append(
                    f"scope_label violated: {row.get('metric_id')}/{row.get('period_label')} "
                    f"carries scope_label {row.get('scope_label')!r} instead of {label!r}"
                )
    elif kind == "errata_absence":
        metric = pin.get("metric_id")
        code = pin.get("code")
        if not metric or not code:
            problems.append("errata_absence pin misses metric_id/code")
            return problems
        matching = [r for r in rows if r.get("metric_id") == metric]
        if not any(r.get("code") == code for r in matching):
            problems.append(
                f"errata_absence pin: no gold cell for {metric} carries code {code}"
            )
        if any(r.get("verification_state") == "verified_from_bytes" for r in matching):
            problems.append(
                f"errata_absence pin: {metric} has a valued gold cell, so the typed "
                "absence the errata pins does not hold"
            )
        candidate = pin.get("candidate_concept")
        if candidate:
            for row in matching:
                if (row.get("trace") or {}).get("concept") == candidate:
                    problems.append(
                        f"errata_absence pin: a gold cell for {metric} cites the "
                        f"not-aliased candidate {candidate}"
                    )
    elif kind == "not_applicable_class":
        if manifest.get("issuer_class") != pin.get("issuer_class"):
            problems.append("not_applicable_class pin issuer_class differs from the manifest")
            return problems
        for metric in pin.get("metric_ids") or []:
            matching = [r for r in rows if r.get("metric_id") == metric]
            if not matching:
                problems.append(f"not_applicable_class metric {metric} has no gold cells")
            for row in matching:
                if row.get("verification_state") not in (
                    "not_applicable_verified",
                    "typed_absence_verified",
                ):
                    problems.append(
                        f"not_applicable_class violated: {metric}/{row.get('period_label')} "
                        f"is {row.get('verification_state')}, not a class-based absence"
                    )
    elif kind == "dual_listing":
        # The pin's listings are the committed issuer group for this cik10 (data). The
        # captured listing(s) recorded in the g_src manifests must be members of it:
        # every listing in the group projects onto the same issuer packet.
        keys = sorted(pin.get("listing_keys") or [])
        groups = _issuer_group_members() if issuer_groups is None else issuer_groups
        group = groups.get(str(manifest.get("cik10")))
        if len(keys) < 2:
            problems.append("dual_listing pin needs at least two listings")
        if group is None:
            problems.append("dual_listing pin has no committed issuer group for the manifest cik10")
        elif keys != sorted(group):
            problems.append("dual_listing pin listing_keys differ from the committed issuer group")
        if not set(manifest.get("listing_keys") or []) <= set(keys):
            problems.append("dual_listing pin does not cover the manifest listing_keys")
    return problems


def check_packet_agreement(pack: dict) -> list[str]:
    problems: list[str] = []
    basis = pack["manifest"].get("packet_basis") or {}
    rows_by_period: dict[tuple, dict] = {}
    for row in pack["rows"]:
        if row.get("view") != basis.get("view") or row.get("source_accession") != basis.get("source_accession"):
            continue
        period = row.get("period_key") or []
        if len(period) == 3:
            kind, start, end = period[0], period[1], period[2]
        elif len(period) == 2:
            kind, start, end = period[0], None, period[1]
        else:
            kind, start, end = None, None, None
        key = (row.get("metric_id"), kind, start, end)
        if key in rows_by_period:
            raise AssertionError(f"packet-agreement join key is not unique: {key}")
        rows_by_period[key] = row
    seen_cells: set[tuple] = set()
    for cell in pack["packet"].get("cells") or []:
        period_obj = cell.get("period") or {}
        key = (
            cell.get("metric_id"),
            period_obj.get("kind"),
            period_obj.get("start"),
            period_obj.get("end"),
        )
        if key in seen_cells:
            raise AssertionError(f"packet cell period key is not unique: {key}")
        seen_cells.add(key)
        row = rows_by_period.get(key)
        if row is None:
            # M5: a packet cell whose join key has no gold row is a problem,
            # not a silent skip -- the packet must not exceed the gold.
            problems.append(f"packet cell {key} has no gold row")
            continue
        if cell.get("provenance_kind") == "direct":
            trace = row.get("trace") or {}
            if cell.get("concept") and cell["concept"] != trace.get("concept"):
                problems.append(f"packet cell {key} concept differs from the gold cell")
            if cell.get("accession") and cell["accession"] != trace.get("accession"):
                problems.append(f"packet cell {key} accession differs from the gold cell")
        if row.get("verification_state") == "verified_from_bytes":
            if cell.get("value") is None or Decimal(str(cell["value"])) != Decimal(row["value_exact"]):
                problems.append(f"packet cell {key} value differs from the gold cell")
        else:
            if cell.get("value") is not None:
                problems.append(f"packet cell {key} is valued while the gold cell is not")
    return problems


# M7: the closed correction-basis rule set. Each ruling maps to the evidence
# alternatives that satisfy it (outer tuple = alternatives, inner = conjuncts).
_CORRECTION_EVIDENCE_RULES: dict[str, tuple[tuple[str, ...], ...]] = {
    "R-G-2": (("byte_reread",), ("dependency_rows",)),
    "R-G-4": (("catalog", "coverage"),),
    "R-G-5": (("byte_confirm", "filed_location"),),
}
_NUMERIC_CORRECTION_FIELDS = frozenset({"value_exact", "value"})


def _correction_metric(entry: dict):
    """row_key.metric_id for gold corrections, cell.metric_id for packet ones."""
    row_key = entry.get("row_key")
    if isinstance(row_key, dict) and row_key.get("metric_id"):
        return row_key.get("metric_id")
    cell = entry.get("cell")
    if isinstance(cell, dict):
        return cell.get("metric_id")
    return None


def check_correction_basis(pack: dict) -> list[str]:
    """M7: every gold/packet correction needs an admissible ruling basis.

    R-G-2 needs a byte reread or the dependency rows; R-G-4 (class closure)
    needs the catalog policy and the coverage contract, may never correct a
    numeric field, must set verification_state to not_applicable_verified,
    and its metric must be one the catalog refuses for the manifest issuer
    class (checked against the shipped catalog, not trusted from prose);
    R-G-5 needs a byte confirm plus the filed location. An R-G-4
    evidence.kernel_observation / evidence.kernel value is a classification
    input only -- it never satisfies the rule on its own.
    """
    problems: list[str] = []
    applicability = _metric_applicability()
    issuer_class = pack["manifest"].get("issuer_class")
    for list_name in ("gold_corrections", "packet_corrections"):
        for entry in pack["manifest"].get(list_name) or []:
            if not isinstance(entry, dict):
                problems.append(f"{list_name} entry is not an object")
                continue
            ruling = entry.get("ruling")
            label = f"{ruling!r} on {_correction_metric(entry)!r}.{entry.get('field')}"
            alternatives = _CORRECTION_EVIDENCE_RULES.get(ruling)
            if alternatives is None:
                problems.append(f"correction {label} carries an unknown ruling")
                continue
            evidence = entry.get("evidence")
            if not isinstance(evidence, dict):
                evidence = {}
            if not any(
                all(evidence.get(key) for key in required) for required in alternatives
            ):
                problems.append(
                    f"correction {label} lacks the evidence its ruling requires "
                    f"({' or '.join(' and '.join(required) for required in alternatives)})"
                )
            if ruling == "R-G-4":
                field = entry.get("field")
                if field in _NUMERIC_CORRECTION_FIELDS:
                    problems.append(
                        f"correction {label} is class-closure only but corrects "
                        f"the numeric field {field!r}"
                    )
                if field == "verification_state" and entry.get(
                    "corrected_value"
                ) != "not_applicable_verified":
                    problems.append(
                        f"correction {label} must set verification_state to "
                        "not_applicable_verified"
                    )
                if not _class_refuses(
                    applicability.get(_correction_metric(entry)), issuer_class
                ):
                    problems.append(
                        f"correction {label} is not refused by the catalog for "
                        f"issuer class {issuer_class!r}"
                    )
    return problems


def _all_pack_problems(pack: dict) -> list[str]:
    gsrc = _gsrc_issuer(pack["manifest"]["cik10"])
    problems: list[str] = []
    problems += check_closed_inventory(pack["dir"])
    problems += check_identity(pack, gsrc)
    problems += check_admitted_set(pack["manifest"], gsrc)
    problems += check_view_a_admitted(pack["rows"], pack["manifest"])
    problems += check_direct_traces(pack["rows"], gsrc)
    problems += check_formulas(pack["rows"], _formulas())
    problems += check_absences(pack["rows"], pack["manifest"].get("issuer_class"))
    problems += check_attestation(pack)
    problems += check_no_specialist(pack)
    problems += check_pending_and_not_gold(pack)
    problems += check_pins(pack, _metric_statement_families())
    problems += check_packet_agreement(pack)
    problems += check_correction_basis(pack)
    return problems


# ---------------------------------------------------------------------------
# Pack tests
# ---------------------------------------------------------------------------

_PACKS = _pack_dirs()

pytestmark = pytest.mark.skipif(not _PACKS, reason="no g_pack fixtures committed yet")


@pytest.mark.parametrize("pack_dir", _PACKS, ids=lambda p: p.name)
def test_pack_hermetic_rules(pack_dir: Path) -> None:
    pack = _load_pack(pack_dir)
    problems = _all_pack_problems(pack)
    assert not problems, "\n".join(problems)


def test_packs_discovered_and_closed() -> None:
    assert _PACKS, "g_pack root exists but holds no issuer packs"
    for pack_dir in _PACKS:
        assert re.fullmatch(r"\d{10}", pack_dir.name), pack_dir.name


# ---------------------------------------------------------------------------
# Self-test: this file carries no issuer identity literal
# ---------------------------------------------------------------------------


def _identity_literals() -> dict[str, list[str]]:
    literals: dict[str, list[str]] = {"ticker": [], "cik": [], "name": [], "entity": [], "accession": []}
    for row in _d0_issuer_rows():
        literals["ticker"].append(str(row["ticker"]))
        literals["cik"].extend([str(row["cik"]), str(row["cik"]).zfill(10)])
        literals["name"].append(str(row["legal_name"]))
        binding = row.get("security_master_binding") or {}
        for field in ("issuer_id", "security_id", "listing_key"):
            if binding.get(field):
                literals["entity"].append(str(binding[field]))
    for pack_dir in _pack_dirs():
        manifest = json.loads((pack_dir / "pack_manifest.json").read_text(encoding="utf-8"))
        literals["cik"].append(str(manifest["cik10"]))
        literals["name"].append(str(manifest["legal_name"]))
        for field in ("entity_id",):
            literals["entity"].append(str(manifest[field]))
        literals["entity"].extend(manifest.get("security_ids") or [])
        literals["entity"].extend(manifest.get("listing_keys") or [])
        literals["accession"].extend(manifest.get("admitted_accessions") or [])
        literals["accession"].append(manifest["packet_basis"]["source_accession"])
        for pin in manifest.get("pins") or []:
            for vintage in pin.get("vintages") or []:
                literals["accession"].append(vintage["accession"])
            if pin.get("source_accession"):
                literals["accession"].append(pin["source_accession"])
    for kind in literals:
        literals[kind] = sorted(set(literals[kind]))
    return literals


_GENERIC_NAME_TOKENS = frozenset(
    {"bank", "of", "america", "corp", "inc", "the", "company", "corporation", "de"}
)


def test_own_source_carries_no_issuer_identity() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    literals = _identity_literals()
    for ticker in literals["ticker"]:
        assert not re.search(rf"\b{re.escape(ticker)}\b", source), f"ticker literal: {ticker}"
    for cik in literals["cik"]:
        assert not re.search(rf"\b{re.escape(cik)}\b", source), f"CIK literal: {cik}"
    for name in literals["name"]:
        assert name not in source, f"legal-name literal: {name}"
        for token in re.findall(r"[A-Za-z]{5,}", name):
            if token.lower() in _GENERIC_NAME_TOKENS:
                continue
            assert not re.search(rf"\b{token}\b", source), f"company-name token literal: {token}"
    for entity in literals["entity"]:
        assert entity not in source, f"entity-id literal: {entity}"
    for accession in literals["accession"]:
        assert accession not in source, f"accession literal: {accession}"
    assert not _ACCESSION_RE.search(source), "accession-shaped literal in source"
    assert _FORBIDDEN_WORD not in source


# ---------------------------------------------------------------------------
# Negative unit tests over a synthetic in-memory pack (invented identity)
# ---------------------------------------------------------------------------

_SYN_CIK = "0000099999"
_SYN_A = "synthetic-accession-alpha"
_SYN_B = "synthetic-accession-beta"
_SYN_SHA_A = "a" * 64
_SYN_SHA_B = "b" * 64


def _synthetic_gsrc() -> dict:
    def manifest(accepted: str, member: str, sha: str) -> dict:
        return {
            "entity_id": "ISS:US-XTEST-ZZ",
            "legal_name": "Zyx Testworks Inc.",
            "security_id": "SEC:US-XTEST-ZZ",
            "listing_key": "US-XTEST-ZZ",
            "source_accepted_at": accepted,
            "members": [
                {"name": member, "state": "stored", "content_sha256": sha, "role": "primary"}
            ],
        }

    return {
        "capture_index": [
            {"accession": _SYN_A, "admission": "ADMITTED"},
            {"accession": _SYN_B, "admission": "ADMITTED"},
            {"accession": "synthetic-accession-capture", "admission": "not_admitted:capture_only"},
        ],
        "manifests": {
            _SYN_A: manifest("2026-09-01T00:00:00.000Z", "doc-alpha.htm", _SYN_SHA_A),
            _SYN_B: manifest("2026-03-01T00:00:00.000Z", "doc-beta.htm", _SYN_SHA_B),
        },
    }


def _synthetic_rows() -> list[dict]:
    base = {
        "view": "as_filed",
        "source_accession": _SYN_A,
        "knowledge_time": "2026-09-01T00:00:00.000Z",
        "knowledge_time_source": "sec_submissions_witness.json:acceptanceDateTime",
        "attested": False,
        "historical_attestation": _HISTORICAL_ATTESTATION,
    }
    revenue = dict(
        base,
        metric_id="revenue",
        period_key=["duration", "2026-01-01", "2026-12-31"],
        period_label="FY2026",
        verification_state="verified_from_bytes",
        mapping_rule_id="mapping.revenue/v1",
        concept="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        value_exact="2000",
        trace={
            "accession": _SYN_A,
            "member_file": "doc-alpha.htm",
            "member_sha256": _SYN_SHA_A,
            "concept": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            "contextRef": "c-1",
            "unitRef": "usd",
            "decimals": "-3",
            "scale": "0",
            "sign": None,
            "format": "ixt:num-dot-decimal",
        },
    )
    gross_profit = dict(
        revenue,
        metric_id="gross_profit",
        period_label="FY2026",
        mapping_rule_id="mapping.gross_profit/v1",
        concept="us-gaap:GrossProfit",
        value_exact="700",
    )
    gross_profit["trace"] = dict(revenue["trace"], concept="us-gaap:GrossProfit")
    gross_margin = dict(
        base,
        metric_id="gross_margin",
        period_key=["duration", "2026-01-01", "2026-12-31"],
        period_label="FY2026",
        verification_state="verified_from_bytes",
        formula_rule_id="formula.gross_margin/v1",
        expression="gross_profit / revenue",
        dependencies=["gross_profit", "revenue"],
        dependency_period_alignment="same_period",
        dep_periods={
            "gross_profit": {
                "output_period": ["duration", "2026-01-01", "2026-12-31"],
                "dep_period": ["duration", "2026-01-01", "2026-12-31"],
                "alignment": "same_period",
                "dep_kind": "duration",
            },
            "revenue": {
                "output_period": ["duration", "2026-01-01", "2026-12-31"],
                "dep_period": ["duration", "2026-01-01", "2026-12-31"],
                "alignment": "same_period",
                "dep_kind": "duration",
            },
        },
        value_exact="0.35",
        unit="ratio",
        provenance="formula",
        decimal_contract="R-G1 prec=34 ROUND_HALF_EVEN Emin=-6143 Emax=6144 capitals=1",
    )
    total_debt_dep = dict(
        base,
        metric_id="short_term_debt",
        period_key=["instant", "2026-12-31"],
        period_label="2026-12-31",
        verification_state="typed_absence_verified",
        mapping_rule_id="mapping.short_term_debt/v1",
        code="missing_standard_fact",
        r1_code="MISSING_CONCEPT",
        detail="synthetic zero-hit",
    )
    total_debt = dict(
        base,
        metric_id="total_debt",
        period_key=["instant", "2026-12-31"],
        period_label="2026-12-31",
        verification_state="typed_absence_verified",
        formula_rule_id="formula.total_debt/v1",
        expression="short_term_debt + long_term_debt_current + long_term_debt",
        dependencies=["short_term_debt", "long_term_debt_current", "long_term_debt"],
        dependency_period_alignment="same_period",
        dep_periods={
            dep: {
                "output_period": ["instant", "2026-12-31"],
                "dep_period": ["instant", "2026-12-31"],
                "alignment": "same_period",
                "dep_kind": "instant",
            }
            for dep in ("short_term_debt", "long_term_debt_current", "long_term_debt")
        },
        code="missing_dependency",
        r1_code="MISSING_DEPENDENCY",
        missing_inputs=[
            {
                "dependency": "short_term_debt",
                "state": "typed_absence_verified",
                "code": "missing_standard_fact",
                "dep_period": ["instant", "2026-12-31"],
            }
        ],
    )
    long_term_debt = dict(
        base,
        metric_id="long_term_debt",
        period_key=["instant", "2026-12-31"],
        period_label="2026-12-31",
        verification_state="typed_absence_verified",
        mapping_rule_id="mapping.long_term_debt/v1",
        code="missing_standard_fact",
        r1_code="MISSING_CONCEPT",
        detail="synthetic zero-hit",
    )
    long_term_debt_current = dict(long_term_debt, metric_id="long_term_debt_current")
    return [
        revenue,
        gross_profit,
        gross_margin,
        total_debt_dep,
        total_debt,
        long_term_debt,
        long_term_debt_current,
    ]


def _synthetic_manifest(pins: list[dict] | None = None) -> dict:
    return {
        "schema": "fif.g_pack/v1",
        "cik10": _SYN_CIK,
        "entity_id": "ISS:US-XTEST-ZZ",
        "legal_name": "Zyx Testworks Inc.",
        "security_ids": ["SEC:US-XTEST-ZZ"],
        "listing_keys": ["US-XTEST-ZZ"],
        "issuer_class": "software",
        "attested": False,
        "historical_attestation": _HISTORICAL_ATTESTATION,
        "admission_state": "admitted",
        "admitted_accessions": [_SYN_A, _SYN_B],
        "packet_basis": {
            "view": "as_filed",
            "source_accession": _SYN_A,
            "knowledge_time": "2026-09-01T00:00:00.000Z",
            "knowledge_time_source": "sec_submissions_witness.json:acceptanceDateTime",
        },
        "pins": pins if pins is not None else _synthetic_pins(),
        "gold_corrections": [],
        "defects": [],
    }


def _synthetic_pins() -> list[dict]:
    return [
        {
            "type": "kpi_vintages",
            "ruling": "synthetic",
            "metric_label": "Synthetic count",
            "vintages": [
                {
                    "accession": _SYN_A,
                    "admitted": True,
                    "member_file": "doc-alpha.htm",
                    "member_sha256": _SYN_SHA_A,
                    "byte_offset": 10,
                    "row_label": "Synthetic count",
                    "value": "41",
                },
                {
                    "accession": _SYN_B,
                    "admitted": True,
                    "member_file": "doc-beta.htm",
                    "member_sha256": _SYN_SHA_B,
                    "byte_offset": 20,
                    "row_label": "Synthetic count",
                    "value": "39",
                },
            ],
            "splice_refused": True,
        },
        {
            "type": "decimals_precision",
            "ruling": "synthetic",
            "concept": "us-gaap:SyntheticObligation",
            "period_key": ["instant", "2026-12-31"],
            "source_accession": _SYN_A,
            "contextRef": "c-2",
            "value_exact": "9000000000",
            "decimals": "-8",
            "scale": "9",
            "member_file": "doc-alpha.htm",
            "member_sha256": _SYN_SHA_A,
            "byte_offset": 30,
        },
        {
            "type": "negative_mapping",
            "ruling": "synthetic",
            "metric_id": "long_term_debt",
            "forbidden_concept": "us-gaap:SyntheticDebtNoncurrent",
        },
        {
            "type": "errata_absence",
            "ruling": "synthetic",
            "errata": "R3",
            "metric_id": "long_term_debt",
            "code": "missing_standard_fact",
        },
    ]


def _synthetic_packet() -> dict:
    return {
        "schema": "financial_intelligence_packet.v1",
        "packet_id": NOT_GOLD,
        "content_sha256": NOT_GOLD,
        "attested": False,
        "historical_attestation": _HISTORICAL_ATTESTATION,
        "view": "as_filed",
        "source_accession": _SYN_A,
        "entity": {
            "cik": _SYN_CIK,
            "entity_id": "ISS:US-XTEST-ZZ",
            "name": "Zyx Testworks Inc.",
        },
        "cells": [
            {
                "metric_id": "revenue",
                "period": {
                    "label": "FY2026",
                    "kind": "duration",
                    "start": "2026-01-01",
                    "end": "2026-12-31",
                },
                "provenance_kind": "direct",
                "value": "2000",
                "concept": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
                "accession": _SYN_A,
                "cell_id": NOT_GOLD,
                "source_digest": NOT_GOLD,
                "source_occurrence_ids": [NOT_GOLD],
            },
            {
                "metric_id": "short_term_debt",
                "period": {
                    "label": "2026-12-31",
                    "kind": "instant",
                    "start": None,
                    "end": "2026-12-31",
                },
                "provenance_kind": "none",
                "value": None,
            },
        ],
        "limitations": ["synthetic"],
    }


def _synthetic_pack(
    rows: list[dict] | None = None,
    manifest: dict | None = None,
    packet: dict | None = None,
    run: dict | None = None,
) -> dict:
    return {
        "dir": Path("/synthetic-pack"),
        "manifest": manifest or _synthetic_manifest(),
        "rows": rows if rows is not None else _synthetic_rows(),
        "run": run or _synthetic_run(),
        "packet": packet or _synthetic_packet(),
        "sheet": "# synthetic gold sheet\n",
    }


def _synthetic_run() -> dict:
    return {
        "schema": "fif.expected_run/v1",
        "canonical_bytes": NOT_GOLD,
        "canonical_sha256": NOT_GOLD,
        "run_id": NOT_GOLD,
        "attested": False,
        "historical_attestation": _HISTORICAL_ATTESTATION,
        "finding_states": {
            "accruals_trending_up": "not_evaluable",
            "capital_intensity_rising": "not_evaluable",
            "inventory_build": "not_evaluable",
            "margin_compression_despite_revenue_growth": "not_evaluable",
            "receivables_stretch": "not_evaluable",
        },
    }


_SYN_D0_ROWS = [
    {
        "ticker": "ZZTEST",
        "cik": "99999",
        "legal_name": "Zyx Testworks Inc.",
        "issuer_class": "software",
    }
]


def test_synthetic_pack_passes_every_hermetic_rule() -> None:
    """The synthetic pack is well formed under every checker used on real packs."""
    pack = _synthetic_pack()
    gsrc = _synthetic_gsrc()
    assert not check_identity(pack, gsrc, _SYN_D0_ROWS)
    assert not check_admitted_set(pack["manifest"], gsrc)
    assert not check_view_a_admitted(pack["rows"], pack["manifest"])
    assert not check_direct_traces(pack["rows"], gsrc)
    assert not check_formulas(pack["rows"], _formulas())
    assert not check_absences(pack["rows"])
    assert not check_no_specialist(pack)
    assert not check_pins(pack, _metric_statement_families())
    assert not check_packet_agreement(pack)
    assert not check_correction_basis(pack)
    problems = check_pending_and_not_gold(pack)
    assert not problems, problems


def test_negative_closed_inventory(tmp_path: Path) -> None:
    for name in PACK_FILES:
        (tmp_path / name).write_text("{}", encoding="utf-8")
    (tmp_path / "extra.txt").write_text("x", encoding="utf-8")
    problems = check_closed_inventory(tmp_path)
    assert any("unexpected file" in p for p in problems)
    (tmp_path / "extra.txt").unlink()
    (tmp_path / "pack_manifest.json").unlink()
    problems = check_closed_inventory(tmp_path)
    assert any("missing pack file" in p for p in problems)


def test_negative_identity_mismatch() -> None:
    gsrc = _synthetic_gsrc()
    packet = _synthetic_packet()
    packet["entity"]["name"] = "Another Name Inc."
    problems = check_identity(_synthetic_pack(packet=packet), gsrc, _SYN_D0_ROWS)
    assert any("packet entity name" in p for p in problems)
    manifest = _synthetic_manifest()
    manifest["issuer_class"] = "bank"
    problems = check_identity(_synthetic_pack(manifest=manifest), gsrc, _SYN_D0_ROWS)
    assert any("issuer_class differs from the D0 coverage contract" in p for p in problems)
    manifest = _synthetic_manifest()
    manifest["cik10"] = "0000088888"
    problems = check_identity(_synthetic_pack(manifest=manifest), gsrc, _SYN_D0_ROWS)
    assert any("not in the D0 coverage contract" in p for p in problems)


def test_negative_admitted_set_and_view_a() -> None:
    gsrc = _synthetic_gsrc()
    manifest = _synthetic_manifest()
    manifest["admitted_accessions"] = [_SYN_A]
    problems = check_admitted_set(manifest, gsrc)
    assert any("admitted_accessions" in p for p in problems)
    rows = _synthetic_rows()
    rows[0]["source_accession"] = "synthetic-accession-capture"
    problems = check_view_a_admitted(rows, _synthetic_manifest())
    assert any("non-admitted accession" in p for p in problems)


def test_negative_trace_completeness() -> None:
    gsrc = _synthetic_gsrc()
    rows = _synthetic_rows()
    rows[0]["trace"].pop("member_sha256")
    problems = check_direct_traces(rows, gsrc)
    assert any("trace misses member_sha256" in p for p in problems)
    rows = _synthetic_rows()
    rows[0]["trace"]["member_sha256"] = "c" * 64
    problems = check_direct_traces(rows, gsrc)
    assert any("member_sha256 differs" in p for p in problems)


def test_negative_formula_recompute_and_e2() -> None:
    rows = _synthetic_rows()
    rows[2]["value_exact"] = "0.5"
    problems = check_formulas(rows, _formulas())
    assert any("does not recompute" in p for p in problems)
    # E2: total_debt valued while a dependency is a typed absence.
    rows = _synthetic_rows()
    total_debt = rows[3 + 1]
    total_debt.pop("code")
    total_debt.pop("missing_inputs")
    total_debt["verification_state"] = "verified_from_bytes"
    total_debt["value_exact"] = "100"
    problems = check_formulas(rows, _formulas())
    assert any("E2 violation" in p for p in problems)
    # A formula row whose dependency has no gold cell at all.
    rows = _synthetic_rows()
    rows[3]["metric_id"] = "something_else"
    problems = check_formulas(rows, _formulas())
    assert any("dependency short_term_debt has no gold cell" in p for p in problems)
    # An absence formula that carries the wrong code.
    rows = _synthetic_rows()
    rows[3 + 1]["code"] = "missing_standard_fact"
    problems = check_formulas(rows, _formulas())
    assert any("must carry code missing_dependency" in p for p in problems)


def test_negative_absence_vocabulary() -> None:
    rows = _synthetic_rows()
    rows[3]["code"] = "made_up_code"
    problems = check_absences(rows)
    assert any("outside the repo no-result vocabulary" in p for p in problems)
    rows = _synthetic_rows()
    rows[3]["value_exact"] = "0"
    problems = check_absences(rows)
    assert any("carries a value" in p for p in problems)


def test_absence_not_applicable_requires_catalog_class_refusal() -> None:
    applicability = _metric_applicability()
    metric, policy = next(
        (m, p)
        for m, p in sorted(applicability.items())
        if p["excluded_classes"] and not p["applicable_classes"]
    )
    refused = policy["excluded_classes"][0]
    row = {
        "view": "as_filed",
        "metric_id": metric,
        "period_label": "2026-12-31",
        "verification_state": "not_applicable_verified",
        "code": NOT_APPLICABLE_CODE,
    }
    assert not check_absences([row], refused)
    assert any("catalog applicability refusal" in p for p in check_absences([row], None))
    assert any(
        "catalog applicability refusal" in p
        for p in check_absences([row], refused + "_synthetic_other")
    )
    wrong_state = dict(row, verification_state="typed_absence_verified")
    assert any("catalog applicability refusal" in p for p in check_absences([wrong_state], refused))
    unknown_metric = dict(row, metric_id="synthetic_metric_outside_catalog")
    assert any(
        "catalog applicability refusal" in p for p in check_absences([unknown_metric], refused)
    )
    # Default-inert metrics never earn the class refusal.
    inert = next(m for m, p in sorted(applicability.items()) if not any(p.values()))
    assert any(
        "catalog applicability refusal" in p
        for p in check_absences([dict(row, metric_id=inert)], refused)
    )


def test_orphan_dependency_cell_counts_only_as_an_absence() -> None:
    rows = _synthetic_rows()
    dep = rows.pop(3)  # short_term_debt; total_debt now has no standalone dependency cell
    formula_row = next(r for r in rows if r.get("metric_id") == "total_debt")
    assert any("dependency short_term_debt has no gold cell" in p for p in check_formulas(rows, _formulas()))
    formula_row["dependency_cells"] = {"short_term_debt": dict(dep)}
    assert not check_formulas(rows, _formulas())
    # Wrong period: the embedded cell must sit on the expected dependency period.
    formula_row["dependency_cells"] = {
        "short_term_debt": dict(dep, period_key=["instant", "2025-12-31"])
    }
    assert any("has no gold cell" in p for p in check_formulas(rows, _formulas()))
    # A valued embedded cell never substitutes for a traced standalone cell.
    formula_row["dependency_cells"] = {
        "short_term_debt": dict(dep, verification_state="verified_from_bytes", value_exact="5")
    }
    assert any("has no gold cell" in p for p in check_formulas(rows, _formulas()))
    # A different accession's embedded cell does not count for an as-filed row.
    formula_row["dependency_cells"] = {
        "short_term_debt": dict(dep, source_accession="synthetic-accession-other")
    }
    assert any("has no gold cell" in p for p in check_formulas(rows, _formulas()))


def test_negative_attestation_and_specialist() -> None:
    manifest = _synthetic_manifest()
    manifest["attested"] = True
    problems = check_attestation(_synthetic_pack(manifest=manifest))
    # The synthetic dir has no files on disk; the row-level check fires first.
    assert any("attested" in p for p in problems)
    packet = _synthetic_packet()
    packet["specialist_pack_result"] = {"pk": "unspecified"}
    problems = check_no_specialist(_synthetic_pack(packet=packet))
    assert any("specialist_pack_result" in p for p in problems)


def test_negative_pending_and_not_gold_placement() -> None:
    run = _synthetic_run()
    run["run_id"] = DRAFT_PLACEHOLDER
    problems = check_pending_and_not_gold(_synthetic_pack(run=run))
    assert any("draft placeholder" in p for p in problems)
    packet = _synthetic_packet()
    packet["limitations"] = [NOT_GOLD]
    problems = check_pending_and_not_gold(_synthetic_pack(packet=packet))
    assert any("non-identity key" in p for p in problems)


def test_negative_pin_kpi_vintages() -> None:
    pins = _synthetic_pins()
    pins[0]["vintages"][1]["value"] = "41"  # two admitted vintages, same value
    problems = check_pins(_synthetic_pack(manifest=_synthetic_manifest(pins)), _metric_statement_families())
    assert any("admitted vintages with different values" in p for p in problems)
    pins = _synthetic_pins()
    pins[0]["splice_refused"] = False
    problems = check_pins(_synthetic_pack(manifest=_synthetic_manifest(pins)), _metric_statement_families())
    assert any("does not refuse splicing" in p for p in problems)
    pins = _synthetic_pins()
    pins[0]["vintages"][0].pop("byte_offset")
    problems = check_pins(_synthetic_pack(manifest=_synthetic_manifest(pins)), _metric_statement_families())
    assert any("misses byte_offset" in p for p in problems)


def test_negative_pin_decimals_precision() -> None:
    pins = _synthetic_pins()
    pins[1].pop("decimals")
    problems = check_pins(_synthetic_pack(manifest=_synthetic_manifest(pins)), _metric_statement_families())
    assert any("misses decimals" in p for p in problems)
    pins = _synthetic_pins()
    pins[1]["member_sha256"] = "not-a-sha"
    problems = check_pins(_synthetic_pack(manifest=_synthetic_manifest(pins)), _metric_statement_families())
    assert any("not a sha256" in p for p in problems)


def test_negative_pin_segment_as_filed() -> None:
    pin = {
        "type": "segment_as_filed",
        "ruling": "synthetic",
        "period_key": ["duration", "2026-01-01", "2026-12-31"],
        "source_accession": _SYN_A,
        "segments": [{"member": "seg-a", "value": "60", "trace": {"concept": "x"}}],
        "consolidated": {"value": "100", "trace": None},
        "reconciling_items": [],
    }
    problems = _check_pin("segment_as_filed", pin, _synthetic_manifest(), _synthetic_rows(), {}, _metric_statement_families())
    assert any("consolidated value lacks its own trace" in p for p in problems)
    pin["consolidated"]["trace"] = {"concept": "us-gaap:Revenues"}
    pin["segments"][0].pop("trace")
    problems = _check_pin("segment_as_filed", pin, _synthetic_manifest(), _synthetic_rows(), {}, _metric_statement_families())
    assert any("segment misses trace" in p for p in problems)


def test_negative_pin_negative_mapping() -> None:
    rows = _synthetic_rows()
    rows[5]["verification_state"] = "verified_from_bytes"
    rows[5]["value_exact"] = "500"
    rows[5]["trace"] = {
        "accession": _SYN_A,
        "member_file": "doc-alpha.htm",
        "member_sha256": _SYN_SHA_A,
        "concept": "us-gaap:SyntheticDebtNoncurrent",
        "contextRef": "c-9",
        "unitRef": "usd",
        "decimals": "-3",
    }
    problems = check_pins(_synthetic_pack(rows=rows), _metric_statement_families())
    assert any("negative_mapping violated" in p for p in problems)


def test_negative_pin_scope_label() -> None:
    pin = {
        "type": "scope_label",
        "ruling": "synthetic",
        "statement_families": ["income_statement"],
        "label": "consolidated (synthetic)",
    }
    problems = _check_pin("scope_label", pin, _synthetic_manifest(), _synthetic_rows(), {}, _metric_statement_families())
    # revenue is an income_statement metric in the shipped catalog and carries
    # no scope_label, so the pin must refuse.
    assert any("scope_label violated" in p for p in problems)
    rows = _synthetic_rows()
    for row in rows:
        if row["metric_id"] in ("revenue", "gross_profit"):
            row["scope_label"] = "consolidated (synthetic)"
    problems = _check_pin("scope_label", pin, _synthetic_manifest(), rows, {}, _metric_statement_families())
    assert not problems, problems


def test_negative_pin_errata_absence() -> None:
    pins = _synthetic_pins()
    pins[3]["code"] = "missing_dependency"  # no long_term_debt row carries it
    problems = check_pins(_synthetic_pack(manifest=_synthetic_manifest(pins)), _metric_statement_families())
    assert any("no gold cell for long_term_debt carries code" in p for p in problems)
    rows = _synthetic_rows()
    rows[5]["verification_state"] = "verified_from_bytes"
    rows[5]["value_exact"] = "500"
    problems = check_pins(_synthetic_pack(rows=rows), _metric_statement_families())
    assert any("has a valued gold cell" in p for p in problems)


def test_negative_pin_not_applicable_class() -> None:
    pin = {
        "type": "not_applicable_class",
        "ruling": "synthetic",
        "issuer_class": "bank",
        "metric_ids": ["gross_profit"],
    }
    manifest = _synthetic_manifest()
    problems = _check_pin("not_applicable_class", pin, manifest, _synthetic_rows(), {}, _metric_statement_families())
    assert any("issuer_class differs" in p for p in problems)
    pin["issuer_class"] = "software"
    problems = _check_pin("not_applicable_class", pin, manifest, _synthetic_rows(), {}, _metric_statement_families())
    assert any("not a class-based absence" in p for p in problems)


def test_negative_pin_dual_listing() -> None:
    pin = {
        "type": "dual_listing",
        "ruling": "synthetic",
        "listing_keys": ["US-XTEST-ZZ", "US-XTEST-ZZ2"],
    }
    fams = _metric_statement_families()
    group = {_SYN_CIK: ["US-XTEST-ZZ", "US-XTEST-ZZ2"]}
    assert _check_pin("dual_listing", pin, _synthetic_manifest(), _synthetic_rows(), {}, fams, group) == []
    problems = _check_pin(
        "dual_listing", pin, _synthetic_manifest(), _synthetic_rows(), {}, fams,
        {_SYN_CIK: ["US-XTEST-ZZ", "US-XTEST-ZZ3"]},
    )
    assert any("differ from the committed issuer group" in p for p in problems)
    problems = _check_pin("dual_listing", pin, _synthetic_manifest(), _synthetic_rows(), {}, fams, {})
    assert any("no committed issuer group" in p for p in problems)
    other = dict(pin, listing_keys=["US-XTEST-ZZ2", "US-XTEST-ZZ3"])
    problems = _check_pin(
        "dual_listing", other, _synthetic_manifest(), _synthetic_rows(), {}, fams,
        {_SYN_CIK: ["US-XTEST-ZZ2", "US-XTEST-ZZ3"]},
    )
    assert any("does not cover the manifest listing_keys" in p for p in problems)
    pin["listing_keys"] = ["US-XTEST-ZZ"]
    problems = _check_pin("dual_listing", pin, _synthetic_manifest(), _synthetic_rows(), {}, fams, group)
    assert any("needs at least two listings" in p for p in problems)


def test_negative_packet_agreement() -> None:
    packet = _synthetic_packet()
    packet["cells"][0]["value"] = "2001"
    problems = check_packet_agreement(_synthetic_pack(packet=packet))
    assert any("value differs from the gold cell" in p for p in problems)
    packet = _synthetic_packet()
    packet["cells"][1]["value"] = "7"
    problems = check_packet_agreement(_synthetic_pack(packet=packet))
    assert any("is valued while the gold cell is not" in p for p in problems)
    # M5: a packet cell whose join key has no gold row is a problem.
    packet = _synthetic_packet()
    packet["cells"].append(
        {
            "metric_id": "operating_income",
            "period": {
                "label": "FY2026",
                "kind": "duration",
                "start": "2026-01-01",
                "end": "2026-12-31",
            },
            "provenance_kind": "direct",
            "value": "310",
        }
    )
    problems = check_packet_agreement(_synthetic_pack(packet=packet))
    assert any("has no gold row" in p for p in problems)


def _class_refused_metric() -> tuple[str, str]:
    """A catalog metric and a class its own policy refuses (data, no literals)."""
    applicability = _metric_applicability()
    metric, policy = next(
        (m, p)
        for m, p in sorted(applicability.items())
        if p["excluded_classes"] and not p["applicable_classes"]
    )
    return metric, policy["excluded_classes"][0]


def _syn_gold_correction(
    ruling: str, field: str, corrected, evidence: dict, metric: str
) -> dict:
    return {
        "row_key": {
            "view": "as_filed",
            "source_accession": _SYN_A,
            "metric_id": metric,
            "period_key": ["duration", "2026-01-01", "2026-12-31"],
        },
        "field": field,
        "op": "set",
        "r2_value": "prior",
        "corrected_value": corrected,
        "evidence": evidence,
        "ruling": ruling,
    }


def _correction_basis_problems(
    gold: list[dict], packet_corr: list[dict] | None = None, issuer_class: str | None = None
) -> list[str]:
    manifest = _synthetic_manifest()
    if issuer_class is not None:
        manifest["issuer_class"] = issuer_class
    manifest["gold_corrections"] = gold
    manifest["packet_corrections"] = packet_corr or []
    return check_correction_basis(_synthetic_pack(manifest=manifest))


def test_negative_correction_basis() -> None:
    """M7: every correction needs an admissible ruling + evidence basis."""
    metric, refused = _class_refused_metric()
    inert = next(
        m for m, p in sorted(_metric_applicability().items()) if not any(p.values())
    )

    def entry(ruling, field, corrected, evidence, metric_id=metric):
        return _syn_gold_correction(ruling, field, corrected, evidence, metric_id)

    problems = _correction_basis_problems(
        [entry("R-G-9", "code", "x", {"byte_reread": "r"})]
    )
    assert any("unknown ruling" in p for p in problems)
    # R-G-2 with only kr_ids: neither a byte reread nor dependency rows.
    problems = _correction_basis_problems(
        [entry("R-G-2", "code", "x", {"kr_ids": ["kr"]})]
    )
    assert any("lacks the evidence" in p for p in problems)
    # R-G-4 missing coverage; a kernel observation never substitutes for it.
    problems = _correction_basis_problems(
        [entry("R-G-4", "code", "NOT_APPLICABLE",
               {"catalog": "policy", "kernel_observation": "kr"})],
        issuer_class=refused,
    )
    assert any("lacks the evidence" in p for p in problems)
    # R-G-4 is class-closure only: it may never correct a numeric field.
    problems = _correction_basis_problems(
        [entry("R-G-4", "value_exact", "5", {"catalog": "p", "coverage": "c"})],
        issuer_class=refused,
    )
    assert any("numeric field" in p for p in problems)
    # R-G-4 whose metric the catalog does not refuse for the class.
    problems = _correction_basis_problems(
        [entry("R-G-4", "verification_state", "not_applicable_verified",
               {"catalog": "p", "coverage": "c"}, metric_id=inert)],
        issuer_class=refused,
    )
    assert any("not refused by the catalog" in p for p in problems)
    # R-G-4 on verification_state must set not_applicable_verified.
    problems = _correction_basis_problems(
        [entry("R-G-4", "verification_state", "typed_absence_verified",
               {"catalog": "p", "coverage": "c"})],
        issuer_class=refused,
    )
    assert any("not_applicable_verified" in p for p in problems)
    # R-G-5 missing filed_location.
    problems = _correction_basis_problems(
        [entry("R-G-5", "value_exact", "5", {"byte_confirm": "bytes"})]
    )
    assert any("lacks the evidence" in p for p in problems)


def test_correction_basis_accepts_each_ruling() -> None:
    """M7 positive: one admissible entry of each ruling passes, packet side too."""
    metric, refused = _class_refused_metric()
    manifest = _synthetic_manifest()
    manifest["issuer_class"] = refused
    manifest["gold_corrections"] = [
        _syn_gold_correction(
            "R-G-2", "code", "disallowed_dimension",
            {"byte_reread": "staged reread", "kr_ids": ["kr"]}, metric,
        ),
        _syn_gold_correction(
            "R-G-4", "verification_state", "not_applicable_verified",
            {"catalog": "policy", "coverage": "contract", "kernel": "classification input"},
            metric,
        ),
        _syn_gold_correction(
            "R-G-5", "value_exact", "4",
            {"byte_confirm": "bytes", "filed_location": {"member_file": "doc-alpha.htm"}},
            metric,
        ),
    ]
    manifest["packet_corrections"] = [
        {
            "cell": {
                "metric_id": metric,
                "kind": "duration",
                "start": "2026-01-01",
                "end": "2026-12-31",
            },
            "field": "non_value_state",
            "op": "set",
            "r2_value": "missing_dependency",
            "corrected_value": "not_applicable",
            "evidence": {
                "catalog": "policy",
                "coverage": "contract",
                "kernel": "classification input",
            },
            "ruling": "R-G-4",
        }
    ]
    assert not check_correction_basis(_synthetic_pack(manifest=manifest))


def test_negative_unknown_pin_type() -> None:
    pins = _synthetic_pins()
    pins.append({"type": "brand_new_pin", "ruling": "synthetic"})
    problems = check_pins(_synthetic_pack(manifest=_synthetic_manifest(pins)), _metric_statement_families())
    assert any("unknown pin type" in p for p in problems)


# ---------------------------------------------------------------------------
# data_gate: byte-level re-check over the staged filing bytes
# ---------------------------------------------------------------------------


class _InlineXbrlFinder(HTMLParser):
    """Collects ix:nonFraction / ix:nonNumeric elements by concept+contextRef.

    Nested wrappers (the basic-equals-diluted rendering pattern) inherit the
    innermost element's text. Attribute names arrive lowercased from
    html.parser, so unitRef/xsi:nil are read as unitref/xsi:nil.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.matches: list[dict] = []
        self._stack: list[dict] = []

    def handle_starttag(self, tag, attrs) -> None:
        attrs_dict = dict(attrs)
        if tag in ("ix:nonfraction", "ix:nonnumeric"):
            entry = {
                "name": attrs_dict.get("name"),
                "ctx": attrs_dict.get("contextref"),
                "unitref": attrs_dict.get("unitref"),
                "decimals": attrs_dict.get("decimals"),
                "scale": attrs_dict.get("scale"),
                "sign": attrs_dict.get("sign"),
                "format": attrs_dict.get("format"),
                "xsi:nil": attrs_dict.get("xsi:nil"),
                "text": [],
                "kids": [],
            }
            if self._stack:
                self._stack[-1]["kids"].append(entry)
            self._stack.append(entry)
        elif self._stack:
            self._stack[-1]["depth"] = self._stack[-1].get("depth", 1) + 1

    def handle_endtag(self, tag) -> None:
        if self._stack:
            entry = self._stack[-1]
            entry["depth"] = entry.get("depth", 1) - 1
            if entry["depth"] <= 0:
                self._stack.pop()
                self.matches.append(entry)

    def handle_data(self, data) -> None:
        if self._stack:
            self._stack[-1]["text"].append(data)


def _effective_text(entry: dict) -> str:
    own = "".join(entry["text"]).strip()
    if own:
        return own
    for kid in entry["kids"]:
        text = _effective_text(kid)
        if text:
            return text
    return ""


def _ix_value(entry: dict) -> Decimal:
    # A nil fact carries no value at all (xsi:nil compares case-insensitively;
    # html.parser lowercases the attribute name to xsi:nil).
    if str(entry.get("xsi:nil") or "").strip().lower() == "true":
        raise ValueError("nil fact")
    # ixt:fixed-zero states an explicit filed zero whatever glyph is displayed
    # (Inline XBRL Transformation Registry); it is a filed value, not an
    # absence. Any other non-numeric text -- including empty text -- still
    # fails Decimal parsing.
    if (entry.get("format") or "").rsplit(":", 1)[-1] == "fixed-zero":
        return Decimal(0)
    text = (
        _effective_text(entry)
        .replace(",", "")
        .replace("\xa0", "")
        .replace("$", "")
        .replace(" ", "")
        .strip()
    )
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    value = Decimal(text)
    if entry.get("scale"):
        value = value * (Decimal(10) ** int(entry["scale"]))
    if entry.get("sign") == "-":
        value = -value
    return value


def test_ix_value_fixed_zero_transform_only() -> None:
    """A dash is a filed zero only under the fixed-zero transform."""
    import decimal

    dash = {"text": ["\u2014"], "kids": [], "scale": "3", "sign": None}
    assert _ix_value({**dash, "format": "ixt:fixed-zero"}) == Decimal(0)
    assert _ix_value({**dash, "format": "ixt-sec:fixed-zero"}) == Decimal(0)
    with pytest.raises(decimal.InvalidOperation):
        _ix_value({**dash, "format": "ixt:num-dot-decimal"})
    with pytest.raises(decimal.InvalidOperation):
        _ix_value(dash)


def test_ix_value_nil_fact_has_no_value() -> None:
    """M3: a nil element never reads as zero, whatever text it renders."""
    import decimal

    nil_entry = {"text": ["0"], "kids": [], "scale": None, "sign": None, "xsi:nil": "true"}
    with pytest.raises(ValueError, match="nil fact"):
        _ix_value(nil_entry)
    # The comparison is case-insensitive.
    with pytest.raises(ValueError, match="nil fact"):
        _ix_value({**nil_entry, "xsi:nil": "TRUE"})
    # Nil wins even under the fixed-zero transform: there is no filed value.
    with pytest.raises(ValueError, match="nil fact"):
        _ix_value({**nil_entry, "format": "ixt:fixed-zero"})
    # An empty element (no text of its own and no nested text) is not zero
    # either; only the fixed-zero transform may state a bare zero.
    empty = {"text": [], "kids": [], "scale": None, "sign": None}
    with pytest.raises(decimal.InvalidOperation):
        _ix_value(empty)
    with pytest.raises(decimal.InvalidOperation):
        _ix_value({**empty, "text": ["   "]})
    assert _ix_value({**empty, "format": "ixt:fixed-zero"}) == Decimal(0)


def test_inline_finder_records_nil_unitref_and_decimals() -> None:
    """M3/M4 groundwork: the parser keeps xsi:nil, unitref and decimals."""
    html = (
        '<ix:nonFraction name="us-gaap:Revenues" contextRef="c-1" unitRef="usd" '
        'decimals="-3" scale="3" sign="-" format="ixt:num-dot-decimal" '
        'xsi:nil="true">0</ix:nonFraction>'
    )
    finder = _InlineXbrlFinder()
    finder.feed(html)
    finder.close()
    assert len(finder.matches) == 1
    entry = finder.matches[0]
    assert entry["unitref"] == "usd"
    assert entry["decimals"] == "-3"
    assert entry["xsi:nil"] == "true"
    with pytest.raises(ValueError, match="nil fact"):
        _ix_value(entry)


def _parse_member(path: Path) -> dict[tuple[str, str], list[dict]]:
    parser = _InlineXbrlFinder()
    parser.feed(path.read_bytes().decode("utf-8", "replace"))
    parser.close()
    index: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for entry in parser.matches:
        index[(entry["name"], entry["ctx"])].append(entry)
    return index


def _trace_attr_matches(entry_value, trace_value) -> bool:
    """Attribute agreement between a staged element and the gold trace.

    A null trace value matches an attribute the element does not carry; any
    other value must be equal (compared as strings: scale/decimals may be
    recorded as int or text on either side).
    """
    if trace_value is None:
        return entry_value is None
    if entry_value is None:
        return False
    return str(entry_value) == str(trace_value)


def _byte_candidates_agree(index: dict, trace: dict, want: Decimal) -> str | None:
    """M4: the staged bytes must agree with the gold value on the traced fact.

    The candidate set is the elements indexed under (trace.concept,
    trace.contextRef) whose unitref, decimals, scale, sign and format all
    equal the trace's values. The check passes only when that set is
    non-empty and every candidate's value equals ``want`` -- inline XBRL
    legitimately repeats a fact, so equal duplicates are fine, but an
    unequal duplicate in the same concept, context and unit is a problem.
    Returns the problem message, or None when the bytes agree.
    """
    candidates = [
        entry
        for entry in index.get((trace.get("concept"), trace.get("contextRef")), [])
        if _trace_attr_matches(entry.get("unitref"), trace.get("unitRef"))
        and _trace_attr_matches(entry.get("decimals"), trace.get("decimals"))
        and _trace_attr_matches(entry.get("scale"), trace.get("scale"))
        and _trace_attr_matches(entry.get("sign"), trace.get("sign"))
        and _trace_attr_matches(entry.get("format"), trace.get("format"))
    ]
    where = (
        f"{trace.get('concept')} @ {trace.get('contextRef')} unit "
        f"{trace.get('unitRef')} decimals {trace.get('decimals')} scale "
        f"{trace.get('scale')} sign {trace.get('sign')} format {trace.get('format')}"
    )
    if not candidates:
        return f"no staged element matches {where}"
    values = [_ix_value(entry) for entry in candidates]
    if any(value != want for value in values):
        distinct = sorted({str(value) for value in values})
        return f"staged values {distinct} at {where} disagree with the gold value {want}"
    return None


def _syn_ix_entry(text: str, **attrs) -> dict:
    """A staged-element record shaped exactly like _InlineXbrlFinder output."""
    entry = {
        "name": "us-gaap:Revenues",
        "ctx": "c-1",
        "unitref": "usd",
        "decimals": "-3",
        "scale": "0",
        "sign": None,
        "format": "ixt:num-dot-decimal",
        "xsi:nil": None,
        "text": [text],
        "kids": [],
    }
    entry.update(attrs)
    return entry


_SYN_TRACE = {
    "concept": "us-gaap:Revenues",
    "contextRef": "c-1",
    "unitRef": "usd",
    "decimals": "-3",
    "scale": "0",
    "sign": None,
    "format": "ixt:num-dot-decimal",
}


def _syn_index(*entries: dict) -> dict:
    return {("us-gaap:Revenues", "c-1"): list(entries)}


def test_byte_candidates_agree_ignores_wrong_unit_or_decimals() -> None:
    """M4: only the traced fact counts -- a same-value wrong-unit element does not."""
    wrong_unit = _syn_index(_syn_ix_entry("700", unitref="usdPerShare"))
    problem = _byte_candidates_agree(wrong_unit, _SYN_TRACE, Decimal("700"))
    assert problem is not None and "no staged element matches" in problem
    wrong_decimals = _syn_index(_syn_ix_entry("700", decimals="-6"))
    problem = _byte_candidates_agree(wrong_decimals, _SYN_TRACE, Decimal("700"))
    assert problem is not None and "no staged element matches" in problem


def test_byte_candidates_agree_rejects_inconsistent_duplicate() -> None:
    """M4: an unequal duplicate under the same concept, context and unit fails."""
    inconsistent = _syn_index(_syn_ix_entry("700"), _syn_ix_entry("800"))
    problem = _byte_candidates_agree(inconsistent, _SYN_TRACE, Decimal("700"))
    assert problem is not None
    assert "700" in problem and "800" in problem


def test_byte_candidates_agree_accepts_consistent_duplicate() -> None:
    """M4: inline XBRL legitimately repeats a fact; equal duplicates agree."""
    consistent = _syn_index(_syn_ix_entry("700"), _syn_ix_entry("700.0"))
    assert _byte_candidates_agree(consistent, _SYN_TRACE, Decimal("700")) is None
    assert _byte_candidates_agree(_syn_index(_syn_ix_entry("700")), _SYN_TRACE, Decimal("700")) is None


@pytest.mark.data_gate
def test_staged_bytes_match_gold_cells_and_pins() -> None:
    stage_root = os.environ.get("FIF_GSRC_STAGE_ROOT")
    if not stage_root:
        pytest.skip("FIF_GSRC_STAGE_ROOT is not set; staged bytes are not present")
    stage = Path(stage_root).expanduser()
    packs = _pack_dirs()
    assert packs, "no committed g_pack fixtures to check against"
    parsed: dict[tuple[str, str], dict] = {}
    for pack_dir in packs:
        pack = _load_pack(pack_dir)
        manifest = pack["manifest"]
        cik10 = manifest["cik10"]
        gsrc = _gsrc_issuer(cik10)
        member_digests: dict[tuple[str, str], str] = {}
        for accession, gman in gsrc["manifests"].items():
            for member in gman.get("members", []):
                if member.get("state") == "stored":
                    member_digests[(accession, member["name"])] = member["content_sha256"]
        for row in pack["rows"]:
            if row.get("verification_state") != "verified_from_bytes" or "trace" not in row:
                continue
            trace = row["trace"]
            member_path = stage / cik10 / trace["accession"] / "members" / trace["member_file"]
            payload = member_path.read_bytes()
            assert hashlib.sha256(payload).hexdigest() == trace["member_sha256"], (
                row["metric_id"],
                trace["member_file"],
            )
            key = (trace["accession"], trace["member_file"])
            if key not in parsed:
                parsed[key] = _parse_member(member_path)
            want = Decimal(row["value_exact"])
            problem = _byte_candidates_agree(parsed[key], trace, want)
            assert problem is None, (
                f"{row['metric_id']} / {row.get('period_key')}: {problem}"
            )
        for pin in manifest.get("pins") or []:
            if pin.get("type") == "kpi_vintages":
                for vintage in pin["vintages"]:
                    member_path = (
                        stage / cik10 / vintage["accession"] / "members" / vintage["member_file"]
                    )
                    payload = member_path.read_bytes()
                    assert (
                        hashlib.sha256(payload).hexdigest() == vintage["member_sha256"]
                    ), vintage["accession"]
                    window = payload[vintage["byte_offset"] : vintage["byte_offset"] + 4096]
                    label_text = _html_text(window.decode("utf-8", "replace"))
                    assert vintage["row_label"].rstrip("0123456789()") .strip() in label_text or (
                        vintage["row_label"] in label_text
                    ), f"row label not at byte_offset in {vintage['accession']}"
                    value_offset = vintage.get("value_byte_offset")
                    if value_offset is None:
                        assert vintage["value"] in label_text.split(), (
                            f"value {vintage['value']} not in the row window"
                        )
                    else:
                        value_window = payload[value_offset : value_offset + 64]
                        assert re.match(
                            rb"^\s*[><0-9]", value_window
                        ) and vintage["value"].encode() in value_window, (
                            f"value {vintage['value']} not at value_byte_offset in "
                            f"{vintage['accession']}"
                        )


def _html_text(raw: str) -> str:
    class _Text(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []

        def handle_data(self, data) -> None:
            self.parts.append(data)

    parser = _Text()
    parser.feed(raw)
    return " ".join(" ".join(parser.parts).split())
