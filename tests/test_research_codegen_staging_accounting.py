"""Invented, explicitly initialized fixtures; actual incumbent core API required."""
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import os
import stat
import subprocess
import sys
import threading
import time

import pytest
from engine import trial_ledger
from engine.research_codegen import accounting_contract, contracts
from engine.research_codegen import staging_accounting as sa
from engine.research_codegen.bridge import BoundBytes, SyntheticTestCommission

ROOT = "01a1333c-a475-7052-95a8-72a88eb8c17b"
FAMILY = "rf.synthetic.p01"
PROTOCOL = hashlib.sha256(b"invented frozen protocol").hexdigest()


def bound(value):
    raw = value if type(value) is bytes else json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return BoundBytes(raw, hashlib.sha256(raw).hexdigest(), len(raw))


def config(label, p):
    return dict(source_sha256=hashlib.sha256(label.encode()).hexdigest(), parameters={"p": p},
        information_set_sha256="2"*64, horizon_id="h21", objective_id="adverse_pair")


def descriptor(name, doc):
    return dict(variant_id=name, source_sha256=doc["source_sha256"],
        config_sha256=contracts.canonical_json_sha256(doc), incumbent_config_hash=trial_ledger._hash(FAMILY, doc))


def expected(docs, anchor, inherited=()):
    return bound(dict(schema="research_codegen.expected_generation.v1", original_root_id=ROOT,
        family=FAMILY, protocol_sha256=PROTOCOL, history_anchor_sha256=anchor.sha256,
        variants=[descriptor(n, d) for n, d in docs], inherited_variants=list(inherited),
        trial_ceiling=4, vault_required=False, vault_request=None))


def initialize(path):
    """Fixture OWNER exclusively creates its new history before supplying anchor."""
    path.mkdir()
    fd = os.open(path / sa.LEDGER_BASENAME, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try: os.fsync(fd)
    finally: os.close(fd)
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


@pytest.fixture
def case(tmp_path):
    path = tmp_path.resolve() / "explicit-new-synthetic-family"
    initialize(path)
    docs = (("good", config("invented good bytes", 1)), ("controlled-refusal", config("invented wrong bytes", 2)))
    anchor = bound(b"")
    kw = dict(commission=SyntheticTestCommission(ROOT, str(path)), run_id="first-engineering-run",
        expected_generation=expected(docs, anchor), history_anchor=anchor,
        configurations=tuple(sa.ScientificConfigBinding(n, d["source_sha256"], bound(d)) for n, d in docs))
    return path, docs, kw


def stage(case, **changes):
    return sa.stage_synthetic_generation(**{**case[2], **changes})


def rows(path):
    return [json.loads(line) for line in (path / sa.LEDGER_BASENAME).read_bytes().splitlines()]


def test_actual_full_generation_before_driver_and_closed_readback(case):
    path, docs, kw = case
    r = stage(case)
    assert r.newly_recorded_count == 2
    records = rows(path)
    assert {x["config_hash"] for x in records if "config" in x} == {trial_ledger._hash(FAMILY, d) for _, d in docs}
    # The driver sentinel is reached only after actual complete generation readback.
    driver_reached = len([x for x in records if "config" in x]) == 2
    assert driver_reached
    trial = json.loads(r.trial_readback.raw)
    assessment = accounting_contract.assess_accounting_references(json.loads(kw["expected_generation"].raw), trial_readback=trial)
    assert assessment["status"] == "STRUCTURALLY_COMPLETE_DISABLED"
    assert assessment["owner_origin_and_durability"] == "UNQUALIFIED"
    assert not any(assessment[k] for k in ("generation_enabled", "execution_enabled", "evaluation_enabled", "authority_granted"))
    assert trial["snapshot_sha256"] == hashlib.sha256(r.raw_snapshot.raw).hexdigest()
    writer = json.loads(r.writer_observation.raw)
    assert (writer["staging_dev"], writer["staging_ino"]) == (path.stat().st_dev, path.stat().st_ino)
    assert writer["staging_ino"] != (path / sa.LEDGER_BASENAME).stat().st_ino


def test_replay_and_rename_same_file_explicitly_sync_without_new_charge(case, monkeypatch):
    first = stage(case)
    original, calls = os.fsync, []
    def observe(fd):
        calls.append(stat.S_ISREG(os.fstat(fd).st_mode))
        return original(fd)
    monkeypatch.setattr(os, "fsync", observe)
    replay = stage(case, run_id="renamed-receipt-only")
    assert replay.newly_recorded_count == 0 and replay.raw_snapshot.raw == first.raw_snapshot.raw
    assert any(calls), "a read-only replay must not invent successful file fsync"
    assert json.loads(replay.durable_readback_observation.raw)["durability_state"] == "DURABLE_RECONCILED"
    assert not (case[0] / "renamed-receipt-only").exists()


def test_later_generation_includes_prior_full_strong_history(case):
    first = stage(case)
    prior = [descriptor(n, d) for n, d in case[1]]
    doc = config("invented changed source", 3)
    configs = (sa.ScientificConfigBinding("third", doc["source_sha256"], bound(doc)),)
    r = stage(case, history_anchor=first.raw_snapshot,
        expected_generation=expected((("third", doc),), first.raw_snapshot, prior), configurations=configs)
    assert r.newly_recorded_count == 1
    assert json.loads(r.trial_readback.raw)["literal_n"] == 3


@pytest.mark.parametrize("rename", [False, True])
def test_lost_history_never_recreated(case, rename):
    stage(case)
    path = case[0] / sa.LEDGER_BASENAME
    path.unlink()
    with pytest.raises(sa.StagingAccountingRefused, match="ORIGINAL_HISTORY_MISSING"):
        stage(case, run_id="renamed" if rename else case[2]["run_id"])
    assert not path.exists()


def test_raw_anchor_is_not_identity_digest(case):
    doc = json.loads(case[2]["expected_generation"].raw)
    doc["history_anchor_sha256"] = contracts.canonical_json_sha256(dict(family=FAMILY, protocol_sha256=PROTOCOL,
        trial_ceiling=4, inherited_config_hashes=[]))
    with pytest.raises(sa.StagingAccountingRefused, match="ORIGINAL_ANCHOR_INVALID"):
        stage(case, expected_generation=bound(doc))
    assert (case[0] / sa.LEDGER_BASENAME).read_bytes() == b""


def test_changed_prefix_refuses_before_new_generation(case):
    first = stage(case)
    fake = bound(first.raw_snapshot.raw.replace(b"staging_synthetic_generation", b"rewritten_original_history"))
    doc = json.loads(case[2]["expected_generation"].raw)
    doc["history_anchor_sha256"] = fake.sha256
    before = (case[0] / sa.LEDGER_BASENAME).read_bytes()
    with pytest.raises(sa.StagingAccountingRefused, match="ORIGINAL_ANCHOR_MISMATCH"):
        stage(case, expected_generation=bound(doc), history_anchor=fake)
    assert (case[0] / sa.LEDGER_BASENAME).read_bytes() == before


@pytest.mark.parametrize("damage", ["declared-bool-time", "declared-bad-time", "non-utc-time", "missing-newline", "duplicate-key", "nonfinite", "extra", "wrong-family"])
def test_full_raw_history_damage_refuses(case, damage):
    stage(case)
    path = case[0] / sa.LEDGER_BASENAME
    raw = path.read_bytes()
    values = [json.loads(line) for line in raw.splitlines()]
    if damage == "declared-bool-time": values[-1]["ts"] = True
    elif damage == "declared-bad-time": values[-1]["ts"] = "not-a-date"
    elif damage == "non-utc-time": values[-1]["ts"] = "2026-01-01T01:00:00+01:00"
    elif damage == "extra": values[0]["extra"] = 1
    elif damage == "wrong-family": values[0]["family"] = "rf.synthetic.renamed"
    if damage == "missing-newline": raw = raw[:-1]
    elif damage == "duplicate-key": raw = raw.replace(b'"family":', b'"family":"forged","family":', 1)
    elif damage == "nonfinite": raw = raw.replace(b'"p": 1', b'"p": NaN') if b'"p": 1' in raw else raw.replace(b'"p":1', b'"p":NaN')
    else: raw = b"".join(json.dumps(v).encode() + b"\n" for v in values)
    path.write_bytes(raw)
    with pytest.raises(sa.StagingAccountingRefused): stage(case)
    assert path.read_bytes() == raw


def test_short_hash_collision_does_not_substitute_strong_history(case, monkeypatch):
    original = trial_ledger._hash
    source = case[1][0][1]["source_sha256"]
    def collide(family, doc):
        return "c" * 16 if type(doc) is dict and doc.get("source_sha256") == source else original(family, doc)
    monkeypatch.setattr(trial_ledger, "_hash", collide)
    monkeypatch.setattr(sa, "_incumbent_hash", collide)
    kw = dict(case[2], expected_generation=expected(case[1], case[2]["history_anchor"]))
    sa.stage_synthetic_generation(**kw)
    path = case[0] / sa.LEDGER_BASENAME
    values = rows(case[0]); values[0]["config"]["parameters"] = {"p": 999}
    raw = b"".join(json.dumps(v).encode() + b"\n" for v in values); path.write_bytes(raw)
    with pytest.raises(sa.StagingAccountingRefused): sa.stage_synthetic_generation(**kw)
    assert path.read_bytes() == raw


def test_post_declaration_fsync_failure_requires_actual_same_file_recovery(case, monkeypatch):
    original = os.fsync
    declaration_hash = trial_ledger._hash(FAMILY, {"__declared_budget__": 4, "reason": sa._DECLARED_REASON})
    failed = []
    def fail_declaration(fd):
        if stat.S_ISREG(os.fstat(fd).st_mode) and (case[0] / sa.LEDGER_BASENAME).exists():
            if declaration_hash.encode() in (case[0] / sa.LEDGER_BASENAME).read_bytes() and not failed:
                failed.append(True); raise OSError("controlled fsync failure after declaration bytes")
        return original(fd)
    with monkeypatch.context() as m:
        m.setattr(os, "fsync", fail_declaration)
        with pytest.raises(sa.StagingAccountingRefused): stage(case)
    before = (case[0] / sa.LEDGER_BASENAME).read_bytes(); calls = []
    def observed(fd):
        calls.append(stat.S_ISREG(os.fstat(fd).st_mode)); return original(fd)
    monkeypatch.setattr(os, "fsync", observed)
    r = stage(case)
    assert failed and r.newly_recorded_count == 0 and r.raw_snapshot.raw == before and any(calls)
    assert json.loads(r.durable_readback_observation.raw)["durability_state"] == "DURABLE_RECONCILED"


@pytest.mark.parametrize("damage", ["omitted-control", "bool-ceiling", "swapped-source", "bad-anchor-binding", "foreign-configuration", "foreign-commission"])
def test_exact_inputs_refuse_before_ledger_mutation(case, damage):
    kw = dict(case[2])
    if damage == "omitted-control": kw["configurations"] = kw["configurations"][:1]
    elif damage in ("bool-ceiling", "swapped-source"):
        doc = json.loads(kw["expected_generation"].raw)
        if damage == "bool-ceiling": doc["trial_ceiling"] = True
        else: doc["variants"][0]["source_sha256"] = "9" * 64
        kw["expected_generation"] = bound(doc)
    elif damage == "bad-anchor-binding": kw["history_anchor"] = replace(kw["history_anchor"], sha256="9"*64)
    else:
        class Foreign:
            def __getattribute__(self, name): pytest.fail("foreign hook")
        if damage == "foreign-configuration": kw["configurations"] = (Foreign(),)
        else: kw["commission"] = Foreign()
    with pytest.raises(sa.StagingAccountingRefused): sa.stage_synthetic_generation(**kw)
    assert (case[0] / sa.LEDGER_BASENAME).read_bytes() == b""


@pytest.mark.parametrize("alias", ["symlink", "hardlink", "fifo"])
def test_unsafe_ledger_alias_refuses(case, alias):
    path = case[0] / sa.LEDGER_BASENAME; path.unlink()
    other = case[0] / "invented-other"; other.write_bytes(b"")
    if alias == "symlink": path.symlink_to(other)
    elif alias == "hardlink": os.link(other, path)
    else: os.mkfifo(path)
    with pytest.raises(sa.StagingAccountingRefused): stage(case)


def test_missing_core_owner_seam_refuses_before_append(case, monkeypatch):
    monkeypatch.delattr(trial_ledger.TrialLedger, "owner_transaction", raising=False)
    with pytest.raises(sa.StagingAccountingRefused, match="CORE_OWNER_TRANSACTION_UNAVAILABLE"): stage(case)
    assert (case[0] / sa.LEDGER_BASENAME).read_bytes() == b""


def test_two_real_processes_share_incumbent_owner_lock(case):
    path, _, kw = case
    job = dict(root=ROOT, path=str(path), expected=kw["expected_generation"].raw.hex(), anchor=kw["history_anchor"].raw.hex(),
        configs=[dict(name=x.variant_id, source=x.source_sha256, raw=x.config.raw.hex()) for x in kw["configurations"]])
    file = path / "static-engineering-job.json"; file.write_text(json.dumps(job))
    code = '''import json,sys,hashlib
from pathlib import Path
from engine.research_codegen import staging_accounting as s
from engine.research_codegen.bridge import BoundBytes,SyntheticTestCommission
j=json.loads(Path(sys.argv[1]).read_text())
def b(h):
 r=bytes.fromhex(h);return BoundBytes(r,hashlib.sha256(r).hexdigest(),len(r))
r=s.stage_synthetic_generation(commission=SyntheticTestCommission(j['root'],j['path']),run_id='same-family-concurrent',expected_generation=b(j['expected']),history_anchor=b(j['anchor']),configurations=tuple(s.ScientificConfigBinding(x['name'],x['source'],b(x['raw'])) for x in j['configs']))
print(r.newly_recorded_count)
'''
    directory = Path(sa.__file__).resolve().parents[2]
    a = subprocess.Popen([sys.executable, "-B", "-c", code, str(file)], cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    b = subprocess.Popen([sys.executable, "-B", "-c", code, str(file)], cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    aa, ae = a.communicate(timeout=30); bb, be = b.communicate(timeout=30)
    assert a.returncode == b.returncode == 0, (ae, be)
    assert sorted([int(aa), int(bb)]) == [0, 2]
    assert len([r for r in rows(path) if "config" in r]) == 2


def test_staging_holds_one_continuous_core_transaction(case, monkeypatch):
    entered, release, attempted, done = (threading.Event() for _ in range(4))
    original = sa._strict_replay; errors = []
    def paused(raw, family, full):
        if raw == b"" and not entered.is_set():
            entered.set(); assert release.wait(5)
        return original(raw, family, full)
    monkeypatch.setattr(sa, "_strict_replay", paused)
    def holder():
        try: stage(case)
        except Exception as e: errors.append(repr(e))
    def ordinary():
        attempted.set()
        try: trial_ledger.TrialLedger(path=case[0]/sa.LEDGER_BASENAME, family=FAMILY).log_trial(case[1][0][1], source=sa._ROW_SOURCE)
        except Exception as e: errors.append(repr(e))
        finally: done.set()
    a = threading.Thread(target=holder); a.start(); assert entered.wait(5)
    b = threading.Thread(target=ordinary); b.start(); assert attempted.wait(5)
    try: assert not done.wait(.1)
    finally: release.set(); a.join(5); b.join(5)
    assert not a.is_alive() and not b.is_alive() and not errors, errors
    assert len([r for r in rows(case[0]) if "config" in r]) == 2


def test_filesystem_open_race_is_a_closed_refusal(case, monkeypatch):
    original = os.open
    ledger = case[0] / sa.LEDGER_BASENAME
    def refused_open(path, flags, *args, **kwargs):
        if str(path) == str(ledger):
            raise PermissionError('controlled file access race')
        return original(path, flags, *args, **kwargs)
    monkeypatch.setattr(os, 'open', refused_open)
    with pytest.raises(sa.StagingAccountingRefused, match='SNAPSHOT_UNREADABLE'):
        stage(case)
    assert ledger.read_bytes() == b''

def test_staging_snapshot_reads_use_existing_owner_lock(case, monkeypatch):
    # A cooperating writer may append to the same immutable inode while this
    # caller is outside the original TrialLedger sidecar flock. Even a nofollow
    # stat/open pair then refuses a legitimate append as PATH_SWAPPED_DURING_READ.
    from engine import trial_ledger
    calls=[]
    original=sa._read_snapshot
    def guarded(path):
        owner=getattr(trial_ledger._ACTIVE_OWNER, 'owner', None)
        assert owner is not None and owner._transaction is not None, (
            "snapshot read outside original TrialLedger owner transaction")
        calls.append(path)
        return original(path)
    monkeypatch.setattr(sa, '_read_snapshot', guarded)
    result=stage(case)
    assert result.newly_recorded_count==2
    assert len(calls)>=2
