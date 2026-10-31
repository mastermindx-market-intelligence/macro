"""Tests for engine/qledger_evidence_clock.py — the WRITE-ONCE record of each
qledger claim family's first prospective-registration instant (Eval OS P3).

THE PROPERTY UNDER TEST: `record_start` NEVER overwrites an existing family's
timestamp, no matter what a later call passes — a start timestamp that could
move forward would let a family's track record read as older/more-matured
than it honestly is. `test_second_call_never_overwrites_the_first` is that
property made executable; see this file's tail for the manual mutation-control
notes (paste-output requirement lives in the task report, not here — a
regression test cannot assert against code that isn't there).
"""
from __future__ import annotations

from engine import qledger_evidence_clock as qclock
import json
import pytest


def test_absent_family_reads_as_none(tmp_path):
    assert qclock.read_start("stock_desk", root=tmp_path) is None


def test_record_start_persists_and_reads_back(tmp_path):
    rec = qclock.record_start("stock_desk", horizon_d=20, horizon_unit="trading_days",
                              git_sha="abc123", root=tmp_path, now="2026-08-14T03:00:00+00:00")
    assert rec["claim_family"] == "stock_desk"
    assert rec["first_prospective_registration_utc"] == "2026-08-14T03:00:00+00:00"
    assert rec["declared_horizon_d"] == 20
    assert rec["horizon_unit"] == "trading_days"
    assert rec["git_sha"] == "abc123"
    reread = qclock.read_start("stock_desk", root=tmp_path)
    assert reread == rec


def test_second_call_never_overwrites_the_first(tmp_path):
    """THE write-once property. A second call — even with a LATER `now`, a
    DIFFERENT git_sha, and a DIFFERENT declared horizon — must return the
    ORIGINAL record byte-for-byte. This is the exact property CEO §evidence-
    clock requires: nothing may move a family's start timestamp forward."""
    first = qclock.record_start("stock_desk", horizon_d=20, horizon_unit="trading_days",
                                git_sha="sha-one", root=tmp_path, now="2026-08-14T03:00:00+00:00")
    second = qclock.record_start("stock_desk", horizon_d=999, horizon_unit="calendar_days",
                                 git_sha="sha-two", root=tmp_path, now="2027-01-01T00:00:00+00:00")
    assert second == first
    assert second["first_prospective_registration_utc"] == "2026-08-14T03:00:00+00:00"
    assert second["git_sha"] == "sha-one"
    assert second["declared_horizon_d"] == 20
    # the file on disk agrees — a caller who never called record_start again
    # and only re-read the file sees the same, unmoved timestamp.
    assert qclock.read_start("stock_desk", root=tmp_path) == first


def test_families_are_independent_files(tmp_path):
    qclock.record_start("stock_desk", horizon_d=20, horizon_unit="trading_days",
                        root=tmp_path, now="2026-08-14T03:00:00+00:00")
    assert qclock.read_start("thematic_desk", root=tmp_path) is None
    qclock.record_start("thematic_desk", horizon_d=20, horizon_unit="trading_days",
                        root=tmp_path, now="2026-08-15T03:00:00+00:00")
    stock = qclock.read_start("stock_desk", root=tmp_path)
    thematic = qclock.read_start("thematic_desk", root=tmp_path)
    assert stock["first_prospective_registration_utc"] == "2026-08-14T03:00:00+00:00"
    assert thematic["first_prospective_registration_utc"] == "2026-08-15T03:00:00+00:00"


def test_record_defaults_now_to_utc_wall_clock_when_not_supplied(tmp_path):
    rec = qclock.record_start("demand_chain", horizon_d=126, horizon_unit="trading_days",
                              root=tmp_path)
    assert rec["first_prospective_registration_utc"]
    # ISO-8601 with an explicit UTC offset (the CEO's exact requirement).
    ts = rec["first_prospective_registration_utc"]
    assert ts.endswith("+00:00") or ts.endswith("Z")


def test_git_sha_prefers_env_over_subprocess(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_SHA", "env-sha-value")
    assert qclock.git_sha(root=tmp_path) == "env-sha-value"


def test_git_sha_never_raises_on_a_non_repo_path(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    # tmp_path is not a git repo — `git rev-parse HEAD` fails; must return None,
    # never raise.
    assert qclock.git_sha(root=tmp_path) is None


def test_default_unreadable_clock_is_unavailable_and_never_restamped(tmp_path):
    path=qclock._clock_path('stock_desk',tmp_path);path.parent.mkdir(parents=True)
    original=b'{ not json';path.write_bytes(original)
    assert qclock.read_start('stock_desk',root=tmp_path) is None
    rec=qclock.record_start('stock_desk',horizon_d=20,horizon_unit='trading_days',root=tmp_path,now='2027-01-01T00:00:00+00:00')
    assert rec is None and path.read_bytes()==original


def test_clock_persistence_failure_is_strict_or_explicitly_unavailable(tmp_path, monkeypatch):
    from pathlib import Path
    import pytest
    def refused(*a, **k):
        raise OSError('fixture clock persistence refused')
    monkeypatch.setattr(qclock.os, 'link', refused)
    with pytest.raises(OSError, match='persistence refused'):
        qclock.record_start('thematic_desk', horizon_d=5, horizon_unit='trading_days', root=tmp_path, strict=True)
    assert qclock.record_start('stock_desk', horizon_d=5, horizon_unit='trading_days', root=tmp_path) is None
    assert not qclock._clock_path('stock_desk',tmp_path).exists()


def test_explicit_strict_clock_preserves_unreadable_original(tmp_path):
    import pytest
    path = qclock._clock_path('thematic_desk', tmp_path)
    path.parent.mkdir(parents=True)
    path.write_bytes(b'original malformed clock\n')
    with pytest.raises(ValueError):
        qclock.record_start('thematic_desk', horizon_d=5, horizon_unit='trading_days', root=tmp_path, strict=True)
    assert path.read_bytes() == b'original malformed clock\n'


def test_explicit_strict_clock_returns_exact_existing_without_restamping(tmp_path):
    first = qclock.record_start('thematic_desk', horizon_d=5, horizon_unit='trading_days', root=tmp_path,
                                now='2026-01-01T00:00:00+00:00', strict=True)
    second = qclock.record_start('thematic_desk', horizon_d=99, horizon_unit='different', root=tmp_path,
                                 now='2026-02-01T00:00:00+00:00', strict=True)
    assert second == first == qclock.read_start('thematic_desk', tmp_path)


def test_explicit_strict_clock_readback_mismatch_is_not_success(tmp_path, monkeypatch):
    from pathlib import Path
    import pytest
    actual_link = qclock.os.link
    def different(source, target, **kwargs):
        value = actual_link(source, target, **kwargs)
        qclock._clock_path("thematic_desk", tmp_path).write_text('{"first_prospective_registration_utc":"foreign-original"}')
        return value
    monkeypatch.setattr(qclock.os, "link", different)
    with pytest.raises(ValueError, match="readback differs"):
        qclock.record_start("thematic_desk", horizon_d=5, horizon_unit="trading_days", root=tmp_path, strict=True)
    assert qclock.read_start("thematic_desk", tmp_path)["first_prospective_registration_utc"] == "foreign-original"


def test_strict_two_absent_callers_preserve_first_installed_clock(tmp_path, monkeypatch):
    import os
    import threading
    from pathlib import Path
    target = qclock._clock_path('thematic_desk', tmp_path)
    both_absent = threading.Barrier(2)
    first_returned = threading.Event()
    real_open, real_write, real_link = Path.open, Path.write_text, os.link
    real_snapshot, observed = qclock._strict_clock_snapshot, set()
    def absent_read(path, field):
        value = real_snapshot(path, field)
        name = threading.current_thread().name
        if path == target and value is None and name not in observed:
            observed.add(name)
            both_absent.wait(timeout=5)
        return value
    def ordered_write(path, *a, **k):
        if threading.current_thread().name == 'clock-B' and path.name.endswith('.tmp'):
            assert first_returned.wait(5)
        return real_write(path, *a, **k)
    def ordered_link(source, destination, *a, **k):
        if threading.current_thread().name == 'clock-B' and Path(destination).name == target.name:
            assert first_returned.wait(5)
        return real_link(source, destination, *a, **k)
    monkeypatch.setattr(qclock, '_strict_clock_snapshot', absent_read)
    monkeypatch.setattr(Path, 'write_text', ordered_write)
    monkeypatch.setattr(os, 'link', ordered_link)
    values, errors = {}, []
    def worker(name):
        try:
            values[name] = qclock.record_start('thematic_desk', horizon_d=5, horizon_unit='trading_days',
                root=tmp_path, now=f'2026-01-0{1 if name == "A" else 2}T00:00:00+00:00', strict=True)
        except BaseException as exc:
            errors.append(exc)
        finally:
            if name == 'A':
                first_returned.set()
    threads = [threading.Thread(target=worker, args=(name,), name='clock-'+name) for name in ('A', 'B')]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert not any(thread.is_alive() for thread in threads) and not errors
    assert values['A']['first_prospective_registration_utc'] == '2026-01-01T00:00:00+00:00'
    assert values['B'] == values['A'] == qclock.read_start('thematic_desk', tmp_path)


def test_strict_link_response_loss_preserves_original_and_next_read_never_reinstalls(tmp_path, monkeypatch):
    import pytest
    target = qclock._clock_path('thematic_desk', tmp_path)
    real_link = qclock.os.link
    installs = []
    def lost(source, destination, **kwargs):
        real_link(source, destination, **kwargs)
        installs.append(target)
        raise OSError('fixture install return lost')
    monkeypatch.setattr(qclock.os, 'link', lost)
    with pytest.raises(OSError, match='return lost'):
        qclock.record_start('thematic_desk', horizon_d=5, horizon_unit='trading_days', root=tmp_path,
                             now='2026-01-01T00:00:00+00:00', strict=True)
    original = target.read_bytes()
    winner = qclock.record_start('thematic_desk', horizon_d=99, horizon_unit='changed', root=tmp_path,
                                 now='2026-02-01T00:00:00+00:00', strict=True)
    assert winner['first_prospective_registration_utc'] == '2026-01-01T00:00:00+00:00'
    assert target.read_bytes() == original and installs == [target]
    assert list(target.parent.iterdir()) == [target]


def test_strict_collision_never_heals_invalid_winner(tmp_path, monkeypatch):
    import pytest
    target = qclock._clock_path('thematic_desk', tmp_path)
    def collision(source, destination, **kwargs):
        target.write_bytes(b'original invalid winner\n')
        raise FileExistsError('fixture another installer won')
    monkeypatch.setattr(qclock.os, 'link', collision)
    with pytest.raises(ValueError):
        qclock.record_start('thematic_desk', horizon_d=5, horizon_unit='trading_days', root=tmp_path, strict=True)
    assert target.read_bytes() == b'original invalid winner\n'
    assert list(target.parent.iterdir()) == [target]


def test_strict_collision_missing_winner_is_uncertain_without_second_install(tmp_path, monkeypatch):
    import pytest
    target = qclock._clock_path('thematic_desk', tmp_path)
    attempts = []
    def collision(source, destination, **kwargs):
        attempts.append(target)
        raise FileExistsError('fixture collision winner removed')
    monkeypatch.setattr(qclock.os, 'link', collision)
    with pytest.raises(ValueError, match='winner unavailable'):
        qclock.record_start('thematic_desk', horizon_d=5, horizon_unit='trading_days', root=tmp_path, strict=True)
    assert attempts == [target] and not target.exists()


def test_strict_partial_private_staging_never_installs_or_adopts_other_temporaries(tmp_path, monkeypatch):
    import pytest
    target = qclock._clock_path('thematic_desk', tmp_path)
    target.parent.mkdir(parents=True)
    shared, orphan = target.with_name(target.name+'.tmp'), target.with_name('.'+target.name+'.orphan.tmp')
    shared.write_bytes(b'original shared partial')
    orphan.write_bytes(b'original private partial')
    real_fdopen = qclock.os.fdopen
    class Partial:
        def __init__(self, handle):
            self.handle = handle
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.handle.close()
        def write(self, payload):
            self.handle.write(payload[:8])
            self.handle.flush()
            raise OSError('fixture private staging interrupted')
    monkeypatch.setattr(qclock.os, 'fdopen', lambda *a, **k: Partial(real_fdopen(*a, **k)))
    monkeypatch.setattr(qclock.os, 'link', lambda *a: pytest.fail('partial clock was installed'))
    with pytest.raises(OSError, match='staging interrupted'):
        qclock.record_start('thematic_desk', horizon_d=5, horizon_unit='trading_days', root=tmp_path, strict=True)
    assert not target.exists()
    assert shared.read_bytes() == b'original shared partial' and orphan.read_bytes() == b'original private partial'
    assert set(target.parent.iterdir()) == {shared, orphan}



@pytest.mark.parametrize('original',[b'[]',b'null',b'{"other":"unproven"}',b'{"first_prospective_registration_utc":""}'])
def test_default_unqualified_existing_clock_preserves_all_bytes(tmp_path,original):
    path=qclock._clock_path('stock_desk',tmp_path);path.parent.mkdir(parents=True);path.write_bytes(original)
    assert qclock.record_start('stock_desk',horizon_d=20,horizon_unit='trading_days',root=tmp_path,now='2027-01-01T00:00:00+00:00') is None
    assert path.read_bytes()==original
    assert qclock.read_start('stock_desk',root=tmp_path) is None


def test_default_permission_unavailability_cannot_restamp(tmp_path,monkeypatch):
    from pathlib import Path
    path=qclock._clock_path('stock_desk',tmp_path);path.parent.mkdir(parents=True)
    original=b'{"first_prospective_registration_utc":"2026-01-01T00:00:00+00:00"}';path.write_bytes(original)
    real_read,real_open=Path.read_text,qclock.os.open
    def unavailable_read(subject,*args,**kwargs):
        if subject==path:raise PermissionError('test-owned unavailable original read')
        return real_read(subject,*args,**kwargs)
    def unavailable_open(subject,*args,**kwargs):
        if subject==path.name:raise PermissionError('test-owned unavailable original read')
        return real_open(subject,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',unavailable_read);monkeypatch.setattr(qclock.os,'open',unavailable_open)
    assert qclock.record_start('stock_desk',horizon_d=20,horizon_unit='trading_days',root=tmp_path,now='2027-01-01T00:00:00+00:00') is None
    assert path.read_bytes()==original


def test_default_valid_existing_clock_preserves_original_format_and_fields(tmp_path):
    path=qclock._clock_path('stock_desk',tmp_path);path.parent.mkdir(parents=True)
    raw=b'{ "first_prospective_registration_utc" : "2026-01-01T00:00:00+00:00", "original_extra" : 7 }\n';path.write_bytes(raw)
    actual=qclock.record_start('stock_desk',horizon_d=999,horizon_unit='changed',root=tmp_path,now='2027-01-01T00:00:00+00:00')
    assert actual==json.loads(raw) and path.read_bytes()==raw


@pytest.mark.parametrize('valid_winner',[False,True])
def test_default_clock_collision_never_replaces_first_visible_winner(tmp_path,monkeypatch,valid_winner):
    path=qclock._clock_path('stock_desk',tmp_path)
    winner=b'{"first_prospective_registration_utc":"2026-01-01T00:00:00+00:00","original_extra":7}\n' if valid_winner else b'original unqualified bytes'
    real_link=qclock.os.link
    def compete(source,destination,**kwargs):
        if destination==path.name:path.write_bytes(winner)
        return real_link(source,destination,**kwargs)
    monkeypatch.setattr(qclock.os,'link',compete)
    rec=qclock.record_start('stock_desk',horizon_d=20,horizon_unit='trading_days',root=tmp_path,now='2027-01-01T00:00:00+00:00')
    assert rec==(json.loads(winner) if valid_winner else None)
    assert path.read_bytes()==winner


def test_default_lost_directory_barrier_is_unavailable_without_recovery_restamp(tmp_path,monkeypatch):
    from engine import qledger_store_native as native
    path=qclock._clock_path('stock_desk',tmp_path);real=native._sync_dir
    def uncertain(directory):
        if path.exists():raise OSError('test-owned lost original directory barrier')
        return real(directory)
    with monkeypatch.context() as scoped:
        scoped.setattr(native,'_sync_dir',uncertain)
        rec=qclock.record_start('stock_desk',horizon_d=20,horizon_unit='trading_days',root=tmp_path,now='2026-01-01T00:00:00+00:00')
    assert rec is None
    original=path.read_bytes();assert json.loads(original)['first_prospective_registration_utc']=='2026-01-01T00:00:00+00:00'
    visible=qclock.record_start('stock_desk',horizon_d=999,horizon_unit='changed',root=tmp_path,now='2027-01-01T00:00:00+00:00')
    assert visible==json.loads(original) and path.read_bytes()==original
    # A later visible family record does not settle the earlier original effect.
