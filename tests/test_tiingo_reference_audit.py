"""Public catalogue census is not account access or PIT-universe evidence."""
from datetime import date
import csv
import io
import zipfile

import pytest
import scripts.tiingo_reference_audit as ref


FIELDS = list(ref.FIELDS)


def zipped(rows, header=FIELDS, name="supported_tickers.csv"):
    text = io.StringIO(newline="")
    writer = csv.writer(text)
    writer.writerow(header)
    writer.writerows(rows)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, text.getvalue())
    return out.getvalue()


def audit(raw, **kw):
    defaults = dict(observed_at="2026-10-09T20:38:54Z", start=date(2000, 1, 1),
                    end=date(2026, 10, 8), limit=25)
    defaults.update(kw)
    return ref.audit_catalogue(raw, **defaults)


def test_reservations_null_dates_and_inactive_history_are_not_faked():
    out = audit(zipped([
        ["OLD", "NYSE", "Stock", "USD", "1980-01-01", "2005-01-01"],
        ["NEW", "NYSE", "Stock", "USD", "2025-01-01", "2026-10-08"],
        ["RESERVED", "NYSE", "Stock", "USD", "", ""],
    ]))
    assert out["rows"] == 3 and out["missing_history_bounds"] == 1
    assert out["acquisition_candidate_count"] == 2
    assert out["historical_survivorship_safe_universe"] is False
    assert out["catalogue_is_account_entitlement_proof"] is False
    assert out["downloaded_price_rows"] == 0
    old = next(x for x in out["selected"] if x["ticker"] == "OLD")
    assert old["request_start"] == "2000-01-01"
    assert old["request_end"] == "2005-01-01"


def test_invalid_adapter_symbols_are_reported_not_rewritten():
    out = audit(zipped([["-ODD", "NYSE", "Stock", "USD", "2000-01-01", "2020-01-01"]]))
    assert out["current_adapter_symbol_refused"] == 1
    assert out["acquisition_candidate_count"] == 0


def test_currency_and_asset_types_filter_without_claiming_global_access():
    raw = zipped([
        ["000001", "SHE", "Stock", "CNY", "2000-01-01", "2026-10-08"],
        ["AAA", "NYSE", "Stock", "USD", "2000-01-01", "2026-10-08"],
        ["FUND", "NYSE", "ETF", "USD", "2000-01-01", "2026-10-08"],
    ])
    out = audit(raw, currencies=("USD",), asset_types=("Stock",))
    assert out["rows"] == 3 and out["acquisition_candidate_count"] == 1
    assert out["selected"][0]["ticker"] == "AAA"
    assert out["currencies"] == {"CNY": 1, "USD": 2}


def test_conflicting_reference_key_is_quarantined():
    raw = zipped([
        ["AAA", "NYSE", "Stock", "USD", "2000-01-01", "2020-01-01"],
        ["AAA", "NYSE", "Stock", "USD", "2010-01-01", "2026-10-08"],
    ])
    out = audit(raw)
    assert out["conflicting_catalogue_keys"] == 1
    assert out["acquisition_candidate_count"] == 0


def test_cross_listing_ticker_ambiguity_does_not_auto_join():
    out = audit(zipped([
        ["AAA", "NYSE", "Stock", "USD", "2000-01-01", "2020-01-01"],
        ["AAA", "LSE", "Stock", "GBP", "2010-01-01", "2026-10-08"],
    ]))
    assert out["ambiguous_ticker_strings"] == 1
    assert out["acquisition_candidate_count"] == 0


def test_duplicate_exact_row_is_counted_but_not_requested_twice():
    row = ["AAA", "NYSE", "Stock", "USD", "2000-01-01", "2020-01-01"]
    out = audit(zipped([row, row]))
    assert out["duplicate_exact_rows"] == 1
    assert out["unique_catalogue_keys"] == out["acquisition_candidate_count"] == 1


def test_bad_dates_keep_denominator_visible():
    out = audit(zipped([
        ["AAA", "NYSE", "Stock", "USD", "2000-01-01", "1999-01-01"],
        ["BBB", "NYSE", "Stock", "USD", "broken", "2020-01-01"],
        ["CCC", "NYSE", "Stock", "USD", "20000101", "2020-01-01"],
    ]))
    assert out["rows"] == out["invalid_history_bounds"] == 3


def test_catalogue_page_checks_source_hash():
    raw = zipped([["AAA", "NYSE", "Stock", "USD", "2000-01-01", "2020-01-01"],
                  ["BBB", "NYSE", "Stock", "USD", "2000-01-01", "2020-01-01"]])
    first = audit(raw, limit=1)
    second = audit(raw, offset=first["next_offset"], limit=1,
                   expected_sha256=first["catalogue_sha256"])
    assert first["selected"][0]["ticker"] == "AAA"
    assert second["selected"][0]["ticker"] == "BBB"
    assert second["next_offset"] is None
    with pytest.raises(ref.ReferenceAuditError, match="catalogue changed"):
        audit(raw, expected_sha256="0" * 64)


@pytest.mark.parametrize("name", ["../supported_tickers.csv", "other.csv"])
def test_no_zip_paths_are_extracted_or_followed(name):
    with pytest.raises(ref.ReferenceAuditError):
        audit(zipped([], name=name))


def test_duplicate_or_missing_columns_are_refused():
    with pytest.raises(ref.ReferenceAuditError):
        audit(zipped([], header=["ticker", "ticker"]))


def test_ragged_csv_is_not_partial_success():
    with pytest.raises(ref.ReferenceAuditError):
        audit(zipped([["AAA", "NYSE"]]))


def test_limits_are_enforced_before_unbounded_read(monkeypatch):
    raw = zipped([["AAA", "NYSE", "Stock", "USD", "2000-01-01", "2020-01-01"]])
    monkeypatch.setattr(ref, "MAX_CSV_BYTES", 10)
    with pytest.raises(ref.ReferenceAuditError):
        audit(raw)


def test_empty_catalogue_never_implies_data_access():
    out = audit(zipped([]))
    assert out["rows"] == out["acquisition_candidate_count"] == 0
    assert out["earliest_advertised_history"] is None
    assert out["execution_authorized"] is False


def test_observation_clock_requires_timezone():
    with pytest.raises(ref.ReferenceAuditError):
        audit(zipped([]), observed_at="2026-10-09T20:00:00")



def test_full_history_sizing_counts_current_annual_chunks_without_authorizing_requests():
    # Two-year span needs three 366-day windows; one-day span only one.
    raw = zipped([
        ["AAA", "NYSE", "Stock", "USD", "2020-01-01", "2022-01-02"],
        ["BBB", "NYSE", "ETF", "USD", "2020-01-01", "2020-01-01"],
        ["CCC", "SHE", "Stock", "CNY", "2020-01-01", "2020-01-01"],
    ])
    out = audit(raw, start=date(2020, 1, 1), end=date(2022, 1, 2),
                currencies=("USD",))
    sizing = out["historical_eod_request_sizing"]
    assert sizing["eligible_public_catalogue_records"] == 2
    assert sizing["current_366_day_chunk_requests"] == 4
    assert sizing["single_full_history_request_hypothesis"] == 2
    assert sizing["one_call_guaranteed_by_vendor"] is False
    assert sizing["entitlement_confirmed"] is False
    assert sizing["downloaded_history"] is False
    assert sizing["execution_authorized"] is False
    assert sizing["network"] is False
    assert sizing["groups"] == [
        {"asset_type": "ETF", "currency": "USD",
         "eligible_records": 1, "current_366_day_requests": 1},
        {"asset_type": "Stock", "currency": "USD",
         "eligible_records": 1, "current_366_day_requests": 3},
    ]


def test_sizing_respects_ticker_quarantine_and_history_date_clipping():
    raw = zipped([
        ["VALID", "NYSE", "Stock", "USD", "1900-01-01", "2020-01-01"],
        ["DUP", "NYSE", "Stock", "USD", "2020-01-01", "2020-01-01"],
        ["DUP", "LSE", "Stock", "GBP", "2020-01-01", "2020-01-01"],
        ["CONFLICT", "NYSE", "Stock", "USD", "2020-01-01", "2021-01-01"],
        ["CONFLICT", "NYSE", "Stock", "USD", "2020-01-01", "2022-01-01"],
        ["OUTSIDE", "NYSE", "Stock", "USD", "2023-01-01", "2023-01-05"],
        ["RESERVATION", "NYSE", "Stock", "USD", "", ""],
    ])
    out = audit(raw, start=date(2020, 1, 1), end=date(2020, 1, 31),
                currencies=("USD",))
    sizing = out["historical_eod_request_sizing"]
    assert sizing["eligible_public_catalogue_records"] == 1
    assert sizing["current_366_day_chunk_requests"] == 1
    assert sizing["single_full_history_request_hypothesis"] == 1
    assert out["conflicting_catalogue_keys"] == 1
    assert out["ambiguous_ticker_strings"] == 1


def test_sizing_is_stable_across_catalogue_pagination_and_empty_cohorts():
    raw = zipped([
        ["AAA", "NYSE", "Stock", "USD", "2020-01-01", "2020-01-10"],
        ["BBB", "NYSE", "Stock", "USD", "2020-01-01", "2020-01-10"],
    ])
    first = audit(raw, start=date(2020, 1, 1), end=date(2020, 1, 10),
                  offset=0, limit=1)
    second = audit(raw, start=date(2020, 1, 1), end=date(2020, 1, 10),
                   offset=1, limit=1,
                   expected_sha256=first["catalogue_sha256"])
    assert first["historical_eod_request_sizing"] == second["historical_eod_request_sizing"]
    empty = audit(zipped([]))
    assert empty["historical_eod_request_sizing"]["current_366_day_chunk_requests"] == 0
    assert empty["historical_eod_request_sizing"]["groups"] == []
