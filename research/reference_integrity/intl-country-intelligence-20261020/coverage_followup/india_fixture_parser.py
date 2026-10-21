"""Research-only parser for one reviewed native PDF; no network or admission.

This is a local follow-up prototype, not a change to the production collector.
The pinned hash identifies the original bytes acquired on 2026-10-20.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import io
import re

SOURCE_URL = "https://www.mospi.gov.in/uploads/latestReleases/latest_release_1788172583113_d65a77cf-240e-4491-82ee-59f78618fa41_Press_Note_on_GDP_Estimates_for_Q1_2026-27.pdf"
SOURCE_SHA256 = "152d9020853769fe4fe4433bec038a558aae1312bbb13ec072058e8dd5b0bc49"
PUBLISHED = "2026-08-31"


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _normal(text):
    return " ".join(text.split())


def parse_reviewed_texts(pages):
    """Semantic checks are separate so rejection cases can mutate only memory."""
    _require(type(pages) is list and len(pages) == 12, "unexpected_page_count")
    _require(all(type(page) is str and len(page) < 100_000 for page in pages), "invalid_page_text")
    cover, identity, highlights, narrative, revision, tables = (
        _normal(pages[i]) for i in (0, 1, 2, 3, 7, 8)
    )
    _require("NATIONAL STATISTICS OFFICE" in cover and "GOVERNMENT OF INDIA" in cover,
             "publisher_identity_mismatch")
    _require("31st August, 2026" in identity, "publication_date_mismatch")
    _require("First Quarter (Q1, April-June) of Financial Year (FY) 2026-27" in identity,
             "native_period_mismatch")
    _require("at Constant (2022-23) and Current prices" in identity,
             "price_base_mismatch")
    _require("with base year 2022-23 on 27th February, 2026" in identity,
             "series_revision_identity_mismatch")
    headline = re.findall(r"Real GDP has been estimated to grow by ([0-9]+\.[0-9])% in Q1 of FY 2026-27,", highlights)
    _require(len(headline) == 1, "observed_real_headline_not_unique")
    rate = Decimal(headline[0])
    _require("Real GDP or GDP at Constant Prices in Q1 of FY 2026-27" in narrative
             and "in Q1 of FY 2025-26, showing a growth rate of " + headline[0] + "%" in narrative,
             "comparison_period_or_rate_mismatch")
    _require("Estimates are, therefore, likely to undergo revisions" in revision,
             "revision_status_mismatch")
    _require("Second Quarter (July-September) of FY 2026-27" in revision
             and "scheduled on 30th November, 2026" in revision,
             "next_release_identity_mismatch")

    title1 = "Statement 1: Quarterly Estimates of GVA at Basic Prices for Q1, 2026-27 (Constant Prices)"
    title2 = "Statement 2: Quarterly Estimates of Expenditure Components of GDP for Q1, 2026-27 (Constant Prices)"
    _require(tables.count(title1) == 1 and tables.count(title2) == 1, "constant_price_tables_not_identified")
    _require("* Values are (in ₹ Crore)" in tables, "native_unit_mismatch")
    section1 = tables.split(title1, 1)[1].split(title2, 1)[0]
    section2 = tables.split(title2, 1)[1]
    table_rows = []
    for section in (section1, section2):
        # PDF text order interleaves the adjacent multi-row column headings.
        # Match only the two observed bounded interleavings, or contiguous text.
        _require(re.search(r"Percentage Change Over(?: Quarterly Levels(?: Sector)?)? Previous(?: Quarterly Levels)? Year", section) is not None,
                 "growth_basis_mismatch")
        _require("2024-25 2025-26 2026-27 2025-26 2026-27" in section,
                 "column_order_mismatch")
        match = re.findall(r"\bGDP ([0-9,]+) ([0-9,]+) ([0-9,]+) ([0-9]+\.[0-9]) ([0-9]+\.[0-9])(?:\s|$)", section)
        _require(len(match) == 1, "gdp_row_not_unique")
        row = match[0]
        _require(all(re.fullmatch(r"[0-9]{1,2}(?:,[0-9]{2})*,[0-9]{3}", value)
                     for value in row[:3]), "native_level_format_changed")
        table_rows.append((*(int(value.replace(",", "")) for value in row[:3]),
                           Decimal(row[3]), Decimal(row[4])))
    _require(table_rows[0] == table_rows[1], "gdp_statements_disagree")
    earlier, previous, current, previous_rate, table_rate = table_rows[0]
    _require(all(level > 0 for level in (earlier, previous, current)), "nonpositive_gdp_level")
    _require(table_rate == rate, "headline_table_rate_disagreement")
    calculated = (Decimal(current) / Decimal(previous) - 1) * 100
    previous_calculated = (Decimal(previous) / Decimal(earlier) - 1) * 100
    _require(calculated.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP) == rate,
             "current_level_rate_disagreement")
    _require(previous_calculated.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP) == previous_rate,
             "previous_level_rate_disagreement")
    _require(not re.search(r"seasonally|seasonal adjustment", " ".join(pages), re.I),
             "seasonal_label_requires_new_review")
    return {
        "cc": "IN", "metric": "gdp", "value": float(rate), "value_text": headline[0],
        "reported_decimals": 1, "unit": "% y/y", "status": "provisional",
        "source_status_label": "Quarterly Estimates", "period": "2026-Q2",
        "reference_start": "2026-04-01", "reference_end": "2026-06-30",
        "native_period": "Q1 FY 2026-27 (April-June 2026)",
        "comparison_native_period": "Q1 FY 2025-26 (April-June 2025)",
        "price_basis": "constant_2022_23_prices", "measure_basis": "real_gdp",
        "growth_basis": "year_over_year", "seasonal_adjustment": "not_stated",
        "seasonal_review_scope": "12-page extracted text; physical page 9 visually verified separately",
        "method": "published_rate_with_native_level_crosscheck",
        "provider": "MoSPI / National Statistics Office", "published": PUBLISHED,
        "source_url": SOURCE_URL, "source_physical_page": 9, "source_printed_page": 8,
        "source_tables": [title1, title2],
        "native_level_unit": "INR crore at constant 2022-23 prices",
        "native_levels": [
            {"native_period": "Q1 FY 2024-25", "value": earlier},
            {"native_period": "Q1 FY 2025-26", "value": previous},
            {"native_period": "Q1 FY 2026-27", "value": current},
        ],
        "calculated_yoy_unrounded_decimal": str(calculated),
        "next_release_date": "2026-11-30",
    }


def parse_reviewed_pdf(blob, receipt, *, as_of):
    """Require original byte custody before applying the release-specific parser."""
    _require(type(blob) is bytes and 0 < len(blob) <= 4_000_000 and blob.startswith(b"%PDF-"),
             "invalid_pdf_bytes")
    stamp = sha256(blob).hexdigest()
    _require(stamp == SOURCE_SHA256, "unreviewed_source_payload")
    _require(type(receipt) is dict and receipt.get("http_status") == 200,
             "successful_http_receipt_required")
    _require(receipt.get("requested_url") == SOURCE_URL and receipt.get("final_url") == SOURCE_URL,
             "source_url_mismatch")
    _require(receipt.get("source_sha256") == stamp and receipt.get("source_bytes") == len(blob),
             "source_receipt_hash_or_length_mismatch")
    try:
        retrieved = datetime.fromisoformat(receipt["retrieved_at"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid_retrieval_clock") from error
    _require(retrieved.tzinfo is not None and retrieved.utcoffset() is not None,
             "retrieval_clock_must_be_aware")
    _require(as_of.tzinfo is not None and retrieved <= as_of
             and retrieved.date().isoformat() >= PUBLISHED, "retrieval_clock_out_of_order")
    import pdfplumber
    with pdfplumber.open(io.BytesIO(blob)) as pdf:
        _require(len(pdf.pages) == 12, "unexpected_page_count")
        pages = [page.extract_text(x_tolerance=2, y_tolerance=3) or "" for page in pdf.pages]
    parsed = parse_reviewed_texts(pages)
    return {
        "schema": "research_national_gdp_parser_result.v1", "research_only": True,
        "production_admitted": False, "admission_state": "not_admitted",
        "source_sha256": stamp, "retrieved_at": receipt["retrieved_at"],
        "first_production_admission_at": None,
        "parser_version": "local_mospi_20260831_reviewed_fixture_v1",
        "observation_candidate": parsed,
    }
