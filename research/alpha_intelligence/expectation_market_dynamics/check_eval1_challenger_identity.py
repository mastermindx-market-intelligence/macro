"""Check the EVAL-1 challenger trial identity against its registration and the EXP-1 emitter.

This module validates the committed identity document only. It never reads labels,
outcomes, or any file under data/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

IDENTITY_RELPATH = "research/alpha_intelligence/expectation_market_dynamics/eval1_challenger_trial_identity.v1.json"
SCHEMA = "k3e.eval1_challenger_trial_identity/v1"
REGISTRATION_ID = "K3E-EVAL-1-V1"
REGISTRATION_DIGEST = "1ca158a213fca3f90c5c4fdc1359d40bf9146f2400cb10d8caa202b18f293bd4"
BOUNDARY_COMMIT = "01fcaf748c2794aa717b25d3e34ad1f53c539801"
REQUIRED_ELEMENTS = (
    "model_family",
    "target",
    "horizon",
    "feature_set",
    "preprocessing",
    "hyperparameters",
    "seed_policy",
)
REGISTERED_FAMILY = "REGULARIZED_LINEAR_OR_HAZARD"
TARGET_ID = "T1_NEXT_REVISION_DIRECTION"
HORIZON_SESSIONS = 21
SEED = 480336034
FDR_FAMILY = "k3e_expectation_market_dynamics_v1"
EMITTER_PATH = "engine/k3e_expectation_surface.py"
EMITTER_FUNCTION = "inspect_expectation_surface"
DENOMINATOR_FIELD = "denominators.capture_clock_bounded_relevant_records"
EXP1_EMITTED_COMPONENTS = {
    "rights_blocked_state": "normalized_baseline.rights_state",
    "true_missing_share": "denominators.true_missing_records",
    "invalid_or_inconsistent_excluded_share": "denominators.invalid_or_inconsistent_excluded_records",
}
FORBIDDEN_TUNING_KEYS = frozenset(
    {
        "grid",
        "param_grid",
        "search_space",
        "candidates",
        "range",
        "lambda_range",
        "cv_folds",
        "cross_validation",
        "tuning_grid",
        "sweep",
    }
)
VALUE_ORIGIN = "SEAT_FIXED_AT_COMMIT_NOT_DATA_DERIVED"


def git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode() + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def iter_citations(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "citations" and isinstance(value, list):
                for item in value:
                    yield item
            else:
                yield from iter_citations(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_citations(item)


def _malformed_citation_repr(cit) -> str:
    if isinstance(cit, dict):
        path = cit.get("path")
        line = cit.get("line")
    else:
        path = type(cit).__name__
        line = None
    return f"malformed citation: {path!r}:{line!r}"


def resolve_citation(cit, repo_root: Path, notes: list[str]) -> str | None:
    if not isinstance(cit, dict):
        return _malformed_citation_repr(cit)
    path = cit.get("path")
    line = cit.get("line")
    quote = cit.get("quote")
    blob = cit.get("blob")
    if (
        not isinstance(path, str)
        or not path
        or path.startswith("/")
        or ".." in Path(path).parts
        or not isinstance(line, int)
        or isinstance(line, bool)
        or line < 1
        or not isinstance(quote, str)
        or not quote
        or not isinstance(blob, str)
        or len(blob) != 40
        or blob != blob.lower()
        or not all(c in "0123456789abcdef" for c in blob)
    ):
        return _malformed_citation_repr(cit)

    f = repo_root / path
    if not f.is_file():
        return f"unresolvable citation: {path}:{line}"

    data = f.read_bytes()
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    if 1 <= line <= len(lines) and quote in lines[line - 1]:
        return None

    if git_blob_sha1(data) == blob:
        return f"unresolvable citation: {path}:{line}"

    if quote in text:
        notes.append(f"citation drifted, quote found elsewhere in current file: {path}:{line}")
        return None

    blob8 = blob[:8]
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "cat-file", "-p", blob],
            capture_output=True,
            timeout=20,
            env={**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"},
        )
        if proc.returncode == 0:
            old_text = proc.stdout.decode("utf-8", errors="replace")
            old_lines = old_text.splitlines()
            if 1 <= line <= len(old_lines) and quote in old_lines[line - 1]:
                notes.append(
                    f"citation drifted, resolved at cited blob {blob8}: {path}:{line}"
                )
                return None
            return f"unresolvable citation: {path}:{line}"
        notes.append(
            f"citation drifted and cited blob unavailable, not verified: {path}:{line}"
        )
        return None
    except Exception:
        notes.append(
            f"citation drifted and cited blob unavailable, not verified: {path}:{line}"
        )
        return None


def _value(identity: dict, name: str):
    els = identity.get("elements")
    if not isinstance(els, dict):
        return None
    entry = els.get(name)
    if not isinstance(entry, dict):
        return None
    return entry.get("value")


def _section(errors: list[str], identity: dict, name: str, fn) -> None:
    try:
        fn(errors, identity)
    except Exception as exc:
        errors.append(f"malformed {name}: {type(exc).__name__}")


def check_identity(
    identity, repo_root: Path, notes: list[str] | None = None
) -> list[str]:
    if notes is None:
        notes = []
    if not isinstance(identity, dict):
        return [f"malformed identity: {type(identity).__name__}"]

    errors: list[str] = []

    def header(errors: list[str], identity: dict) -> None:
        for field, expected in (
            ("schema", SCHEMA),
            ("registration_id", REGISTRATION_ID),
            ("registration_digest", REGISTRATION_DIGEST),
            ("boundary_commit", BOUNDARY_COMMIT),
        ):
            if identity.get(field) != expected:
                errors.append(f"{field} mismatch")

    def elements(errors: list[str], identity: dict) -> None:
        els = identity.get("elements")
        if not isinstance(els, dict):
            els = {}
        for name in REQUIRED_ELEMENTS:
            entry = els.get(name)
            if not isinstance(entry, dict) or "value" not in entry:
                errors.append(f"missing element: {name}")
            elif not isinstance(entry.get("citations"), list) or not entry["citations"]:
                errors.append(f"uncited element: {name}")
        for key in els:
            if key not in REQUIRED_ELEMENTS:
                errors.append(f"unknown element: {key}")
        id_def = identity.get("identity_definition")
        if not isinstance(id_def, dict) or id_def.get("elements") != list(REQUIRED_ELEMENTS):
            errors.append("identity_definition mismatch")

    def citations(errors: list[str], identity: dict) -> None:
        for item in iter_citations(identity):
            err = resolve_citation(item, repo_root, notes)
            if err is not None:
                errors.append(err)

    def model_family(errors: list[str], identity: dict) -> None:
        value = _value(identity, "model_family")
        if value is None:
            return
        if not isinstance(value, dict) or value.get("registered_family") != REGISTERED_FAMILY:
            errors.append("family mismatch")

    def target(errors: list[str], identity: dict) -> None:
        value = _value(identity, "target")
        if value is None:
            return
        if not isinstance(value, dict) or value.get("target_id") != TARGET_ID:
            errors.append("target mismatch")

    def horizon(errors: list[str], identity: dict) -> None:
        value = _value(identity, "horizon")
        if value is None:
            return
        sessions = value.get("sessions") if isinstance(value, dict) else None
        if isinstance(sessions, bool) or sessions != HORIZON_SESSIONS:
            errors.append("horizon mismatch")

    def feature_set(errors: list[str], identity: dict) -> None:
        value = _value(identity, "feature_set")
        if value is None:
            return
        if not isinstance(value, dict):
            errors.append("selection must be ENTIRE_BOUND_UNIVERSE")
            return
        if value.get("selection") != "ENTIRE_BOUND_UNIVERSE":
            errors.append("selection must be ENTIRE_BOUND_UNIVERSE")
        emitter = value.get("emitter")
        if (
            not isinstance(emitter, dict)
            or emitter.get("path") != EMITTER_PATH
            or emitter.get("function") != EMITTER_FUNCTION
        ):
            errors.append("emitter mismatch")
        features = value.get("features")
        if not isinstance(features, list):
            features = []
        seen: list[str] = []
        for f in features:
            name = f.get("name") if isinstance(f, dict) else repr(f)
            if name in seen:
                errors.append(f"duplicate feature: {name}")
            else:
                seen.append(name)
            if not isinstance(f, dict) or not isinstance(f.get("citations"), list) or not f["citations"]:
                errors.append(f"uncited feature: {name}")
                continue
            if name not in EXP1_EMITTED_COMPONENTS:
                errors.append(f"feature not in EXP-1 emitted set: {name}")
            else:
                if f.get("source_field") != EXP1_EMITTED_COMPONENTS[name]:
                    errors.append(f"feature source mismatch: {name}")
                if f.get("denominator_field") != DENOMINATOR_FIELD:
                    errors.append(f"feature denominator mismatch: {name}")
        for name in EXP1_EMITTED_COMPONENTS:
            if name not in seen:
                errors.append(f"bound universe feature missing: {name}")

    def preprocessing(errors: list[str], identity: dict) -> None:
        value = _value(identity, "preprocessing")
        if value is None:
            return
        steps = value.get("steps") if isinstance(value, dict) else None
        if not isinstance(steps, list) or not steps:
            errors.append("preprocessing has no steps")
            return
        for s in steps:
            name = s.get("name") if isinstance(s, dict) else repr(s)
            if not isinstance(s, dict) or s.get("fit_scope") != "F_DEV":
                errors.append(f"fit scope other than F_DEV: {name}")

    def hyperparameters(errors: list[str], identity: dict) -> None:
        value = _value(identity, "hyperparameters")
        if value is None:
            return
        if not isinstance(value, dict):
            errors.append("tunable hyperparameter: tuning")
            return
        if value.get("tuning") != "NONE":
            errors.append("tunable hyperparameter: tuning")
        for key, val in value.items():
            if key in FORBIDDEN_TUNING_KEYS or isinstance(val, (list, tuple, dict)):
                errors.append(f"tunable hyperparameter: {key}")
        lam = value.get("l2_lambda")
        if isinstance(lam, bool) or not isinstance(lam, (int, float)) or not (lam > 0):
            msg = "tunable hyperparameter: l2_lambda"
            if msg not in errors:
                errors.append(msg)
        if value.get("value_origin") != VALUE_ORIGIN:
            errors.append("hyperparameter value_origin mismatch")

    def seed_policy(errors: list[str], identity: dict) -> None:
        value = _value(identity, "seed_policy")
        if value is None:
            return
        if not isinstance(value, dict):
            errors.append("seed mismatch")
            errors.append("rng used")
            return
        seed = value.get("seed")
        if isinstance(seed, bool) or seed != SEED:
            errors.append("seed mismatch")
        if value.get("rng_used") is not False:
            errors.append("rng used")

    def trial_accounting(errors: list[str], identity: dict) -> None:
        ta = identity.get("trial_accounting")
        if not isinstance(ta, dict):
            ta = {}
        if ta.get("trial_ordinal") != 1:
            errors.append("trial accounting mismatch: trial_ordinal")
        if ta.get("eval1_trials_allotted") != 1:
            errors.append("trial accounting mismatch: eval1_trials_allotted")
        if ta.get("fdr_family") != FDR_FAMILY:
            errors.append("trial accounting mismatch: fdr_family")
        if ta.get("failed_trials_count") is not True:
            errors.append("trial accounting mismatch: failed_trials_count")

    def label_access(errors: list[str], identity: dict) -> None:
        la = identity.get("label_access")
        if not isinstance(la, str) or not la.startswith("NONE:"):
            errors.append("label access not NONE")

    def custody(errors: list[str], identity: dict) -> None:
        custody = identity.get("custody")
        if not isinstance(custody, dict):
            custody = {}
        if custody.get("is_sol_ruling") is not False:
            errors.append("custody is_sol_ruling must be false")

    for name, fn in (
        ("header", header),
        ("elements", elements),
        ("citations", citations),
        ("model_family", model_family),
        ("target", target),
        ("horizon", horizon),
        ("feature_set", feature_set),
        ("preprocessing", preprocessing),
        ("hyperparameters", hyperparameters),
        ("seed_policy", seed_policy),
        ("trial_accounting", trial_accounting),
        ("label_access", label_access),
        ("custody", custody),
    ):
        _section(errors, identity, name, fn)

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check the EVAL-1 challenger trial identity against its registration and the EXP-1 emitter."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    parser.add_argument(
        "--identity",
        type=Path,
        default=None,
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root
    identity_path = args.identity or (repo_root / IDENTITY_RELPATH)
    try:
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
    except Exception:
        print("ERROR: unreadable identity")
        return 1
    notes: list[str] = []
    errors = check_identity(identity, repo_root, notes)
    for note in notes:
        print("NOTE: " + note)
    for error in errors:
        print("ERROR: " + error)
    if errors:
        return 1
    n_citations = sum(1 for _ in iter_citations(identity))
    print(
        f"OK: EVAL-1 challenger trial identity: {len(REQUIRED_ELEMENTS)} elements, "
        f"{n_citations} citations resolved"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
