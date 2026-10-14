#!/usr/bin/env python3
"""SNI-local DRAFT full-coverage seal verifier (SCHK).

Independent of residual/ and event_response/ `--check` subsets (XREP-01/02/05).
Regenerates each sealed v1.1 study from a pinned input ref into a /tmp
directory and byte-compares EVERY committed file in the run directory.

Float tolerance (named, bounded, reported -- never silent). The committed
seal was cut on Linux x86_64, and a Linux re-execution reproduces every byte
(XREP receipt). A macOS arm64 re-execution differs only in the last digits of
float tokens in a handful of text files (measured 2026-10-13: 10 S1 P03
files, worst relative difference 4.62e-12, worst absolute 5.50e-14; the
text skeleton and every integer token are identical). By default a differing
TEXT file whose skeleton and integer tokens match exactly and whose float
tokens all agree within ULP_REL_TOL / ULP_ABS_TOL is reported as
``ulp-equivalent`` -- counted separately, never as identical and never as a
failure. Binary files, exception-handled files, any structural or integer
difference, and any float difference beyond tolerance stay failures.
``--strict-bytes`` turns the tolerance off. Byte identity of the seal rests
on the Linux receipt, not on a tolerant run.

This module is an SNI-local DRAFT contract that CONSUMES owner-supplied
values. It does not re-implement Data OS identity, Company Event/Earnings,
FIF, Capital Structure, Stock Identity, Options, Research Vault, or
qledger/Evaluation. Identity ids are caller-supplied opaque strings; this
module never mints, derives, or guesses canonical HK/US issuer or security
identifiers. Unknown identity stays UNRESOLVED / null.

Authority flags stay false everywhere they are written here. Nothing in this
module feeds a ranker, gate, sizer, signal, escalation, or trade path. A
caller that tries to set any of rank_authority, gate_authority,
size_authority, signal_authority, escalation_authority, trade_authority
true is refused (raised).

Residual and event-response statistics that the runners emit are DESCRIPTIVE.
They are never causal, never "news impact" (A24), never a forecast, signal,
or validation. An unestimable family ABSTAINS with a named reason; this
verifier never substitutes a default 50/50 (A25). Then-known views are not
reconstructed here: the runners already own as-of inputs via the pinned
input_ref.

REGISTERED = False. This file does not write qledger and does not cut a seal.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

REGISTERED = False

AUTHORITY_KEYS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)
AUTHORITY_FLAGS = {
    "rank_authority": False,
    "gate_authority": False,
    "size_authority": False,
    "signal_authority": False,
    "escalation_authority": False,
    "trade_authority": False,
}

INPUT_REF_DEFAULT = "5ef7a7f39f99232bf9b574c7603da1011ee3af66"

S1_V1_1_REL = "research/single_name_intelligence/runs/s1_residual_v1_1"
S2_V1_1_REL = "research/single_name_intelligence/runs/s2_event_response_v1_1"
S1_V1_REL = "research/single_name_intelligence/runs/s1_residual"
S2_V1_REL = "research/single_name_intelligence/runs/s2_event_response"

# Confirmed from committed S1 v1.1 SEAL_AND_BUDGET.json.
S1_V1_1_TRIAL_LEDGER_PATH = (
    "research/single_name_intelligence/runs/s1_residual_v1_1/trial_ledger.jsonl"
)
# s1_prereg.RUNS_REL fallback used when build_seal out_dir is outside the repo.
S1_V1_TRIAL_LEDGER_PATH = (
    "research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl"
)
# Confirmed from committed S2 v1.1 SEAL_AND_BUDGET.json (v1 path; XREP-04).
S2_V1_TRIAL_LEDGER_PATH = (
    "research/single_name_intelligence/runs/s2_event_response/trial_ledger.jsonl"
)
# Confirmed from committed S2 v1.1 LANE_MANIFEST.json (v1.1 path; XREP-04).
S2_V1_1_TRIAL_LEDGER_PATH = (
    "research/single_name_intelligence/runs/s2_event_response_v1_1/trial_ledger.jsonl"
)

KIND_MISSING = "missing-in-produced"
KIND_EXTRA = "extra-in-produced"
KIND_DIFFER = "bytes-differ"
KIND_ULP = "ulp-equivalent"

# Float tolerance for a cross-platform re-execution. Two orders of magnitude
# above the worst measured macOS-vs-Linux drift (rel 4.62e-12, abs 5.50e-14).
ULP_REL_TOL = 1e-10
ULP_ABS_TOL = 1e-13
ULP_TEXT_SUFFIXES = (".json", ".jsonl", ".md", ".csv", ".tsv", ".txt")
_NUM = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w.])")

ExceptionFn = Callable[[Path, Path], list["Diff"]]


@dataclass(frozen=True)
class Diff:
    kind: str
    relpath: str
    detail: str = ""


@dataclass
class StudyResult:
    name: str
    compared: int = 0
    identical: int = 0
    named_exception_passes: int = 0
    failures: int = 0
    ulp_equivalent: int = 0
    host_platform: str = ""
    diffs: list[Diff] = field(default_factory=list)


def refuse_nonfalse_authority(flags=None) -> None:
    """Raise if any authority flag is not literal False.

    Accepts the six ``*_authority`` keys and the short S1 names
    rank/gate/size/signal/escalation/trade. Nested dicts and lists are
    walked. A caller that tries to set any of them true is refused.
    """
    obj = AUTHORITY_FLAGS if flags is None else flags
    _walk_authority(obj, path="")


def _walk_authority(obj, *, path: str) -> None:
    names = set(AUTHORITY_KEYS)
    short = {k[: -len("_authority")] for k in AUTHORITY_KEYS}
    if isinstance(obj, dict):
        for k, v in obj.items():
            here = f"{path}.{k}" if path else str(k)
            folded = str(k).strip().casefold()
            if folded in names or folded in short or folded.endswith("_authority"):
                if v is not False:
                    raise ValueError(
                        f"authority flag {k!r} is not literal False (got {v!r} at {here})"
                    )
            if isinstance(v, (dict, list)):
                _walk_authority(v, path=here)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, (dict, list)):
                _walk_authority(item, path=f"{path}[{i}]")
    elif obj is not None and obj is not False and path:
        # Non-container payload with no keys: nothing to refuse.
        return


def rel_files(root: Path) -> set[str]:
    """Every regular file under root, as posix paths relative to root."""
    out: set[str] = set()
    if not root.exists():
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            p = Path(dirpath) / name
            if p.is_file():
                out.add(p.relative_to(root).as_posix())
    return out


def _is_float_token(tok: str) -> bool:
    return any(c in tok for c in ".eE")


def ulp_equivalent(a: bytes, b: bytes) -> tuple[bool, int, float]:
    """Float-tolerant text equality. Pure: no I/O.

    Returns (equivalent, differing float tokens, worst relative difference).
    Equivalent only when both sides decode as UTF-8, the text with every
    numeric token masked is identical, every integer token is identical,
    no token changes between integer and float spelling, and every float
    token pair satisfies math.isclose(rel_tol=ULP_REL_TOL,
    abs_tol=ULP_ABS_TOL).
    """
    try:
        ta = a.decode("utf-8")
        tb = b.decode("utf-8")
    except UnicodeDecodeError:
        return False, 0, 0.0
    if _NUM.sub("#", ta) != _NUM.sub("#", tb):
        return False, 0, 0.0
    na = _NUM.findall(ta)
    nb = _NUM.findall(tb)
    if len(na) != len(nb):
        return False, 0, 0.0
    n_diff = 0
    worst = 0.0
    for x, y in zip(na, nb):
        if x == y:
            continue
        if not (_is_float_token(x) and _is_float_token(y)):
            return False, n_diff, worst
        fx, fy = float(x), float(y)
        if not math.isclose(fx, fy, rel_tol=ULP_REL_TOL, abs_tol=ULP_ABS_TOL):
            return False, n_diff, worst
        n_diff += 1
        scale = max(abs(fx), abs(fy))
        if scale:
            worst = max(worst, abs(fx - fy) / scale)
    return True, n_diff, worst


def walk_compare(
    committed_dir: Path,
    produced_dir: Path,
    exceptions: dict[str, ExceptionFn] | None = None,
    *,
    ulp_tolerant: bool = False,
) -> list[Diff]:
    """Pure recursive comparator. No git, no subprocess, no network.

    Walks every file under committed_dir and every file under produced_dir.
    Returns missing-in-produced, extra-in-produced, and bytes-differ. A
    relative path that is a key of ``exceptions`` is compared by that
    callable instead of raw bytes; the callable returns a (possibly empty)
    list of Diff. With ``ulp_tolerant`` a differing non-exception text file
    that passes ``ulp_equivalent`` is reported as ulp-equivalent instead of
    bytes-differ; the default is strict bytes.
    """
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    exceptions = exceptions or {}
    committed_dir = Path(committed_dir)
    produced_dir = Path(produced_dir)
    c_files = rel_files(committed_dir)
    p_files = rel_files(produced_dir)
    diffs: list[Diff] = []
    for rel in sorted(c_files - p_files):
        diffs.append(Diff(KIND_MISSING, rel))
    for rel in sorted(p_files - c_files):
        diffs.append(Diff(KIND_EXTRA, rel))
    for rel in sorted(c_files & p_files):
        c_path = committed_dir / rel
        p_path = produced_dir / rel
        fn = exceptions.get(rel)
        if fn is not None:
            diffs.extend(fn(c_path, p_path))
            continue
        c_bytes = c_path.read_bytes()
        p_bytes = p_path.read_bytes()
        if c_bytes == p_bytes:
            continue
        if ulp_tolerant and rel.endswith(ULP_TEXT_SUFFIXES):
            ok, n_tok, worst = ulp_equivalent(c_bytes, p_bytes)
            if ok:
                diffs.append(Diff(
                    KIND_ULP, rel,
                    f"{n_tok} float tokens within tolerance, worst rel {worst:.2e}",
                ))
                continue
        diffs.append(Diff(KIND_DIFFER, rel))
    return diffs


def XREP03_S1_SEAL_LEDGER_PATH(committed: Path, produced: Path) -> list[Diff]:
    """XREP-03: S1 v1.1 SEAL_AND_BUDGET.json / .md embed trial_ledger_path.

    residual/build_seal.py ~L155 stamps trial_ledger_path from _runs_rel
    (~L182-186), which falls back to s1_prereg.RUNS_REL when out_dir is
    outside the repo. A /tmp regeneration therefore differs only in that
    field. This callable parses both sides, requires every other field to
    match, and asserts the COMMITTED value is exactly
    S1_V1_1_TRIAL_LEDGER_PATH. Any other differing field is a failure.
    """
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    if committed.suffix == ".json":
        return _xrep03_json(committed, produced)
    return _xrep03_md(committed, produced)


def _xrep03_json(committed: Path, produced: Path) -> list[Diff]:
    rel = committed.name
    try:
        c_obj = json.loads(committed.read_text(encoding="utf-8"))
        p_obj = json.loads(produced.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [Diff(KIND_DIFFER, rel, f"SEAL JSON parse failed: {e}")]
    diffs: list[Diff] = []
    c_path = c_obj.get("trial_ledger_path")
    if c_path != S1_V1_1_TRIAL_LEDGER_PATH:
        diffs.append(Diff(
            KIND_DIFFER, rel,
            f"committed trial_ledger_path {c_path!r} != {S1_V1_1_TRIAL_LEDGER_PATH!r}",
        ))
    c_rest = {k: v for k, v in c_obj.items() if k != "trial_ledger_path"}
    p_rest = {k: v for k, v in p_obj.items() if k != "trial_ledger_path"}
    if c_rest != p_rest:
        extra = sorted(set(c_rest) ^ set(p_rest))
        changed = sorted(k for k in c_rest if k in p_rest and c_rest[k] != p_rest[k])
        diffs.append(Diff(
            KIND_DIFFER, rel,
            "SEAL_AND_BUDGET.json differs in a field other than trial_ledger_path "
            f"(XREP-03); extra_or_missing={extra} changed={changed}",
        ))
    return diffs


def _xrep03_md(committed: Path, produced: Path) -> list[Diff]:
    rel = committed.name
    prefix = "- trial_ledger_path:"

    def split(text: str) -> tuple[str | None, list[str]]:
        path_val = None
        rest: list[str] = []
        for line in text.splitlines():
            if line.startswith(prefix):
                path_val = line.split(":", 1)[1].strip()
                rest.append(prefix + " <XREP-03>")
            else:
                rest.append(line)
        return path_val, rest

    c_path, c_rest = split(committed.read_text(encoding="utf-8"))
    _p_path, p_rest = split(produced.read_text(encoding="utf-8"))
    diffs: list[Diff] = []
    if c_path != S1_V1_1_TRIAL_LEDGER_PATH:
        diffs.append(Diff(
            KIND_DIFFER, rel,
            f"committed trial_ledger_path {c_path!r} != {S1_V1_1_TRIAL_LEDGER_PATH!r}",
        ))
    if c_rest != p_rest:
        diffs.append(Diff(
            KIND_DIFFER, rel,
            "SEAL_AND_BUDGET.md differs in a field other than trial_ledger_path (XREP-03)",
        ))
    return diffs


def XREP04_S2_SEAL_V1_LEDGER_PATH(committed_dir: Path) -> list[Diff]:
    """XREP-04: assertion on committed S2 v1.1 bytes only.

    SEAL_AND_BUDGET.json trial_ledger_path equals the v1 path string
    (s2_seal.py L229 TRIAL_LEDGER_REL_PATH). LANE_MANIFEST.json
    trial_ledger_path equals the v1.1 path string (run_s2.py L70
    V1_1_LEDGER_REL). The known inconsistency is pinned so a silent change
    is caught; it is documented as known, not hidden. No regeneration
    difference is involved.
    """
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    diffs: list[Diff] = []
    seal_path = Path(committed_dir) / "SEAL_AND_BUDGET.json"
    lane_path = Path(committed_dir) / "LANE_MANIFEST.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    lane = json.loads(lane_path.read_text(encoding="utf-8"))
    got_seal = seal.get("trial_ledger_path")
    if got_seal != S2_V1_TRIAL_LEDGER_PATH:
        diffs.append(Diff(
            KIND_DIFFER, "SEAL_AND_BUDGET.json",
            f"committed seal trial_ledger_path {got_seal!r} != pinned v1 "
            f"{S2_V1_TRIAL_LEDGER_PATH!r}",
        ))
    got_lane = lane.get("trial_ledger_path")
    if got_lane != S2_V1_1_TRIAL_LEDGER_PATH:
        diffs.append(Diff(
            KIND_DIFFER, "LANE_MANIFEST.json",
            f"committed lane trial_ledger_path {got_lane!r} != pinned v1.1 "
            f"{S2_V1_1_TRIAL_LEDGER_PATH!r}",
        ))
    return diffs


def _s1_ledger_exception(committed: Path, produced: Path) -> list[Diff]:
    """S1 trial_ledger.jsonl: import run_s1._ledger_equal (drops wall-clock ts).

    Semantics: residual/run_s1.py L1133-1145.
    """
    # This file lives at research/single_name_intelligence/evaluation/; parents[3]
    # is the repo root. Do not derive the repo from committed/produced (/tmp).
    _prepare_s1_imports(Path(__file__).resolve().parents[3])
    import run_s1  # noqa: WPS433  — lazy; walk_compare stays import-free of runners
    if not run_s1._ledger_equal(committed, produced):
        return [Diff(
            KIND_DIFFER, "trial_ledger.jsonl",
            "S1 _ledger_equal (run_s1.py L1133-1145) reported a difference",
        )]
    return []


def _s2_ledger_exception(committed: Path, produced: Path) -> list[Diff]:
    """S2 trial_ledger.jsonl: ts-dropping compare from run_s2.run_check.

    run_s2.py L1072-1078 is inline (not a function); this reimplements that
    exact comparison: load JSONL rows, pop 'ts', json.dumps(..., sort_keys=True).
    """
    def rows(path: Path) -> list[dict]:
        out = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
               if line.strip()]
        for row in out:
            row.pop("ts", None)
        return out
    la = rows(committed)
    lb = rows(produced)
    if json.dumps(la, sort_keys=True) != json.dumps(lb, sort_keys=True):
        return [Diff(
            KIND_DIFFER, "trial_ledger.jsonl",
            "S2 ts-dropped ledger differs (run_s2.py L1072-1078)",
        )]
    return []


def s1_exceptions() -> dict[str, ExceptionFn]:
    return {
        "SEAL_AND_BUDGET.json": XREP03_S1_SEAL_LEDGER_PATH,
        "SEAL_AND_BUDGET.md": XREP03_S1_SEAL_LEDGER_PATH,
        "trial_ledger.jsonl": _s1_ledger_exception,
    }


def s2_exceptions() -> dict[str, ExceptionFn]:
    return {
        "trial_ledger.jsonl": _s2_ledger_exception,
    }


def input_ref_present(repo_root: Path, input_ref: str) -> bool:
    """True iff the commit object exists locally. Never fetches."""
    r = subprocess.run(
        ["git", "cat-file", "-e", f"{input_ref}^{{commit}}"],
        cwd=repo_root, capture_output=True,
    )
    return r.returncode == 0


def _porcelain(repo_root: Path) -> str:
    r = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root, capture_output=True, text=True, check=True,
    )
    return r.stdout


def _refuse_repo_out_dir(repo_root: Path, out_dir: Path) -> None:
    try:
        out_dir.resolve().relative_to(Path(repo_root).resolve())
    except ValueError:
        return
    raise RuntimeError(
        f"out_dir {out_dir} is inside the repository; regeneration writes only under /tmp"
    )


def _prepare_s1_imports(hint: Path) -> Path:
    """Put residual/ and repo root on sys.path. Locate repo_root from a path."""
    repo_root = hint
    for p in [hint, *hint.parents]:
        if (p / "research" / "single_name_intelligence" / "residual" / "run_s1.py").exists():
            repo_root = p
            break
    residual = repo_root / "research" / "single_name_intelligence" / "residual"
    for entry in (str(residual), str(repo_root)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    return repo_root


S1_BUILD_SEAL_MODULE = "sni_residual_build_seal"


def _load_s1_build_seal(repo_root: Path):
    """Load residual/build_seal.py by file path under a private module name.

    residual/ and event_response/ both ship a build_seal.py. A bare
    `import build_seal` binds whichever directory sits earlier on sys.path, or
    whatever is already cached in sys.modules, so a caller that put
    event_response/ first got the S2 builder (AttributeError: no build_all).
    Its sibling imports still resolve through residual/ on sys.path; those
    basenames are unique across the SNI subdirectories.
    """
    import importlib.util  # noqa: WPS433

    path = (Path(repo_root) / "research" / "single_name_intelligence" / "residual"
            / "build_seal.py").resolve()
    cached = sys.modules.get(S1_BUILD_SEAL_MODULE)
    if cached is not None and getattr(cached, "__file__", None) == str(path):
        return cached
    spec = importlib.util.spec_from_file_location(S1_BUILD_SEAL_MODULE, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load S1 seal builder from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[S1_BUILD_SEAL_MODULE] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(S1_BUILD_SEAL_MODULE, None)
        raise
    return module


def regenerate_s1(repo_root: Path, input_ref: str, out_dir: Path) -> None:
    """Invoke S1 the way residual/run_s1.py --check does, plus the seal builder.

    --check calls run_pipeline into a temp dir with ledger_file in that dir
    and ledger_arg equal to the committed v1.1 ledger path string
    (run_s1.py L1189-1194). This function does the same with out_dir under
    /tmp, then residual/build_seal.build_all into the same out_dir so every
    committed file has a produced counterpart. Never writes a repository path.
    """
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    repo_root = Path(repo_root).resolve()
    out_dir = Path(out_dir)
    _refuse_repo_out_dir(repo_root, out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    _prepare_s1_imports(repo_root)
    from s1_data import GitBlobStore  # noqa: WPS433
    from s1_prereg import AUTHORITY_FLAGS as S1_FLAGS  # noqa: WPS433
    from s1_prereg import BASE, INPUT_PINS, assert_authority_false  # noqa: WPS433
    import run_s1  # noqa: WPS433
    s1_build_seal = _load_s1_build_seal(repo_root)

    assert_authority_false(S1_FLAGS)
    store = GitBlobStore(repo_root, input_ref, dict(INPUT_PINS))
    store.verify_all()
    run_s1.DETECTED_AT = store.commit_date_iso(BASE)
    runs_rel = S1_V1_1_REL
    run_s1.run_pipeline(
        store, repo_root, out_dir, S1_V1_1_TRIAL_LEDGER_PATH,
        ledger_file=out_dir / "trial_ledger.jsonl",
        runs_rel=runs_rel,
    )
    s1_build_seal.build_all(repo_root, input_ref, out_dir)


def regenerate_s2(repo_root: Path, input_ref: str, out_dir: Path) -> None:
    """Invoke S2 the way event_response/run_s2.py --check does, plus the seal builder.

    run_check calls generate_outputs into a temp dir with the ledger file in
    that dir and --seal-dir the committed v1.1 run (run_s2.py L1058-1062).
    Seal artifacts are written by event_response/build_seal.py (XREP summary).
    Subprocess keeps residual/ and event_response/ module names from colliding.
    """
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    repo_root = Path(repo_root).resolve()
    out_dir = Path(out_dir)
    _refuse_repo_out_dir(repo_root, out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    runner = repo_root / "research" / "single_name_intelligence" / "event_response" / "run_s2.py"
    builder = repo_root / "research" / "single_name_intelligence" / "event_response" / "build_seal.py"
    seal_dir = repo_root / S2_V1_1_REL
    r1 = subprocess.run(
        [sys.executable, str(runner),
         "--input-ref", input_ref,
         "--out-dir", str(out_dir),
         "--trial-ledger-path", str(out_dir / "trial_ledger.jsonl"),
         "--seal-dir", str(seal_dir),
         "--repo-root", str(repo_root)],
        cwd=str(repo_root), env=env, capture_output=True, text=True,
    )
    if r1.returncode != 0:
        raise RuntimeError(
            f"S2 generate_outputs exited {r1.returncode}: {r1.stderr[-4000:]}"
        )
    r2 = subprocess.run(
        [sys.executable, str(builder),
         "--input-ref", input_ref,
         "--out-dir", str(out_dir),
         "--repo-root", str(repo_root)],
        cwd=str(repo_root), env=env, capture_output=True, text=True,
    )
    if r2.returncode != 0:
        raise RuntimeError(
            f"S2 build_seal exited {r2.returncode}: {r2.stderr[-4000:]}"
        )


def check_study(
    name: str,
    repo_root: Path,
    input_ref: str,
    out_dir: Path,
    *,
    strict_bytes: bool = False,
) -> StudyResult:
    """Regenerate one study into out_dir and full-compare against the committed run.

    Unless ``strict_bytes``, float-only last-digit differences in text files
    are counted as ulp_equivalent (see module docstring), never as identical.
    """
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    repo_root = Path(repo_root).resolve()
    if name == "s1":
        committed = repo_root / S1_V1_1_REL
        exceptions = s1_exceptions()
        regenerate_s1(repo_root, input_ref, out_dir)
    elif name == "s2":
        committed = repo_root / S2_V1_1_REL
        exceptions = s2_exceptions()
        regenerate_s2(repo_root, input_ref, out_dir)
    else:
        raise ValueError(f"unknown study {name!r}")

    diffs = walk_compare(committed, out_dir, exceptions, ulp_tolerant=not strict_bytes)
    c_files = rel_files(committed)
    p_files = rel_files(out_dir)
    compared = c_files | p_files
    exception_rels = set(exceptions)
    identical = 0
    named_ok = 0
    for rel in compared:
        if rel in exception_rels and rel in c_files and rel in p_files:
            if not any(d.relpath == rel for d in diffs):
                named_ok += 1
        elif rel in c_files and rel in p_files and rel not in exception_rels:
            if not any(d.relpath == rel for d in diffs):
                identical += 1

    if name == "s2":
        pin_diffs = XREP04_S2_SEAL_V1_LEDGER_PATH(committed)
        diffs.extend(pin_diffs)
        if pin_diffs:
            pass
        else:
            named_ok += 1  # XREP-04 pin held on committed bytes

    ulp = sum(1 for d in diffs if d.kind == KIND_ULP)
    return StudyResult(
        name=name,
        compared=len(compared),
        identical=identical,
        named_exception_passes=named_ok,
        failures=len(diffs) - ulp,
        ulp_equivalent=ulp,
        host_platform=f"{platform.system()} {platform.machine()}",
        diffs=diffs,
    )


def _print_result(res: StudyResult) -> None:
    print(
        f"{res.name}: files compared={res.compared} identical={res.identical} "
        f"named-exception passes={res.named_exception_passes} "
        f"ulp-equivalent={res.ulp_equivalent} failures={res.failures} "
        f"[{res.host_platform}]"
    )
    for d in res.diffs:
        extra = f" ({d.detail})" if d.detail else ""
        print(f"  {d.kind}: {d.relpath}{extra}")


def main(argv: list[str] | None = None) -> int:
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--study", choices=("s1", "s2", "all"), required=True)
    ap.add_argument("--input-ref", default=INPUT_REF_DEFAULT)
    ap.add_argument("--repo-root", default=None)
    ap.add_argument(
        "--strict-bytes", action="store_true",
        help="disable the float tolerance; every differing byte is a failure",
    )
    args = ap.parse_args(argv)

    if args.repo_root:
        repo_root = Path(args.repo_root).resolve()
    else:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            print("not inside a git checkout; pass --repo-root", file=sys.stderr)
            return 2
        repo_root = Path(proc.stdout.strip()).resolve()

    if not input_ref_present(repo_root, args.input_ref):
        print("SEAL FULL CHECK: REFUSED (input_ref absent; never fetched)")
        return 2

    names = ("s1", "s2") if args.study == "all" else (args.study,)
    before = _porcelain(repo_root)
    results: list[StudyResult] = []
    failed = False
    try:
        for name in names:
            tmp = Path(tempfile.mkdtemp(prefix=f"schk_{name}_", dir="/tmp"))
            res = check_study(
                name, repo_root, args.input_ref, tmp,
                strict_bytes=args.strict_bytes,
            )
            _print_result(res)
            results.append(res)
            if res.failures:
                failed = True
    finally:
        after = _porcelain(repo_root)
        if after != before:
            print("SEAL FULL CHECK: DIFFERS", file=sys.stderr)
            print("git status --porcelain changed after regeneration:", file=sys.stderr)
            print(after, file=sys.stderr)
            return 1

    if failed:
        print("SEAL FULL CHECK: DIFFERS")
        return 1
    ulp_total = sum(r.ulp_equivalent for r in results)
    if ulp_total:
        host = results[0].host_platform if results else ""
        print(
            f"SEAL FULL CHECK: OK ({ulp_total} files float-equivalent on {host} "
            f"within rel {ULP_REL_TOL:g} / abs {ULP_ABS_TOL:g}, not byte-identical; "
            "byte identity rests on the XREP Linux receipt)"
        )
        return 0
    print("SEAL FULL CHECK: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
