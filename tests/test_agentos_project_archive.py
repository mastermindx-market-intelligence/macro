"""Actual canonical owner and bounded archive capture, no archive mutations."""
import copy
import datetime
import json
from pathlib import Path

import pytest
import yaml

from scripts import agentos
from scripts.agentos_project_archive import read_archive_sample
from tests.test_agentos_direction_owner import workstream


def declared():
    return {'schema': 'agentos.workstream_archive.v1', 'state': 'ARCHIVED',
            'archived_on': '2026-11-04', 'archived_by': 'synthetic-test-owner', 'reason': 'Explicit retained source declaration.'}


def save(root, rec):
    path = root / ('agentos/workstreams/WS-' + rec['key'] + '.md')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('---\n' + yaml.safe_dump(rec, allow_unicode=True) + '---\nPreserved record body.\n')
    return path


def read(root, refs):
    return read_archive_sample(root, captured_commit='a' * 40, qualified_work_refs=refs,
                               owner=agentos, programs={'executive-os'})


@pytest.mark.parametrize('status', ['done', 'parked', 'killed', 'active'])
def test_status_never_implies_archived_and_empty_is_sample_only(tmp_path, status):
    rec = workstream(); rec['status'] = status
    save(tmp_path, rec)
    result = read(tmp_path, ['WS:DIRECTION-TEST'])
    assert result['availability'] == 'AVAILABLE' and result['items'] == []
    assert result['coverage'] == {'kind': 'QUALIFIED_CATALOGUE_SAMPLE', 'supplied_count': 1,
                                 'observed_count': 1, 'company_total': None}


def test_explicit_archive_preserves_source_identity_and_day_precision(tmp_path):
    rec = workstream(); rec['archive'] = declared()
    path = save(tmp_path, rec)
    before = path.read_bytes()
    result = read(tmp_path, ['WS:DIRECTION-TEST'])
    assert result['availability'] == 'AVAILABLE' and len(result['items']) == 1
    row = result['items'][0]
    assert row['work_ref'] == 'WS:DIRECTION-TEST' and row['archive'] == declared()
    assert row['source']['path'] == 'agentos/workstreams/WS-DIRECTION-TEST.md'
    assert row['source']['commit'] == 'a' * 40
    assert result['can_restore'] is False and path.read_bytes() == before


@pytest.mark.parametrize('value', [None, {}, {'state': 'ARCHIVED'}, {**declared(), 'state': 'done'},
    {**declared(), 'archived_on': '2026-02-30'}, {**declared(), 'archived_on': '2026-11-04T00:00:00Z'},
    {**declared(), 'archived_on': datetime.datetime(2026, 11, 4)}, {**declared(), 'archived_by': ''},
    {**declared(), 'restore': True}])
def test_native_inline_owner_rejects_malformed_archive(value):
    rec = workstream(); rec['archive'] = value
    assert any(p.hard and p.rule == 'bad-archive' for p in agentos.check_workstream(rec, Path('WS-DIRECTION-TEST.md'), None))


def test_native_day_object_and_legacy_validation_need_no_new_helper(monkeypatch):
    rec = workstream(); rec['archive'] = {**declared(), 'archived_on': datetime.date(2026, 11, 4)}
    original = copy.deepcopy(rec)
    def denied(*args, **kwargs):
        pytest.fail('inline archive validation acquired an external helper')
    monkeypatch.setattr(Path, 'open', denied)
    assert not any(p.hard for p in agentos.check_workstream(rec, Path('WS-DIRECTION-TEST.md'), None))
    assert rec == original


def test_missing_or_invalid_member_never_becomes_empty_complete_sample(tmp_path):
    save(tmp_path, workstream())
    result = read(tmp_path, ['WS:DIRECTION-TEST', 'WS:MISSING'])
    assert result['availability'] == 'UNAVAILABLE' and result['items'] == []
    assert result['coverage']['observed_count'] < result['coverage']['supplied_count']


def test_symlink_and_caller_path_are_not_archive_sources(tmp_path):
    path = save(tmp_path, workstream())
    raw = path.read_bytes(); path.unlink()
    target = tmp_path / 'foreign.md'; target.write_bytes(raw); path.symlink_to(target)
    assert read(tmp_path, ['WS:DIRECTION-TEST'])['availability'] == 'UNAVAILABLE'
    with pytest.raises(ValueError):
        read(tmp_path, ['WS:../foreign'])
