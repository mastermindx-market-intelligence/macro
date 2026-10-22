from datetime import date, datetime
import pytest
from engine.liquidity_source_availability import source_expected_session, coverage_clock

@pytest.mark.parametrize('stamp,expected', [
 ('2026-10-20T14:59:59+00:00','2026-10-16'),
 ('2026-10-20T15:00:00+00:00','2026-10-19'),
 ('2026-10-19T14:59:59+00:00','2026-10-16'),
 ('2026-10-18T16:00:00+00:00','2026-10-16'),
 ('2026-11-03T15:59:59+00:00','2026-10-30'),
 ('2026-11-03T16:00:00+00:00','2026-11-02'),
 ('2026-07-06T15:00:00+00:00','2026-07-02'),
])
def test_source_availability_boundary_dst_weekend_and_holiday(stamp,expected):
 assert source_expected_session(datetime.fromisoformat(stamp)) == date.fromisoformat(expected)

def test_schedule_is_not_publication_evidence():
 c=coverage_clock(datetime.fromisoformat('2026-10-20T07:00:00+00:00'))
 assert c['market_completed_session']=='2026-10-19'
 assert c['source_expected_session']=='2026-10-16'
 assert c['schedule_is_publication_evidence'] is False
 assert 'known_at' not in c

@pytest.mark.parametrize('stamp',[None,datetime(2026,10,20)])
def test_no_clock_guess(stamp):
 with pytest.raises(ValueError): source_expected_session(stamp)
