"""Rotation Core v2 — two-key defensive-rotation evaluation on Ken French 49 industries (corrected v1 engine).

Implements protocol_header_v2 (draft rev 7; the frozen JSON governs once it exists). Pure functions; research only.
Nothing here sizes, gates, ranks, alerts or trades.

Seal: any input path under `sealed_post2019/` is refused unless research/rotation_core/HOLDOUT_RELEASE_v2.json is
committed and clean; every loader also truncates at the caller's `end` before computing anything.
"""
from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from engine import rotation_core_evaluation as rc

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "research/rotation_core/HOLDOUT_RELEASE_v2.json"
SEALED_MARK = "sealed_post2019"
FROZEN_V2_SHA256 = "ca5af27429b54df534e959bde8a3db037c95f7fe5c7c430fe7e6bb5b03d01728"
HEADER_V2 = ROOT / "research/rotation_core/protocol_header_v2.json"
GRID = [(3, 25.0), (3, 37.5), (5, 25.0), (5, 37.5)]


def verify_header_v2(path=HEADER_V2, expected: str = FROZEN_V2_SHA256) -> dict:
    """Refuse any header bytes other than the frozen v2 header."""
    import hashlib, json
    raw = Path(path).read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != expected:
        raise rc.HeaderMismatch(f"protocol header v2 sha256 {got} != frozen {expected}")
    return json.loads(raw)      # (h near-high %, b breadth-drop pp)
FEE_INDUSTRY_BP = 10.0
FEE_FUND_BP = 5.0


class SealedRefusal(PermissionError):
    pass


RELEASE2 = ROOT / "research/rotation_core/HOLDOUT_RELEASE_v2_stage2.json"
W_PRE = "pre1998_1928_1997"
W_H = "2020-01-02..2025-12-31"
PRE_END = pd.Timestamp("1997-12-31")
H_START, H_END = pd.Timestamp("2020-01-02"), pd.Timestamp("2025-12-31")


def _committed_clean(path: Path, root: Path = None) -> bool:
    root = Path(root or ROOT)
    try:
        rel = str(Path(path).resolve().relative_to(root.resolve()))
    except ValueError:
        return False                                   # outside the repo: never counts as committed
    try:
        _git("ls-files", "--error-unmatch", rel, root=root)
    except subprocess.CalledProcessError:
        return False
    st = _git("status", "--porcelain", "--", rel, root=root, check=False)
    if st.returncode != 0:
        raise SealedRefusal("refused: git status failed")
    return st.stdout.strip() == b""


# R29.2: inside a run, every repository file the runner reads is read as a blob at the fetched head of its repository.
_READ = {"root": None, "sha": None}


def set_read_head(root, sha) -> None:
    _READ["root"], _READ["sha"] = (str(Path(root).resolve()), sha) if root is not None else (None, None)


def _read_head_for(path):
    import os
    if _READ["root"] is None:
        return None
    rp = os.path.realpath(str(path))
    if rp.startswith(_READ["root"] + os.sep):
        return _READ["root"], _READ["sha"], os.path.relpath(rp, _READ["root"])
    return None


def read_repo_bytes(path, root=None) -> bytes | None:
    """A repository file as a blob at the fetched head (inside a run), never the working tree; None if absent from
    that tree. Refuses if the path carries a skip-worktree or assume-unchanged flag. Outside a run (a direct call,
    declared under R27.0) the committed working-tree file."""
    h = _read_head_for(path)
    if h is None:
        return Path(path).read_bytes() if (Path(path).exists() and _committed_clean(path, root)) else None
    r, sha, rel = h
    check_read_flags(r, [rel])
    return blob_at(sha, rel, r)


def load_release_blob(path: Path, root: Path = None) -> tuple:
    """R31.1(a): the release document AND the sha256 of the exact blob bytes parsed (None, None if absent)."""
    import json
    b = read_repo_bytes(path, root)
    return (None, None) if b is None else (json.loads(b), sha256_bytes(b))


def _load_release(path: Path, root: Path = None) -> dict | None:
    """The release document, carrying `_blob_sha256` (the hash START records, R31.1(a))."""
    doc, sha = load_release_blob(path, root)
    if doc is not None:
        doc["_blob_sha256"] = sha
    return doc


SELECTION_RESULT = ROOT / "research/rotation_core/results_v2_selection_rerun.json"   # R15: rerun pins the setting
SELECTED_REF = (3.0, 25.0)            # grid point selected at 1ca5228b3c (R13-g(i)); R14(d) sensitivity uses it


def selected_setting(selection: Path, root: Path = None) -> tuple[float, float]:
    """R13-g(i)/R15.6/R29.2: the gate setting is read from the committed selection result (a blob at the fetched
    head inside a run), never from a free argument; the path is required (R29.5)."""
    import json, re
    if selection is None:
        raise SealedRefusal("refused: the selection result path is required")
    b = read_repo_bytes(selection, root)
    if b is None:
        raise SealedRefusal("refused: selection result is not committed")
    sel = json.loads(b)["selection"]["selected"]
    m = re.fullmatch(r"h(\d+)_b([\d.]+)", sel)
    return float(m.group(1)), float(m.group(2))


BRANCH = "fable/rotation-core-20261110"
REMOTE = "origin"
REMOTE_URL = "https://github.com/mastermindx-market-intelligence/macro.git"      # R23.3: pinned identity
GH_REPO = "mastermindx-market-intelligence/macro"
ANCHOR_COMMIT = "ac68f2e72a4de055c36b048cb02301ccd7544964"                      # R22.1(c): header freeze commit
RULESET_ID = 27041175                                                           # R23.2
REMOTE_REF = f"{REMOTE}/{BRANCH}"
OPENING_HYPOTHESES = ("H1", "H3")       # R16 S1c: constant; no release can name or change it
ERAS_GATE = ("E1_1928_1945", "E2_1946_1997")
GATE_READINGS, GATE_COSTS = ("eq", "drift"), ("base", "strict")
PINNED_PATHS = ["engine", "scripts", "tests", "research/rotation_core/protocol_header_v2.json",
                "research/rotation_core/results_v2_selection.json",                 # superseded 2x rows (R18.3)
                "research/rotation_core/v2_power/FRENCH_SEALED_FULL_FILES_SHA256.txt",  # recorded sealed hashes
                "research/rotation_core/v2_power/REAL_INPUT_SHA256.txt"]               # R28.3 readable real inputs
COVERED_MODULE_PREFIXES = ("engine.", "scripts.", "tests.")
LEDGER = ROOT / "research/rotation_core/results_v2_run_ledger.json"
SEALED_RECORD = ROOT / "research/rotation_core/v2_power/FRENCH_SEALED_FULL_FILES_SHA256.txt"


class LedgerPushFailed(SealedRefusal):
    pass


RECORD_KINDS = ("GATE", "REPRODUCTION_OK", "FINAL")
OBJ_DIR_PREFIX = "rc_ledger_objects_"
PROXY_VARS = ("http_proxy", "https_proxy", "all_proxy")


def check_env_vars() -> None:
    """R26.4: no inherited GIT_* / GH_* variable and no proxy variable (either case)."""
    import os
    for k in os.environ:
        if k.startswith(("GIT_", "GH_")) or k.lower() in PROXY_VARS:
            raise SealedRefusal(f"refused: the environment variable {k} is set")


RUNTIME_REFUSED = ("LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT", "TMPDIR", "TEMP", "TMP")
OBJ_BASE = "/dev/shm"          # R27.2: the private object directory never touches a disk
LOCK_PATH = "/dev/shm/rotation_core_v2.lock"
SYSTEM_TMP = "/tmp"            # TMPDIR / TEMP / TMP are refused, so this is the system temporary directory


def no_core() -> None:
    """R27.6: no core file and no apport report: RLIMIT_CORE = 0 (inherited by children) and PR_SET_DUMPABLE = 0.
    Refuses if either call fails."""
    import ctypes, resource
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(4, 0, 0, 0, 0) != 0:                    # PR_SET_DUMPABLE = 4
            raise OSError(ctypes.get_errno(), "prctl")
        if libc.prctl(3, 0, 0, 0, 0) != 0:                    # PR_GET_DUMPABLE = 3 -> must read 0
            raise OSError("dumpable")
    except (OSError, ValueError, AttributeError) as e:
        raise SealedRefusal(f"refused: could not disable core dumps ({type(e).__name__})") from None


def check_runtime_env() -> None:
    """R27.2: the runner's own process refuses loader and temporary-directory overrides; /dev/shm must exist."""
    import os
    for k in RUNTIME_REFUSED:
        if k in os.environ:
            raise SealedRefusal(f"refused: the environment variable {k} is set")
    if not os.path.isdir(OBJ_BASE):
        raise SealedRefusal(f"refused: {OBJ_BASE} is absent")


# R27.2/R29.4/R30.4: repository-scope config ALLOWLIST of (key, value) pairs, each with its reason; keys and values
# are full-matched separately on `git config --list -z` output.
SAFE_VALUE = r"[^\n!\-][^\n]*"            # no newline, no leading `!` or `-`
REPO_CONFIG_ALLOWED = [
    (r"core\.repositoryformatversion", r"1", "this checkout's repository format (R32.4: 0 only in a test repository)"),
    (r"core\.filemode", r"true", "this checkout's value"),
    (r"core\.bare", r"false", "a working checkout"),
    (r"core\.logallrefupdates", r"true", "this checkout's value"),
    (r"core\.ignorecase", r"false", "the Linux default"),
    (r"core\.precomposeunicode", r"false", "the Linux default"),
    (r"extensions\.worktreeconfig", r"true", "per-worktree config (this repository uses worktrees)"),
    (r"remote\.origin\.url", r"https://github\.com/mastermindx-market-intelligence/macro\.git",
     "the pinned remote (also checked by check_remote_identity)"),
    (r"remote\.origin\.fetch", r"\+refs/heads/\*:refs/remotes/origin/\*|\+refs/heads/main:refs/remotes/origin/main",
     "the standard refspec, or this checkout's single-branch one (fetches use --refmap= anyway; accepted by R30.4)"),
    (r"remote\.origin\.promisor", r"true", "this checkout is a partial clone of origin"),
    (r"remote\.origin\.partialclonefilter", r"blob:none", "blob-less partial clone"),
    (r"extensions\.partialclone", r"origin", "partial-clone extension, only for origin"),
    (r"branch\.[^\n=]+\.(remote|merge)", SAFE_VALUE, "upstream tracking of local branches"),
    (r"branch\.[^\n=]+\.(t3-merge-base|t3-merge-base-ref|gh-merge-base)", SAFE_VALUE, "T3 / gh branch metadata"),
    (r"user\.(name|email)", SAFE_VALUE, "commit identity"),
    (r"core\.sparsecheckout", r"true", "the worktree is a sparse checkout"),
    (r"core\.sparsecheckoutcone", r"true", "cone-mode sparse checkout"),
]


def check_repo_config(root: Path, remote_url: str, test_repo: bool = False) -> None:
    """`test_repo=True` (a supplied test context's temporary repository only) also accepts repository format 0."""
    import re
    root = Path(root)
    allowed = REPO_CONFIG_ALLOWED + ([(r"core\.repositoryformatversion", r"0", "a temporary test repository")]
                                     if test_repo else [])
    pats = [(re.compile(k), re.compile(v), why) for k, v, why in allowed]
    for scope in ("--local", "--worktree"):
        r = _git("config", scope, "--list", "-z", root=root, check=False)
        if r.returncode != 0:
            wt = _git("config", "--local", "--get", "extensions.worktreeconfig", root=root, check=False)
            if scope == "--worktree" and wt.returncode == 1:
                continue                                     # no worktree config extension in this repository
            raise SealedRefusal(f"refused: reading git config {scope} failed")
        for rec in r.stdout.decode(errors="replace").split("\0"):
            if not rec:
                continue
            key, _, val = rec.partition("\n")
            if key == "remote.origin.url" and val == remote_url:
                continue                                     # a test repository's own pinned local remote
            if not any(kp.fullmatch(key) and vp.fullmatch(val) for kp, vp, _ in pats):
                raise SealedRefusal(f"refused: repository-scope git config {key} is not allowed with that value")


def check_gh_socket() -> None:
    r = subprocess.run([tool("gh"), "config", "get", "http_unix_socket"], capture_output=True, env=child_env())
    if r.returncode != 0 or r.stdout.strip():
        raise SealedRefusal("refused: gh http_unix_socket is set (or gh config is unreadable)")


class RunLock:
    """R27.3: one invocation at a time: an exclusive flock on a fixed file, held for the whole invocation."""
    def __init__(self, path: str = LOCK_PATH):
        self.path, self.fd = path, None

    def __enter__(self):
        import fcntl, os
        try:
            self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        except OSError:
            raise SealedRefusal("refused: the run lock file cannot be opened") from None
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(self.fd); self.fd = None
            raise SealedRefusal("refused: another invocation of the runner holds the lock") from None
        return self

    def __exit__(self, *a):
        import os
        if self.fd is not None:
            os.close(self.fd); self.fd = None
        return False


def cleanup_leftover_object_dirs() -> int:
    """R26.1: delete leftover private object directories of a killed run, WITHOUT reading their contents."""
    import glob, shutil, tempfile
    n = 0
    for d in glob.glob(str(Path(OBJ_BASE) / (OBJ_DIR_PREFIX + "*"))):
        shutil.rmtree(d, ignore_errors=True); n += 1
    return n


CODE_SUFFIXES = (".py", ".pth", ".so", ".pyc", ".pyd", ".dylib", ".zip", ".egg-link")


def check_worktree_code(root: Path = None) -> None:
    """R26.3: no untracked OR ignored *.py, *.pth, *.so, or *.pyc outside __pycache__, anywhere in the working tree."""
    root = Path(root or ROOT)
    r = _git("status", "--porcelain", "-z", "--untracked-files=all", "--ignored", root=root, check=False)
    if r.returncode != 0:
        raise SealedRefusal("refused: git status failed")
    for ln in r.stdout.decode(errors="replace").split("\0"):
        if not ln.startswith(("?? ", "!! ")):
            continue
        path = ln[3:]
        if path.endswith(".pyc") and "__pycache__/" in path:
            continue
        if path.endswith(CODE_SUFFIXES) or path.endswith("/"):
            if path.endswith("/"):                         # an untracked/ignored directory listed whole
                import os
                for dp, _, fs in os.walk(root / path):
                    for f in fs:
                        if f.endswith(CODE_SUFFIXES) and not (f.endswith(".pyc") and "__pycache__" in dp):
                            raise SealedRefusal(f"refused: untracked or ignored code file {Path(dp, f)}")
                continue
            raise SealedRefusal(f"refused: untracked or ignored code file {path}")


TOOL_DIRS = ("/usr/bin", "/usr/local/bin")
_TOOLS: dict = {}


def tool(name: str) -> str:
    """R25.3: `git` / `gh` resolved once, never through PATH: the first of /usr/bin/<name>, /usr/local/bin/<name>
    whose REAL path lies under one of those directories and is not writable by group or other."""
    import os, stat
    if name in _TOOLS:
        return _TOOLS[name]
    for d in TOOL_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            real = os.path.realpath(p)
            if not any(real.startswith(x + os.sep) for x in TOOL_DIRS):
                raise SealedRefusal(f"refused: {name} resolves outside {TOOL_DIRS}")
            if os.stat(real).st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                raise SealedRefusal(f"refused: {name} is writable by group or other")
            _TOOLS[name] = real
            return real
    raise SealedRefusal(f"refused: {name} not found in {TOOL_DIRS}")


_TOOL_VERSIONS: dict = {}


def tool_versions() -> dict:
    """R25.3: path and `--version` of git and gh, recorded in versions() (pinned by the release)."""
    if not _TOOL_VERSIONS:
        for n in ("git", "gh"):
            p = tool(n)
            r = subprocess.run([p, "--version"], capture_output=True, env=child_env())
            if r.returncode != 0:
                raise SealedRefusal(f"refused: {n} --version failed")
            v = r.stdout.decode().splitlines()
            _TOOL_VERSIONS[n] = {"path": p, "version": v[0] if v else ""}
    return dict(_TOOL_VERSIONS)


def child_env(extra: dict | None = None) -> dict:
    """R27.2: every git / gh child gets a CONSTRUCTED environment, never the inherited one."""
    import os, pwd
    env = {"PATH": "/usr/bin:/bin", "HOME": pwd.getpwuid(os.getuid()).pw_dir, "LANG": "C", "LC_ALL": "C",
           "GIT_NO_LAZY_FETCH": "1"}               # R29.1(c): no read may depend on a lazy fetch (materialise() only)
    env.update(extra or {})
    return {k: v for k, v in env.items() if v is not None}


GIT_FIXED = ["-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false"]


def _git(*a, check=True, root=None, env=None, input=None) -> subprocess.CompletedProcess:
    """git by absolute path, constructed environment (`env` = extra variables only, e.g. the private object store),
    hooks, fsmonitor and the untracked cache disabled (R25.3, R27.2)."""
    return subprocess.run([tool("git"), *GIT_FIXED, "-C", str(root or ROOT), *a], capture_output=True, check=check,
                          env=child_env(env), input=input)


# R25.2: the normalised syntax-tree sha256 of each Phase A function, registered by the runner at import; carried in
# versions() (pinned by the release) and in every ledger entry.
_PHASE_A = {"ast_sha256": None}


def register_phase_a(digest: dict) -> None:
    _PHASE_A["ast_sha256"] = dict(digest)


def check_import_environment(root: Path = ROOT, commit: str | None = None) -> None:
    """R20.8/R22.4/R23.4: refuse PYTHONPATH, PYTHONSTARTUP, PYTHONHOME; a loaded usercustomize; and any module in
    sys.modules whose REAL path lies outside the interpreter's stdlib, platstdlib, purelib, platlib or the repository.
    One exception, ruled (R21.0/R22.4): the distribution's own sitecustomize, accepted only where its link sits in the
    stdlib directory (its real file is /etc/python3.X on Debian/Ubuntu), with its content pinned by sha256 in
    versions(). Covered modules (engine., scripts., tests.) must also equal their blob at `commit`."""
    import os, sys, sysconfig
    for v in ("PYTHONPATH", "PYTHONSTARTUP", "PYTHONHOME"):
        if os.environ.get(v):
            raise SealedRefusal(f"refused: {v} is set (the sealed-run command line is `python -E ...`)")
    if "usercustomize" in sys.modules:
        raise SealedRefusal("refused: usercustomize is loaded")
    rr = os.path.realpath(root)
    for pkg in ("engine", "scripts", "tests"):                       # R32.2: the top-level packages themselves
        mod = sys.modules.get(pkg)
        if mod is None:
            continue
        locs = [getattr(mod, "__file__", None)] if getattr(mod, "__file__", None) else list(getattr(mod, "__path__", []))
        if not locs or not all(os.path.realpath(x).startswith(rr + os.sep) for x in locs):
            raise SealedRefusal(f"refused: package {pkg} is not the repository's own")
    paths = sysconfig.get_paths()
    stdlib_link = Path(os.path.abspath(paths["stdlib"]))
    roots = [os.path.realpath(paths[k]) for k in ("stdlib", "platstdlib", "purelib", "platlib")] + [os.path.realpath(root)]
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        real = os.path.realpath(f)
        if name == "sitecustomize":
            if Path(os.path.abspath(f)).parent != stdlib_link:
                raise SealedRefusal("refused: a sitecustomize outside the interpreter's own library is loaded")
            continue
        if not any(real == r or real.startswith(r + os.sep) for r in roots):
            raise SealedRefusal(f"refused: module {name} loaded from outside the interpreter and the repository")
        if not name.startswith(COVERED_MODULE_PREFIXES):
            continue
        rel = Path(real).relative_to(os.path.realpath(root)) if real.startswith(os.path.realpath(root) + os.sep) else None
        if rel is None:
            raise SealedRefusal(f"refused: covered module {name} imported from outside the repository")
        if commit is not None:
            w = _git("rev-parse", f"{commit}:{rel}", check=False, root=root)
            h = _git("hash-object", "--no-filters", str(rel), check=False, root=root)
            want, got = w.stdout.decode().strip(), h.stdout.decode().strip()
            if w.returncode != 0 or h.returncode != 0 or not want or want != got:
                raise SealedRefusal(f"refused: covered module {name} differs from the engine commit")


def check_pinned_blobs(commit: str, root: Path = ROOT, paths=None) -> int:
    """R28.6: every file the engine commit holds under the pinned paths is present in the working tree, its index
    entry carries neither skip-worktree nor assume-unchanged, and its working-tree bytes hash (no filters) to the
    commit's blob. Not through `git status` alone."""
    paths = list(paths or PINNED_PATHS)
    tree = _git("ls-tree", "-r", "-z", commit, "--", *paths, root=root, check=False)
    if tree.returncode != 0:
        raise SealedRefusal(f"refused: cannot read the pinned paths at {commit}")
    want = {}
    for rec in tree.stdout.decode(errors="replace").split("\0"):
        if rec:
            meta, path = rec.split("\t", 1)
            want[path] = meta.split()[2]
    check_read_flags(root, paths)
    names = sorted(want)
    missing = [n for n in names if not (Path(root) / n).is_file()]
    if missing:
        raise SealedRefusal(f"refused: pinned path {missing[0]} is not present in the working tree")
    h = _git("hash-object", "--no-filters", "--stdin-paths", input="\n".join(names).encode() + b"\n",
             root=root, check=False)
    if h.returncode != 0:
        raise SealedRefusal("refused: hashing the pinned paths failed")
    got = h.stdout.decode().split()
    if len(got) != len(names):
        raise SealedRefusal("refused: hashing the pinned paths was incomplete")
    for n, g in zip(names, got):
        if want[n] != g:
            raise SealedRefusal(f"refused: pinned path {n} differs from the engine commit's blob")
    return len(names)


PYCACHE_PREFIX = "/dev/shm/rotation_core_v2_pycache"


def check_bytecode_flags(require_empty: bool = True) -> None:
    """R29.3: run as `python -E -P -B -X pycache_prefix=/dev/shm/rotation_core_v2_pycache`; at start the prefix directory
    is absent or empty (so every module is compiled from its source)."""
    import os, sys
    if not sys.dont_write_bytecode or getattr(sys, "pycache_prefix", None) != PYCACHE_PREFIX:
        raise SealedRefusal(f"refused: run with -B -X pycache_prefix={PYCACHE_PREFIX} (R29.3)")
    if require_empty and os.path.exists(PYCACHE_PREFIX) and (not os.path.isdir(PYCACHE_PREFIX)
                                                             or os.listdir(PYCACHE_PREFIX)):
        raise SealedRefusal(f"refused: {PYCACHE_PREFIX} is not empty")


def check_no_bytecode_modules(root: Path = ROOT) -> None:
    """R29.3: no module under the repository was loaded from bytecode."""
    import importlib.machinery as m, os, sys
    rr = os.path.realpath(root)
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if not f or not os.path.realpath(f).startswith(rr + os.sep):
            continue
        spec = getattr(mod, "__spec__", None)
        if f.endswith((".pyc", ".pyo")) or isinstance(getattr(mod, "__loader__", None), m.SourcelessFileLoader) \
                or (spec is not None and spec.cached and os.path.isfile(spec.cached)):
            raise SealedRefusal(f"refused: module {name} was loaded from bytecode")


def refuse_shadowed_modules(root: Path = ROOT) -> None:
    """R31.6(c)/R32.8(a): strict outside pytest (no module but `engine`, `scripts`, `tests` and the script itself
    loaded from the root); under pytest, the names-only rule (no standard-library or installed-package name)."""
    import os, sys
    import importlib.metadata as md
    strict = "pytest" not in sys.modules
    protected = None if strict else set(sys.stdlib_module_names) | set(md.packages_distributions())
    rr = os.path.realpath(root)
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        top = name.split(".")[0]
        if not f or name == "__main__" or top in ("engine", "scripts", "tests"):
            continue
        if not strict and top not in protected:
            continue
        if os.path.realpath(f).startswith(rr + os.sep):
            raise SealedRefusal(f"refused: module {name} was loaded from the repository directory (R31.6)")


def check_engine_commit(commit: str, root: Path = ROOT) -> None:
    """S5/R20.8/R28.6: pinned paths at HEAD identical to `commit`, every pinned file's bytes equal to its blob, no
    flag hiding an edit, no modified or UNTRACKED file under them, and a clean import environment."""
    if _git("diff", "--quiet", commit, "HEAD", "--", *PINNED_PATHS, check=False, root=root).returncode != 0:
        raise SealedRefusal(f"refused: pinned paths differ from release engine_commit {commit}")
    st = _git("status", "--porcelain", "--untracked-files=all", "--", *PINNED_PATHS, check=False, root=root)
    if st.returncode != 0 or st.stdout.strip():
        raise SealedRefusal("refused: modified or untracked files under the pinned paths")
    check_pinned_blobs(commit, root)
    check_import_environment(root, commit)


# R27.7: the only credential settings accepted: this host's helper for github.com and gist.github.com, each preceded by
# the empty reset line that `gh auth setup-git` writes.
CREDENTIAL_ALLOWED = {(f"credential.https://{h}.helper", v) for h in ("github.com", "gist.github.com")
                      for v in ("", "!/usr/bin/gh auth git-credential")}


def _config_regexp(pattern: str, root) -> list:
    """`git config --get-regexp`: exit 1 means no match; any other failure refuses (never read as absence)."""
    r = _git("config", "--get-regexp", pattern, check=False, root=root)
    if r.returncode not in (0, 1):
        raise SealedRefusal("refused: reading git config failed")
    return r.stdout.decode(errors="replace").splitlines()


def check_remote_identity(root: Path, url: str) -> None:
    """R23.3: origin's fetch and push URLs equal the pinned URL; no url.*.insteadOf / pushInsteadOf at any level;
    no GIT_CONFIG* variable in the environment."""
    import os
    if any(k.startswith("GIT_CONFIG") for k in os.environ):
        raise SealedRefusal("refused: a GIT_CONFIG* variable is set")
    check_env_vars()
    if _config_regexp(r"^url\..*\.(insteadof|pushinsteadof)$", root):
        raise SealedRefusal("refused: a url.*.insteadOf / pushInsteadOf rewrite is configured")
    if _config_regexp(r"^(http\..*proxy|https\.proxy|http\.proxy|core\.gitproxy|core\.sshcommand)$", root):
        raise SealedRefusal("refused: a git proxy or ssh-command override is configured")
    if any(ln.split()[-1].lower() in ("false", "0", "no", "off")
           for ln in _config_regexp(r"^http\.(.*\.)?sslverify$", root) if ln.split()):
        raise SealedRefusal("refused: http sslVerify is disabled in git config")
    # R27.7: further redirections / re-trust at any scope
    if _config_regexp(r"^(remote\..*\.proxy|http\.(.*\.)?(curloptresolve|sslcainfo|sslcapath|extraheader)|http\.sslbackend)$", root):
        raise SealedRefusal("refused: a git proxy, resolve override, CA or extra-header setting is configured")
    for ln in _config_regexp(r"^credential\.", root):
        key, _, val = ln.partition(" ")
        if (key, val) not in CREDENTIAL_ALLOWED:
            raise SealedRefusal(f"refused: git credential setting {key} is not the host's gh helper")
    for args in (("remote", "get-url", REMOTE), ("remote", "get-url", "--push", REMOTE)):
        r = _git(*args, check=False, root=root)
        if r.returncode != 0 or r.stdout.decode().strip() != url:
            raise SealedRefusal("refused: the origin URL is not the pinned repository")


def fetch_remote(root: Path, branch: str, url: str) -> str:
    """R20.5/R22.2/R23.3: fails closed; NOT forced (a non-fast-forward remote refuses); remote identity checked;
    returns the sha just fetched. Every remote check takes this sha, never a stale ref."""
    check_remote_identity(root, url)
    r = _git("fetch", "-q", "--refmap=", REMOTE, f"refs/heads/{branch}:refs/remotes/{REMOTE}/{branch}", check=False,
             root=root)
    if r.returncode != 0:
        raise SealedRefusal("refused: fetching the remote branch failed or was not a fast-forward (a rewritten or "
                            "re-created branch); no check runs on an unfetched ref")
    return _git("rev-parse", f"refs/remotes/{REMOTE}/{branch}", root=root).stdout.decode().strip()


def is_ancestor(a: str, b: str, root) -> bool:
    """R30.2: `merge-base --is-ancestor` is three-valued: 0 yes, 1 no, anything else an error that refuses."""
    r = _git("merge-base", "--is-ancestor", a, b, check=False, root=root)
    if r.returncode == 0:
        return True
    if r.returncode == 1:
        return False
    raise SealedRefusal("refused: an ancestry check failed (not read as 'not an ancestor')")


def on_remote(path: Path, remote_sha: str, root: Path) -> None:
    """S5: the commit that last touched `path` (and the file content) must be contained in the fetched remote sha."""
    rel = str(Path(path).resolve().relative_to(Path(root).resolve()))
    lg = _git("log", "-1", "--format=%H", "--", rel, check=False, root=root)
    if lg.returncode != 0:
        raise SealedRefusal(f"refused: cannot read the history of {rel}")
    c = lg.stdout.decode().strip()
    if not c or not is_ancestor(c, remote_sha, root):
        raise SealedRefusal(f"refused: {rel} is not committed on the remote branch")
    check_read_flags(root, [rel])                         # R29.2: the runner reads the blob, never the working tree
    if blob_at(remote_sha, rel, root) is None:
        raise SealedRefusal(f"refused: {rel} is not in the remote branch's tree")


def commit_on_remote(commit: str, remote_sha: str, root: Path) -> None:
    if not is_ancestor(commit, remote_sha, root):
        raise SealedRefusal(f"refused: commit {commit} is not contained in the remote branch")


def blob_at(sha: str, rel: str, root) -> bytes | None:
    """R29.1(a): a blob's bytes at a commit. Absence is established ONLY from the tree (`ls-tree`): None if the path
    is truly absent there; any failed read of a present path refuses (never read as absence)."""
    r = _git("show", f"{sha}:{rel}", check=False, root=root)
    if r.returncode == 0:
        return r.stdout
    if not path_in_tree(sha, rel, root):
        return None
    raise SealedRefusal(f"refused: {rel} is present at {sha[:12]} but its blob could not be read (not absence)")


def path_in_tree(sha: str, rel: str, root) -> bool:
    t = _git("ls-tree", sha, "--", rel, check=False, root=root)
    if t.returncode != 0:
        raise SealedRefusal(f"refused: cannot read the tree of {sha[:12]}")
    return bool(t.stdout.strip())


def _commits_touching(rel: str, sha: str, root, first_parent=False) -> list:
    args = ["log", "--format=%H", "--reverse", "--full-history"] + (["--first-parent"] if first_parent else []) + \
        [sha, "--", rel]
    out = _git(*args, check=False, root=root)
    if out.returncode != 0:
        raise SealedRefusal(f"refused: cannot read the history of {rel}")
    return out.stdout.decode().split()


def file_versions(rel: str, remote_sha: str, root: Path) -> list:
    """Every committed version of `rel` on the remote branch, oldest first: [(commit, bytes)]; a commit where the
    path is absent from the tree (a deletion) is skipped; a failed read of a present path refuses (R29.1(a))."""
    vs = []
    for c in _commits_touching(rel, remote_sha, root, first_parent=True):      # R30.3: the branch's own history
        b = blob_at(c, rel, root)
        if b is not None:
            vs.append((c, b))
    return vs


def check_no_merges(root, head: str, created: str, rels) -> None:
    """R30.3: the branch is linear by construction (activity log: pushes only, each a fast-forward). Refuse if any
    commit after the branch's creation commit up to the fetched head has more than one parent and touches the
    ledger, a release file or the selection file."""
    r = _git("rev-list", "--min-parents=2", "--full-history", f"{created}..{head}", "--", *rels, check=False, root=root)
    if r.returncode != 0:
        raise SealedRefusal("refused: cannot list the branch's history")
    if r.stdout.strip():
        raise SealedRefusal("refused: a merge commit on the branch touches the ledger, a release or the selection")


def check_worktree_matches_head(root, head: str, rels) -> None:
    """R31.1(c): before START (and in --preflight) the working-tree copy of each release and selection file equals the
    blob at the fetched head, byte for byte (no filters); a file in only one of the two refuses."""
    for rel in rels:
        b = blob_at(head, rel, root)
        p = Path(root) / rel
        w = p.read_bytes() if p.is_file() else None
        if b != w:
            raise SealedRefusal(f"refused: the working-tree copy of {rel} differs from the committed blob at the "
                                "fetched head")


def release_docs(versions_by_file: dict) -> dict:
    """sha256 of every committed version of every release file -> its document. The one mapping both `append`
    (R31.1(b)) and `validate_ledger` use to decide whether a START names a committed release."""
    import json
    docs = {}
    for name, vs in versions_by_file.items():
        for _, b in vs:
            docs[sha256_bytes(b)] = json.loads(b)
    return docs


def check_read_flags(root, rels) -> None:
    """R29.2: refuse a skip-worktree (`S`) or assume-unchanged (lower-case) flag on any path the runner reads."""
    r = _git("ls-files", "-v", "-z", "--", *rels, check=False, root=root)
    if r.returncode != 0:
        raise SealedRefusal("refused: git ls-files failed")
    for rec in r.stdout.decode(errors="replace").split("\0"):
        if rec and (rec[0] == "S" or rec[0].islower()):
            raise SealedRefusal(f"refused: {rec[2:]} is marked skip-worktree or assume-unchanged")


def materialise(root, sha: str, rels) -> int:
    """R29.1(c): after a fetch, bring every blob the runner is about to read (every committed version of each path in
    `rels` on the history of `sha`) into the object store, then confirm with lazy fetching OFF that none is missing.
    No later read depends on a lazy fetch."""
    oids = set()
    for rel in rels:
        for c in [sha] + _commits_touching(rel, sha, root):
            t = _git("ls-tree", "-r", c, "--", rel, check=False, root=root)
            if t.returncode != 0:
                raise SealedRefusal(f"refused: cannot read the tree of {c[:12]}")
            for ln in t.stdout.decode().splitlines():
                meta = ln.split("\t", 1)[0].split()
                if meta[1] == "blob":
                    oids.add(meta[2])
    if not oids:
        return 0
    batch = ("\n".join(sorted(oids)) + "\n").encode()
    chk = lambda: _git("cat-file", "--batch-check", input=batch, root=root, check=False)
    first = chk()
    if first.returncode != 0:
        raise SealedRefusal("refused: checking the object store failed")
    missing = [ln.split()[0] for ln in first.stdout.decode().splitlines() if ln.endswith(" missing")]
    if missing:                                              # the only lazy fetch the runner allows
        _git("cat-file", "--batch", input=("\n".join(missing) + "\n").encode(), root=root, check=False,
             env={"GIT_NO_LAZY_FETCH": None})
        r = chk()
        if r.returncode != 0 or any(ln.endswith(" missing") for ln in r.stdout.decode().splitlines()):
            raise SealedRefusal("refused: a blob the runner must read could not be brought into the object store")
    return len(oids)


def sha256_bytes(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()


def sha256_file(path) -> str:
    import hashlib, io
    if isinstance(path, io.StringIO):
        return sha256_bytes(path.getvalue().encode())
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def versions() -> dict:
    """Library versions, plus the sha256 of a loaded sitecustomize (R20.8 as amended), pinned by the release."""
    import platform, sys, numpy, pandas, pyarrow, scipy
    sc = getattr(sys.modules.get("sitecustomize"), "__file__", None)
    return {"python": platform.python_version(), "numpy": numpy.__version__, "pandas": pandas.__version__,
            "pyarrow": pyarrow.__version__, "scipy": scipy.__version__,
            "sitecustomize_sha256": sha256_file(sc) if sc else None, "pth_count": pth_digest()[0],
            "pth_sha256": pth_digest()[1], "tools": tool_versions(), "phase_a_ast_sha256": _PHASE_A["ast_sha256"]}


def site_dirs() -> list:
    import site, sys
    ds = set(site.getsitepackages() if hasattr(site, "getsitepackages") else [])
    if site.ENABLE_USER_SITE:
        ds.add(site.getusersitepackages())
    ds |= {d for d in sys.path if Path(d).name in ("site-packages", "dist-packages")}
    return sorted(d for d in ds if Path(d).is_dir())


def pth_digest() -> tuple[int, str]:
    """R22.4: sha256 over the sorted (relative name, file sha256) of every *.pth in every site directory."""
    items = sorted((str(Path(d).name) + "/" + f.name, sha256_file(f)) for d in site_dirs() for f in Path(d).glob("*.pth"))
    return len(items), sha256_bytes(canonical_bytes(items))


def check_manifest(r: dict, inputs: dict) -> dict:
    """O6: every input file's sha256 and the library versions must equal the release's manifest."""
    for p in inputs.values():
        io_check(p, "read")
    got = {k: sha256_file(p) for k, p in inputs.items()}
    if r.get("inputs_sha256") != got:
        raise SealedRefusal("refused: input file hashes differ from the release manifest")
    want, got_v = r.get("versions") or {}, versions()
    if want != got_v:
        keys = sorted(k for k in set(want) | set(got_v) if want.get(k) != got_v.get(k))
        raise SealedRefusal(f"refused: library versions differ from the release manifest (keys: {', '.join(keys)})")
    return got


def stage1_release(release: Path, inputs: dict | None = None, remote_sha: str | None = None,
                   root: Path = None, selection: Path = None, engine_check=None) -> dict:
    """Committed stage-1 release, checked against the header, the selection rerun (commit, sha256, on the remote:
    R20.9), the engine commit and the manifest."""
    if root is None:
        raise SealedRefusal("refused: the release repository root is required (R29.5)")
    root = Path(root)
    if selection is None:
        raise SealedRefusal("refused: the selection result path is required")
    selection = Path(selection)
    r = _load_release(release, root)
    if r is None or r.get("windows_released") != [W_PRE]:
        raise SealedRefusal(f"refused: stage 1 needs a committed {Path(release).name} with windows_released exactly "
                            f"[\"{W_PRE}\"]")
    if r.get("protocol_header_sha256") != FROZEN_V2_SHA256:
        raise SealedRefusal("refused: release names a different header sha256")
    if "opening_condition_hypotheses" in r and tuple(r["opening_condition_hypotheses"]) != OPENING_HYPOTHESES:
        raise SealedRefusal("refused: the opening list is the constant (H1, H3)")
    sc = r.get("selection_results_commit", "<missing>")
    if _git("diff", "--quiet", sc, "HEAD", "--", str(selection.resolve().relative_to(root.resolve())), check=False,
            root=root).returncode != 0:
        raise SealedRefusal("refused: selection results differ from the release's selection_results_commit")
    sb = read_repo_bytes(selection, root)                         # R29.2: the committed bytes, not the working tree
    if sb is None or sha256_bytes(sb) != r.get("selection_results_sha256"):
        raise SealedRefusal("refused: selection results sha256 differs from the release")
    if remote_sha is not None:                                           # R20.9
        commit_on_remote(sc, remote_sha, root)
        on_remote(selection, remote_sha, root)
        on_remote(release, remote_sha, root)
        check_release_pins(r, remote_sha, root)
    h, b = selected_setting(selection, root)
    g = r.get("selected_grid_point", {})
    if (float(g.get("h_near_high_pct", -1)), float(g.get("b_breadth_drop_pp", -1))) != (h, b):
        raise SealedRefusal("refused: release names a configuration other than the committed selection")
    (engine_check or check_engine_commit)(r.get("engine_commit", "<missing>"))
    if inputs is not None:
        check_manifest(r, inputs)
    return r


# ------------------------------------------------------------------ R20 run ledger (append-only, hash-chained, pushed)
def chain_hash(entries: list) -> str:
    return sha256_bytes(canonical_bytes(entries))


def verify_chain(entries: list) -> None:
    for i, e in enumerate(entries):
        if e.get("prev_chain_sha256") != (chain_hash(entries[:i]) if i else None) or e.get("index") != i:
            raise SealedRefusal(f"refused: ledger entry {i} is not chained to its predecessors")


def ledger_doc(entries: list) -> bytes:
    import json
    return (json.dumps({"schema": "rotation_core.run_ledger/v2", "header_sha256": FROZEN_V2_SHA256,
                        "entries": entries}, indent=1, sort_keys=True) + "\n").encode()


def gate_keys(hyp: str, eras=ERAS_GATE) -> set:
    return {f"{hyp}|{e}|{r}|{c}" for e in eras for r in GATE_READINGS for c in GATE_COSTS}


def gate_decision(signs: dict, eras=ERAS_GATE) -> tuple[bool, dict]:
    """R13/R14(c)/R18/R20.3: open iff H1 or H3 has EXACTLY its eight keys (two eras x two readings x base/strict),
    all '+'. Any other key set (empty, short, extra) is closed; a NaN is neither sign (O5)."""
    if not isinstance(signs, dict) or set(signs) != gate_keys("H1", eras) | gate_keys("H3", eras):
        return False, {h: False for h in OPENING_HYPOTHESES}
    per = {h: all(signs[k] == "+" for k in gate_keys(h, eras)) for h in OPENING_HYPOTHESES}
    return any(per.values()), per


A2_ABORT_REASONS = ("stage1_not_reproduced", "stage1_reproduction_exception")


def _a2_abort(r) -> bool:
    return r.get("a2") is not None and r["a2"]["kind"] == "INTEGRITY_ABORT"


def _runs(entries: list) -> list:
    """Group ledger entries into runs: [{"start", "outcome", "a2", "record"}] in order. Stage 2 has a second
    integrity step after a clean Phase A (R24.1(a), Phase A2: reproduction of stage 1): REPRODUCTION_OK, or
    INTEGRITY_ABORT with a stage1_* reason; FINAL needs REPRODUCTION_OK."""
    runs = []
    for e in entries:
        if e["kind"] == "START":
            runs.append({"start": e, "outcome": None, "a2": None, "record": None})
            continue
        if not runs or e.get("start_index") != runs[-1]["start"]["index"]:
            raise SealedRefusal(f"refused: ledger entry {e['index']} does not belong to the latest START")
        r = runs[-1]
        stage2 = r["start"]["stage"] == "stage2"
        clean = r["outcome"] is not None and r["outcome"]["kind"] == "PHASE_A_CLEAN"
        if stage2 and clean and r["a2"] is None and r["record"] is None and (
                e["kind"] == "REPRODUCTION_OK" or
                (e["kind"] == "INTEGRITY_ABORT" and e.get("reason") in A2_ABORT_REASONS)):
            r["a2"] = e
        elif e["kind"] in ("INTEGRITY_ABORT", "PHASE_A_CLEAN"):
            if r["outcome"] is not None:
                raise SealedRefusal("refused: two Phase A outcomes for one START")
            r["outcome"] = e
        elif e["kind"] in ("GATE", "FINAL"):
            want = "FINAL" if stage2 else "GATE"
            ok_a2 = (not stage2) or (r["a2"] is not None and r["a2"]["kind"] == "REPRODUCTION_OK")
            if e["kind"] != want or not clean or not ok_a2 or r["record"]:
                raise SealedRefusal(f"refused: ledger entry {e['index']} is out of order")
            r["record"] = e
        else:
            raise SealedRefusal(f"refused: unknown ledger entry kind {e['kind']}")
    return runs


def _identity(start: dict) -> tuple:
    return (start["stage"], start["release_sha256"], start["engine_commit"],
            canonical_bytes(start["inputs_sha256"]))


def start_allowed(entries: list, new: dict, release: dict) -> None:
    """R20.1 state rules for a new START (stage1 or stage2) after `entries`. Raises SealedRefusal."""
    runs = _runs(entries)
    gates = [r["record"] for r in runs if r["record"] and r["record"]["kind"] == "GATE"]
    if any(g["gate_open"] is not True for g in gates):
        raise SealedRefusal("refused: a stage-1 gate record is closed; closed is final (R17, R20.1)")
    if any(r["record"] and r["record"]["kind"] == "FINAL" for r in runs):
        raise SealedRefusal("refused: the final conjunction has run; nothing further may run (run once)")
    last = runs[-1] if runs else None
    # R23.1: scan ALL runs. A Phase-A-clean run with no record, not later completed by a run of the same identity,
    # binds every later START to its identity, permanently, whatever came after.
    for i, r in enumerate(runs):
        if r["outcome"] is not None and r["outcome"]["kind"] == "PHASE_A_CLEAN" and r["record"] is None \
                and not _a2_abort(r):
            ident = _identity(r["start"])
            if any(_identity(x["start"]) == ident and x["record"] is not None for x in runs[i + 1:]):
                continue
            if _identity(new) != ident:
                raise SealedRefusal("refused: a Phase-A-clean run has no record; the only permitted action is the "
                                    "identical rerun (same stage, release, engine commit and inputs), permanently "
                                    "(R20.1, R23.1)")
            return
    unrecorded = [r["start"]["index"] for r in runs if r["record"] is None]      # START-only and aborts
    same = [r for r in runs if r["start"]["stage"] == new["stage"] and r["start"]["engine_commit"] == new["engine_commit"]]
    if same and all(r["outcome"] is None or _a2_abort(r) for r in same):
        # R21.2(ii): only START(s) with no Phase A outcome at this commit: nothing was computed. R24.1(a): likewise a
        # stage-2 run that ended at Phase A2 (stage 1 not reproduced; no 2020-2025 number). A rerun at the same
        # commit needs a NEW release that cites them (checked below with every other unrecorded run).
        if new["release_sha256"] in {r["start"]["release_sha256"] for r in same}:
            raise SealedRefusal("refused: a rerun after a START with no Phase A outcome needs a new release that "
                                "cites it in ledger_records_cited (R21.2)")
        same = []
    if same:
        raise SealedRefusal("refused: this stage already ran (or aborted) at this engine commit; a rerun needs a new "
                            "engine commit and a new release (R17, R19, item 36 as amended by R20.1)")
    if unrecorded and release.get("ledger_records_cited") != unrecorded:
        raise SealedRefusal(f"refused: the release must cite every run without a record (ledger START indices "
                            f"{unrecorded}) in ledger_records_cited (R19.1)")
    if new["stage"] == "stage2":
        s1 = [r for r in runs if r["start"]["stage"] == "stage1"]
        if not s1 or s1[-1]["record"] is None:
            raise SealedRefusal("refused: stage 2 needs the latest stage-1 run to have an open gate record")
        if new["engine_commit"] != s1[-1]["start"]["engine_commit"]:
            raise SealedRefusal("refused: stage-2 engine commit differs from the latest stage-1 run's")


def check_real_host_records(entries: list) -> None:
    """R27.1(b): on the REAL ledger every entry carries a host record of ruleset 27041175 with a parseable
    updated_at, and never the test stub's flag."""
    import datetime
    for e in entries:
        h = e.get("host")
        if not isinstance(h, dict) or "stub" in h or h.get("ruleset_id") != RULESET_ID:
            raise SealedRefusal(f"refused: ledger entry {e.get('index')} has no real host record")
        try:
            datetime.datetime.fromisoformat(str(h.get("ruleset_updated_at")).replace("Z", "+00:00"))
        except ValueError:
            raise SealedRefusal(f"refused: ledger entry {e.get('index')} has an unparseable ruleset updated_at") from None


def validate_ledger(entries: list, versions_entries: list, release_docs: dict, real: bool = False) -> None:
    """R20.2/R20.3: chain; every committed version a prefix of the current; replay every START under the state
    rules; every GATE's gate_open equals gate_decision(its own signs) after a clean Phase A."""
    verify_chain(entries)
    if real:
        check_real_host_records(entries)
    for i, v in enumerate(versions_entries):
        if entries[:len(v)] != v:
            raise SealedRefusal(f"refused: committed ledger version {i} is not a prefix of the current ledger")
    for e in entries:
        if e["kind"] == "START":
            doc = release_docs.get(e["release_sha256"])
            if doc is None:
                raise SealedRefusal(f"refused: ledger START {e['index']} names a release never committed")
            start_allowed(entries[:e["index"]], e, doc)
        if e["kind"] == "GATE" and e.get("closed_by") in ("phase_b_exception", "phase_b_refusal"):
            if e["gate_open"] is not False or "gate_signs" in e:
                raise SealedRefusal(f"refused: ledger GATE {e['index']}: a phase-B-exception record must be closed "
                                    "and carry no signs")
        elif e["kind"] == "GATE":
            if e["gate_open"] is not gate_decision(e["gate_signs"])[0]:
                raise SealedRefusal(f"refused: ledger GATE {e['index']}: gate_open disagrees with its own signs")
    _runs(entries)


def check_release_history(versions_by_file: dict, entries: list) -> dict:
    """R20.1: every version of every release file on the remote must map to ledger START entries, or be listed as
    unused in a LATER version's `supersedes_unused_releases`. Returns sha256 -> document for all versions."""
    docs, started = release_docs(versions_by_file), {e["release_sha256"] for e in entries if e["kind"] == "START"}
    for name, vs in versions_by_file.items():
        shas = [sha256_bytes(b) for _, b in vs]
        for i, s in enumerate(shas[:-1]):
            later = [docs[x].get("supersedes_unused_releases", []) for x in shas[i + 1:]]
            if s not in started and not any(s in L for L in later):
                raise SealedRefusal(f"refused: an earlier {name} version has no ledger START and was not superseded "
                                    "as unused by a later release")
    return docs


class MemoryLedger:
    """In-memory ledger for the fixture dry run and tests (never a release path)."""
    branch = "memory"

    def __init__(self, entries=None, fail_on=()):
        self._e = list(entries or []); self.fail_on = set(fail_on)
        self.last_commit, self.host_record = None, None

    def entries(self) -> list:
        return [dict(x) for x in self._e]

    def append(self, entry: dict, precheck=None) -> dict:
        if precheck is not None:
            precheck(self.entries())
        if entry["kind"] in self.fail_on:
            raise LedgerPushFailed(f"refused: pushing the {entry['kind']} ledger entry failed")
        if self.host_record is not None:
            entry = dict(entry, host=self.host_record)
        entry = dict(entry, phase_a_ast_sha256=_PHASE_A["ast_sha256"])
        e = dict(entry, index=len(self._e), prev_chain_sha256=chain_hash(self._e) if self._e else None)
        self._e.append(e)
        self.last_commit = f"memory-{e['index']}"
        return e


class GitLedger:
    """R20.1: the runner writes the record. Each append builds a commit from a temporary index on top of the just-
    fetched remote head (the working tree is not touched), pushes it, and refuses to go on if the push fails. Only
    after a successful push is the local branch fast-forwarded. Starts only when the local HEAD equals the fetched
    remote head."""
    def __init__(self, root: Path, path: Path, branch: str, remote_url: str, code_root: Path, read_paths=(),
                 release_paths=()):
        self.root, self.branch, self.remote_url, self.code_root = Path(root), branch, remote_url, Path(code_root)
        self.rel = str(Path(path).resolve().relative_to(self.root.resolve()))
        self.read_paths = [str(Path(p).resolve().relative_to(self.root.resolve())) for p in read_paths]
        # R31.1(b): the release files a START may name (the runner always passes both; temporary test and rehearsal
        # ledgers pass none and carry no release)
        self.release_paths = [str(Path(p).resolve().relative_to(self.root.resolve())) for p in release_paths]
        self._seen = None                  # R29.1(b): the last ledger read in this invocation
        self.remote_sha = None
        self.last_commit = None
        self.host_record = None            # R22.1/R23.2: the invocation's host-check record, copied into every entry
        self.engine_commit = None          # R27.4: set by the runner once the release's engine commit is verified

    def fetch(self) -> str:
        self.remote_sha = fetch_remote(self.root, self.branch, self.remote_url)
        materialise(self.root, self.remote_sha, [self.rel] + self.read_paths +
                    (PINNED_PATHS if self.root.resolve() == ROOT.resolve() else []))      # R29.1(c)
        return self.remote_sha

    def require_local_equals_remote(self) -> None:
        head = _git("rev-parse", "HEAD", root=self.root).stdout.decode().strip()
        if head != self.remote_sha:
            raise SealedRefusal("refused: the local branch is not the fetched remote head (unpushed or stale commits)")

    def _entries_at(self, sha: str) -> list:
        """R29.1(a): [] only when the ledger is truly absent from that commit's tree."""
        import json
        b = blob_at(sha, self.rel, self.root)
        return [] if b is None else json.loads(b)["entries"]

    def commit_adding_entry(self, index: int) -> str | None:
        """R26.5: the first remote commit whose ledger holds entry `index`."""
        import json
        for c in _commits_touching(self.rel, self.remote_sha, self.root, first_parent=True):   # R30.3
            b = blob_at(c, self.rel, self.root)
            if b is not None and len(json.loads(b)["entries"]) > index:
                return c
        return None

    def entries(self) -> list:
        """R29.1(b): within one invocation a later read must extend the last ledger read."""
        if self.remote_sha is None:
            raise SealedRefusal("refused: ledger read before a fetch")
        e = self._entries_at(self.remote_sha)
        if self._seen is not None and e[:len(self._seen)] != self._seen:
            raise SealedRefusal("refused: the ledger read now does not extend the ledger read earlier in this run")
        self._seen = e
        return [dict(x) for x in e]

    def version_entries(self) -> list:
        """R29.1(b): every first-parent commit touching the ledger, oldest first; each version must extend the one
        before; a deletion after the ledger existed refuses."""
        import json
        out, prev, seen = [], [], False
        for c in _commits_touching(self.rel, self.remote_sha, self.root, first_parent=True):
            b = blob_at(c, self.rel, self.root)
            if b is None:
                if seen:
                    raise SealedRefusal("refused: the ledger was deleted at a commit on the branch")
                continue
            cur = json.loads(b)["entries"]
            if cur[:len(prev)] != prev:
                raise SealedRefusal("refused: a ledger version does not extend its predecessor")
            out.append(cur); prev, seen = cur, True
        return out

    def append(self, entry: dict, precheck=None) -> dict:
        """precheck(entries) runs on the FRESHLY fetched entries, immediately before the commit is built (R23.1 N2:
        the state rules of a START are re-evaluated so a concurrent record cannot slip between check and push)."""
        import os, tempfile
        self.fetch()
        cur = self.entries()
        verify_chain(cur)
        if precheck is not None:
            precheck(cur)
        if entry["kind"] == "START" and self.release_paths:          # R31.1(b): the same mapping validate_ledger uses
            docs = release_docs({r: file_versions(r, self.remote_sha, self.root) for r in self.release_paths})
            if entry.get("release_sha256") not in docs:
                raise SealedRefusal("refused: START names a release hash that is not a committed version of a release "
                                    "file at the fetched head")
        if self.host_record is not None:
            entry = dict(entry, host=self.host_record)
        entry = dict(entry, phase_a_ast_sha256=_PHASE_A["ast_sha256"])
        e = dict(entry, index=len(cur), prev_chain_sha256=chain_hash(cur) if cur else None)
        if e["kind"] in RECORD_KINDS:                       # R26.3/R27.4: the environment again, right before a record
            check_import_environment(ROOT, self.engine_commit)   # location AND blob equality at the engine commit
            refuse_shadowed_modules(ROOT)                    # R31.6(c)
            check_worktree_code(self.code_root)
            if _IO["mode"] is not None:                      # inside main, where the flags are enforced (R29.3)
                check_bytecode_flags(require_empty=False)
                check_no_bytecode_modules(ROOT)
        # R26.1: every object of this entry is written into a private object directory (mode 700) layered over the
        # real store, used only by these child calls, and removed in every outcome before this method returns or
        # raises. The real store receives the objects only through the fetch after a successful push.
        real_objects = _git("rev-parse", "--path-format=absolute", "--git-path", "objects",
                            root=self.root).stdout.decode().strip()
        td = tempfile.mkdtemp(prefix=OBJ_DIR_PREFIX, dir=OBJ_BASE)
        try:
            env = {"GIT_OBJECT_DIRECTORY": td, "GIT_ALTERNATE_OBJECT_DIRECTORIES": real_objects,
                   "GIT_INDEX_FILE": str(Path(td) / "index")}
            blob = _git("hash-object", "-w", "--no-filters", "--stdin", input=ledger_doc(cur + [e]), root=self.root,
                        env=env).stdout.decode().strip()
            _git("read-tree", self.remote_sha, root=self.root, env=env)
            _git("update-index", "--add", "--cacheinfo", f"100644,{blob},{self.rel}", root=self.root, env=env)
            tree = _git("write-tree", root=self.root, env=env).stdout.decode().strip()
            msg = (f"rotation-core run ledger: {e['kind']} (index {e['index']})\n\nWritten by the runner (R20.1).\n\n"
                   "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n").encode()
            c = _git("commit-tree", tree, "-p", self.remote_sha, input=msg, root=self.root, env=env).stdout.decode().strip()
            # R27.2: push to the pinned URL, not the remote name, so no tracking ref moves to objects about to be
            # removed; the fetch below updates the tracking ref.
            p = _git("push", "-q", self.remote_url, f"{c}:refs/heads/{self.branch}", check=False, root=self.root,
                     env=env)
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)
        if p.returncode != 0:
            raise LedgerPushFailed(f"refused: pushing the {e['kind']} ledger entry did not confirm; its state is "
                                   "UNKNOWN until the next invocation's fetch decides (R22.4(2))")
        if self.fetch() != c:
            raise LedgerPushFailed("refused: the remote head after the push is not the ledger commit; state UNKNOWN")
        self.last_commit = c
        if _git("merge", "--ff-only", "-q", c, check=False, root=self.root).returncode != 0:
            raise SealedRefusal("refused: the ledger entry is pushed but the local branch could not fast-forward")
        return e


# ------------------------------------------------------------------ R22.1 / R23.2 host record (fail closed)
ZERO_SHA = "0" * 40


def gh_api(path: str, paginate: bool = False):
    """The authenticated `gh api` already on the host. Fails closed: any non-zero exit or unparsable body raises."""
    import json, os
    for v in ("GH_HOST", "GH_REPO"):
        if os.environ.get(v):
            raise SealedRefusal(f"refused: {v} is set")
    cmd = [tool("gh"), "api", "--hostname", "github.com", "-H", "Accept: application/vnd.github+json", path]
    if paginate:
        cmd[2:2] = ["--paginate", "--jq", ".[] | @json"]
    r = subprocess.run(cmd, capture_output=True, env=child_env())
    if r.returncode != 0:
        raise SealedRefusal("refused: the GitHub API call failed; the host record cannot be read")
    try:
        if paginate:
            return [json.loads(x) for x in r.stdout.decode().splitlines() if x.strip()]
        return json.loads(r.stdout)
    except ValueError:
        raise SealedRefusal("refused: the GitHub API response did not parse") from None


def check_activity(entries: list, remote_sha: str, anchor: str, is_ancestor, ref: str) -> dict:
    """R22.1(b)-(d) on the branch activity log (oldest first). The log keeps deleted history and records force_push,
    branch_deletion and a second branch_creation (probe on fable/rotation-core-ledger-probe-20261111, 15:22Z)."""
    need = {"id", "activity_type", "before", "after", "ref", "timestamp"}
    if not isinstance(entries, list) or not entries:
        raise SealedRefusal("refused: the branch activity log is not a non-empty list (unexpected API response)")
    if not all(isinstance(e, dict) and need <= set(e) for e in entries):
        raise SealedRefusal("refused: the branch activity log has entries of an unexpected shape (unexpected API "
                            "response)")
    es = sorted(entries, key=lambda e: (e["timestamp"], e["id"]))
    if any(e.get("ref") != ref for e in es):
        raise SealedRefusal("refused: the activity log contains another ref")
    if es[0]["activity_type"] != "branch_creation" or es[0]["before"] != ZERO_SHA:
        raise SealedRefusal("refused: the activity log does not start at the branch's creation (truncated)")
    if any(e["activity_type"] != "push" for e in es[1:]):
        raise SealedRefusal("refused: the activity log records a force_push, deletion or re-creation; final")
    for p, e in zip(es, es[1:]):
        if e["before"] != p["after"]:
            raise SealedRefusal("refused: the activity log is not one unbroken chain")
        if not is_ancestor(e["before"], e["after"]):                 # R26.6: every push a fast-forward, locally
            raise SealedRefusal("refused: an activity push is not a fast-forward in the local history")
    if es[-1]["after"] != remote_sha:
        raise SealedRefusal("refused: the newest activity entry is not the fetched head")
    # the anchor lies inside the chain: an `after` contains it and that entry's `before` does not (the freeze commit
    # ac68f2e72a is not itself a push boundary: it arrived inside the push 3f5b44f3c6 -> af488e68dd)
    if not any(is_ancestor(anchor, e["after"]) and (e["before"] == ZERO_SHA or not is_ancestor(anchor, e["before"]))
               for e in es):
        raise SealedRefusal("refused: the activity chain does not reach the anchor commit")
    canon = [[e["activity_type"], e["before"], e["after"]] for e in es]
    return {"activity_entries": len(es), "activity_sha256": sha256_bytes(canonical_bytes(canon))}


def check_rules(rules: list, ruleset: dict) -> dict:
    """R23.2: the branch carries non_fast_forward and deletion; ruleset RULESET_ID active with no bypass actors."""
    types = {r.get("type") for r in (rules or []) if isinstance(r, dict)}
    if not {"non_fast_forward", "deletion"} <= types:
        raise SealedRefusal("refused: the branch rules lack non_fast_forward or deletion")
    if not isinstance(ruleset, dict) or ruleset.get("id") != RULESET_ID or ruleset.get("enforcement") != "active" \
            or ruleset.get("bypass_actors") != []:
        raise SealedRefusal("refused: the ledger ruleset is not active with no bypass actors")
    rec = {"ruleset_id": RULESET_ID, "ruleset_updated_at": ruleset.get("updated_at")}
    if ruleset.get("stub"):
        rec["stub"] = True                                   # R27.1(b): a REAL validation refuses this key
    return rec


def host_checks(remote_sha: str, root: Path, api, branch: str, anchor: str) -> dict:
    """R22.1 + R23.2, after the fetch and before anything else, on every invocation (stage 1, stage 2, the selection-
    rerun check). `api` exists for tests only; the real entry point never sets it."""
    from urllib.parse import quote
    if api is None:
        check_gh_socket()                                    # R27.2
    api = api or gh_api
    ref = f"refs/heads/{branch}"
    log = api(f"/repos/{GH_REPO}/activity?ref={quote(ref, safe='')}&per_page=100&direction=asc", paginate=True)
    rec = check_activity(log, remote_sha, anchor, lambda a, b: is_ancestor(a, b, root), ref)
    rec["branch_created_commit"] = sorted(log, key=lambda e: (e["timestamp"], e["id"]))[0]["after"]
    rec.update(check_rules(api(f"/repos/{GH_REPO}/rules/branches/{quote(branch, safe='')}"),
                           api(f"/repos/{GH_REPO}/rulesets/{RULESET_ID}")))
    return rec


def check_release_pins(r: dict, remote_sha: str, root: Path, ledger=None) -> None:
    """R22.2: `branch_head_at_release` is an ancestor of the fetched head; for stage 2, `gate_commit` is an ancestor
    and contains the latest GATE entry of the pinned prefix; `activity_anchor_commit`, if given, is the anchor."""
    isanc = lambda a, b: is_ancestor(a, b, root)
    h = r.get("branch_head_at_release")
    if not (isinstance(h, str) and len(h) == 40 and isanc(h, remote_sha)):
        raise SealedRefusal("refused: branch_head_at_release is missing or not an ancestor of the fetched head")
    if r.get("activity_anchor_commit", ANCHOR_COMMIT) != ANCHOR_COMMIT:
        raise SealedRefusal("refused: the release names another activity anchor")
    if "_gate_latest" in r:
        g = r.get("gate_commit")
        if not (isinstance(g, str) and len(g) == 40 and isanc(g, remote_sha)):
            raise SealedRefusal("refused: gate_commit is missing or not an ancestor of the fetched head")
        at = ledger._entries_at(g) if ledger is not None else []
        if not any(x == r["_gate_latest"] for x in at):
            raise SealedRefusal("refused: gate_commit does not contain the latest gate record")


# ------------------------------------------------------------------ R20.7 stage-2 opening (inside the runner only)
_STAGE2_OPEN = {"open": False}


def code_text(path) -> str:
    """R29.2: a record of the code repository read as a blob at HEAD (the verified engine commit), never the working
    tree; a flag hiding an edit refuses."""
    rel = str(Path(path).resolve().relative_to(ROOT.resolve()))
    check_read_flags(ROOT, [rel])
    b = blob_at("HEAD", rel, ROOT)
    if b is None:
        raise SealedRefusal(f"refused: {rel} is not committed")
    return b.decode()


def sealed_record() -> dict:
    """basename -> recorded sha256 of the full French files, hashed unopened before sealing."""
    out = {}
    for ln in code_text(SEALED_RECORD).splitlines():
        if ln.strip():
            h, p = ln.split()[:2]
            out[Path(p).name] = h
    return out


class stage2_opened:
    """Unseal (mode 0400) the sealed files, check their recorded hashes, open the loaders; re-seal (mode 000) and
    close on exit, whatever happens. Entered by the runner only after the stage-2 release and ledger verified."""
    def __init__(self, sealed_paths, recorded: dict | None = None):
        self.paths = [Path(p) for p in sealed_paths]; self.recorded = recorded

    def __enter__(self):
        import os
        for p in self.paths:
            io_check(p, "chmod")                                 # R28.3: only the real run unseals
        try:
            for p in self.paths:
                os.chmod(p, 0o400)
            rec = sealed_record() if self.recorded is None else self.recorded
            for p in self.paths:
                if rec.get(p.name) != sha256_file(p):
                    raise SealedRefusal(f"refused: {p.name} differs from its recorded sealed hash")
        except BaseException:
            self.__exit__(None, None, None)
            raise
        _STAGE2_OPEN["open"] = True
        return self

    def __exit__(self, *a):
        import os
        _STAGE2_OPEN["open"] = False
        for p in self.paths:
            try:
                os.chmod(p, 0o000)
            except OSError:
                pass
        return False


def seal_guard(path) -> None:
    """A path under the seal is readable only inside the runner's verified stage-2 context."""
    if SEALED_MARK in str(path) and not _STAGE2_OPEN["open"]:
        raise SealedRefusal("refused: sealed path outside the verified stage-2 run")


def assert_window(end) -> None:
    if pd.Timestamp(end) > rc.D_END and not _STAGE2_OPEN["open"]:
        raise SealedRefusal("refused: a window end after 2019-12-31 outside the verified stage-2 run")


def verify_release2(r: dict, entries: list) -> dict:
    """Pure checks of the stage-2 release against the ledger: window, header, no opening list (S1c), the ledger
    prefix pinned by length and chain hash, every gate record open and consistent, engine commit (S1a)."""
    if r is None or r.get("windows_released") != [W_H]:
        raise SealedRefusal(f"refused: stage 2 needs a committed release with windows_released [\"{W_H}\"]")
    if "opening_condition_hypotheses" in r:
        raise SealedRefusal("refused: the stage-2 release cannot name the opening list")
    if r.get("protocol_header_sha256") != FROZEN_V2_SHA256:
        raise SealedRefusal("refused: release names a different header sha256")
    n = r.get("ledger_prefix_len")
    if not isinstance(n, int) or n < 1 or n > len(entries) or chain_hash(entries[:n]) != r.get("ledger_prefix_chain_sha256"):
        raise SealedRefusal("refused: the release's pinned ledger prefix does not match the ledger")
    runs = _runs(entries[:n])
    gates = [x["record"] for x in runs if x["record"] and x["record"]["kind"] == "GATE"]
    if not gates or any(g["gate_open"] is not True or g["gate_open"] is not gate_decision(g["gate_signs"])[0]
                        for g in gates):
        raise SealedRefusal("refused: a stage-1 gate record is closed or inconsistent; closed is final (R17)")
    s1 = [x for x in runs if x["start"]["stage"] == "stage1"]
    if s1[-1]["record"] is None:
        raise SealedRefusal("refused: the latest stage-1 run in the pinned prefix has no gate record")
    if r.get("engine_commit") != s1[-1]["start"]["engine_commit"]:
        raise SealedRefusal("refused: stage-2 engine commit differs from the latest stage-1 run's")
    out = dict(r)
    out["_gate_latest"] = s1[-1]["record"]
    return out


def canonical_bytes(obj) -> bytes:
    import json
    return (json.dumps(obj, sort_keys=True, default=float, separators=(",", ":")) + "\n").encode()


def magnitudes_sha(obj) -> str:
    """S6: stage 1 keeps no magnitudes file; it records only this hash."""
    import hashlib
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def verify_reproduction(obj, expected_sha: str) -> None:
    """Final run: its pre-1998 recomputation must reproduce the recorded magnitudes hash before printing."""
    got = magnitudes_sha(obj)
    if got != expected_sha:
        raise SealedRefusal(f"refused: pre-1998 recomputation sha {got} != recorded {expected_sha}")


def sign(x) -> str:
    """O5: a NaN is neither sign."""
    return "NaN" if not np.isfinite(x) else ("+" if x > 0 else "-")


def assert_stage1_window(end) -> None:
    if pd.Timestamp(end) > PRE_END:
        raise SealedRefusal(f"refused: stage 1 reads nothing after {PRE_END.date()} (asked {end})")


# --------------------------------------------------------------------------- R28.3 the I/O choke point
REAL_DATA_ROOT = Path("/home/ubuntu2/tmp/rotation-core/data")        # the code's data root (FR.parent, YAHOO.parent)
REAL_INPUT_RECORD = ROOT / "research/rotation_core/v2_power/REAL_INPUT_SHA256.txt"
# None: a direct call beneath main (declared, R27.0); "real": the real run; "test": a wholly temporary supplied
# context; "supplied_real": a supplied context touching anything real (it may read and write no data at all).
_IO = {"mode": None}


def set_io_mode(mode) -> None:
    _IO["mode"] = mode


def recorded_real_hashes() -> set:
    out = set()
    for rec in (REAL_INPUT_RECORD, SEALED_RECORD):
        for ln in code_text(rec).splitlines():
            if ln.strip() and not ln.startswith("#"):
                out.add(ln.split()[0])
    return out


def _under(p, base) -> bool:
    import os
    r, b = os.path.realpath(str(p)), os.path.realpath(str(base))
    return r == b or r.startswith(b + os.sep)


def io_check(path, kind: str) -> None:
    """Every data read ("read"), result write ("write") and sealed chmod ("chmod") passes here, before opening."""
    import io as _io
    mode = _IO["mode"]
    if mode in (None, "real"):
        return
    if mode == "supplied_real":
        raise SealedRefusal("refused: a supplied context touching the real repository reads and writes no data")
    if kind == "chmod":
        raise SealedRefusal("refused: a sealed file is unsealed only by the real run")
    if isinstance(path, _io.StringIO):
        if kind == "read" and sha256_bytes(path.getvalue().encode()) in recorded_real_hashes():
            raise SealedRefusal("refused: an in-memory input equals a real input")
        return
    if not _under(path, "/tmp") or _under(path, ROOT) or _under(path, REAL_DATA_ROOT):
        raise SealedRefusal("refused: a test context reads or writes only under the system temporary directory")
    if kind == "read" and Path(path).is_file() and sha256_file(path) in recorded_real_hashes():
        raise SealedRefusal("refused: a test context input equals a recorded real input")


def write_text(path, text: str) -> None:
    io_check(path, "write")
    Path(path).write_text(text)


# --------------------------------------------------------------------------- loaders
def _lines(path):
    """A file path, or an in-memory text buffer (R20.4: the fixture dry run takes no path)."""
    import io
    io_check(path, "read")
    if isinstance(path, io.StringIO):
        return io.StringIO(path.getvalue())
    return open(path)


def load_french_industries(path, end) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(value-weighted, equal-weighted) daily returns as fractions, NaN where missing (-99.99 / -999), dates <= end.
    Lines dated after `end` are skipped by their date field before any value is parsed."""
    seal_guard(path); assert_window(end)
    endk = pd.Timestamp(end).strftime("%Y%m%d")
    secs, cur = {}, None
    for ln in _lines(path):
        if "Weighted Returns -- Daily" in ln:
            cur = "vw" if "Value" in ln else "ew"; secs[cur] = {"cols": None, "rows": []}; continue
        if cur is None:
            continue
        if secs[cur]["cols"] is None and ln.startswith(","):
            secs[cur]["cols"] = [c.strip() for c in ln.split(",")[1:]]; continue
        k = ln.split(",", 1)[0].strip()
        if len(k) == 8 and k.isdigit():
            if k > endk:
                continue
            secs[cur]["rows"].append(ln.rstrip("\n").split(","))
    out = []
    for key in ("vw", "ew"):
        r = secs[key]["rows"]
        df = pd.DataFrame([x[1:] for x in r], index=pd.to_datetime([x[0].strip() for x in r], format="%Y%m%d"),
                          columns=secs[key]["cols"]).astype(float)
        out.append(df.where(df > -99.0) / 100.0)
    return out[0], out[1]


def load_yahoo_tr(path, end) -> pd.Series:
    """F1: daily total return from a Yahoo parquet, rows filtered on the Date column at the Arrow level before any
    pandas frame exists; a window end after 2019-12-31 needs a valid stage-2 release (R13)."""
    import pyarrow.parquet as pq
    seal_guard(path); assert_window(end); io_check(path, "read")
    end = pd.Timestamp(end)
    t = pq.read_table(path, columns=["Date", "Adj Close"], filters=[("Date", "<=", end.to_pydatetime())])
    d = t.to_pandas()
    if "Date" not in d.columns:
        d = d.reset_index()
    x = d["Adj Close"].astype(float)
    x.index = pd.to_datetime(d["Date"]).dt.normalize().values
    assert x.index.max() <= end, "post-seal row reached a frame"
    return x.sort_index()


def load_french_market(path, end) -> tuple[pd.Series, pd.Series]:
    seal_guard(path); assert_window(end)
    endk = pd.Timestamp(end).strftime("%Y%m%d")
    rows = []
    for ln in _lines(path):
        k = ln.split(",", 1)[0].strip()                    # R26.6: the date field alone decides, before any split
        if not (len(k) == 8 and k.isdigit() and k <= endk):
            continue
        rows.append([x.strip() for x in ln.split(",")])
    idx = pd.to_datetime([r[0] for r in rows], format="%Y%m%d")
    mkt = pd.Series([float(r[1]) + float(r[4]) for r in rows], index=idx) / 100
    rf = pd.Series([float(r[4]) for r in rows], index=idx) / 100
    return mkt, rf


# --------------------------------------------------------------------------- legs, breadth
@dataclass
class Legs:
    formed: dict          # month-end -> (offence list, defence list, eligible list)
    returns: pd.DataFrame  # daily OFF, DEF, BASE leg returns (net of intra-leg re-formation cost at the leg level)
    valid: pd.DataFrame    # daily valid-member counts per leg
    dropped_industry_days: int
    fee_bp: float = FEE_INDUSTRY_BP        # re-formation cost rate inside `returns` (net legs)


def held_leg_returns(blk: np.ndarray) -> np.ndarray:
    """Equal weights at the first row, then held (drifting); a missing member-day is dropped from that day's
    average and its weight carries unchanged."""
    w = np.full(blk.shape[1], 1.0 / blk.shape[1])
    out = np.full(blk.shape[0], np.nan)
    for d_ in range(blk.shape[0]):
        ok = np.isfinite(blk[d_])
        if ok.any():
            out[d_] = float((w[ok] * blk[d_][ok]).sum() / w[ok].sum())
            w = w.copy(); w[ok] = w[ok] * (1 + blk[d_][ok]); w = w / w.sum()
    return out


def form_legs(vw: pd.DataFrame, mkt: pd.Series, start=None, min_valid: int = 252, min_pairs: int = 200,
              fee_bp: float = FEE_INDUSTRY_BP, leg_size: int | None = None, fixed: tuple | None = None) -> Legs:
    """Industries: legs = top / bottom third by trailing beta. Funds (F4): leg_size=3. fixed=(offence, defence)
    holds named members (named mapping, descriptive), base = all eligible."""
    s = vw.index
    valid = vw.notna()
    nvalid = valid.cumsum()
    me = pd.DatetimeIndex(pd.Series(s, index=s).groupby([s.year, s.month]).max().values)
    if start is not None:
        me = me[me >= pd.Timestamp(start) - pd.offsets.MonthEnd(2)]
    formed = {}
    for t in me:
        i = s.get_loc(t)
        if i < 253:
            continue
        w = slice(s[i - 252], s[i - 1])                    # data to t-1
        y, x = vw.loc[w], mkt.reindex(s).loc[w]
        b = {}
        for c in vw.columns:
            ok = y[c].notna() & x.notna()
            if nvalid[c].iloc[i - 1] >= min_valid and ok.sum() >= min_pairs:
                b[c] = float(np.cov(y[c][ok], x[ok])[0, 1] / np.var(x[ok], ddof=1))
        if len(b) < 6:
            continue
        bs = pd.Series(b).sort_values(kind="mergesort")
        if fixed is not None:
            off = [c for c in fixed[0] if c in b]; dfn = [c for c in fixed[1] if c in b]
            if off and dfn:
                formed[t] = (off, dfn, list(bs.index))
            continue
        k = leg_size if leg_size is not None else len(bs) // 3
        formed[t] = (list(bs.index[-k:]), list(bs.index[:k]), list(bs.index))
    keys = pd.DatetimeIndex(sorted(formed))
    cols = ["OFF", "DEF", "BASE", "OFF_DRIFT", "DEF_DRIFT", "BASE_DRIFT",
            "OFF_TURN", "DEF_TURN", "BASE_TURN", "OFF_DRIFT_TURN", "DEF_DRIFT_TURN", "BASE_DRIFT_TURN"]
    R = pd.DataFrame(np.nan, index=s, columns=cols)
    V = pd.DataFrame(0, index=s, columns=cols)
    unique_dropped = set()
    dropped = 0
    prev = None
    fee = fee_bp / 1e4
    for j, t in enumerate(keys):
        a = s.get_loc(t) + 1
        z = s.get_loc(keys[j + 1]) + 1 if j + 1 < len(keys) else len(s)
        days = s[a:z]
        legs = formed[t]
        for col, mem in zip(["OFF", "DEF", "BASE"], legs):
            blk = vw.loc[days, mem]
            ok = blk.notna()
            if col == "BASE":                 # S8: unique industry-days (the base contains every eligible member)
                for c_ in blk.columns[(~ok).any(axis=0).values]:
                    for d_ in blk.index[~ok[c_].values]:
                        unique_dropped.add((c_, d_))
            R.loc[days, col] = blk.mean(axis=1, skipna=True)     # missing industry-day dropped, not imputed
            V.loc[days, col] = ok.sum(axis=1)
            if prev is not None and len(days):
                old = set(prev[["OFF", "DEF", "BASE"].index(col)])
                repl = len(set(mem) - old) / max(1, len(mem))
                R.loc[days[0], col] = (1 + R.loc[days[0], col]) / (1 + 2 * repl * fee) - 1   # re-formation cost
                R.loc[days[0], col + "_TURN"] = 2 * repl
        # R14(b) / S4: drift reading for ALL three legs: equal weights at the month's first session, then held
        if len(days):
            for col, mem in zip(["OFF", "DEF", "BASE"], legs):
                R.loc[days, col + "_DRIFT"] = held_leg_returns(vw.loc[days, mem].to_numpy(dtype=float))
                V.loc[days, col + "_DRIFT"] = V.loc[days, col]
                if prev is not None:
                    repl = len(set(mem) - set(prev[["OFF", "DEF", "BASE"].index(col)])) / max(1, len(mem))
                    R.loc[days[0], col + "_DRIFT"] = (1 + R.loc[days[0], col + "_DRIFT"]) / (1 + 2 * repl * fee) - 1
                    R.loc[days[0], col + "_DRIFT_TURN"] = 2 * repl
        prev = legs
    for c in [c for c in cols if c.endswith("_TURN")]:
        R[c] = R[c].fillna(0.0)
    return Legs(formed, R, V, len(unique_dropped), fee_bp)


def observed_level_sma(vw: pd.DataFrame, n: int = 50) -> tuple[pd.DataFrame, pd.DataFrame]:
    """S3: per industry, the level is defined only on observed closes (a missing day is not a close; the level
    carries across it without a 0% close), and the SMA is the mean of the last n OBSERVED levels. Both are NaN on
    a missing day, so the industry drops out of that day's breadth numerator and denominator."""
    lvl = pd.DataFrame(np.nan, index=vw.index, columns=vw.columns)
    sma = lvl.copy()
    for c in vw.columns:
        x = vw[c].dropna()
        lv = (1 + x).cumprod()
        lvl.loc[lv.index, c] = lv.values
        sma.loc[lv.index, c] = lv.rolling(n, min_periods=n).mean().values
    return lvl, sma


def breadth_i(vw: pd.DataFrame, legs: Legs, n: int = 50) -> pd.Series:
    """Share of the offence leg's industries above their own 50-session SMA (missing industry-days dropped)."""
    lvl, sma = observed_level_sma(vw, n)
    above = (lvl > sma).astype(float).where(sma.notna() & vw.notna())
    out = pd.Series(np.nan, index=vw.index)
    keys = pd.DatetimeIndex(sorted(legs.formed))
    for j, t in enumerate(keys):
        a = vw.index.get_loc(t) + 1
        z = vw.index.get_loc(keys[j + 1]) + 1 if j + 1 < len(keys) else len(vw.index)
        days = vw.index[a:z]
        out.loc[days] = above.loc[days, legs.formed[t][0]].astype(float).mean(axis=1, skipna=True).to_numpy(dtype=float)
    return out


def relative_line(legs: Legs) -> pd.Series:
    r = legs.returns
    started = (r["OFF"].notna() & r["DEF"].notna()).cumsum() > 0
    line = (1 + r["OFF"].fillna(0)).cumprod() / (1 + r["DEF"].fillna(0)).cumprod()
    return line.where(started)            # S2: no flat padding before the first formed leg


# --------------------------------------------------------------------------- state machines (draft rev 4)
NEUTRAL, DEFEND, ATTACK = 0, 1, 2
ARM_MEMORY = 21          # fixed setting (R4), not in the grid
ATTACK_MIN_HOLD = 63     # fixed (R1), not in the grid
WASH_LO, WASH_MAX = 0.25, 20


def washout_spells(sh: np.ndarray, lo: float = WASH_LO):
    """For each close i: if close i is the first close above `lo` after a run of closes <= `lo` (a spell ending at
    i-1), return the spell length and the sessions from the spell's lowest close (earliest if tied) to i.
    Otherwise NaN. Uses only closes <= i."""
    n = len(sh); run_len = np.full(n, np.nan); from_low = np.full(n, np.nan)
    start = None; low_i = None
    for i in range(n):
        v = sh[i]
        if np.isfinite(v) and v <= lo:
            if start is None:
                start, low_i = i, i
            elif v < sh[low_i]:
                low_i = i
        else:
            if start is not None and np.isfinite(v):
                run_len[i] = i - start
                from_low[i] = i - low_i
            if np.isfinite(v):
                start, low_i = None, None
    return run_len, from_low


def current_leg_breadth(vw: pd.DataFrame, legs: Legs, lookback: int = 126, n: int = 50) -> dict:
    """R2: for each day t, breadth history over the look-back is recomputed on the CURRENT leg's members.
    Returns per-day arrays: br (today), br_max126 (max over t-125..t on current members), wash_run_prev (length of
    the washout spell ending at t-1 when t is its recovery close), wash_from_low (sessions from that spell's lowest
    close to t), n_members."""
    lvl, sma = observed_level_sma(vw, n)
    above = (lvl > sma).astype(float).where(sma.notna() & vw.notna())
    s = vw.index
    br = pd.Series(np.nan, index=s); bmax = br.copy(); run_prev = br.copy(); from_low = br.copy(); nm = br.copy()
    keys = pd.DatetimeIndex(sorted(legs.formed))
    for j, t in enumerate(keys):
        a_ = s.get_loc(t) + 1
        z = s.get_loc(keys[j + 1]) + 1 if j + 1 < len(keys) else len(s)
        if a_ >= z:
            continue
        mem = legs.formed[t][0]
        lo = max(0, a_ - lookback - 400)
        sh = above.iloc[lo:z][mem].mean(axis=1, skipna=True).to_numpy(dtype=float)
        mx = pd.Series(sh).rolling(lookback, min_periods=lookback).max().to_numpy()
        rl, fl = washout_spells(sh)
        k0 = a_ - lo
        br.iloc[a_:z] = sh[k0:]
        bmax.iloc[a_:z] = mx[k0:]
        run_prev.iloc[a_:z] = rl[k0:]
        from_low.iloc[a_:z] = fl[k0:]
        nm.iloc[a_:z] = len(mem)
    return {"br": br, "bmax": bmax, "wash_run_prev": run_prev, "wash_from_low": from_low, "n_members": nm}


def h1_states(rel: pd.Series, bd: dict, h: float, b: float, use_breadth: bool = True,
              arm_memory: int = ARM_MEMORY, return_log: bool = False):
    """H1 / price-only control state decided at each close, draft rev 4 rules R1-R5.
    Entry: DEFEND when armed within the last `arm_memory` sessions and the relative line crosses below its 50-session
    SMA; ATTACK on the first close above 25% after a washout spell (consecutive closes <= 25%) if the spell QUALIFIES
    (R12: on at least one close inside the spell the relative line is within h% of its 126-session low, i.e.
    rel <= (1 + h/100) * min(rel over the 126 sessions ending at that close)) and that close is within 20 sessions of
    the spell's lowest breadth close (earliest if tied). Same-day DEFEND and ATTACK: DEFEND wins (counted).
    Exits: DEFEND -> ATTACK at an ATTACK confirm, or -> NEUTRAL at the first month-end (after the entry day) on which
    the relative line closes above its SMA50. ATTACK -> DEFEND at a DEFEND trigger, or -> NEUTRAL at the first
    month-end at least 63 sessions after entry. A state is never exited on its entry day. Re-triggering the state
    already in force is ignored (its clock is not reset)."""
    s = rel.index
    hi = rel.rolling(126, min_periods=126).max()
    sma = rel.rolling(50, min_periods=50).mean()
    br, bmax = bd["br"].reindex(s), bd["bmax"].reindex(s)
    runp, fromlow = bd["wash_run_prev"].reindex(s), bd["wash_from_low"].reindex(s)
    near = (rel >= (1 - h / 100) * hi)
    lo126 = rel.rolling(126, min_periods=126).min()
    near_low = (rel <= (1 + h / 100) * lo126).fillna(False).values      # R12: literal mirror of `near`
    armed = near & ((br <= bmax - b / 100 + 1e-12) if use_breadth else True)
    armed = armed & hi.notna() & (bmax.notna() if use_breadth else True)
    armed_recent = armed.astype(float).rolling(arm_memory + 1, min_periods=1).max() > 0
    month_end = (pd.Series(s, index=s).groupby([s.year, s.month]).transform("max") == s).values
    cross_dn = ((rel < sma) & (rel.shift(1) >= sma.shift(1))).values
    above_sma = (rel > sma).values
    runp_v, fromlow_v = runp.values, fromlow.values
    st = np.full(len(s), np.nan)
    log = {"conflicts": 0, "wash_fired": 0, "wash_expired": 0, "wash_spells": 0, "wash_qualified": 0,
           "armed": armed.values.copy(), "exit": {"DEFEND_by_ATTACK": 0, "DEFEND_by_month_end_above_sma": 0,
                                                  "ATTACK_by_DEFEND": 0, "ATTACK_by_63_month_end": 0}}
    state, entry_i = NEUTRAL, None
    formed_n = rel.notna().cumsum()
    ready = (hi.notna() & sma.notna() & bmax.notna() & (formed_n >= 126)).values   # S2
    has_legs = rel.notna().values
    for i in range(len(s)):
        if not ready[i]:
            if has_legs[i]:
                st[i] = NEUTRAL               # S2: legs exist, look-backs not yet full -> NEUTRAL and unarmed
            continue
        defend = bool(armed_recent.iloc[i]) and bool(cross_dn[i])
        attack = False
        if np.isfinite(runp_v[i]) and runp_v[i] > 0:          # recovery close of a washout spell
            log["wash_spells"] += 1
            k = int(runp_v[i])
            qualifies = bool(near_low[max(0, i - k):i].any())   # R12: line near its 126-session low inside the spell
            log["wash_qualified"] += qualifies
            if qualifies and fromlow_v[i] <= WASH_MAX:          # trough clock (final R3)
                attack = True; log["wash_fired"] += 1
            else:
                log["wash_expired"] += 1
        if defend and attack:
            log["conflicts"] += 1
            attack = False
        if defend and state != DEFEND:
            if state == ATTACK:
                log["exit"]["ATTACK_by_DEFEND"] += 1
            state, entry_i = DEFEND, i
        elif attack and state != ATTACK:
            if state == DEFEND:
                log["exit"]["DEFEND_by_ATTACK"] += 1
            state, entry_i = ATTACK, i
        elif state == DEFEND and i != entry_i and month_end[i] and above_sma[i]:
            log["exit"]["DEFEND_by_month_end_above_sma"] += 1
            state, entry_i = NEUTRAL, None
        elif state == ATTACK and i != entry_i and month_end[i] and (i - entry_i) >= ATTACK_MIN_HOLD:
            log["exit"]["ATTACK_by_63_month_end"] += 1
            state, entry_i = NEUTRAL, None
        st[i] = state
    out = pd.Series(st, index=s)
    return (out, log) if return_log else out


def h3_states(legs: Legs) -> pd.Series:
    r = legs.returns
    started = (r["OFF"].notna() & r["DEF"].notna()).cumsum() > 0
    lo = (1 + r["OFF"].fillna(0)).cumprod().where(started); ld = (1 + r["DEF"].fillna(0)).cumprod().where(started)
    m126 = (lo / lo.shift(126)) - (ld / ld.shift(126))
    s = r.index
    me = pd.Series(s, index=s).groupby([s.year, s.month]).transform("max") == s
    st = pd.Series(np.nan, index=s)
    st[me & m126.notna()] = np.where(m126[me & m126.notna()] > 0, ATTACK, DEFEND)
    return st.ffill()


def targets_from_states(st: pd.Series, cash_for_defend: bool = False) -> pd.DataFrame:
    cols = ["OFF", "DEF", "BASE"]
    T = pd.DataFrame(np.nan, index=st.index, columns=cols)
    ok = st.notna()
    T.loc[ok] = 0.0
    T.loc[ok & (st == NEUTRAL), "BASE"] = 1.0
    T.loc[ok & (st == ATTACK), "OFF"] = 1.0
    if not cash_for_defend:
        T.loc[ok & (st == DEFEND), "DEF"] = 1.0
    return T


def base_view(legs_r: pd.DataFrame, base: str = "eq", kind: str = "net", formed_fee_bp: float = FEE_INDUSTRY_BP,
              book_fee_bp: float | None = None) -> pd.DataFrame:
    """Leg returns OFF/DEF/BASE.
    base: R14 'eq' (equal weight every session over the month's set; governing) or 'drift' (S4: all three legs
      equal at the month's first session, then held).
    kind (R18): 'net'   = as formed, re-formation cost at `formed_fee_bp` (BASE run: book and mix);
                'gross' = no re-formation cost (STRICT run: the matched mix, which pays nothing);
                'book'  = re-formation cost at `book_fee_bp` (STRICT run: the book, 20 bp industries / 10 bp funds)."""
    suf = "_DRIFT" if base == "drift" else ""
    names = ["OFF", "DEF", "BASE"]
    net = legs_r[[n + suf for n in names]].set_axis(names, axis=1)
    if kind == "net":
        return net.copy()
    turn = legs_r[[n + suf + "_TURN" for n in names]].set_axis(names, axis=1) if (names[0] + suf + "_TURN") in legs_r \
        else pd.DataFrame(0.0, index=legs_r.index, columns=names)
    gross = (1 + net) * (1 + turn * formed_fee_bp / 1e4) - 1
    if kind == "gross":
        return gross
    if kind == "book":
        return (1 + gross) / (1 + turn * book_fee_bp / 1e4) - 1
    raise ValueError(kind)


# --------------------------------------------------------------------------- F4: tradable fund tier
FUNDS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "XLRE", "XLC"]
NAMED_OFFENCE, NAMED_DEFENCE = ["XLK"], ["XLP", "XLU", "XLV"]


def load_fund_panel(yahoo_dir, end, tickers=FUNDS) -> tuple[pd.DataFrame, pd.Series]:
    """Fund daily total returns and SPY (the fund tier's beta reference), all via the sealed loader."""
    yd = Path(yahoo_dir)
    rets = {t: load_yahoo_tr(yd / f"{t}.parquet", end).pct_change(fill_method=None) for t in tickers}
    spy = load_yahoo_tr(yd / "SPY.parquet", end).pct_change(fill_method=None)
    sess = spy.index
    R = pd.DataFrame({t: r.reindex(sess) for t, r in rets.items()})
    return R, spy


def form_fund_legs(fund_r: pd.DataFrame, spy_r: pd.Series, fixed=None) -> Legs:
    """Header tradable tier: offence = 3 highest trailing-252-session beta (to SPY, data to t-1), defence = 3 lowest,
    among funds with >= 252 observed sessions; base = equal weight of eligible funds; 5 bp per side."""
    return form_legs(fund_r, spy_r, min_valid=252, min_pairs=200, fee_bp=FEE_FUND_BP, leg_size=3, fixed=fixed)


def map_states_to_sessions(st: pd.Series, sessions: pd.DatetimeIndex) -> pd.Series:
    """Industry state decided at the last industry date <= each fund session (signals from the industry
    portfolios, execution on funds)."""
    s = st.dropna()
    pos = np.searchsorted(s.index.values, pd.DatetimeIndex(sessions).values, side="right") - 1
    vals = np.full(len(sessions), np.nan)
    ok = pos >= 0
    vals[ok] = s.values[pos[ok]]
    return pd.Series(vals, index=sessions)


def tradable_veto(fund_estimates: dict) -> bool:
    """Header rule: 'A pass on industry portfolios with a negative point estimate on the tradable funds in
    2020-2025 is reported as signal not shown to be tradable, not as a pass.' True = veto fires. fund_estimates
    maps each evaluated reading (both R14 base readings; 5 bp and 2x = 10 bp fees) to the point estimate of the fund
    book's excess over its exposure-matched mix on 2020-2025. Any negative estimate fires the veto."""
    return any(not (np.isfinite(v) and v >= 0) for v in fund_estimates.values())      # R23.7: fails closed


def simulate_states(st: pd.Series, legs: Legs, rf: pd.Series, start, end, cash_for_defend=False,
                    fee_bp=FEE_INDUSTRY_BP, name="v2", base: str = "eq", strict: bool = False) -> rc.Book:
    """BASE run (strict=False): legs net of re-formation at legs.fee_bp; switches at fee_bp.
    STRICT run (R18): switches at fee_bp (the caller passes 2x) and re-formation of held legs at the same 2x rate."""
    R = (base_view(legs.returns, base, "book", legs.fee_bp, fee_bp) if strict else base_view(legs.returns, base)).loc[start:end]
    avail = legs.valid[["OFF", "DEF", "BASE"]].loc[start:end] > 0
    return rc.simulate(targets_from_states(st.loc[start:end], cash_for_defend), R, rf.reindex(R.index),
                       fee_bp, name, start=pd.Timestamp(start), end=pd.Timestamp(end), avail=avail,
                       equity_cols=("OFF", "DEF", "BASE"))


# --------------------------------------------------------------------------- matched-mix contrast
def ann_factor(idx) -> float:
    """252 sessions per year of weekday sessions; Saturday sessions (French data before 1952) raise it in
    proportion: 252 * n_sessions / n_weekday_sessions. Exactly 252 on any window without Saturdays, so every
    1998-2019 figure is unchanged (replaces b7ef827b1d's sessions-per-calendar-year factor before any read)."""
    idx = pd.DatetimeIndex(idx)
    wk = int((idx.dayofweek < 5).sum())
    return float(rc.TRADING_DAYS) * len(idx) / wk if wk else float(rc.TRADING_DAYS)


def window_excess(book: rc.Book, legs_r: pd.DataFrame, cash: pd.Series, a, z, ann: float | None = None) -> float:
    """THE gate / sign-leg statistic (R13-g): annualised mean daily excess of the book over its exposure-matched
    static mix, the mix built from the book's own average weights on [a, z] alone; annualised by observed sessions
    per year in [a, z]. One function for the gate and for the final conjunction."""
    idx = book.returns.index
    m = (idx >= pd.Timestamp(a)) & (idx <= pd.Timestamp(z))
    ii = idx[m]
    r = book.returns.loc[ii].values
    W = book.holdings.loc[ii, ["OFF", "DEF", "BASE"]].values
    W = np.concatenate([W, 1 - W.sum(axis=1, keepdims=True)], axis=1)
    L = np.concatenate([legs_r.loc[ii, ["OFF", "DEF", "BASE"]].fillna(0).values,
                        cash.reindex(ii).fillna(0).values[:, None]], axis=1)
    return float(matched_mix_stat(r[None], W[None], L[None], ann=ann_factor(ii) if ann is None else ann)[0])


def matched_mix_stat(r, w, legs_r, ann: float = rc.TRADING_DAYS):
    """Annualised mean of r - (matched static mix), mix weights = this sample's own average weights.
    r: (B, n); w: (B, n, 3) start-of-day weights in OFF/DEF/BASE; legs_r: (B, n, 3); cash = 1 - sum(w) earns 0
    in the reference only if the strategy held cash (ablation), handled by the caller via the 4th column."""
    wbar = w.mean(axis=1, keepdims=True)
    ref = (wbar * legs_r).sum(axis=2)
    return (r - ref).mean(axis=1) * ann


def matched_contrast(book: rc.Book, legs_r: pd.DataFrame, cash: pd.Series, mask, B=10_000, block=21, seed=20261111,
                     ann: float | None = None):
    idx = book.returns.index[mask.reindex(book.returns.index).fillna(False).values]
    ann = ann_factor(idx) if ann is None else ann
    r = book.returns.loc[idx].values
    W = book.holdings.loc[idx, ["OFF", "DEF", "BASE"]].values
    W = np.concatenate([W, 1 - W.sum(axis=1, keepdims=True)], axis=1)       # cash column
    L = np.concatenate([legs_r.loc[idx, ["OFF", "DEF", "BASE"]].fillna(0).values,
                        cash.reindex(idx).fillna(0).values[:, None]], axis=1)
    obs = float(matched_mix_stat(r[None], W[None], L[None], ann)[0])
    out = []
    for c in range(0, B, 1000):
        ii = rc.stationary_bootstrap_indices(len(r), min(1000, B - c), block, seed + c)
        out.append(matched_mix_stat(r[ii], W[ii], L[ii], ann))
    dist = np.concatenate(out)
    return {"observed": obs, "ci95": rc.ci95(dist), "p_one_sided_centred": rc.centred_p(dist, obs),
            "se": float(np.nanstd(dist, ddof=1)), "finite_draws": rc.finite_draws(dist), "n": int(len(r))}


# --------------------------------------------------------------------------- S1: stage-2 evaluator primitives
LEG_COLS = ["OFF", "DEF", "BASE"]


def window_arrays(book: rc.Book, legs_r: pd.DataFrame, cash: pd.Series, a, z):
    """Daily book return r, start-of-day weights W (OFF, DEF, BASE, cash) and leg returns L on [a, z]."""
    idx = book.returns.index
    ii = idx[(idx >= pd.Timestamp(a)) & (idx <= pd.Timestamp(z))]
    r = book.returns.loc[ii].to_numpy(dtype=float)
    W = book.holdings.loc[ii, LEG_COLS].to_numpy(dtype=float)
    W = np.concatenate([W, 1 - W.sum(axis=1, keepdims=True)], axis=1)
    L = np.concatenate([legs_r.loc[ii, LEG_COLS].fillna(0).to_numpy(dtype=float),
                        cash.reindex(ii).fillna(0).to_numpy(dtype=float)[:, None]], axis=1)
    return ii, r, W, L


def mix_series(W: np.ndarray, L: np.ndarray) -> np.ndarray:
    """The exposure-matched static mix's daily return: the window's own average weights times the legs."""
    return L @ W.mean(axis=0)


def max_drawdown(x) -> float:
    x = np.asarray(x, dtype=float)
    if not len(x) or not np.all(np.isfinite(x)):
        return float("nan")
    v = np.cumprod(1 + x)
    return float((v / np.maximum.accumulate(v) - 1).min())


def raw_mix_excess(r, W, L) -> float:
    """Mean daily excess over the matched mix, not annualised: mean(r) - sum_k mean(W_k) mean(L_k). Algebraically
    the same quantity as matched_mix_stat / ann (the mix weights are constant within a sample)."""
    return float(r.mean() - (W.mean(axis=0) * L.mean(axis=0)).sum())


def bootstrap_draws(series: dict, B: int, block: int, seed, chunk: int = 500) -> dict:
    """Stationary-bootstrap draws of each statistic on ONE window, all keys sharing the same resample indices.
    series[key] = ("mix", r, W, L) -> mean(r) - sum_k mean(W_k) mean(L_k) per resample (mix rebuilt per resample);
                  ("paired", d)    -> mean(d) per resample.
    Returns key -> (B,) raw (daily, not annualised) draws. Chunk c uses seed(c) when `seed` is callable (R21.4:
    SeedSequence streams), else seed + c."""
    n = len(next(iter(series.values()))[1])
    out = {k: [] for k in series}
    done, c = 0, 0
    while done < B:
        b = min(chunk, B - done)
        ii = rc.stationary_bootstrap_indices(n, b, block, seed(c) if callable(seed) else seed + c)
        for k, s in series.items():
            if s[0] == "paired":
                out[k].append(s[1][ii].mean(axis=1))
            else:
                _, r, W, L = s
                m = r[ii].mean(axis=1)
                for j in range(W.shape[1]):
                    m = m - W[:, j][ii].mean(axis=1) * L[:, j][ii].mean(axis=1)
                out[k].append(m)
        done += b; c += 1
    return {k: np.concatenate(v) for k, v in out.items()}


def two_sided_p(dist: np.ndarray, obs: float) -> float:
    """Two-sided centred p (reported beside the governing one-sided p, labelled)."""
    d = np.asarray(dist, dtype=float)
    if not np.isfinite(obs):
        return float("nan")
    return float((1 + np.sum(np.isfinite(d) & (np.abs(d - obs) >= abs(obs)))) / (len(d) + 1))


def pooled_weights(windows: list, convention: str) -> np.ndarray:
    """R15.5 / S1b(iv): weight c_w on each window's RAW mean daily statistic so that the pooled value is the
    years-weighted mean of the windows' annualised statistics. 'weekday': ann_w = 252 n_w / weekday_w, years_w =
    n_w / ann_w; 'fixed252': ann_w = 252, years_w = n_w / 252. Pooled = sum_w years_w ann_w m_w / sum_w years_w
    = sum_w n_w m_w / sum_w years_w."""
    n = np.array([len(ix) for ix in windows], dtype=float)
    if convention == "weekday":
        ann = np.array([ann_factor(ix) for ix in windows])
    elif convention == "fixed252":
        ann = np.full(len(windows), float(rc.TRADING_DAYS))
    else:
        raise ValueError(convention)
    years = n / ann
    return n / years.sum()


def verdict(legs: dict, veto: bool | None) -> str:
    """Final label for one hypothesis. legs: name -> bool (every leg of the conjunction)."""
    if not all(v is True for v in legs.values()):
        return "FAIL"
    if veto:
        return "signal not shown to be tradable"
    return "survives falsification on history"
