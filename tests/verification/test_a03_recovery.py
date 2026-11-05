"""A03-1 — release recovery acceptance on the identity reference publish seam.

EVERY fixture generation in this suite is SYNTHETIC. Nothing here is a natural
production event: the stand-in producer writes one-row Parquets through the REAL
``_write_parquet`` into ``tmp_path`` only, and every recovery is driven through
the REAL seam ``scripts/build_security_master.py::run_nightly_refresh``. No test
reads the repository's market data, and no test fixes production code — a defect
is pinned as a strict-xfail FINDING that asserts the correct behaviour.

What the seam is acceptance-tested for (programme DATA-OS-COMPLETION, work
package A03): an interrupted publish leaves the old generation valid and a
partial generation invisible; rollback-shaped restores are byte-exact pointer
moves of the preimage; a second recovery is idempotent; refusals leave inputs,
prior reads and sidecars unchanged; and the only writer is the owner seam.

What does NOT exist on main and is therefore recorded, never tested as passed:
no generation id, current pointer or rollback receipt for the identity
reference set (see ``PENDING_LEGS``).

Run: ~/lanes/venv/bin/python -m pytest tests/verification/test_a03_recovery.py -q
"""
from __future__ import annotations

import hashlib
import inspect
import json
import re
import sys
from itertools import count
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts import build_security_master as BUILD  # noqa: E402
from lib.dataos.identity import IdentityError, validate_reference_snapshot  # noqa: E402

# Legs this hermetic lane cannot close, recorded verbatim (asserted by the last
# test and printed into research/data_os_completion/2026-10-13/A03_RECOVERY.md).
PENDING_LEGS = (
    "UNFINISHED: no generation id, current pointer or rollback receipt exists "
    "for data/reference; production rollback is a git revert of a data commit "
    "(operator act)",
    "UNFINISHED: awaiting C04 LANDED — D6 Terminal JSON regeneration from the "
    "rolled-back generation",
    "UNFINISHED: real-inputs leg — hermetic lane, no data/ reads",
    "GAP: producer receipt carries no generation_id / supersedes (D5.1, D5.2)",
)

#: The visible generation: five artifacts + the receipt (the streak sidecar is
#: bookkeeping about refusals, deliberately not part of a generation).
_SNAPSHOT_NAMES = (*BUILD._NIGHTLY_ARTIFACT_NAMES, BUILD.RECEIPT_NAME)

_SYNTHETIC_INPUT = b"SYNTHETIC identity input - A03-1 hermetic fixture\n"


def _tiny_parquet(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"cik": [1], "name": ["SYNTHETIC"]}).to_parquet(path, index=False)


@pytest.fixture()
def nightly_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A hermetic preflight-passing environment around the REAL nightly seam.

    The seven required identity inputs exist (the preflight only checks
    existence) and both identity rails hold one tiny readable Parquet. Returns
    ``tmp_path/"reference"`` — the out_dir every SYNTHETIC generation lands in.
    """
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    for name in ("constituents.parquet", "midcap.parquet", "smallcap.parquet",
                 "membership.json", "delisted.yml", "config.yml", "ticker_aliases.py"):
        (inputs / name).write_bytes(_SYNTHETIC_INPUT)
    monkeypatch.setattr(BUILD, "CONSTITUENTS", inputs / "constituents.parquet")
    monkeypatch.setattr(BUILD, "MIDCAP_CONSTITUENTS", inputs / "midcap.parquet")
    monkeypatch.setattr(BUILD, "SMALLCAP_CONSTITUENTS", inputs / "smallcap.parquet")
    monkeypatch.setattr(BUILD, "MEMBERSHIP", inputs / "membership.json")
    monkeypatch.setattr(BUILD, "DELISTED_LEDGER", inputs / "delisted.yml")
    monkeypatch.setattr(BUILD, "CONFIG_YML", inputs / "config.yml")
    monkeypatch.setattr(BUILD, "TICKER_ALIASES_PY", inputs / "ticker_aliases.py")
    symdir = tmp_path / "rails" / "symdir"
    cikdir = tmp_path / "rails" / "cik"
    _tiny_parquet(symdir / "snap.parquet")
    _tiny_parquet(cikdir / "map.parquet")
    monkeypatch.setattr(BUILD, "SYMBOL_DIR_SNAPSHOTS", symdir)
    monkeypatch.setattr(BUILD, "CIK_MAP_DIR", cikdir)
    return tmp_path / "reference"


class StagedBuild:
    """SYNTHETIC stand-in for ``BUILD.build``, installed over the real one.

    Writes the five nightly artifacts in the producer's pinned order through the
    REAL ``BUILD._write_parquet`` (one row carrying the generation label), then
    the receipt LAST. ``fail_after=k`` raises ``exc`` before artifact ``k``
    (``k == 5`` = all five Parquets written, receipt not yet). ``generated_at``
    differs on every call, so a receipt-preimage restore is observable.
    """

    _generated_at = count()

    def __init__(self, label: str, fail_after: int | None = None,
                 exc: BaseException | None = None, notes: tuple[str, ...] = ()):
        self.label = label
        self.fail_after = fail_after
        self.exc = exc
        self.notes = tuple(notes)
        self.writes: list[Path] = []
        self.calls = 0

    def __call__(self, out_dir: Path, dry_run: bool = False, **kwargs):
        assert dry_run is False, "the nightly seam must call the writing build"
        out_dir.mkdir(parents=True, exist_ok=True)
        self.calls += 1
        for i, name in enumerate(BUILD._NIGHTLY_ARTIFACT_NAMES):
            if self.fail_after == i:
                raise self.exc
            BUILD._write_parquet(
                [{"generation": self.label, "artifact": name}],
                ("generation", "artifact"),
                out_dir / name,
                {},
            )
            self.writes.append(out_dir / name)
        if self.fail_after == 5:
            raise self.exc
        receipt = {
            "generation": self.label,
            "generated_at": f"SYNTHETIC-{next(StagedBuild._generated_at)}",
            "coverage": {"resolved": 1, "total": 1, "unresolved": 0},
            "notes": list(self.notes),
            "synthetic": True,
        }
        (out_dir / BUILD.RECEIPT_NAME).write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        )
        self.writes.append(out_dir / BUILD.RECEIPT_NAME)
        return receipt


class _HardKill(BaseException):
    """SYNTHETIC process-level crash (OOM kill, signal, or a ``SystemExit``
    raised by a dependency) — deliberately NOT an ``Exception``, so the seam's
    ``except Exception`` cannot catch it. Models everything that sits outside
    the seam's handled-outcome set."""

    def __init__(self, message: str = "SYNTHETIC hard kill"):
        super().__init__(message)


def _snapshot(out_dir: Path) -> dict[str, bytes]:
    """Byte map of the five artifacts + receipt + streak sidecar (present ones)."""
    names = (*_SNAPSHOT_NAMES, BUILD._NIGHTLY_PRUNE_STREAK_NAME)
    return {n: (out_dir / n).read_bytes() for n in names if (out_dir / n).exists()}


def _visible(out_dir: Path) -> dict[str, bytes]:
    """Byte map of just the visible generation (five artifacts + receipt)."""
    return {n: (out_dir / n).read_bytes() for n in _SNAPSHOT_NAMES if (out_dir / n).exists()}


def _tree_digest(root: Path, exclude: Path) -> str:
    """sha256 over every file under ``root`` except those under ``exclude``."""
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*")
                       if p.is_file() and exclude not in p.parents):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _generation_labels(out_dir: Path) -> list[str]:
    """The generation label carried by each of the five artifacts, in order."""
    return [str(pd.read_parquet(out_dir / n)["generation"].iloc[0])
            for n in BUILD._NIGHTLY_ARTIFACT_NAMES]


def _install(monkeypatch: pytest.MonkeyPatch, staged: StagedBuild) -> StagedBuild:
    monkeypatch.setattr(BUILD, "build", staged)
    return staged


def _publish(nightly_env: Path, monkeypatch: pytest.MonkeyPatch, label: str,
             capsys, **kwargs) -> dict[str, bytes]:
    """Publish one complete SYNTHETIC generation through the real seam."""
    _install(monkeypatch, StagedBuild(label, **kwargs))
    assert BUILD.run_nightly_refresh(nightly_env) == 0
    out = capsys.readouterr().out
    assert any("regenerated" in line for line in out.splitlines()), out
    return _visible(nightly_env)


# Every refusal kind the seam has, as StagedBuild kwargs.
_REFUSAL_KINDS = (
    ("exception", dict(fail_after=3, exc=RuntimeError("SYNTHETIC interruption"))),
    ("notes", dict(notes=("SYNTHETIC unmodelled rename",))),
    ("prune-conflict", dict(fail_after=2,
                            exc=BUILD.VendorAliasPruneConflict("SYNTHETIC overlap"))),
)


# ── A03.01 precondition: the staged order mirrors the real producer ───────────
def test_a03_01_build_writes_receipt_after_every_parquet() -> None:
    """Pin the real build body inside the R25 writer wrapper: within its
    ``if not dry_run:`` block there are exactly five ``_write_parquet(`` calls
    and receipt ``write_text`` comes after every one — the order StagedBuild mirrors.
    """
    src = inspect.getsource(BUILD._build_reference_unlocked)
    assert "if not dry_run:" in src
    block = src.split("if not dry_run:", 1)[1]
    writes = [m.start() for m in re.finditer(r"_write_parquet\(", block)]
    assert len(writes) == 5, writes
    receipt_at = block.index("(out_dir / RECEIPT_NAME).write_text")
    assert receipt_at > max(writes)


# ── A03.01 — interrupted publish over a prior generation ──────────────────────
@pytest.mark.parametrize("k", range(6))
def test_a03_01_exception_mid_publish_restores_prior_generation(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys, k: int,
) -> None:
    """A handled interruption at ANY write point (including after all five
    Parquets, before the receipt) restores the prior generation byte-exact."""
    before = _publish(nightly_env, monkeypatch, "A", capsys)
    listing_before = sorted(p.name for p in nightly_env.iterdir())
    _install(monkeypatch, StagedBuild(
        "B", fail_after=k, exc=RuntimeError("SYNTHETIC interruption")))
    assert BUILD.run_nightly_refresh(nightly_env) == 0
    assert _visible(nightly_env) == before
    assert sorted(p.name for p in nightly_env.iterdir()) == listing_before
    out = capsys.readouterr().out
    assert any(line.startswith("::warning title=security-master-nightly::")
               for line in out.splitlines()), out


# ── A03.01 — interrupted FIRST publish ────────────────────────────────────────
@pytest.mark.parametrize("k", range(6))
def test_a03_01_exception_mid_first_publish_leaves_nothing_visible(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys, k: int,
) -> None:
    """With no prior generation, a handled interruption leaves the out_dir with
    no file at all: newly created files are unlinked, nothing partial is left
    visible."""
    _install(monkeypatch, StagedBuild(
        "B", fail_after=k, exc=RuntimeError("SYNTHETIC interruption")))
    assert BUILD.run_nightly_refresh(nightly_env) == 0
    assert nightly_env.is_dir()
    assert list(nightly_env.iterdir()) == []
    out = capsys.readouterr().out
    assert any(line.startswith("::warning title=security-master-nightly::")
               for line in out.splitlines()), out


# ── A03.01 — notes refusal restores the receipt too ───────────────────────────
def test_a03_01_notes_refusal_restores_artifacts_and_receipt(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    """A build that COMPLETES (all six files written) but reports unmodelled
    notes is refused: all six files, including the fresh receipt, are restored
    to the prior generation's bytes."""
    before = _publish(nightly_env, monkeypatch, "A", capsys)
    _install(monkeypatch, StagedBuild("B", notes=("SYNTHETIC unmodelled rename",)))
    assert BUILD.run_nightly_refresh(nightly_env) == 0
    assert _visible(nightly_env) == before
    out = capsys.readouterr().out
    assert any(line.startswith("::warning title=security-master-nightly::")
               for line in out.splitlines()), out


# ── A03.01 — lost response / second recovery is idempotent ────────────────────
def test_a03_01_rerun_of_a_complete_generation_is_a_byte_stable_noop(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    """Re-running a complete generation (a lost response reconciled by re-run)
    is a byte-stable no-op twice over: the fresh ``generated_at`` the stand-in
    wrote is NOT kept — the receipt bytes return to the preimage."""
    receipt_a = _publish(nightly_env, monkeypatch, "A", capsys)[BUILD.RECEIPT_NAME]
    for _ in range(2):
        _install(monkeypatch, StagedBuild("A"))  # fresh generated_at each call
        assert BUILD.run_nightly_refresh(nightly_env) == 0
        out = capsys.readouterr().out
        assert any("byte-stable no-op" in line for line in out.splitlines()), out
        assert (nightly_env / BUILD.RECEIPT_NAME).read_bytes() == receipt_a


# ── A03.01 — hard-kill characterization (PASS test: describes main) ───────────
@pytest.mark.parametrize("k", range(1, 6))
def test_a03_01_hard_kill_mid_publish_leaves_a_torn_visible_set(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys, k: int,
) -> None:
    """OBSERVED ON MAIN (characterization, not a verdict of correctness): a
    process-level crash the seam cannot catch leaves the first ``k`` artifacts
    carrying the NEW generation, the rest the old one, under the OLD receipt —
    a torn set a reader cannot distinguish from a complete one."""
    before = _publish(nightly_env, monkeypatch, "A", capsys)
    _install(monkeypatch, StagedBuild("B", fail_after=k, exc=_HardKill()))
    with pytest.raises(_HardKill):
        BUILD.run_nightly_refresh(nightly_env)
    labels = _generation_labels(nightly_env)
    assert labels == ["B"] * k + ["A"] * (5 - k), labels
    assert (nightly_env / BUILD.RECEIPT_NAME).read_bytes() == before[BUILD.RECEIPT_NAME]
    capsys.readouterr()  # the seam prints nothing: no handler runs


@pytest.mark.xfail(strict=True, reason=(
    "FINDING A03-F1: a process-level crash mid-publish leaves a torn "
    "data/reference set under the previous receipt, and the producer emits no "
    "publication manifest a reader could validate it against"))
def test_a03_f1_torn_visible_set_is_detectable_or_never_visible(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    """CORRECT behaviour for a k=2 hard kill: either the visible set equals the
    prior generation's preimage (crash never became visible), or the producer
    emits the ``identity_publication`` manifest ``validate_reference_snapshot``
    checks (a reader can detect the tear). On main both are false."""
    preimage = _publish(nightly_env, monkeypatch, "A", capsys)
    _install(monkeypatch, StagedBuild("B", fail_after=2, exc=_HardKill()))
    with pytest.raises(_HardKill):
        BUILD.run_nightly_refresh(nightly_env)
    visible_is_preimage = _snapshot(nightly_env) == preimage
    producer_emits_manifest = "identity_publication" in inspect.getsource(BUILD)
    assert visible_is_preimage or producer_emits_manifest, (
        "an unhandled crash must leave either the prior generation visible or a "
        "manifest the reader can validate the visible set against"
    )


@pytest.mark.xfail(strict=True, reason=(
    "FINDING A03-F3: after a torn publish, the next run's refusal restores the "
    "torn snapshot and reports it as last-good"))
def test_a03_f3_refusal_after_a_tear_does_not_certify_the_torn_set_as_last_good(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    """CORRECT behaviour: after a torn publish, the next refusal may only
    restore a COMPLETE generation — the visible five artifacts must all carry
    ONE generation label. On main the restore rewrites the torn bytes and the
    warning calls them last-good."""
    _publish(nightly_env, monkeypatch, "A", capsys)
    _install(monkeypatch, StagedBuild("B", fail_after=2, exc=_HardKill()))
    with pytest.raises(_HardKill):
        BUILD.run_nightly_refresh(nightly_env)
    capsys.readouterr()
    _install(monkeypatch, StagedBuild(
        "C", fail_after=3, exc=RuntimeError("SYNTHETIC second interruption")))
    assert BUILD.run_nightly_refresh(nightly_env) == 0
    out = capsys.readouterr().out
    assert any("keeping last-good artifacts" in line for line in out.splitlines()), out
    labels = _generation_labels(nightly_env)
    assert len(set(labels)) == 1, (
        f"the set reported last-good must be one complete generation, got {labels}"
    )


def test_a03_f3_twin_observed_refusal_after_a_tear_certifies_the_tear(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    """PASS twin of FINDING A03-F3: the OBSERVED main behaviour — after the
    k=2 tear (B,B,A,A,A) the next refusal restores exactly those torn bytes and
    reports them as last-good."""
    before = _publish(nightly_env, monkeypatch, "A", capsys)
    _install(monkeypatch, StagedBuild("B", fail_after=2, exc=_HardKill()))
    with pytest.raises(_HardKill):
        BUILD.run_nightly_refresh(nightly_env)
    capsys.readouterr()
    _install(monkeypatch, StagedBuild(
        "C", fail_after=3, exc=RuntimeError("SYNTHETIC second interruption")))
    assert BUILD.run_nightly_refresh(nightly_env) == 0
    out = capsys.readouterr().out
    assert any("keeping last-good artifacts" in line for line in out.splitlines()), out
    assert _generation_labels(nightly_env) == ["B", "B", "A", "A", "A"]
    assert (nightly_env / BUILD.RECEIPT_NAME).read_bytes() == before[BUILD.RECEIPT_NAME]


# ── A03.02 — failed-generation evidence ───────────────────────────────────────
def test_a03_02_prune_conflict_refusal_leaves_a_durable_streak_record(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    """Positive control: the DEDICATED refusal kind keeps durable data-plane
    evidence — a streak sidecar with both counters, escalating to ``::error``
    on the third consecutive same-text refusal — while restoring the artifacts."""
    before = _publish(nightly_env, monkeypatch, "A", capsys)
    capsys.readouterr()
    conflict = BUILD.VendorAliasPruneConflict("SYNTHETIC overlap")
    escalated = False
    for refusal_n in (1, 2, 3):
        _install(monkeypatch, StagedBuild("X", fail_after=2, exc=conflict))
        assert BUILD.run_nightly_refresh(nightly_env) == 0
        out = capsys.readouterr().out
        assert any(line.startswith("::warning title=security-master-nightly-prune-conflict::")
                   for line in out.splitlines()), out
        core = {n: v for n, v in _snapshot(nightly_env).items()
                if n != BUILD._NIGHTLY_PRUNE_STREAK_NAME}
        assert core == before
        sidecar = json.loads(
            (nightly_env / BUILD._NIGHTLY_PRUNE_STREAK_NAME).read_text())
        if refusal_n == 1:
            assert sidecar["consecutive"] == 1
            assert sidecar["refusals_since_last_success"] == 1
        escalated = escalated or any(
            line.startswith("::error title=security-master-nightly-prune-conflict-stuck")
            for line in out.splitlines())
    assert escalated, "the third consecutive refusal must escalate to ::error"


@pytest.mark.xfail(strict=True, reason=(
    "FINDING A03-F2: a generic or notes refusal erases every trace of the "
    "failed generation from the data plane; only the CI log keeps it"))
def test_a03_f2_generic_failure_leaves_a_durable_failure_record(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    """CORRECT behaviour: after a generic refusal, the out_dir holds SOME file
    other than the six artifacts whose text names the failed attempt. On main
    the restore erases the failed generation entirely — only the CI log keeps
    the evidence."""
    _publish(nightly_env, monkeypatch, "A", capsys)
    capsys.readouterr()
    _install(monkeypatch, StagedBuild(
        "B", fail_after=3, exc=RuntimeError("SYNTHETIC second interruption")))
    assert BUILD.run_nightly_refresh(nightly_env) == 0
    assert any("keeping last-good artifacts" in line
               for line in capsys.readouterr().out.splitlines())
    extra = [p for p in sorted(nightly_env.iterdir())
             if p.name not in _SNAPSHOT_NAMES]
    assert extra and any("SYNTHETIC" in p.read_text(errors="replace") for p in extra), (
        "a refusal must leave a durable data-plane record naming the failed attempt"
    )


@pytest.mark.parametrize("kind,kwargs", _REFUSAL_KINDS, ids=[k for k, _ in _REFUSAL_KINDS])
def test_a03_02_restore_never_relabels(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys, kind: str, kwargs: dict,
) -> None:
    """After every refusal kind the receipt bytes equal the preimage receipt:
    no field is added, no label changed, the SYNTHETIC flag and generation id
    of the last-good generation are untouched (a restore is a byte-exact
    pointer move, never a relabel)."""
    receipt_a = _publish(nightly_env, monkeypatch, "A", capsys)[BUILD.RECEIPT_NAME]
    capsys.readouterr()
    _install(monkeypatch, StagedBuild("B", **kwargs))
    assert BUILD.run_nightly_refresh(nightly_env) == 0
    receipt_now = (nightly_env / BUILD.RECEIPT_NAME).read_bytes()
    assert receipt_now == receipt_a
    parsed = json.loads(receipt_now)
    assert parsed["generation"] == "A"
    assert parsed["synthetic"] is True


# ── A03.03 — nothing else moves ───────────────────────────────────────────────
def test_a03_03_inputs_and_rails_unchanged_across_every_refusal(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    """Every refusal kind (exception at every write point k=0..5, notes, prune
    conflict, hard kill) leaves the inputs and rails byte-identical: the seam
    reads them, it never writes them."""
    _publish(nightly_env, monkeypatch, "A", capsys)
    capsys.readouterr()
    before = _tree_digest(nightly_env.parent, exclude=nightly_env)
    kinds = [(f"exception-k{k}", dict(fail_after=k,
                                      exc=RuntimeError("SYNTHETIC interruption")))
             for k in range(6)]
    kinds += list(_REFUSAL_KINDS)
    kinds.append(("hard-kill", dict(fail_after=2, exc=_HardKill())))
    for kind, kwargs in kinds:
        _install(monkeypatch, StagedBuild("B", **kwargs))
        if kind == "hard-kill":
            with pytest.raises(_HardKill):
                BUILD.run_nightly_refresh(nightly_env)
        else:
            assert BUILD.run_nightly_refresh(nightly_env) == 0
        capsys.readouterr()
        assert _tree_digest(nightly_env.parent, exclude=nightly_env) == before, kind


def test_a03_03_prior_read_equals_read_after_restore(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    """A frame a consumer read BEFORE the failed run is frame-equal to what it
    reads after the restore — the prior read is never invalidated."""
    _publish(nightly_env, monkeypatch, "A", capsys)
    master_before = pd.read_parquet(nightly_env / BUILD.MASTER_NAME)
    aliases_before = pd.read_parquet(nightly_env / BUILD.ALIASES_NAME)
    capsys.readouterr()
    _install(monkeypatch, StagedBuild(
        "B", fail_after=3, exc=RuntimeError("SYNTHETIC interruption")))
    assert BUILD.run_nightly_refresh(nightly_env) == 0
    capsys.readouterr()
    pd.testing.assert_frame_equal(
        pd.read_parquet(nightly_env / BUILD.MASTER_NAME), master_before)
    pd.testing.assert_frame_equal(
        pd.read_parquet(nightly_env / BUILD.ALIASES_NAME), aliases_before)


def test_a03_03_generic_failure_does_not_touch_the_streak_sidecar(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    """A pre-existing prune-conflict streak sidecar (created through the seam)
    is byte-unchanged by a later generic refusal: one refusal kind's evidence
    is not another's to rewrite."""
    _publish(nightly_env, monkeypatch, "A", capsys)
    _install(monkeypatch, StagedBuild(
        "X", fail_after=2, exc=BUILD.VendorAliasPruneConflict("SYNTHETIC overlap")))
    assert BUILD.run_nightly_refresh(nightly_env) == 0
    sidecar = nightly_env / BUILD._NIGHTLY_PRUNE_STREAK_NAME
    sidecar_bytes = sidecar.read_bytes()
    capsys.readouterr()
    _install(monkeypatch, StagedBuild(
        "B", fail_after=3, exc=RuntimeError("SYNTHETIC interruption")))
    assert BUILD.run_nightly_refresh(nightly_env) == 0
    assert any("keeping last-good artifacts" in line
               for line in capsys.readouterr().out.splitlines())
    assert sidecar.read_bytes() == sidecar_bytes


# ── A03.04 — one writer ───────────────────────────────────────────────────────
def test_a03_04_only_the_owner_seam_writes_the_receipt() -> None:
    """Pin the three legacy writers plus the explicit initial-only owner seam.

    The initial promoter atomically replaces only the receipt; it is not a
    nightly refresh or a history-preserving successor publisher. Count its
    rename alongside the existing direct writes instead of hiding a new writer.
    """
    writers = set()
    for name, func in inspect.getmembers(BUILD, inspect.isfunction):
        if func.__module__ != BUILD.__name__:
            continue
        source = inspect.getsource(func)
        if "RECEIPT_NAME" in source and any(
                operation in source for operation in ("write_text", "write_bytes", "os.replace(")):
            writers.add(name)
    assert writers == {
        "_build_reference_unlocked", "_restore_artifacts", "_run_nightly_reference_unlocked",
        "promote_initial_reference_generation",
    }


# ── Census pins (executable) ──────────────────────────────────────────────────
def test_a03_census_the_validator_rejects_the_seam_receipt_shape(
    nightly_env: Path, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    """Executable census pin: the receipt the seam actually writes carries no
    ``publication`` block, so ``validate_reference_snapshot`` — the only
    reader-side validator — refuses it with 'snapshot owner context missing'.
    Matches the step-6 census: no producer of ``identity_publication`` on main
    and no non-test caller of the validator."""
    _publish(nightly_env, monkeypatch, "A", capsys)
    receipt_bytes = (nightly_env / BUILD.RECEIPT_NAME).read_bytes()
    artifact_bytes = {n: (nightly_env / n).read_bytes()
                      for n in BUILD._NIGHTLY_ARTIFACT_NAMES}
    with pytest.raises(IdentityError, match="snapshot owner context missing"):
        validate_reference_snapshot(receipt_bytes, artifact_bytes, receipt_bytes,
                                    alias_records=(), master_records=())


def test_a03_pending_legs_are_declared() -> None:
    """``PENDING_LEGS`` is non-empty, every entry is an UNFINISHED leg or a
    GAP, and the four programme-declared legs are carried verbatim."""
    assert isinstance(PENDING_LEGS, tuple) and PENDING_LEGS
    for entry in PENDING_LEGS:
        assert entry.startswith("UNFINISHED:") or entry.startswith("GAP:"), entry
    assert (
        "UNFINISHED: no generation id, current pointer or rollback receipt exists "
        "for data/reference; production rollback is a git revert of a data commit "
        "(operator act)"
    ) in PENDING_LEGS
    assert (
        "UNFINISHED: awaiting C04 LANDED — D6 Terminal JSON regeneration from the "
        "rolled-back generation"
    ) in PENDING_LEGS
    assert "UNFINISHED: real-inputs leg — hermetic lane, no data/ reads" in PENDING_LEGS
    assert "GAP: producer receipt carries no generation_id / supersedes (D5.1, D5.2)" \
        in PENDING_LEGS
