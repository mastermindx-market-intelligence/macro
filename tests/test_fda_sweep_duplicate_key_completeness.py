"""The sweep must complete when the source feed repeats a dedupe key.

Seat-frozen regression probes for the live openFDA condition measured 2026-09-28:
the endpoint reported ``total: 1601`` while four ``(package_ndc,
initial_posting_date)`` pairs appeared twice, so the sweep's deduplicated
``unique_count`` topped out at 1597. The loop's only success exit compared that
deduplicated count against the RAW reported total, so ``1597 >= 1601`` never held,
the sweep paged past the end of the feed, openFDA answered ``skip >= total`` with
HTTP 404, and the sweep recorded ``PAGE_FAILED`` -> ``qualified: false``. The
public seam then correctly refused, and the served chip read "FDA source
unavailable" for every user.

The completeness question is "did we observe every record the source reported",
which is a statement about RAW rows. Deduplication is a storage concern and must
not be able to make a complete interval look incomplete. Every pre-existing
fixture used feeds where ``raw_count == unique_count``, so none could reach this
branch.
"""
from datetime import datetime, timezone


def _record(ndc, posting="02/20/2018"):
    return {
        "package_ndc": ndc,
        "generic_name": "Synthetic",
        "status": "Current",
        "availability": "Limited Availability",
        "initial_posting_date": posting,
    }


def _paged(generation, rows, total=None, page_size=2):
    """Serve ``rows`` in pages of ``page_size``, reporting ``total`` raw records."""
    reported = len(rows) if total is None else total

    def fetch_page(skip, limit):
        if skip >= reported:
            # openFDA's measured behaviour: 404 NOT_FOUND once skip reaches total.
            raise OSError("HTTP 404 NOT_FOUND — No matches found!")
        return {
            "meta": {"last_updated": generation, "results": {"total": reported}},
            "results": rows[skip:skip + limit],
        }

    return fetch_page


def _sweep(rows, *, page_size=2, max_pages=25, generation="2026-09-26", total=None):
    from collectors.fda_shortages import collect_shortage_sweep

    return collect_shortage_sweep(
        _paged(generation, rows, total=total, page_size=page_size),
        clock=lambda: datetime(2026, 9, 28, 6, tzinfo=timezone.utc),
        page_size=page_size,
        max_pages=max_pages,
    )


def test_duplicate_key_feed_still_qualifies():
    """A feed whose raw total exceeds its unique keys is still a COMPLETE sweep."""
    rows = [_record("A"), _record("B"), _record("A"), _record("C")]
    result = _sweep(rows)

    assert result["failure_code"] is None, result["failure_code"]
    assert result["qualified"] is True
    capture = result["capture"]
    assert capture["raw_count"] == 4
    assert capture["unique_count"] == 3          # the duplicate collapsed
    assert capture["reported_total"] == 4
    assert capture["complete"] is True
    # Stored rows are deduplicated; completeness is not.
    assert len(result["rows"]) == 3


def test_duplicate_key_feed_does_not_page_past_the_end():
    """The overrun is what produced PAGE_FAILED in production — it must not recur."""
    rows = [_record("A"), _record("B"), _record("A"), _record("C")]
    result = _sweep(rows)

    assert result["failure_code"] != "PAGE_FAILED"
    # 4 raw rows at page_size 2 = exactly 2 pages; a third request would 404.
    assert result["capture"]["pages"] == 2


def test_live_shape_1601_raw_with_four_duplicate_keys_qualifies():
    """The measured live shape: 1601 raw records, 4 repeated keys -> 1597 unique."""
    rows = [_record(f"NDC-{i:04d}") for i in range(1597)]
    for i in range(4):                      # four keys served a second time
        rows.append(_record(f"NDC-{i:04d}"))
    assert len(rows) == 1601

    result = _sweep(rows, page_size=100)

    assert result["failure_code"] is None, result["failure_code"]
    assert result["qualified"] is True
    capture = result["capture"]
    assert capture["raw_count"] == 1601
    assert capture["unique_count"] == 1597
    assert capture["reported_total"] == 1601
    assert capture["complete"] is True
    assert len(result["rows"]) == 1597


def test_a_genuinely_short_feed_is_still_incomplete():
    """Falsifier: the fix must not green a sweep that really did miss records.

    A source reporting 6 while serving 4 must stay unqualified — otherwise the
    change has merely deleted the completeness check instead of correcting it.
    """
    rows = [_record("A"), _record("B"), _record("C"), _record("D")]
    result = _sweep(rows, page_size=2, max_pages=3, total=6)

    assert result["qualified"] is False
    assert result["capture"]["complete"] is False


def test_short_feed_with_duplicates_is_still_incomplete():
    """Dedupe must not be able to disguise a genuinely truncated sweep either."""
    from collectors.fda_shortages import collect_shortage_sweep

    rows = [_record("A"), _record("B"), _record("A")]

    def fetch_page(skip, limit):
        # Reports 10 but only ever serves these 3 rows, then 404s.
        if skip >= len(rows):
            raise OSError("HTTP 404 NOT_FOUND")
        return {"meta": {"last_updated": "2026-09-26", "results": {"total": 10}},
                "results": rows[skip:skip + limit]}

    result = collect_shortage_sweep(
        fetch_page,
        clock=lambda: datetime(2026, 9, 28, 6, tzinfo=timezone.utc),
        page_size=2, max_pages=25,
    )
    assert result["qualified"] is False
    assert result["capture"]["complete"] is False
