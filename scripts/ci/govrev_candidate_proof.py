#!/usr/bin/env python3
"""Government Revenue candidate proof gate — prove bytes before publishing them.

The live lane builds a candidate projection and, historically, certified it
with three shell facts: `pytest exited 0`, `git porcelain over
data/government_revenue did not move`, and `the suites that ran are the suites
that were named`.  Each fact has a documented escape:

* an absent prover was a WARNING and an ``exit 0`` — the projection published
  UNPROVEN whenever pytest could not be installed;
* porcelain is blind to git-ignored bytes — anything under
  ``data/government_revenue`` that git does not track could be rewritten by
  the very run that was supposed to check it, with porcelain unchanged;
* a zero exit status with no terminal summary (a stub, a truncated run, a
  lost log) was indistinguishable from a green suite.

This helper closes the three escapes and adds the two the rebase path needed:

* **Proof identity.**  A green run mints a receipt binding, in one digest:
  the source checkout, the candidate generation (queue content id, projection
  clocks, ledger length), the sha256 of every input suite and every output
  artifact, the sha256 of every source dependency the suites read directly,
  the suite/prover versions, and the conclusion.  A missing or partial
  receipt refuses.
* **Exact-generation witness.**  After the commit/rebase retry loop rebuilds,
  the loop must either RE-PROVE or prove the rebuild produced the exact
  generation already accepted: identical output bytes AND identical source
  dependencies AND no material source path moved between the proved checkout
  and HEAD.  A source change never reuses a proof blindly.

Exit codes are a contract, consumed by the workflow and by
``tests/test_govrev_candidate_proof_gate.py``::

    0   proved / covered
    2   the suites genuinely failed — refuses in every mode
    3   pytest unavailable — refuses in EVERY mode
    4   the prover mutated output/source/runtime inputs — refuses in EVERY mode
    5   zero-status run without complete proof output — refuses in EVERY mode
    6   receipt missing/partial, or no usable source checkout
   10   exact-generation witness failed — reprove before publishing

The script is deliberately standalone (stdlib only) so the gate can run in
the collector's venv, which carries no test pack.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from importlib import metadata
from datetime import datetime, timezone
from pathlib import Path

RECEIPT_CONTRACT = "government_revenue.candidate_proof.v1"
PROVER_VERSION = 2

EXIT_PROOF_FAILED = 2
EXIT_PYTEST_UNAVAILABLE = 3
EXIT_TREE_MUTATED = 4
EXIT_INCOMPLETE_PROOF = 5
EXIT_RECEIPT_INVALID = 6
EXIT_WITNESS_MISMATCH = 10
EXIT_USAGE = 64

#: The candidate artifacts this gate certifies.  Order is stable; the receipt
#: binds each path's bytes individually.
DEFAULT_CANDIDATE_PATHS = (
    "data/government_revenue/candidate_ledger.jsonl",
    "data/government_revenue/candidate_queue.json",
    "data/government_revenue/candidate_projection_state.json",
    "data/government_revenue/candidate_projection_status.json",
)
#: The byte-identical public twin of the queue; the proof covers it too.
DEFAULT_PUBLIC_TWIN = "site/government-revenue-data/candidates.json"
SHARED_OUTPUT_PATHS = ("site/theme.js",)
#: The suites the armed gate (DEC:GOVREV-CANDIDATE-PROOF-GATE-ARMED) named.
#: Altering this list is altering the proof, not an implementation detail.
DEFAULT_SUITES = (
    "tests/test_government_revenue_candidates.py",
    "tests/test_government_revenue_candidate_projection.py",
    "tests/test_government_revenue_candidate_fixture.py",
)
PARTICIPATION_SOURCE_PATHS = (
    "engine/__init__.py", "engine/baskets.py", "engine/coiled.py",
    "engine/equity_factors.py", "engine/group_flow.py", "engine/group_pulse.py",
    "engine/indicators.py", "engine/ledger_lane.py", "engine/session_anchor.py",
    "engine/technicals.py", "config.yml",
)
#: Source documents the suites read DIRECTLY (live-probe tests open them from
#: the repo root), plus every code path that could change their outcome.  A
#: witness that binds only outputs would wave through a republished
#: latest.json/graph that the suites have not been run against.
SOURCE_DEPENDENCY_GLOBS = (
    "config/**/*", "contracts/**/*", "engine/government_revenue/**/*.py", "engine/company_intelligence/**/*.py", "engine/earnings_release/**/*.py",
    "scripts/**/*.py", "scripts/**/*.sh", "lib/**/*.py", "collectors/**/*.py",
    "app/**/*.py", "app/requirements*.txt", "templates/**/*", "tests/**/*.py",
    "tests/**/*.js", "tests/**/*.cjs", "tests/**/fixtures/**/*",
    "data/usaspending/**/*", "requirements*.txt", "pytest.ini", "pyproject.toml",
    "setup.cfg", "conftest.py", ".github/workflows/government-revenue-live.yml",
    "research/GOVERNMENT_REVENUE_CANDIDATE_GRADER_PREREG.md",
    ".github/workflows/daily.yml", ".github/workflows/fms-acquire.yml",
    "research/defense_intelligence/e2e_20261011/PUBLISHER_RECOVERY_BASELINE.json",
)
#: Prefixes a material source change may live under.  The checkout-delta half
#: of the witness refuses (reprove) when anything here moved between the
#: proved commit and HEAD ...
MATERIAL_PREFIXES = (
    "data/government_revenue/",
    "data/usaspending/",
    "config/government_revenue/",
    "contracts/government_revenue/",
    "engine/government_revenue/",
    "engine/company_intelligence/",
    "engine/earnings_release/",
    "collectors/",
    "scripts/",
    "lib/",
    "tests/",
    "app/",
    "templates/",
    "site/government-revenue-data/",
    "site/government_revenue",
    "site/government-revenue-",
    "site/theme.js",
    ".github/workflows/government-revenue-live.yml",
    "research/GOVERNMENT_REVENUE_CANDIDATE_GRADER_PREREG.md",
    ".github/workflows/daily.yml", ".github/workflows/fms-acquire.yml",
    "research/defense_intelligence/e2e_20261011/PUBLISHER_RECOVERY_BASELINE.json",
    "data/company_intelligence/event_workspaces/manifest.json",
    "data/massive_stock_day/", "data/reference/",
    "research/licenses/MASSIVE_ENTITLEMENT_RECORD.md", "engine/stock_technicals.py",
    "data/baskets/", "data/yahoo/SPY.parquet", "site/basketdata/",
) + PARTICIPATION_SOURCE_PATHS
_SUMMARY_LINE = re.compile(
    r"^\s*(?:(?P<count>\d+) (?P<kind>passed|failed|error|errors|skipped|deselected|"
    r"xfailed|xpassed|warnings?)(?:,\s*)?)+\s+in\s+\d+(?:\.\d+)?s(?:\s+\([0-9:]+\))?\s*$"
)
_NO_TESTS_LINE = re.compile(r"^\s*no tests ran in \d+(?:\.\d+)?s(?:\s+\([0-9:]+\))?\s*$")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _say(message: str) -> None:
    print(message, flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        try:
            with open(summary, "a", encoding="utf-8") as handle:
                handle.write(message + "\n")
        except OSError:
            # A summary is telemetry; never let it steer the exit status.
            pass


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _head_commit(root: Path) -> str | None:
    try:
        result = _git(root, "rev-parse", "HEAD")
    except subprocess.CalledProcessError:
        return None
    return result.stdout.strip() or None


def _porcelain_candidates(root: Path, candidate_paths: tuple[str, ...]) -> str:
    result = _git(root, "status", "--porcelain", "--", *candidate_paths, check=False)
    return result.stdout


def _file_digest(root: Path, relative: str) -> str | None:
    path = root / relative
    try:
        return _sha256_bytes(path.read_bytes())
    except (FileNotFoundError, IsADirectoryError):
        return None
    except OSError as exc:
        raise SystemExit(f"govrev proof: unreadable input {relative}: {exc}") from exc


def _hash_files(root: Path, relatives) -> dict[str, str]:
    """Hash the files that exist; a listed-but-absent path is recorded as absent.

    Absence must be a *recorded* value, not a silent omission: ``{}`` for
    "every dependency vanished" would make the witness vacuously true.
    """
    manifest: dict[str, str] = {}
    for relative in relatives:
        digest = _file_digest(root, relative)
        manifest[relative] = digest if digest is not None else "absent"
    return manifest


# Exact existing-owner snapshot consumed by the recurring market adapter.
# These paths include ignored files; missing snapshots are explicit inputs.
MARKET_INPUT_PATHS = (
    "data/massive_stock_day/LMT.parquet", "data/massive_stock_day/RTX.parquet",
    "data/massive_stock_day/NOC.parquet", "data/massive_stock_day/LHX.parquet",
    "data/massive_stock_day/.defense_read/manifest.json",
    "data/massive_stock_day/.defense_read/read_receipt.json",
    "data/reference/_receipt.json", "data/reference/security_master.parquet",
    "data/reference/vendor_aliases.parquet", "data/reference/issuer_master.parquet",
    "config/dataset_registry.yml", "research/licenses/MASSIVE_ENTITLEMENT_RECORD.md",
    "engine/stock_technicals.py",
)

PARTICIPATION_OWNER_PATHS = (
    "data/baskets/membership.json", "site/basketdata/pulse.json",
    "site/basketdata/baskets.json", "data/yahoo/SPY.parquet",
)


def _market_input_paths(root: Path) -> tuple[str, ...]:
    # The current defense roster selects its exact raw dependencies. This is
    # an inventory only; GroupPulse and the consuming adapter own validation.
    paths = set(MARKET_INPUT_PATHS) | set(PARTICIPATION_OWNER_PATHS)
    marker = root / PARTICIPATION_OWNER_PATHS[0]
    for part in (marker, *marker.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ValueError("market input symlink refused")
    if marker.is_file():
        membership = json.loads(marker.read_bytes())
        for member in membership['baskets']['defense']['members']:
            ticker = member['ticker']
            if not isinstance(ticker, str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,15}', ticker):
                raise ValueError("participation member path invalid")
            paths.add(f"data/baskets/ohlcv/{ticker}.parquet")
    for relative in paths:
        path = root / relative
        for part in (path, *path.parents):
            if part == root:
                break
            if part.is_symlink():
                raise ValueError("market input symlink refused")
        if path.exists() and not path.is_file():
            raise ValueError("market input is not a regular file")
    return tuple(sorted(paths))


OWNER_MANIFEST_PATH = "data/company_intelligence/event_workspaces/manifest.json"


def _owner_generation_paths(root: Path) -> list[str]:
    """Bind exactly the immutable owner generation the economics reader opens.

    Missing owner data is an explicit absent input, never a silent omission.
    The owner reader/prefetch owns admission and schema validation; this helper
    checks the local marker/file receipts without scanning historical generations.
    """
    paths = {OWNER_MANIFEST_PATH}
    marker = root / OWNER_MANIFEST_PATH
    if marker.is_symlink():
        raise ValueError("owner marker symlink refused")
    if not marker.exists():
        return sorted(paths)
    raw = marker.read_bytes()
    payload = json.loads(raw)
    generation = payload.get("generation_id") if isinstance(payload, dict) else None
    if not isinstance(generation, str) or not generation or generation in (".", "..") or Path(generation).name != generation:
        raise ValueError("invalid owner generation path")
    files = payload.get("files")
    if not isinstance(files, dict):
        raise ValueError("owner generation file receipts missing")
    nest = marker.parent
    immutable = nest / "generations" / generation
    if immutable.is_symlink() or not immutable.resolve().is_relative_to(nest.resolve()):
        raise ValueError("owner generation path outside mirror")
    held_manifest = immutable / "manifest.json"
    if held_manifest.is_symlink() or held_manifest.read_bytes() != raw:
        raise ValueError("owner marker/immutable manifest mismatch")
    paths.add(held_manifest.relative_to(root).as_posix())
    for relative, receipt in files.items():
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or any(part in (".", "..") for part in Path(relative).parts):
            raise ValueError("invalid owner workspace relative path")
        path = immutable / relative
        if path.is_symlink() or not path.resolve().is_relative_to(immutable.resolve()):
            raise ValueError("owner workspace path outside generation")
        body = path.read_bytes()
        digest = _sha256_bytes(body)
        size = receipt.get("bytes") if isinstance(receipt, dict) else None
        if not isinstance(receipt, dict) or receipt.get("sha256") != digest or not isinstance(size, int) or isinstance(size, bool) or size != len(body):
            raise ValueError("owner workspace receipt mismatch")
        paths.add(path.relative_to(root).as_posix())
    if marker.read_bytes() != raw:
        raise ValueError("owner current marker changed while binding generation")
    return sorted(paths)


def _source_dependency_paths(root: Path) -> list[str]:
    relatives: set[str] = set()
    for pattern in SOURCE_DEPENDENCY_GLOBS:
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                relatives.add(path.relative_to(root).as_posix())
    relatives.update(_owner_generation_paths(root))
    relatives.update(_market_input_paths(root))
    relatives.update(PARTICIPATION_SOURCE_PATHS)
    return sorted(relatives)


def fingerprint_tree(root: Path, data_dir: str) -> dict:
    """Content inventory of ``data_dir``: every file, ignored or not.

    Porcelain cannot see ignored bytes; this can.  A prover that rewrites an
    ignored parquet sidecar is a prover writing what it checks.
    """
    base = root / data_dir
    files: dict[str, dict] = {}
    if base.is_dir():
        for path in sorted(base.rglob("*")):
            if path.is_symlink():
                files[path.relative_to(root).as_posix()] = {
                    "symlink": os.readlink(path)
                }
            elif path.is_file():
                payload = path.read_bytes()
                files[path.relative_to(root).as_posix()] = {
                    "sha256": _sha256_bytes(payload),
                    "bytes": len(payload),
                }
    return {
        "data_dir": data_dir,
        "files": files,
        "digest": _sha256_bytes(_canonical(files).encode("utf-8")),
    }


def parse_pytest_summary(log_text: str) -> tuple[str | None, int]:
    """Return (summary line, passed count) from a pytest terminal report.

    A zero exit with no complete terminal summary is not a green suite — it
    is a run whose evidence is missing.  ``no tests ran`` is treated as no
    proof: collecting zero tests proves nothing about the artifacts.
    """
    lines = log_text.splitlines()
    for line in reversed(lines[-120:]):
        if _NO_TESTS_LINE.match(line):
            return line, 0
        match = _SUMMARY_LINE.match(line)
        if match:
            passed = 0
            for count, kind in re.findall(r"(\d+) (passed|failed|error|errors|skipped|deselected|xfailed|xpassed|warnings?)", line):
                if kind == "passed":
                    passed = int(count)
            return line, passed
    return None, -1


def _load_receipt(path: Path) -> dict | None:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(receipt, dict):
        return None
    return receipt


def _required_receipt_fields(receipt: dict) -> list[str]:
    """Fields whose absence makes a receipt partial (and therefore refused)."""
    missing: list[str] = []
    expected = {
        "contract": RECEIPT_CONTRACT,
        "conclusion": "passed",
        "prover_version": PROVER_VERSION,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            missing.append(key)
    for key in (
        "proved_at",
        "source_checkout",
        "generation",
        "inputs",
        "outputs",
        "source_dependencies",
        "suite",
        "pytest_exit",
        "pytest_summary",
        "identity",
        "execution_evidence",
    ):
        if key not in receipt:
            missing.append(key)
    for key in ("inputs", "source_dependencies", "suite", "generation"):
        if not isinstance(receipt.get(key), dict):
            missing.append(key)
    if not isinstance(receipt.get("source_checkout"), str) or not receipt.get("source_checkout"):
        missing.append("source_checkout")
    if not isinstance(receipt.get("outputs"), dict) or not receipt["outputs"]:
        missing.append("outputs")
    if not receipt.get("pytest_summary"):
        missing.append("pytest_summary")
    evidence = receipt.get("execution_evidence", {})
    if not isinstance(evidence, dict) or not evidence.get("nodeids") or not evidence.get("junit_sha256") or set(evidence.get("artifacts", {})) != {"log", "collection", "junit"}:
        missing.append("execution_evidence")
    if receipt.get("pytest_exit") != 0:
        missing.append("pytest_exit")
    return missing


def receipt_identity(receipt: dict) -> str:
    """The digest a receipt is bound by — content only, never clocks.

    Suite and prover versions are part of the identity: the same bytes proved
    by a different pytest generation is a different proof.
    """
    binding = {
        "contract": receipt["contract"],
        "prover_version": receipt["prover_version"],
        "source_checkout": receipt["source_checkout"],
        "generation": receipt["generation"],
        "inputs": receipt["inputs"],
        "outputs": receipt["outputs"],
        "source_dependencies": receipt["source_dependencies"],
        "execution_evidence": receipt["execution_evidence"],
        "suite": {
            "pytest_version": receipt["suite"].get("pytest_version"),
            "xdist_version": receipt["suite"].get("xdist_version"),
            "serial": receipt["suite"].get("serial"),
            "argv": receipt["suite"].get("argv"),
        },
    }
    return _sha256_bytes(_canonical(binding).encode("utf-8"))


def _have_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _module_version(name: str) -> str | None:
    try:
        from importlib import metadata

        return metadata.version(name)
    except Exception:
        return None


def _pip_install(package: str) -> None:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", package],
            capture_output=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        # Installation is best-effort; the refusal below is the guarantee.
        pass


def command_fingerprint(args: argparse.Namespace) -> int:
    inventory = fingerprint_tree(Path(args.root), args.data_dir)
    Path(args.out).write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    return 0


def _tree_identity(
    root: Path,
    candidate_paths: tuple[str, ...],
    suites: tuple[str, ...],
) -> dict:
    required = (*candidate_paths, DEFAULT_PUBLIC_TWIN)
    outputs = _hash_files(root, required)
    for directory in ("data/government_revenue", "site/government-revenue-data"):
        for path in sorted((root / directory).rglob("*")):
            if path.is_symlink():
                raise ValueError(f"published symlink refused: {path}")
            if path.is_file():
                outputs[path.relative_to(root).as_posix()] = _sha256_bytes(path.read_bytes())
    for pattern in ("site/government-revenue-*.js", "site/government-revenue-*.css",
                    "site/government_revenue*.js", "site/government_revenue*.css"):
        for path in sorted(root.glob(pattern)):
            if path.is_symlink():
                raise ValueError(f"published symlink refused: {path}")
            if path.is_file():
                outputs[path.relative_to(root).as_posix()] = _sha256_bytes(path.read_bytes())
    page = "site/government_revenue.html"
    outputs[page] = _file_digest(root, page) or "absent"
    for path in SHARED_OUTPUT_PATHS:
        outputs[path] = _file_digest(root, path) or "absent"
    dependencies = _hash_files(root, _source_dependency_paths(root))
    # Include root discovery/config files even when absent, and the full prover.
    dependencies.update(_hash_files(root, ("pytest.ini", "pyproject.toml", "setup.cfg", "conftest.py")))
    distributions = sorted([d.metadata.get("Name", ""), d.version] for d in metadata.distributions())
    modules = {}
    for name in ("pytest", "xdist", "fastapi", "httpx", "pandas", "numpy", "pyarrow", "jinja2", "jsonschema"):
        spec = importlib.util.find_spec(name)
        origin = spec.origin if spec else None
        modules[name] = {"origin": origin, "sha256": _sha256_bytes(Path(origin).read_bytes()) if origin and Path(origin).is_file() else None}
    inputs = {
        "suites": _hash_files(root, suites),
        "prover": {"script": _sha256_bytes(Path(__file__).read_bytes())},
        "runtime": {"python": sys.version, "executable": sys.executable,
                    "distributions": distributions, "modules": modules,
                    "environment": {key: os.environ.get(key) for key in
                        ("PYTHONPATH", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_PLUGINS")}},
    }
    return {"outputs": outputs, "source_dependencies": dependencies, "inputs": inputs}


def _complete_execution(nodeids: list[str], junit: Path) -> dict:
    """Account for every collected case, including parameterizations/skips."""
    expected = Counter()
    for node in nodeids:
        parts = node.split("::")
        expected[(parts[0].removesuffix(".py").replace("/", ".") +
                  ("." + ".".join(parts[1:-1]) if len(parts) > 2 else ""), parts[-1])] += 1
    tree = ET.parse(junit)
    cases = list(tree.getroot().iter("testcase"))
    actual = Counter((case.get("classname"), case.get("name")) for case in cases)
    if not expected or actual != expected or any(case.find("failure") is not None or case.find("error") is not None for case in cases):
        raise ValueError("JUnit does not account for the complete collected inventory")
    passed = sum(case.find("skipped") is None for case in cases)
    if passed < 1:
        raise ValueError("no passing cases in complete inventory")
    # Aggregate counters must agree with the cases, not just a passing fragment.
    for suite in tree.getroot().iter("testsuite"):
        children = list(suite.iter("testcase"))
        if int(suite.get("tests", "-1")) != len(children) or int(suite.get("failures", "-1")) != 0 or int(suite.get("errors", "-1")) != 0:
            raise ValueError("inconsistent JUnit aggregate")
    return {"nodeids": nodeids, "passed": passed, "cases": len(cases),
            "junit_sha256": _sha256_bytes(junit.read_bytes())}


def _seal_execution_artifacts(receipt_path: Path, log_path: Path, evidence: dict) -> None:
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    files = {"log": log_path, "collection": log_path.with_suffix(log_path.suffix + ".collection"),
             "junit": log_path.with_suffix(log_path.suffix + ".xml")}
    artifacts = {}
    for kind, path in files.items():
        payload = path.read_bytes()
        digest = _sha256_bytes(payload)
        filename = path.name + ".sealed-" + digest[:16]
        sealed = receipt_path.parent / filename
        if sealed.exists() and sealed.read_bytes() != payload:
            raise ValueError("sealed proof artifact collision")
        sealed.write_bytes(payload)
        artifacts[kind] = {"filename": filename, "sha256": digest, "bytes": len(payload)}
    evidence["artifacts"] = artifacts


def _execution_artifacts_match(receipt_path: Path, receipt: dict) -> bool:
    try:
        artifacts = receipt["execution_evidence"]["artifacts"]
        if artifacts["junit"]["sha256"] != receipt["execution_evidence"]["junit_sha256"]:
            return False
        for item in artifacts.values():
            name = item["filename"]
            if not isinstance(name, str) or Path(name).name != name:
                return False
            payload = (receipt_path.parent / name).read_bytes()
            if _sha256_bytes(payload) != item["sha256"] or len(payload) != item["bytes"]:
                return False
        return True
    except (OSError, KeyError, TypeError, ValueError):
        return False


def _retain_previous_evidence(receipt_path: Path, log_path: Path) -> None:
    # A rebuild's failure must not erase the first generation's certificate.
    for path in (receipt_path, log_path, log_path.with_suffix(log_path.suffix + ".xml"),
                 log_path.with_suffix(log_path.suffix + ".collection")):
        if path.is_file():
            payload = path.read_bytes()
            digest = _sha256_bytes(payload)
            archive = path.with_name(path.name + ".previous-" + digest[:16])
            structured = path == receipt_path or path.suffix == ".xml"
            archive.write_bytes(payload if structured else payload[-1048576:])


def command_prove(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    receipt_path, log_path = Path(args.receipt).resolve(), Path(args.log).resolve()
    suites = tuple(args.suite or ()) or DEFAULT_SUITES
    candidate_paths = tuple(args.candidate_path or ()) or DEFAULT_CANDIDATE_PATHS
    # Proof evidence cannot enter the very inventory it certifies.
    if receipt_path.is_relative_to(root) or log_path.is_relative_to(root):
        _say("::error::proof evidence must live outside the source/output root")
        return EXIT_USAGE
    if _head_commit(root) is None:
        return EXIT_RECEIPT_INVALID
    if not _have_module("pytest") or args.simulate_pytest_unavailable:
        if args.install_missing and not args.simulate_pytest_unavailable:
            _pip_install("pytest")
        if not _have_module("pytest") or args.simulate_pytest_unavailable:
            receipt_path.unlink(missing_ok=True)
            _say("::error::pytest unavailable; refusing to publish an unproven candidate projection")
            return EXIT_PYTEST_UNAVAILABLE
    existing = _load_receipt(receipt_path)
    if existing and not _required_receipt_fields(existing) and command_verify(args) == 0:
        _say("govrev candidate proof: prior proof stands; exact generation/source/runtime unchanged")
        return 0
    _retain_previous_evidence(receipt_path, log_path)
    receipt_path.unlink(missing_ok=True)
    have_xdist = not args.simulate_xdist_unavailable and _have_module("xdist")
    if not have_xdist:
        _say("govrev candidate proof: pytest-xdist unavailable — running serially.")
    parallel = ["-n", "2", "--dist", "load", "--max-worker-restart=0"] if have_xdist else []
    head = _head_commit(root)
    try:
        before = _tree_identity(root, candidate_paths, suites)
    except (OSError, ValueError) as exc:
        _say(f"::error::proof input unavailable: {exc}")
        return EXIT_RECEIPT_INVALID
    if any(before["outputs"].get(path) == "absent" for path in (*candidate_paths, DEFAULT_PUBLIC_TWIN)):
        _say("::error::required candidate output missing")
        return EXIT_RECEIPT_INVALID
    child_env = dict(os.environ)
    child_env.pop("PYTEST_ADDOPTS", None)
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    base = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-o", "addopts=", "--color=no"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    collected = subprocess.run([*base, "--collect-only", "-q", *suites], cwd=root,
                               capture_output=True, text=True, env=child_env)
    log_path.with_suffix(log_path.suffix + ".collection").write_text(collected.stdout + collected.stderr)
    nodeids = [line.strip() for line in collected.stdout.splitlines() if "::" in line and any(line.startswith(suite + "::") for suite in suites)]
    junit = log_path.with_suffix(log_path.suffix + ".xml")
    junit.unlink(missing_ok=True)
    argv = [*base, *parallel, *suites, "-q", "-o", "junit_family=xunit2", "--junitxml", str(junit)]
    with log_path.open("wb") as handle:
        if collected.returncode == 0 and nodeids:
            status = subprocess.run(argv, cwd=root, stdout=handle, stderr=subprocess.STDOUT, env=child_env).returncode
        else:
            handle.write((collected.stdout + collected.stderr).encode())
            status = collected.returncode
    try:
        after = _tree_identity(root, candidate_paths, suites)
    except (OSError, ValueError):
        after = None
    if before != after or head != _head_commit(root):
        _say("::error title=govrev candidate proof mutated the tree::output/source/runtime inputs changed during collection or execution")
        _append_log_tail(log_path)
        return EXIT_TREE_MUTATED
    # Bound retained diagnostics without losing the terminal summary.
    payload = log_path.read_bytes()
    if len(payload) > 1048576:
        log_path.write_bytes(b"[earlier output truncated; retained final 1 MiB]\n" + payload[-1048576:])
    summary, passed = parse_pytest_summary(log_path.read_text(errors="replace"))
    if status != 0:
        _say("::error title=govrev candidate proof failed::refusing to publish an unproven candidate projection")
        _append_log_tail(log_path)
        return EXIT_PROOF_FAILED
    try:
        if re.search(r"\b[1-9][0-9]* deselected\b", collected.stdout + collected.stderr + log_path.read_text(errors="replace")):
            raise ValueError("deselected cases mean the named suites were incomplete")
        if collected.returncode != 0 or not nodeids or summary is None or passed < 1:
            raise ValueError("without a complete terminal summary/collection inventory")
        evidence = _complete_execution(nodeids, junit)
        if passed != evidence["passed"]:
            raise ValueError("terminal summary and JUnit counts disagree")
    except (OSError, ValueError, ET.ParseError) as exc:
        _say(f"::error::proof incomplete without a complete terminal summary and matching execution inventory: {exc}")
        _append_log_tail(log_path)
        return EXIT_INCOMPLETE_PROOF
    try:
        state_path = root / "data/government_revenue/candidate_projection_state.json"
        queue = json.loads((root / "data/government_revenue/candidate_queue.json").read_text())
        state = json.loads(state_path.read_text())
        generation = {"queue_content_id": queue["content_id"], "projection_generated_at": state["generated_at"],
                      "state_sha256": _sha256_bytes(state_path.read_bytes()),
                      "ledger_line_count": sum(bool(line.strip()) for line in (root / "data/government_revenue/candidate_ledger.jsonl").read_text().splitlines())}
        if not generation["queue_content_id"] or not generation["projection_generated_at"]:
            raise ValueError("empty generation identity")
    except (OSError, ValueError, KeyError, TypeError):
        return EXIT_RECEIPT_INVALID
    _seal_execution_artifacts(receipt_path, log_path, evidence)
    receipt = {"contract": RECEIPT_CONTRACT, "prover_version": PROVER_VERSION, "conclusion": "passed",
               "proved_at": datetime.now(timezone.utc).isoformat(), "source_checkout": head,
               "generation": generation, **before, "execution_evidence": evidence,
               "suite": {"pytest_version": _module_version("pytest"), "xdist_version": _module_version("xdist") if have_xdist else None,
                         "serial": not have_xdist, "argv": argv[1:]},
               "pytest_exit": status, "pytest_summary": summary}
    receipt["identity"] = receipt_identity(receipt)
    _atomic_write(receipt_path, _canonical(receipt) + "\n")
    _say(f"govrev candidate proof: PASSED ({summary}); receipt {receipt['identity'][:16]} binds complete inventory {len(nodeids)} cases")
    return 0


def _append_log_tail(log_path: Path, lines: int = 40) -> None:
    try:
        tail = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    except OSError:
        return
    for line in tail:
        _say(line)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=str(path.parent), prefix=path.name + ".", delete=False
    )
    try:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(handle.name, path)
    finally:
        if not handle.closed:
            handle.close()
        try:
            os.unlink(handle.name)
        except OSError:
            pass


def _committed_generation(root: Path, receipt: dict, commit: str) -> dict:
    result = _git(root, "ls-tree", "-r", "-z", commit, "--",
                  "data/government_revenue", "site")
    committed = {}
    for row in result.stdout.split("\0"):
        if not row:
            continue
        metadata_row, relative = row.split("\t", 1)
        static = relative in SHARED_OUTPUT_PATHS or (relative.startswith("site/government-revenue-") or relative.startswith("site/government_revenue")) and Path(relative).suffix in (".js", ".css", ".html")
        if not (relative.startswith("data/government_revenue/") or relative.startswith("site/government-revenue-data/") or static):
            continue
        mode, kind, oid = metadata_row.split()
        digest = receipt["outputs"].get(relative)
        if kind != "blob" or mode == "120000" or not digest or digest == "absent":
            raise ValueError(f"committed output lacks sealed byte identity: {relative}")
        # verify() already checked SHA256 against working bytes; Git's blob ID
        # now ties those exact bytes to the named committed generation.
        actual = _git(root, "hash-object", "--", relative).stdout.strip()
        if actual != oid:
            raise ValueError(f"committed bytes differ from sealed working bytes: {relative}")
        committed[relative] = {"git_blob": oid, "sha256": digest}
    ignored_inputs = []
    for relative, digest in receipt["outputs"].items():
        if digest == "absent" or relative in committed:
            continue
        if _git(root, "check-ignore", "-q", "--", relative, check=False).returncode != 0:
            raise ValueError(f"generated bytes were not committed: {relative}")
        ignored_inputs.append(relative)
    if not committed:
        raise ValueError("empty committed generation")
    return {"commit": commit, "artifacts": committed,
            "ignored_proof_inputs_not_published": sorted(ignored_inputs)}


EXIT_PUSH_UNKNOWN = 75
EXIT_PUSH_REFUSED = 76


def _origin_binding(root: Path) -> str:
    # get-url expands Git rewrites. Observe only the single actual push origin.
    fetch = _git(root, "remote", "get-url", "--all", "origin").stdout.splitlines()
    push = _git(root, "remote", "get-url", "--push", "--all", "origin").stdout.splitlines()
    if len(fetch) != 1 or fetch != push:
        raise ValueError("origin must have one identical fetch/push destination")
    return _sha256_bytes(fetch[0].encode())


def command_push_identity(args: argparse.Namespace) -> int:
    root, out = Path(args.root).resolve(), Path(args.out).resolve()
    if out.is_relative_to(root) or out.exists():
        return EXIT_PUSH_UNKNOWN
    try:
        receipt = _load_receipt(Path(args.receipt))
        if not receipt or _required_receipt_fields(receipt) or receipt_identity(receipt) != receipt["identity"]:
            return EXIT_RECEIPT_INVALID
        identity = {"contract": "government_revenue.push_identity.v1",
                    "expected_commit": _head_commit(root), "proof_identity": receipt["identity"],
                    "proof_receipt_sha256": _sha256_bytes(Path(args.receipt).read_bytes()),
                    "origin_binding_sha256": _origin_binding(root),
                    "run_id": os.environ.get("GITHUB_RUN_ID"),
                    "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
                    "push_attempt": args.attempt, "issuance_authority": False}
        identity["identity"] = _sha256_bytes(_canonical(identity).encode())
        _atomic_write(out, _canonical(identity) + "\n")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError, KeyError):
        return EXIT_PUSH_UNKNOWN


def _push_outcome(exit_code: int, body: bytes) -> str:
    if exit_code == 0:
        return "successful"
    text = body.decode("utf-8", errors="replace")
    if re.search(r"error: GH00[16]:|error: GH013:|permission denied|permission to .* denied", text, re.I):
        return "refused"
    if exit_code == 142 or len(body) > 131072:
        return "effect_unknown"
    updates = [line.strip() for line in text.splitlines() if " -> main" in line]
    if exit_code == 1 and len(updates) == 1 and re.fullmatch(
            r"! \[rejected\]\s+HEAD -> main \((?:fetch first|non-fast-forward|stale info)\)", updates[0]):
        return "definite_contention_rejection"
    return "effect_unknown"


def command_push_outcome(args: argparse.Namespace) -> int:
    out = Path(args.out).resolve()
    if out.is_relative_to(Path(args.root).resolve()):
        return EXIT_PUSH_UNKNOWN
    try:
        body = Path(args.log).read_bytes()
        outcome = "refused" if args.terminal_refusal else _push_outcome(args.exit_code, body)
        record = {"contract": "government_revenue.push_outcome.v1", "outcome": outcome,
                  "exit_code": args.exit_code, "response_bytes": len(body),
                  "response_sha256": _sha256_bytes(body), "issuance_authority": False}
        _atomic_write(out, _canonical(record) + "\n")
        return {"successful": 0, "definite_contention_rejection": 1,
                "refused": EXIT_PUSH_REFUSED, "effect_unknown": EXIT_PUSH_UNKNOWN}[outcome]
    except OSError:
        return EXIT_PUSH_UNKNOWN


def command_observe_push(args: argparse.Namespace) -> int:
    root, out = Path(args.root).resolve(), Path(args.out).resolve()
    if out.is_relative_to(root):
        return EXIT_PUSH_UNKNOWN
    record = {"contract": "government_revenue.push_observation.v1",
              "outcome": "effect_unknown", "issuance_authority": False,
              "serving_generation_authority": False, "observed_at": datetime.now(timezone.utc).isoformat()}
    try:
        identity = json.loads(Path(args.identity).read_text())
        claimed = identity.pop("identity")
        if claimed != _sha256_bytes(_canonical(identity).encode()):
            raise ValueError("identity_invalid")
        record.update({"push_identity": claimed, "proof_identity": identity["proof_identity"],
                       "expected_commit": identity["expected_commit"],
                       "origin_binding_sha256": identity["origin_binding_sha256"]})
        if (not args.historical and identity["expected_commit"] != _head_commit(root)) or identity["origin_binding_sha256"] != _origin_binding(root):
            raise ValueError("original_carrier_changed")
        # One bounded same-origin observation. Never issue another push here.
        ref = subprocess.run(["git", "-C", str(root), "ls-remote", "origin", "refs/heads/main"],
                             capture_output=True, text=True, check=True, timeout=20)
        rows = ref.stdout.splitlines()
        if len(rows) != 1:
            raise ValueError("original_effect_not_confirmed")
        observed, name = rows[0].split()
        if name != "refs/heads/main" or not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", observed):
            raise ValueError("invalid_remote_ref")
        record["observed_commit"] = observed
        expected = identity["expected_commit"]
        if expected != observed:
            history_args = ["--filter=blob:none", "--deepen=128"] if args.historical and _git(root, "rev-parse", "--is-shallow-repository").stdout.strip() == "true" else []
            subprocess.run(["git", "-C", str(root), "fetch", "--no-tags", "--no-write-fetch-head", *history_args, "origin", observed, expected],
                           capture_output=True, check=True, timeout=20)
            ancestor = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", expected, observed],
                                      capture_output=True, timeout=5)
            if ancestor.returncode:
                raise ValueError("original_effect_not_confirmed")
        record.update({"outcome": "original_effect_confirmed", "current_ref_equals_expected": expected == observed})
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        # Do not retain Git errors/URLs: they can contain provisioned credentials.
        record["reason"] = "same_origin_observation_did_not_confirm_original_commit"
    _atomic_write(out, _canonical(record) + "\n")
    return 0 if record["outcome"] == "original_effect_confirmed" else EXIT_PUSH_UNKNOWN


def command_publication_witness(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    if out.is_relative_to(root) or args.commit != _head_commit(root):
        return EXIT_WITNESS_MISMATCH
    args.committed = True
    status = command_verify(args)
    if status:
        return status
    receipt = _load_receipt(Path(args.receipt))
    generation = _committed_generation(root, receipt, args.commit)
    observation = None
    if args.push_status == "successful_after_same_carrier_observation":
        try:
            observation_path = Path(args.push_observation)
            observation = json.loads(observation_path.read_text())
            if (observation.get("outcome") != "original_effect_confirmed"
                    or observation.get("expected_commit") != args.commit
                    or observation.get("proof_identity") != receipt["identity"]
                    or observation.get("origin_binding_sha256") != _origin_binding(root)):
                return EXIT_PUSH_UNKNOWN
        except (OSError, ValueError, TypeError, subprocess.SubprocessError):
            return EXIT_PUSH_UNKNOWN
    witness = {"contract": "government_revenue.publication_witness.v1",
               "proof_identity": receipt["identity"], "generation": receipt["generation"],
               "committed_generation": generation, "push_status": args.push_status,
               "push_status_source": "same_origin_original_commit_observation" if observation else "publisher workflow successful push_do branch",
               "push_observation_sha256": _sha256_bytes(Path(args.push_observation).read_bytes()) if observation else None,
               "observed_remote_commit": observation.get("observed_commit") if observation else args.commit,
               "serving_generation_authority": False,
               "observed_at": datetime.now(timezone.utc).isoformat(),
               "issuance_authority": False}
    _atomic_write(out, _canonical(witness) + "\n")
    return 0


def command_verify(args: argparse.Namespace) -> int:
    """Exact-generation witness: does the accepted proof cover THIS tree?

    Acceptance requires all three, in order — a source change never reuses
    a proof blindly:

    1. the receipt is complete and self-consistent (identity digest matches);
    2. every output byte and every source dependency hash is unchanged;
    3. nothing MATERIAL moved between the proved checkout and HEAD (the
       lane's own published outputs are exempt; its inputs are not).
    """
    root = Path(args.root).resolve()
    receipt_path = Path(args.receipt)
    suites: tuple[str, ...] = tuple(args.suite or ()) or DEFAULT_SUITES
    candidate_paths: tuple[str, ...] = tuple(args.candidate_path or ()) or DEFAULT_CANDIDATE_PATHS

    if not receipt_path.exists():
        _say(
            "::error title=govrev candidate proof receipt missing::publication "
            "of candidate artifacts requires a complete proof receipt; none "
            "was minted this run"
        )
        return EXIT_RECEIPT_INVALID
    receipt = _load_receipt(receipt_path)
    if receipt is None:
        _say(
            "::error title=govrev candidate proof receipt unreadable::the "
            "proof receipt exists but does not parse; treating it as partial"
        )
        return EXIT_RECEIPT_INVALID
    missing = _required_receipt_fields(receipt)
    if missing:
        _say(
            "::error title=govrev candidate proof receipt partial::missing or "
            f"wrong-valued fields: {', '.join(sorted(set(missing)))}; refusing"
        )
        return EXIT_RECEIPT_INVALID
    if not _execution_artifacts_match(receipt_path, receipt):
        _say("::error::sealed proof log/collection/JUnit evidence missing or altered")
        return EXIT_RECEIPT_INVALID
    if receipt_identity(receipt) != receipt["identity"]:
        _say(
            "::error title=govrev candidate proof receipt tampered::the "
            "receipt's identity digest does not match its contents; refusing"
        )
        return EXIT_RECEIPT_INVALID

    try:
        current = _tree_identity(root, candidate_paths, suites)
    except (OSError, ValueError) as exc:
        _say(f"::error::current proof inputs unavailable: {exc}")
        return EXIT_WITNESS_MISMATCH
    if current["outputs"] != receipt["outputs"]:
        _say(
            "::error title=govrev candidate proof output drift::the candidate "
            "bytes in this tree differ from the proved generation — reprove "
            "before publishing"
        )
        return EXIT_WITNESS_MISMATCH
    if current["source_dependencies"] != receipt["source_dependencies"]:
        _say(
            "::error title=govrev candidate proof source drift::a source "
            "dependency the suites read directly differs from the proved "
            "generation — reprove before publishing"
        )
        return EXIT_WITNESS_MISMATCH
    if current["inputs"] != receipt["inputs"]:
        _say(
            "::error title=govrev candidate proof suite drift::the suite "
            "files in this tree differ from the ones the accepted proof ran "
            "— reprove before publishing"
        )
        return EXIT_WITNESS_MISMATCH

    delta = _git(
        root, "diff", "--name-only", f"{receipt['source_checkout']}..HEAD", check=False
    )
    if delta.returncode != 0:
        _say(
            "::error title=govrev candidate proof checkout unreachable::the "
            "proved checkout could not be diffed — reprove before publishing"
        )
        return EXIT_WITNESS_MISMATCH
    changed = {line for line in delta.stdout.splitlines() if line}
    material = sorted(
        path
        for path in changed
        if path not in receipt["outputs"]
        and any(path.startswith(prefix) for prefix in MATERIAL_PREFIXES)
    )
    if material:
        _say(
            "::error title=govrev candidate proof material source change::"
            f"material paths moved since the proved checkout ({', '.join(material[:8])}"
            f"{' …' if len(material) > 8 else ''}) — the accepted proof cannot "
            "be reused for this generation; reprove"
        )
        return EXIT_WITNESS_MISMATCH

    if getattr(args, "committed", False):
        try:
            _committed_generation(root, receipt, _head_commit(root))
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            _say(f"::error::committed generation witness refused: {exc}")
            return EXIT_WITNESS_MISMATCH

    _say(
        "govrev candidate proof witness: accepted proof "
        f"{receipt['identity'][:16]}… covers this generation exactly "
        f"(outputs, source dependencies, and checkout delta all identical)."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    fp = sub.add_parser("fingerprint", help="content inventory of data/government_revenue")
    fp.add_argument("--root", default=".")
    fp.add_argument("--data-dir", default="data/government_revenue")
    fp.add_argument("--out", required=True)
    fp.set_defaults(func=command_fingerprint)

    prove = sub.add_parser("prove", help="run the candidate suites and mint a proof receipt")
    prove.add_argument("--root", default=".")
    prove.add_argument("--receipt", required=True)
    prove.add_argument("--log", required=True)
    prove.add_argument("--data-dir", default="data/government_revenue")
    prove.add_argument(
        "--suite",
        action="append",
        default=None,
        help="suite path (repeatable; default: the three armed candidate suites)",
    )
    prove.add_argument(
        "--candidate-path",
        action="append",
        default=None,
        help="candidate artifact path (repeatable; default: the four candidate artifacts)",
    )
    prove.add_argument(
        "--install-missing",
        action="store_true",
        help="attempt `pip install` for pytest/pytest-xdist when absent (live lane)",
    )
    prove.add_argument(
        "--simulate-pytest-unavailable",
        action="store_true",
        help="TEST SEAM: behave as if pytest were not installed",
    )
    prove.add_argument(
        "--simulate-xdist-unavailable",
        action="store_true",
        help="TEST SEAM: behave as if pytest-xdist were not installed",
    )
    prove.set_defaults(func=command_prove)

    verify = sub.add_parser("verify", help="exact-generation witness against an accepted receipt")
    verify.add_argument("--root", default=".")
    verify.add_argument("--receipt", required=True)
    verify.add_argument("--suite", action="append", default=None)
    verify.add_argument("--candidate-path", action="append", default=None)
    verify.add_argument("--committed", action="store_true", help="also require the sealed generation's bytes in HEAD")
    verify.set_defaults(func=command_verify)

    witness = sub.add_parser("publication-witness", help="record exact committed generation after the publisher observes push success")
    witness.add_argument("--root", default=".")
    witness.add_argument("--receipt", required=True)
    witness.add_argument("--suite", action="append", default=None)
    witness.add_argument("--candidate-path", action="append", default=None)
    witness.add_argument("--commit", required=True)
    witness.add_argument("--push-status", choices=("successful", "successful_after_same_carrier_observation"), required=True)
    witness.add_argument("--push-observation")
    witness.add_argument("--out", required=True)
    witness.set_defaults(func=command_publication_witness)
    identity = sub.add_parser("push-identity", help="pin the original publisher commit and single origin before push")
    identity.add_argument("--root", default=".")
    identity.add_argument("--receipt", required=True)
    identity.add_argument("--attempt", required=True)
    identity.add_argument("--out", required=True)
    identity.set_defaults(func=command_push_identity)
    outcome = sub.add_parser("push-outcome", help="sanitize/classify one push response without replay")
    outcome.add_argument("--root", default=".")
    outcome.add_argument("--exit-code", required=True, type=int)
    outcome.add_argument("--log", required=True)
    outcome.add_argument("--terminal-refusal", action="store_true")
    outcome.add_argument("--out", required=True)
    outcome.set_defaults(func=command_push_outcome)
    observe = sub.add_parser("observe-push", help="one bounded read of the original origin; never retry a push")
    observe.add_argument("--root", default=".")
    observe.add_argument("--identity", required=True)
    observe.add_argument("--historical", action="store_true", help="read-only reconciliation of an authenticated retained prior-run identity")
    observe.add_argument("--out", required=True)
    observe.set_defaults(func=command_observe_push)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
