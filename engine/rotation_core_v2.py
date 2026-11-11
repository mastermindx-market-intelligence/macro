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


def _committed_clean(path: Path) -> bool:
    try:
        rel = str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return False                                   # outside the repo: never counts as committed
    try:
        subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", rel], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        return False
    out = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", rel], capture_output=True).stdout
    return out.strip() == b""


def _load_release(path: Path) -> dict | None:
    import json
    if not (Path(path).exists() and _committed_clean(path)):
        return None
    return json.loads(Path(path).read_text())


SELECTION_RESULT = ROOT / "research/rotation_core/results_v2_selection_rerun.json"   # R15: rerun pins the setting
SELECTED_REF = (3.0, 25.0)            # grid point selected at 1ca5228b3c (R13-g(i)); R14(d) sensitivity uses it


def selected_setting(selection: Path | None = None) -> tuple[float, float]:
    """R13-g(i)/R15.6: the gate setting is read from the committed selection result (the R15 rerun), never from
    an argument."""
    import json, re
    selection = SELECTION_RESULT if selection is None else selection
    if not _committed_clean(selection):
        raise SealedRefusal("refused: selection result is not committed")
    sel = json.loads(Path(selection).read_text())["selection"]["selected"]
    m = re.fullmatch(r"h(\d+)_b([\d.]+)", sel)
    return float(m.group(1)), float(m.group(2))


BRANCH = "fable/rotation-core-20261110"
REMOTE = "origin"
REMOTE_REF = f"{REMOTE}/{BRANCH}"
OPENING_HYPOTHESES = ("H1", "H3")       # R16 S1c: constant; no release can name or change it
ERAS_GATE = ("E1_1928_1945", "E2_1946_1997")
GATE_READINGS, GATE_COSTS = ("eq", "drift"), ("base", "strict")
PINNED_PATHS = ["engine", "scripts", "tests", "research/rotation_core/protocol_header_v2.json",
                "research/rotation_core/results_v2_selection.json",                 # superseded 2x rows (R18.3)
                "research/rotation_core/v2_power/FRENCH_SEALED_FULL_FILES_SHA256.txt"]  # recorded sealed hashes
COVERED_MODULE_PREFIXES = ("engine.", "scripts.", "tests.")
LEDGER = ROOT / "research/rotation_core/results_v2_run_ledger.json"
SEALED_RECORD = ROOT / "research/rotation_core/v2_power/FRENCH_SEALED_FULL_FILES_SHA256.txt"


class LedgerPushFailed(SealedRefusal):
    pass


def _git(*a, check=True, root=None, env=None, input=None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root or ROOT), *a], capture_output=True, check=check, env=env, input=input)


def check_import_environment(root: Path = ROOT, commit: str | None = None) -> None:
    """R20.8: refuse PYTHONPATH, a loaded sitecustomize/usercustomize, and any covered module imported from outside
    the repository or differing from its blob at `commit`."""
    import os, sys
    if os.environ.get("PYTHONPATH"):
        raise SealedRefusal("refused: PYTHONPATH is set")
    if "usercustomize" in sys.modules:
        raise SealedRefusal("refused: usercustomize is loaded")
    sc = getattr(sys.modules.get("sitecustomize"), "__file__", None)
    if sc is not None:
        # R20.8 as amended (the distro interpreter always loads its own sitecustomize; -S would also drop the venv's
        # site-packages): only the interpreter's own file is accepted, and its sha256 is pinned in versions().
        import sysconfig
        if Path(os.path.abspath(sc)).parent != Path(sysconfig.get_paths()["stdlib"]):
            raise SealedRefusal("refused: a sitecustomize outside the interpreter's own library is loaded")
    for name, mod in list(sys.modules.items()):
        if not name.startswith(COVERED_MODULE_PREFIXES):
            continue
        f = getattr(mod, "__file__", None)
        if f is None:
            continue
        try:
            rel = Path(f).resolve().relative_to(Path(root).resolve())
        except ValueError:
            raise SealedRefusal(f"refused: covered module {name} imported from outside the repository") from None
        if commit is not None:
            want = _git("rev-parse", f"{commit}:{rel}", check=False, root=root).stdout.decode().strip()
            got = _git("hash-object", str(rel), check=False, root=root).stdout.decode().strip()
            if not want or want != got:
                raise SealedRefusal(f"refused: covered module {name} differs from the engine commit")


def check_engine_commit(commit: str, root: Path = ROOT) -> None:
    """S5/R20.8: pinned paths at HEAD identical to `commit`, no modified or UNTRACKED file under them, and a clean
    import environment."""
    if _git("diff", "--quiet", commit, "HEAD", "--", *PINNED_PATHS, check=False, root=root).returncode != 0:
        raise SealedRefusal(f"refused: pinned paths differ from release engine_commit {commit}")
    st = _git("status", "--porcelain", "--untracked-files=all", "--", *PINNED_PATHS, check=False, root=root)
    if st.returncode != 0 or st.stdout.strip():
        raise SealedRefusal("refused: modified or untracked files under the pinned paths")
    check_import_environment(root, commit)


def fetch_remote(root: Path = ROOT, branch: str = BRANCH) -> str:
    """R20.5: fails closed; returns the sha just fetched. Every remote check takes this sha, never a stale ref."""
    r = _git("fetch", "-q", REMOTE, f"+refs/heads/{branch}:refs/remotes/{REMOTE}/{branch}", check=False, root=root)
    if r.returncode != 0:
        raise SealedRefusal("refused: fetching the remote branch failed; no check runs on an unfetched ref")
    return _git("rev-parse", f"refs/remotes/{REMOTE}/{branch}", root=root).stdout.decode().strip()


def on_remote(path: Path, remote_sha: str, root: Path = ROOT) -> None:
    """S5: the commit that last touched `path` (and the file content) must be contained in the fetched remote sha."""
    rel = str(Path(path).resolve().relative_to(Path(root).resolve()))
    c = _git("log", "-1", "--format=%H", "--", rel, check=False, root=root).stdout.decode().strip()
    if not c or _git("merge-base", "--is-ancestor", c, remote_sha, check=False, root=root).returncode != 0:
        raise SealedRefusal(f"refused: {rel} is not committed on the remote branch")
    if _git("diff", "--quiet", remote_sha, "--", rel, check=False, root=root).returncode != 0:
        raise SealedRefusal(f"refused: {rel} differs from the remote branch")


def commit_on_remote(commit: str, remote_sha: str, root: Path = ROOT) -> None:
    if _git("merge-base", "--is-ancestor", commit, remote_sha, check=False, root=root).returncode != 0:
        raise SealedRefusal(f"refused: commit {commit} is not contained in the remote branch")


def file_versions(rel: str, remote_sha: str, root: Path = ROOT) -> list:
    """Every committed version of `rel` on the remote branch, oldest first: [(commit, bytes)] (deletions skipped)."""
    out = _git("log", "--format=%H", "--reverse", remote_sha, "--", rel, check=False, root=root)
    vs = []
    for c in out.stdout.decode().split():
        b = _git("show", f"{c}:{rel}", check=False, root=root)
        if b.returncode == 0:
            vs.append((c, b.stdout))
    return vs


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
            "sitecustomize_sha256": sha256_file(sc) if sc else None}


def check_manifest(r: dict, inputs: dict) -> dict:
    """O6: every input file's sha256 and the library versions must equal the release's manifest."""
    got = {k: sha256_file(p) for k, p in inputs.items()}
    if r.get("inputs_sha256") != got:
        raise SealedRefusal("refused: input file hashes differ from the release manifest")
    if r.get("versions") != versions():
        raise SealedRefusal("refused: library versions differ from the release manifest")
    return got


def stage1_release(release: Path = RELEASE, inputs: dict | None = None, remote_sha: str | None = None) -> dict:
    """Committed stage-1 release, checked against the header, the selection rerun (commit, sha256, on the remote:
    R20.9), the engine commit and the manifest."""
    r = _load_release(release)
    if r is None or r.get("windows_released") != [W_PRE]:
        raise SealedRefusal(f"refused: stage 1 needs a committed {Path(release).name} with windows_released exactly "
                            f"[\"{W_PRE}\"]")
    if r.get("protocol_header_sha256") != FROZEN_V2_SHA256:
        raise SealedRefusal("refused: release names a different header sha256")
    if "opening_condition_hypotheses" in r and tuple(r["opening_condition_hypotheses"]) != OPENING_HYPOTHESES:
        raise SealedRefusal("refused: the opening list is the constant (H1, H3)")
    sc = r.get("selection_results_commit", "<missing>")
    if _git("diff", "--quiet", sc, "HEAD", "--", str(SELECTION_RESULT.relative_to(ROOT)), check=False).returncode != 0:
        raise SealedRefusal("refused: selection results differ from the release's selection_results_commit")
    if sha256_file(SELECTION_RESULT) != r.get("selection_results_sha256"):
        raise SealedRefusal("refused: selection results sha256 differs from the release")
    if remote_sha is not None:                                           # R20.9
        commit_on_remote(sc, remote_sha)
        on_remote(SELECTION_RESULT, remote_sha)
        on_remote(release, remote_sha)
    h, b = selected_setting()
    g = r.get("selected_grid_point", {})
    if (float(g.get("h_near_high_pct", -1)), float(g.get("b_breadth_drop_pp", -1))) != (h, b):
        raise SealedRefusal("refused: release names a configuration other than the committed selection")
    check_engine_commit(r.get("engine_commit", "<missing>"))
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


def gate_keys(hyp: str) -> set:
    return {f"{hyp}|{e}|{r}|{c}" for e in ERAS_GATE for r in GATE_READINGS for c in GATE_COSTS}


def gate_decision(signs: dict) -> tuple[bool, dict]:
    """R13/R14(c)/R18/R20.3: open iff H1 or H3 has EXACTLY its eight keys (two eras x two readings x base/strict),
    all '+'. Any other key set (empty, short, extra) is closed; a NaN is neither sign (O5)."""
    if set(signs) != gate_keys("H1") | gate_keys("H3"):
        return False, {h: False for h in OPENING_HYPOTHESES}
    per = {h: all(signs[k] == "+" for k in gate_keys(h)) for h in OPENING_HYPOTHESES}
    return any(per.values()), per


def _runs(entries: list) -> list:
    """Group ledger entries into runs: [{"start": e, "outcome": e|None, "record": e|None}] in order."""
    runs = []
    for e in entries:
        if e["kind"] == "START":
            runs.append({"start": e, "outcome": None, "record": None})
            continue
        if not runs or e.get("start_index") != runs[-1]["start"]["index"]:
            raise SealedRefusal(f"refused: ledger entry {e['index']} does not belong to the latest START")
        r = runs[-1]
        if e["kind"] in ("INTEGRITY_ABORT", "PHASE_A_CLEAN"):
            if r["outcome"] is not None:
                raise SealedRefusal("refused: two Phase A outcomes for one START")
            r["outcome"] = e
        elif e["kind"] in ("GATE", "FINAL"):
            want = "GATE" if r["start"]["stage"] == "stage1" else "FINAL"
            if e["kind"] != want or r["outcome"] is None or r["outcome"]["kind"] != "PHASE_A_CLEAN" or r["record"]:
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
    if last is not None and last["outcome"] is not None and last["outcome"]["kind"] == "PHASE_A_CLEAN" \
            and last["record"] is None:
        if _identity(last["start"]) != _identity(new):
            raise SealedRefusal("refused: a Phase-A-clean run has no record; the only permitted action is the "
                                "identical rerun (same stage, release, engine commit and inputs) (R20.1)")
        return
    unrecorded = [r["start"]["index"] for r in runs if r["record"] is None]      # START-only and aborts
    prior_commits = {r["start"]["engine_commit"] for r in runs if r["start"]["stage"] == new["stage"]}
    if last is not None and last["outcome"] is None and _identity(last["start"]) == _identity(new):
        return                                                    # START with no outcome: no sign existed
    if new["engine_commit"] in prior_commits:
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


def validate_ledger(entries: list, versions_entries: list, release_docs: dict) -> None:
    """R20.2/R20.3: chain; every committed version a prefix of the current; replay every START under the state
    rules; every GATE's gate_open equals gate_decision(its own signs) after a clean Phase A."""
    verify_chain(entries)
    for i, v in enumerate(versions_entries):
        if entries[:len(v)] != v:
            raise SealedRefusal(f"refused: committed ledger version {i} is not a prefix of the current ledger")
    for e in entries:
        if e["kind"] == "START":
            doc = release_docs.get(e["release_sha256"])
            if doc is None:
                raise SealedRefusal(f"refused: ledger START {e['index']} names a release never committed")
            start_allowed(entries[:e["index"]], e, doc)
        if e["kind"] == "GATE":
            if e["gate_open"] is not gate_decision(e["gate_signs"])[0]:
                raise SealedRefusal(f"refused: ledger GATE {e['index']}: gate_open disagrees with its own signs")
    _runs(entries)


def check_release_history(versions_by_file: dict, entries: list) -> dict:
    """R20.1: every version of every release file on the remote must map to ledger START entries, or be listed as
    unused in a LATER version's `supersedes_unused_releases`. Returns sha256 -> document for all versions."""
    import json
    docs, started = {}, {e["release_sha256"] for e in entries if e["kind"] == "START"}
    for name, vs in versions_by_file.items():
        shas = [sha256_bytes(b) for _, b in vs]
        for (c, b), s in zip(vs, shas):
            docs[s] = json.loads(b)
        for i, s in enumerate(shas[:-1]):
            later = [docs[x].get("supersedes_unused_releases", []) for x in shas[i + 1:]]
            if s not in started and not any(s in L for L in later):
                raise SealedRefusal(f"refused: an earlier {name} version has no ledger START and was not superseded "
                                    "as unused by a later release")
    return docs


class MemoryLedger:
    """In-memory ledger for the fixture dry run and tests (never a release path)."""
    def __init__(self, entries=None, fail_on=()):
        self._e = list(entries or []); self.fail_on = set(fail_on)

    def entries(self) -> list:
        return [dict(x) for x in self._e]

    def append(self, entry: dict) -> dict:
        if entry["kind"] in self.fail_on:
            raise LedgerPushFailed(f"refused: pushing the {entry['kind']} ledger entry failed")
        e = dict(entry, index=len(self._e), prev_chain_sha256=chain_hash(self._e) if self._e else None)
        self._e.append(e)
        return e


class GitLedger:
    """R20.1: the runner writes the record. Each append builds a commit from a temporary index on top of the just-
    fetched remote head (the working tree is not touched), pushes it, and refuses to go on if the push fails. Only
    after a successful push is the local branch fast-forwarded. Starts only when the local HEAD equals the fetched
    remote head."""
    def __init__(self, root: Path = ROOT, path: Path = LEDGER, branch: str = BRANCH):
        self.root, self.branch = Path(root), branch
        self.rel = str(Path(path).resolve().relative_to(self.root.resolve()))
        self.remote_sha = None

    def fetch(self) -> str:
        self.remote_sha = fetch_remote(self.root, self.branch)
        return self.remote_sha

    def require_local_equals_remote(self) -> None:
        head = _git("rev-parse", "HEAD", root=self.root).stdout.decode().strip()
        if head != self.remote_sha:
            raise SealedRefusal("refused: the local branch is not the fetched remote head (unpushed or stale commits)")

    def _entries_at(self, sha: str) -> list:
        import json
        b = _git("show", f"{sha}:{self.rel}", check=False, root=self.root)
        if b.returncode != 0:
            if _git("cat-file", "-e", f"{sha}^{{commit}}", check=False, root=self.root).returncode != 0:
                raise SealedRefusal("refused: remote commit unreadable")
            return []
        return json.loads(b.stdout)["entries"]

    def entries(self) -> list:
        if self.remote_sha is None:
            raise SealedRefusal("refused: ledger read before a fetch")
        return self._entries_at(self.remote_sha)

    def version_entries(self) -> list:
        import json
        return [json.loads(b)["entries"] for _, b in file_versions(self.rel, self.remote_sha, self.root)]

    def append(self, entry: dict) -> dict:
        import os, tempfile
        self.fetch()
        cur = self.entries()
        verify_chain(cur)
        e = dict(entry, index=len(cur), prev_chain_sha256=chain_hash(cur) if cur else None)
        blob = _git("hash-object", "-w", "--stdin", input=ledger_doc(cur + [e]), root=self.root).stdout.decode().strip()
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ, GIT_INDEX_FILE=str(Path(td) / "index"))
            _git("read-tree", self.remote_sha, root=self.root, env=env)
            _git("update-index", "--add", "--cacheinfo", f"100644,{blob},{self.rel}", root=self.root, env=env)
            tree = _git("write-tree", root=self.root, env=env).stdout.decode().strip()
        msg = (f"rotation-core run ledger: {e['kind']} (index {e['index']})\n\nWritten by the runner (R20.1).\n\n"
               "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n").encode()
        c = _git("commit-tree", tree, "-p", self.remote_sha, input=msg, root=self.root).stdout.decode().strip()
        p = _git("push", "-q", REMOTE, f"{c}:refs/heads/{self.branch}", check=False, root=self.root)
        if p.returncode != 0:
            raise LedgerPushFailed(f"refused: pushing the {e['kind']} ledger entry failed; nothing further runs")
        if self.fetch() != c:
            raise LedgerPushFailed("refused: the remote head after the push is not the ledger commit")
        if _git("merge", "--ff-only", "-q", c, check=False, root=self.root).returncode != 0:
            raise SealedRefusal("refused: the ledger entry is pushed but the local branch could not fast-forward")
        return e


# ------------------------------------------------------------------ R20.7 stage-2 opening (inside the runner only)
_STAGE2_OPEN = {"open": False}


def sealed_record() -> dict:
    """basename -> recorded sha256 of the full French files, hashed unopened before sealing."""
    out = {}
    for ln in SEALED_RECORD.read_text().splitlines():
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


# --------------------------------------------------------------------------- loaders
def _lines(path):
    """A file path, or an in-memory text buffer (R20.4: the fixture dry run takes no path)."""
    import io
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
    seal_guard(path); assert_window(end)
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
        p = [x.strip() for x in ln.split(",")]
        if len(p[0]) == 8 and p[0].isdigit() and p[0] <= endk:
            rows.append(p)
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
    return any(v < 0 for v in fund_estimates.values())


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


def bootstrap_draws(series: dict, B: int, block: int, seed: int, chunk: int = 500) -> dict:
    """Stationary-bootstrap draws of each statistic on ONE window, all keys sharing the same resample indices.
    series[key] = ("mix", r, W, L) -> mean(r) - sum_k mean(W_k) mean(L_k) per resample (mix rebuilt per resample);
                  ("paired", d)    -> mean(d) per resample.
    Returns key -> (B,) raw (daily, not annualised) draws. Chunk c uses seed + c."""
    n = len(next(iter(series.values()))[1])
    out = {k: [] for k in series}
    done, c = 0, 0
    while done < B:
        b = min(chunk, B - done)
        ii = rc.stationary_bootstrap_indices(n, b, block, seed + c)
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
