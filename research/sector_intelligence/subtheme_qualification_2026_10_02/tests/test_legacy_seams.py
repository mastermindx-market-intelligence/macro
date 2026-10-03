from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legacy_seams import reproduce, calendar_endpoint, coverage_renormalized


def test_calendar_discriminator():
    r=reproduce()
    assert r['calendar_endpoint']=='2026-09-30'
    assert r['calendar_endpoint']!=r['explicit_five_session_endpoint']


def test_iteration_order_changes_legacy_headline():
    r=reproduce()
    assert r['leader_5_then_21']=='v2'
    assert r['leader_21_then_5']=='incumbent'


def test_missing_loser_can_flip_legacy_group_label():
    r=reproduce()
    assert r['full_population_mean']==pytest.approx(-0.035)
    assert r['missing_loser_legacy_mean']==pytest.approx(0.02)


def test_legacy_three_member_floor_does_not_measure_coverage():
    assert coverage_renormalized([0.02]*3+[None]*97)==pytest.approx(0.02)
