"""The CI dependency freeze is complete and conflict-free (F3, CI Lightning).

`ci/constraints.txt` + `PIP_CONSTRAINT` exist to make an upstream release
unable to change what CI installs between two runs of the same commit. A
constraints file that misses a package the manifest installs, or that fights
an explicit `pip install pkg==X` pin in a job step, does not merely lose that
benefit — a conflict FAILS the install outright (pip errors when a constraint
contradicts a requirement). These tests hold both edges:

  * coverage: every package any manifest job pip-installs (directly, by name)
    is constrained;
  * compatibility: every explicit version specifier in the manifest is
    satisfiable within the constraint's version set;
  * wiring: the workflows that run those installs actually export
    PIP_CONSTRAINT at the path where the constraints file lives;
  * placement: the file stays OUTSIDE the CI-definition trees so refreshing
    it does not stale every armed PR's merge-on-green proof, while the
    planner still full-suites the refreshing PR (`**/constraints*.txt` is a
    GLOBAL_INVALIDATORS pattern — asserted, not assumed).

Version comparison here is deliberately tiny (numeric dot segments): every
constraint and every explicit manifest pin in this repository is a plain
PEP-440 release with no pre/post/dev segments. A specifier that breaks that
assumption fails the parse loudly instead of silently comparing wrong.
"""
from __future__ import annotations

import re
import shlex
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONSTRAINTS_PATH = REPO_ROOT / "ci" / "constraints.txt"
MANIFEST_PATH = REPO_ROOT / ".github" / "ci" / "legacy-jobs.yml"
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"

# `constraints*.txt` / `**/constraints*.txt` are GLOBAL_INVALIDATORS entries in
# scripts/run_ci_pack.py; the controller's CI_DEFINITION_TREES is
# ('.github/ci/',). Both facts are load-bearing for the placement argument.
GLOBAL_INVALIDATOR_CONSTRAINTS_PATTERNS = ("constraints*.txt", "**/constraints*.txt")
CONTROLLER_DEFINITION_TREES = (".github/ci/", ".github/workflows/")

_PIP_INSTALL_LINE = re.compile(r"^(?:python3? -m )?pip install (.+)$", re.MULTILINE)
_CONSTRAINT_LINE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*==\s*([^\s#]+)(?:\s|#)")


def canonical(name: str) -> str:
    """PEP 503 normalization, the identity pip matches requirement names by."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_constraints(path: Path) -> dict[str, tuple[str, ...]]:
    """Map canonical package name -> tuple of pinned versions (one or more)."""
    pins: dict[str, tuple[str, ...]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        # pip's requirements parser drops end-of-line comments; mirror it.
        stripped = line.split("#", 1)[0].strip()
        if not stripped:
            continue
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==(.+)$", stripped)
        assert match, f"constraint line is not an exact pin: {line!r}"
        versions = tuple(
            part.strip().lstrip("=").strip() for part in match.group(2).split(",")
        )
        for version in versions:
            assert re.fullmatch(r"[0-9][0-9A-Za-z.+-]*", version), (
                f"constraint version is not a plain release: {line!r}"
            )
        name = canonical(match.group(1))
        assert name not in pins, f"duplicate constraint entry for {name}"
        pins[name] = versions
    assert pins, "constraints file is empty"
    return pins


def manifest_install_specs() -> set[str]:
    """Every literal requirement token the manifest pip-installs, unparsed."""
    specs: set[str] = set()
    jobs = yaml.safe_load(MANIFEST_PATH.read_bytes())["jobs"]
    for job in jobs.values():
        for step in job.get("steps", []):
            run = str(step.get("run", ""))
            if "pip install" not in run:
                continue
            for line in run.splitlines():
                match = _PIP_INSTALL_LINE.match(line.strip())
                if not match:
                    continue
                try:
                    tokens = shlex.split(match.group(1))
                except ValueError:
                    continue
                specs.update(
                    token for token in tokens
                    if not token.startswith("-") and not token.startswith("requirements/")
                )
    assert specs, "no pip install requirements found in the manifest"
    return specs


def explicit_manifest_pins() -> dict[str, list[str]]:
    """Canonical name -> explicit specifier strings (e.g. '==4.26.0', '>=11,<13')."""
    pins: dict[str, list[str]] = {}
    for token in manifest_install_specs():
        if not re.search(r"[=<>!~]", token):
            continue
        parts = re.split(r"(==|>=|<=|!=|~=|>|<)", token, maxsplit=1)
        pins.setdefault(canonical(parts[0]), []).append(token[len(parts[0]):])
    return pins


def version_key(version: str) -> tuple[int, ...]:
    segments = []
    for part in version.split("."):
        match = re.match(r"(\d+)(.*)", part)
        assert match and match.group(2) == "", (
            f"version {version!r} has a non-numeric segment; extend the "
            "comparator before pinning such a version"
        )
        segments.append(int(match.group(1)))
    return tuple(segments)


def satisfies(version: str, specifiers: str) -> bool:
    """True when `version` meets a comma-separated ==/>=/<=/< specifier list."""
    for clause in specifiers.split(","):
        clause = clause.strip()
        match = re.fullmatch(r"(==|>=|<=|<|>|!=)([\d.]+)", clause)
        assert match, f"unsupported specifier clause {clause!r} in the manifest"
        op, bound = match.group(1), match.group(2)
        left, right = version_key(version), version_key(bound)
        # Tuple compare needs equal length; pad the shorter with zeros.
        width = max(len(left), len(right))
        left += (0,) * (width - len(left))
        right += (0,) * (width - len(right))
        if op == "==" and left != right:
            return False
        if op == "!=" and left == right:
            return False
        if op == ">=" and not left >= right:
            return False
        if op == "<=" and not left <= right:
            return False
        if op == ">" and not left > right:
            return False
        if op == "<" and not left < right:
            return False
    return True


def test_constraints_file_exists_outside_the_ci_definition_trees():
    assert CONSTRAINTS_PATH.is_file()
    relative = CONSTRAINTS_PATH.relative_to(REPO_ROOT).as_posix()
    for tree in CONTROLLER_DEFINITION_TREES:
        assert not relative.startswith(tree), (
            f"{relative} lives inside the controller's CI-definition tree "
            f"{tree!r}; refreshing it would stale every armed PR's proof"
        )


def test_constraints_filename_remains_a_planner_global_invalidator():
    """The refreshing PR must still run the full suite (fail-closed)."""
    source = (REPO_ROOT / "scripts" / "run_ci_pack.py").read_text(encoding="utf-8")
    for pattern in GLOBAL_INVALIDATOR_CONSTRAINTS_PATTERNS:
        assert f'"{pattern}"' in source, (
            f"{pattern} disappeared from GLOBAL_INVALIDATORS in "
            "scripts/run_ci_pack.py — a constraints edit would no longer run "
            "the full suite"
        )


def test_every_manifest_pip_package_is_constrained():
    pins = parse_constraints(CONSTRAINTS_PATH)
    unpinned_names = {
        canonical(re.split(r"[=<>!~\[ ]", token)[0])
        for token in manifest_install_specs()
    }
    missing = sorted(unpinned_names - set(pins))
    assert not missing, (
        "packages the manifest pip-installs without a constraints entry "
        f"(they drift freely): {missing}"
    )


def test_playwright_constraint_equals_the_single_native_constant():
    from scripts.ci_apt_native_plan import QUALIFIED_PLAYWRIGHT_VERSION

    pins = parse_constraints(CONSTRAINTS_PATH)
    assert pins[canonical("playwright")] == (QUALIFIED_PLAYWRIGHT_VERSION,), (
        "ci/constraints.txt playwright pin must equal "
        f"ci_apt_native_plan.QUALIFIED_PLAYWRIGHT_VERSION={QUALIFIED_PLAYWRIGHT_VERSION}"
    )


def test_explicit_manifest_pins_never_conflict_with_the_constraints():
    pins = parse_constraints(CONSTRAINTS_PATH)
    problems = []
    for name, specifiers in explicit_manifest_pins().items():
        versions = pins[name]
        for specifier in specifiers:
            if not any(satisfies(version, specifier) for version in versions):
                problems.append(f"{name}{specifier} vs constraint {name}=={','.join(versions)}")
    assert not problems, (
        "explicit manifest pins that no constrained version satisfies "
        "(pip would fail the install): " + "; ".join(problems)
    )


def test_ci_pack_job_exports_pip_constraint_at_the_constraints_path():
    workflow = yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    pack_env = workflow["jobs"]["ci-pack"]["env"]
    assert pack_env.get("PIP_CONSTRAINT", "").endswith("/ci/constraints.txt"), (
        "ci-pack must export PIP_CONSTRAINT pointing at ci/constraints.txt "
        f"(job-level env so every legacy dependency step inherits it), got {pack_env}"
    )


def test_control_plane_install_steps_export_pip_constraint():
    """ci-plan's and contract-delta's own pip installs are frozen too."""
    text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    count = text.count("PIP_CONSTRAINT: ${{ github.workspace }}/ci/constraints.txt")
    # ci-pack job-level + ci-plan install step + contract-delta install step.
    assert count >= 3, (
        f"expected PIP_CONSTRAINT on ci-pack (job env), the ci-plan install "
        f"step and the contract-delta install step; found {count}"
    )


def test_every_constraint_pins_exactly_one_version():
    """One == version per package — `pkg==A,==B` is not an option.

    pip 26 refuses a multi-`==` constraint against a job's explicit
    `pkg==A` requirement ("The user requested (constraint) pkg==A,==B"), so a
    dual entry would break the explicitly pinned job's install outright.
    Where the manifest pins a job explicitly, the constraint MUST equal that
    exact version.
    """
    pins = parse_constraints(CONSTRAINTS_PATH)
    explicit = explicit_manifest_pins()
    problems = []
    for name, versions in pins.items():
        if len(versions) != 1:
            problems.append(f"{name}=={','.join(versions)} has {len(versions)} versions")
            continue
        for spec in explicit.get(name, []):
            if spec.startswith("==") and versions[0] != spec[2:]:
                problems.append(f"{name}{spec} conflicts with constraint {name}=={versions[0]}")
    assert not problems, "; ".join(problems)
