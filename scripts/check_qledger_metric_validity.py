"""
scripts/check_qledger_metric_validity.py — Universal Scoreboard metric-validity gate.

Audits the qledger claim/grade corpus for the three ways a reader can compute an
impressive-looking number that does not mean what it appears to mean. The
invariants, their evidence, and why each is silent are documented in
:mod:`engine.qledger_validity`.

WARN-TIER BY DEFAULT — AND WHY (deliberate, not an oversight)
-------------------------------------------------------------
The findings this gate emits are PRE-EXISTING CONDITIONS of the corpus, not
regressions introduced by any one PR. On the 2026-08-12 store it reports on the
majority of families the moment it is wired. Shipping it as a hard gate would
red main on day one for a property no PR author caused, which is how a guard
gets disabled instead of obeyed (`DNR` precedent: a gate that fires fleet-wide
is routed around, not satisfied).

So: default exit 0 with ``::warning`` annotations. ``--strict`` exits 1 and is
the intended CI mode ONCE the emitters listed in
``research/MASTERMIND_INTELLIGENCE_OS_V1_PLAN.md`` T3 stop publishing the
invalid readings. Flipping the default is a one-word change and a deliberate act.

Annotations are emitted with a bare ``print`` and ``flush=True`` per CLAUDE.md
§"GitHub annotations must START the line" — a logger would prefix the line and
GitHub would silently drop it.

Usage
-----
  python scripts/check_qledger_metric_validity.py [--root PATH] [--strict]
  python scripts/check_qledger_metric_validity.py --selftest
  python scripts/check_qledger_metric_validity.py --project-findings INPUT.json

Options
-------
  --root PATH   Repo root holding data/qledger/{claims,grades}.jsonl
                (default: parent of scripts/).
  --strict      Exit 1 when any finding has severity 'invalid'.
  --json        Emit a JSON object to stdout instead of annotations. ALWAYS an
                object, never a bare list: {store_absent, missing, claims,
                grades, findings}. When the store is absent, `findings` is null
                rather than [] — an empty list would render "could not look" as
                "looked and clean" (standards §9.2).
  --selftest    Inject synthetic corpora proving the auditor catches each
                invariant AND stays silent on a clean corpus. Exits 0 if every
                expected finding is caught, 1 otherwise.
                Precedent: scripts/check_synapse_registry.py --selftest.
  --project-findings INPUT.json
                Bounded T12 consumer route. Reads ONE caller-supplied regular
                JSON file (qledger.research_findings_input.v1: exactly schema,
                claims, grades, reported_metrics metric-name arrays, registry
                snapshot, evidence_link locator), hands it to the pure owner
                engine.qledger_validity.project_research_findings, and prints
                qledger.research_findings_cli.v1: {schema, input{path, bytes,
                sha256}, result, error} — the input's byte length and SHA-256
                plus the owner's UNCHANGED result.

                SNAPSHOT ONLY. This mode never reads the live claim or grade
                stores, never fetches registry inputs, never calls providers,
                never dereferences evidence_link, never writes a Discovery and
                never changes a gate, clock or production state. It does not
                verify the evidence link, scientific validity, rights, or
                Discovery admission — those stay with their existing owners.
                Because a snapshot must never masquerade as a store audit, an
                explicit --root, --strict or --selftest is refused BEFORE the
                input is opened (--json is accepted but redundant: this mode
                only speaks JSON).

                The file is bounded at 16 MiB and must be a regular file.
                Missing, unreadable, oversized, or moving inputs, malformed
                UTF-8 or JSON, duplicate JSON keys, non-finite JSON constants
                and wrong schema/shapes exit 2 with a bounded structured error
                and a NULL result — never an empty clean finding set, never a
                traceback, never echoed input. A pre-read and a post-read
                fstat are compared to REFUSE an input that moved underneath
                the read; endpoint comparison detects some concurrent
                modifications and guarantees NO atomicity, which is why the
                payload reports the bytes it saw instead of claiming
                stability. Metric scope, the exact unique canonical engine
                binding and every other semantic stay with the pure owner;
                this mode adds no scheduler, store, evaluator or authority.

An ABSENT store is not a failure: the qledger store is gitignored on some
checkouts and absent in sparse agent worktrees. A missing file exits 0 with a
notice, because "I could not look" must never render as "I looked and it was
clean" (CLAUDE.md §Epistemics; nulls are printed, not hidden).
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import math
import os
import stat
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.qledger_validity import (  # noqa: E402
    SEVERITY_INVALID,
    Finding,
    audit,
    project_research_findings,
)

CLAIMS_REL = ("data", "qledger", "claims.jsonl")
GRADES_REL = ("data", "qledger", "grades.jsonl")
DEFAULT_ROOT = Path(__file__).resolve().parents[1]

PROJECT_FINDINGS_INPUT_SCHEMA = "qledger.research_findings_input.v1"
PROJECT_FINDINGS_CLI_SCHEMA = "qledger.research_findings_cli.v1"
PROJECT_FINDINGS_MAX_BYTES = 16 * 1024 * 1024
_PROJECT_FINDINGS_KEYS = frozenset(
    {"schema", "claims", "grades", "reported_metrics", "registry", "evidence_link"}
)


def _read_jsonl(path: Path, *, qledger_claims: bool = False) -> list[dict]:
    """Read a qledger JSONL store, skipping '#' schema-comment lines.

    Several ledger stores in this repo lead with '#' comment lines documenting
    the row schema, so a naive json.loads-per-line raises on line 1.
    """
    rows: list[dict] = []
    if qledger_claims:
        from engine.qledger_store import open_raw_lines

        source = open_raw_lines(path)
    else:
        source = path.open("r", encoding="utf-8")
    with source as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _json_payload(
    findings: list[Finding] | None,
    *,
    store_absent: bool,
    n_claims: int | None = None,
    n_grades: int | None = None,
    missing: list[str] | None = None,
) -> str:
    """The --json contract: ALWAYS an object, never a bare list.

    `store_absent` is a first-class field rather than an empty findings list,
    because an empty list would render "I could not look" as "I looked and it
    was clean" — the exact substitution research/MASTERMIND_EVALUATION_STANDARDS.md
    §9.2 forbids. A consumer must be able to tell the two apart without parsing
    prose, so `findings` is null (not []) when nothing was audited.
    """
    return json.dumps(
        {
            "store_absent": store_absent,
            "missing": missing or [],
            "claims": n_claims,
            "grades": n_grades,
            "findings": None
            if findings is None
            else [
                {
                    "code": f.code,
                    "family": f.family,
                    "severity": f.severity,
                    "detail": f.detail,
                }
                for f in findings
            ],
        },
        indent=2,
    )


def _emit(findings: list[Finding], as_json: bool, n_claims: int, n_grades: int) -> None:
    if as_json:
        print(
            _json_payload(
                findings, store_absent=False, n_claims=n_claims, n_grades=n_grades
            ),
            flush=True,
        )
        return
    for finding in findings:
        level = "error" if finding.severity == SEVERITY_INVALID else "warning"
        # Bare print, line-start, flushed — see module docstring.
        print(
            f"::{level} title=qledger-metric-validity::"
            f"[{finding.code}] {finding.family}: {finding.detail}",
            flush=True,
        )


def _selftest() -> int:
    """Prove the auditor catches each invariant and stays quiet on a clean corpus."""
    checks: list[tuple[str, bool]] = []

    # V1 — a family holding both directions must refuse a pooled signed excess.
    mixed = [
        {"claim_family": "mixed", "claim_id": "a", "direction": 1, "horizon_d": 5},
        {"claim_family": "mixed", "claim_id": "b", "direction": -1, "horizon_d": 5},
    ]
    grades_v1 = [{"claim_id": "a", "horizon_d": 5}, {"claim_id": "b", "horizon_d": 5}]
    codes = {f.code for f in audit(mixed, grades_v1)}
    checks.append(("V1 mixed-direction family flagged", "SIGNED_EXCESS_POOLED_ACROSS_DIRECTIONS" in codes))

    # V1 negative control — a single-direction family must NOT be flagged.
    homo = [
        {"claim_family": "homo", "claim_id": "c", "direction": 1, "horizon_d": 5},
        {"claim_family": "homo", "claim_id": "d", "direction": 1, "horizon_d": 5},
    ]
    grades_homo = [{"claim_id": "c", "horizon_d": 5}, {"claim_id": "d", "horizon_d": 5}]
    codes = {f.code for f in audit(homo, grades_homo)}
    checks.append(("V1 single-direction family clean", "SIGNED_EXCESS_POOLED_ACROSS_DIRECTIONS" not in codes))

    # V2 — a salience-only family must refuse a hit rate.
    salience = [
        {"claim_family": "sal", "claim_id": "e", "direction": 0, "horizon_d": 5},
        {"claim_family": "sal", "claim_id": "f", "direction": 0, "horizon_d": 5},
    ]
    grades_sal = [{"claim_id": "e", "horizon_d": 5}, {"claim_id": "f", "horizon_d": 5}]
    codes = {f.code for f in audit(salience, grades_sal)}
    checks.append(("V2 salience family flagged", "HIT_RATE_ON_A_SALIENCE_FAMILY" in codes))
    checks.append(("V2 salience family may still pool excess", "SIGNED_EXCESS_POOLED_ACROSS_DIRECTIONS" not in codes))

    # V3 — a 63d family graded only at 5d/21d is ACCRUING, not a verdict.
    long_h = [{"claim_family": "lng", "claim_id": "g", "direction": 1, "horizon_d": 63}]
    grades_short = [{"claim_id": "g", "horizon_d": 5}, {"claim_id": "g", "horizon_d": 21}]
    codes = {f.code for f in audit(long_h, grades_short)}
    checks.append(("V3 off-horizon verdict flagged", "OFF_HORIZON_VERDICT" in codes))

    # V3 negative control — once the ruler matures, the finding clears.
    grades_matured = grades_short + [{"claim_id": "g", "horizon_d": 63}]
    codes = {f.code for f in audit(long_h, grades_matured)}
    checks.append(("V3 clears once the declared ruler matures", "OFF_HORIZON_VERDICT" not in codes))

    # Placebo rows must not decide a real family's direction profile.
    with_placebo = homo + [
        {"claim_family": "homo", "claim_id": "p", "direction": -1, "is_placebo": True, "horizon_d": 5}
    ]
    codes = {f.code for f in audit(with_placebo, grades_homo)}
    checks.append(("placebo excluded from direction profile", "SIGNED_EXCESS_POOLED_ACROSS_DIRECTIONS" not in codes))

    ok = True
    for label, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}", flush=True)
        ok = ok and passed
    print(f"selftest: {'PASS' if ok else 'FAIL'} ({sum(1 for _, p in checks if p)}/{len(checks)})", flush=True)
    return 0 if ok else 1


class ProjectFindingsError(Exception):
    """A refused --project-findings input.

    Carries a stable machine code for the structured exit-2 payload; the
    message is bounded and never echoes input content.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message[:300]


def _project_findings_payload(
    result: dict[str, Any] | None,
    *,
    source: str,
    nbytes: int | None,
    digest: str | None,
    error: dict[str, str] | None,
) -> str:
    """The --project-findings contract: ALWAYS the same object shape.

    `result` is the pure owner's unchanged projection, or null when the input
    was refused — an empty issues list would render "could not look" as
    "looked and clean" (§9.2). `bytes`/`sha256` record the exact bytes that
    were read; on a refusal they are filled only as far as the read got, and
    they are a record of what was seen, not a claim that the read was atomic.
    """
    return json.dumps(
        {
            "schema": PROJECT_FINDINGS_CLI_SCHEMA,
            "input": {"path": source, "bytes": nbytes, "sha256": digest},
            "result": result,
            "error": error,
        },
        indent=2,
    )


def _read_bounded_input(path: Path) -> tuple[bytes, int, str]:
    """Read one bounded regular file. Returns (raw, byte length, sha256).

    The file is bounded at PROJECT_FINDINGS_MAX_BYTES and must be a regular
    file (symlinks resolve before the check; directories, devices and FIFOs
    are refused — O_NONBLOCK so a named pipe cannot hang the open). A pre-read
    and a post-read fstat are compared to REFUSE an input that moved
    underneath the read; endpoint comparison detects some concurrent
    modifications and guarantees NO atomicity — a file rewritten in place
    within the read window can still slip through, which is why the caller
    reports the bytes it saw instead of claiming stability.
    """
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except FileNotFoundError:
        raise ProjectFindingsError("input_missing", f"input file not found: {path}") from None
    except OSError as exc:
        if exc.errno == errno.EISDIR:
            raise ProjectFindingsError(
                "input_not_regular_file", f"input is not a regular file: {path}"
            ) from None
        raise ProjectFindingsError(
            "input_unreadable", f"input could not be opened: {exc.strerror}"
        ) from None
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ProjectFindingsError(
                "input_not_regular_file", f"input is not a regular file: {path}"
            )
        if before.st_size > PROJECT_FINDINGS_MAX_BYTES:
            raise ProjectFindingsError(
                "input_too_large",
                f"input exceeds the {PROJECT_FINDINGS_MAX_BYTES}-byte bound",
            )
        chunks = []
        remaining = PROJECT_FINDINGS_MAX_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(remaining, 65536))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        named = path.stat()
        def identity(info):
            return (info.st_dev, info.st_ino, info.st_size,
                    info.st_mtime_ns, info.st_ctime_ns)
        if (identity(after) != identity(before) or identity(named) != identity(before)
                or not stat.S_ISREG(named.st_mode) or len(raw) != before.st_size):
            raise ProjectFindingsError(
                "input_changed_during_read",
                "input changed while it was read; nothing atomic is claimed",
            )
    except OSError as exc:
        raise ProjectFindingsError(
            "input_unreadable", f"input could not be read: {exc.strerror}"
        ) from None
    finally:
        os.close(fd)
    if len(raw) > PROJECT_FINDINGS_MAX_BYTES:
        raise ProjectFindingsError(
            "input_too_large", f"input exceeds the {PROJECT_FINDINGS_MAX_BYTES}-byte bound"
        )
    return raw, len(raw), hashlib.sha256(raw).hexdigest()


def _parse_bounded_json(raw: bytes) -> Any:
    """Strict JSON only: no duplicate object keys, no NaN/Infinity constants."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ProjectFindingsError("input_not_utf8", "input is not valid UTF-8") from None

    def pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict:
        seen: dict = {}
        for key, value in pairs:
            if key in seen:
                raise ProjectFindingsError(
                    "duplicate_json_key", "input contains a duplicate JSON object key"
                )
            seen[key] = value
        return seen

    def refuse_constant(name: str) -> None:
        raise ProjectFindingsError(
            "non_finite_json_constant", "input contains a non-finite JSON number"
        )

    def finite_float(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            refuse_constant(value)
        return number

    try:
        return json.loads(
            text, object_pairs_hook=pairs_without_duplicates,
            parse_constant=refuse_constant, parse_float=finite_float
        )
    except json.JSONDecodeError as exc:
        raise ProjectFindingsError(
            "input_not_json",
            f"input is not valid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})",
        ) from None
    except RecursionError:
        raise ProjectFindingsError("input_not_json", "input nests too deeply to parse") from None
    except ValueError:
        raise ProjectFindingsError("input_not_json", "input contains an unsupported JSON number") from None


def _object_rows(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(row, dict) for row in value)


def _validate_research_input(
    document: Any,
) -> tuple[list[dict], list[dict], dict[str, set[str]], dict, str]:
    """Shape-check qledger.research_findings_input.v1 and delegate the semantics.

    This only decides that the shapes are the ones the pure owner expects, so
    a malformed file exits 2 here instead of surfacing as a TypeError inside
    engine.qledger_validity. Every semantic decision — which metrics are
    legal, whether the intended scope covers every claim family, whether the
    supplied registry binds exactly one canonical engine — stays with the
    owner. Metric-name arrays become sets here and only here, because sets are
    what the owner consumes and refuses anything else for.
    """
    if not isinstance(document, dict):
        raise ProjectFindingsError("input_schema_invalid", "input must be a JSON object")
    if set(document) != _PROJECT_FINDINGS_KEYS:
        raise ProjectFindingsError(
            "input_schema_invalid",
            "input must hold exactly schema, claims, grades, reported_metrics, "
            "registry, evidence_link",
        )
    if document["schema"] != PROJECT_FINDINGS_INPUT_SCHEMA:
        raise ProjectFindingsError(
            "input_schema_invalid", f"input schema must be {PROJECT_FINDINGS_INPUT_SCHEMA}"
        )
    claims, grades = document["claims"], document["grades"]
    if not _object_rows(claims):
        raise ProjectFindingsError("input_schema_invalid", "claims must be a list of objects")
    if not _object_rows(grades):
        raise ProjectFindingsError("input_schema_invalid", "grades must be a list of objects")
    # Preserve the owner's optional fields and legacy desk fallback, but do not
    # let container-valued identities silently disappear or reach set lookups.
    for rows, fields in ((claims, ("claim_family", "desk", "claim_id")),
                         (grades, ("claim_id",))):
        for row in rows:
            if any(row.get(field) is not None and not isinstance(row[field], str)
                   for field in fields):
                raise ProjectFindingsError("input_schema_invalid", "row identities must be strings or null")
    reported_metrics = document["reported_metrics"]
    if not isinstance(reported_metrics, dict) or not all(
        isinstance(family, str)
        and isinstance(metrics, list)
        and all(isinstance(metric, str) for metric in metrics)
        for family, metrics in reported_metrics.items()
    ):
        raise ProjectFindingsError(
            "input_schema_invalid",
            "reported_metrics must map family names to lists of metric names",
        )
    registry = document["registry"]
    if not isinstance(registry, dict):
        raise ProjectFindingsError(
            "input_schema_invalid", "registry must be a JSON object (a canonical supplied snapshot)"
        )
    evidence_link = document["evidence_link"]
    if not isinstance(evidence_link, str):
        raise ProjectFindingsError("input_schema_invalid", "evidence_link must be a string")
    metric_sets = {family: set(metrics) for family, metrics in reported_metrics.items()}
    return claims, grades, metric_sets, registry, evidence_link


def _project_findings_mode(args: argparse.Namespace) -> int:
    """The bounded T12 consumer route: one supplied file in, one snapshot out.

    Runs before any store import on purpose: this mode never touches the live
    claim/grade stores, never fetches registry inputs, never dereferences
    evidence_link and never writes a Discovery. Incompatible modes are
    refused BEFORE the input is opened.
    """
    source = args.project_findings
    conflicts = [
        flag
        for flag, requested in (
            ("--strict", args.strict),
            ("--selftest", args.selftest),
            ("--root", args.root is not None),
        )
        if requested
    ]
    nbytes: int | None = None
    digest: str | None = None
    error: dict[str, str] | None = None
    if conflicts:
        error = {
            "code": "mode_conflict",
            "message": (
                "--project-findings is a pure snapshot of the caller-supplied file; "
                f"it reads no store, so {', '.join(conflicts)} is not accepted"
            ),
        }
    else:
        try:
            raw, nbytes, digest = _read_bounded_input(source)
            document = _parse_bounded_json(raw)
            claims, grades, reported_metrics, registry, evidence_link = (
                _validate_research_input(document)
            )
            result = project_research_findings(
                claims,
                grades,
                reported_metrics=reported_metrics,
                registry=registry,
                evidence_link=evidence_link,
            )
        except ProjectFindingsError as exc:
            error = {"code": exc.code, "message": exc.message}
        except (ValueError, TypeError, OverflowError, RecursionError):
            # The pure owner's contract is to refuse malformed semantics with
            # ValueError (bounded locator, missing metric scope, ambiguous
            # binding, non-canonical registry). Surface that refusal as the
            # same bounded exit-2 shape instead of a traceback.
            error = {"code": "engine_refused_input", "message": "supplied input cannot be projected by the metric owner"}
        else:
            print(
                _project_findings_payload(
                    result, source=str(source), nbytes=nbytes, digest=digest, error=None
                ),
                flush=True,
            )
            return 0
    print(
        _project_findings_payload(
            None, source=str(source), nbytes=nbytes, digest=digest, error=error
        ),
        flush=True,
    )
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument(
        "--project-findings",
        type=Path,
        default=None,
        metavar="INPUT.json",
        help="project the pure research-findings owner over ONE supplied bounded "
        "JSON file (qledger.research_findings_input.v1); reads no store",
    )
    args = parser.parse_args()

    if args.project_findings is not None:
        # Routed first on purpose: an explicit --root, --strict or --selftest
        # alongside this mode is refused before anything is read or run.
        return _project_findings_mode(args)

    if args.selftest:
        return _selftest()

    root = args.root if args.root is not None else DEFAULT_ROOT
    claims_path = root.joinpath(*CLAIMS_REL)
    grades_path = root.joinpath(*GRADES_REL)
    from engine.qledger_store import uses_native_claims
    from engine.qledger_store_protocol import SnapshotIntegrityError

    native_claims = uses_native_claims(claims_path)
    claims = None
    if native_claims:
        # A missing grade sidecar must not hide an incomplete claims snapshot.
        try:
            claims = _read_jsonl(claims_path, qledger_claims=True)
        except SnapshotIntegrityError as exc:
            if args.json:
                payload = json.loads(_json_payload(None, store_absent=False))
                payload["storage_error"] = str(exc)
                payload["storage_error_code"] = exc.code
                print(json.dumps(payload, indent=2), flush=True)
            else:
                print(
                    "::error title=qledger-metric-validity::"
                    f"claims storage integrity failure, not audited: {exc}",
                    flush=True,
                )
            return 2

    missing = [
        p for p in (claims_path, grades_path)
        if not (p == claims_path and native_claims) and not p.exists()
    ]
    if missing:
        # Absent store: say so out loud, exit 0. Never render as "clean".
        if args.json:
            print(
                _json_payload(None, store_absent=True, missing=[str(p) for p in missing]),
                flush=True,
            )
        else:
            for path in missing:
                print(f"::notice title=qledger-metric-validity::store absent, not audited: {path}", flush=True)
        return 0

    if not native_claims:
        claims = _read_jsonl(claims_path, qledger_claims=True)
    grades = _read_jsonl(grades_path)
    findings = audit(claims, grades)

    _emit(findings, args.json, len(claims), len(grades))
    invalid = [f for f in findings if f.severity == SEVERITY_INVALID]
    if not args.json:
        print(
            f"qledger metric validity: {len(claims)} claims, {len(grades)} grades, "
            f"{len(findings)} finding(s) ({len(invalid)} invalid)",
            flush=True,
        )
    if args.strict and invalid:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
