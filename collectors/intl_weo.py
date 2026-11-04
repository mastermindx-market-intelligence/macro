"""Official IMF WEO statistical-table ingestion for the country cockpit.

Each registered release has an explicit date, artifact and table contract.
Parsing checks units, annual columns, sections and economy coverage before
admission. Figures labelled Q4/Q4 or end-of-period are never annual averages.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
import io
import re

from lib.intl_forecast_vintages import normalize_publication

WEO_OCTOBER_2026 = {
    "provider": "IMF", "family": "WEO", "edition": "2026-10",
    "published": "2026-10-13", "information_cutoff": "2026-09-30",
    "source_url": "https://www.imf.org/en/publications/weo/issues/2026/10/13/world-economic-outlook-october-2026",
    "dataset_url": "https://www.imf.org/-/media/files/publications/weo/2026/october/english/tablea.pdf",
    "documentation_url": "https://www.imf.org/-/media/files/publications/weo/2026/october/english/statsappendix.pdf",
    "format": "weo_statistical_tables", "parser_version": "weo_tables_2026_v1",
    "year": 2026, "max_bytes": 4_000_000,
}
LABELS = {"Japan": "JP", "Korea": "KR", "Taiwan Province of China": "TW",
          "World": "WORLD", "India": "IN", "Australia": "AU", "United Kingdom": "GB", "Euro Area": "EZ"}
# Reporting basis is indicator-specific. Table F and the country documentation
# show India's April--March national accounts, prices and balance-of-payments
# annual periods. No country-wide calendar relabel is applied to other inputs.
FISCAL_SERIES = {("IN", key): 4 for key in
                 ("real_gdp_growth", "inflation_average", "current_account")}
TABLES = {
    "A1": {"page": 1, "title": "Summary of World Output",
           "unit": "Annual percent change", "columns": 12,
           "series": "real_gdp_growth", "economies": ("WORLD",)},
    "A2": {"page": 2, "title": "Advanced Economies: Real GDP and Total Domestic Demand",
           "unit": "Annual percent change", "columns": 15,
           "series": "real_gdp_growth", "economies": ("JP", "KR", "TW", "AU", "GB", "EZ")},
    "A4": {"page": 5, "title": "Emerging Market and Developing Economies: Real GDP",
           "unit": "Annual percent change", "columns": 12,
           "series": "real_gdp_growth", "economies": ("IN",)},
    "A6": {"page": 9, "title": "Advanced Economies: Consumer Prices",
           "unit": "Annual percent change", "columns": 15,
           "series": "inflation_average", "economies": ("JP", "KR", "TW", "AU", "GB", "EZ")},
    "A7": {"page": 10, "title": "Emerging Market and Developing Economies: Consumer Prices",
           "unit": "Annual percent change", "columns": 15,
           "series": "inflation_average", "economies": ("IN",)},
    "A8": {"page": 13, "title": "Major Advanced Economies: General Government Fiscal Balances and Debt",
           "unit": "Percent of GDP, unless noted otherwise", "columns": 12,
           "series": "fiscal", "economies": ("JP", "GB", "EZ")},
    "A11": {"page": 19, "title": "Advanced Economies: Current Account Balance",
            "unit": "Percent of GDP", "columns": 11,
            "series": "current_account", "economies": ("JP", "KR", "TW", "AU", "GB", "EZ")},
    "A12": {"page": 20, "title": "Emerging Market and Developing Economies: Current Account Balance",
            "unit": "Percent of GDP", "columns": 11,
            "series": "current_account", "economies": ("IN",)},
}


def _normal(text):
    return re.sub(r"\s+", " ", text.replace("\u00ad", "")).strip()


def _numbers(text, count):
    text = _normal(text).replace("–", "-").replace("−", "-")
    text = re.sub(r"\.\s*\.\s*\.", "NA", text)
    tokens = text.split()
    if len(tokens) != count:
        raise ValueError("weo_column_count_changed")
    values = []
    for token in tokens:
        if token in ("NA", "n/a"):
            values.append(None)
        elif re.fullmatch(r"-?\d+(?:\.\d+)?", token):
            values.append(float(token))
        else:
            raise ValueError("weo_nonnumeric_cell")
    return values


def _row(lines, label, count):
    # Footnote superscripts may be attached to the country label.
    pattern = re.compile(r"^" + re.escape(label) + r"(?:\d)?\s+(.+)$", re.I)
    matches = [(line, pattern.match(line)) for line in lines]
    matches = [(line, match) for line, match in matches if match]
    if len(matches) != 1:
        raise ValueError("weo_country_row_missing_or_ambiguous:" + label)
    line, match = matches[0]
    return _numbers(match.group(1), count), sha256(line.encode()).hexdigest()


def parse_weo_table_texts(texts, *, release, retrieved_at, source_sha256):
    """Parse extracted pages with the same contract used for downloaded bytes."""
    if (type(release) is not dict or release.get("parser_version") != "weo_tables_2026_v1"
            or release.get("year") != 2026 or release.get("published") != "2026-10-13"):
        raise ValueError("unregistered_weo_table_contract")
    records = []
    labels = {cc: label for label, cc in LABELS.items()}
    for table, spec in TABLES.items():
        text = texts.get(table) if type(texts) is dict else None
        if not isinstance(text, str) or len(text) > 80_000:
            raise ValueError("weo_table_missing:" + table)
        lines = [_normal(line) for line in text.splitlines()]
        lowered = text.lower()
        if (f"Online Table {table}.".lower() not in lowered
                or spec["title"].lower() not in lowered
                or f"({spec['unit']})".lower() not in lowered
                or "International Monetary Fund | October 2026".lower() not in lowered):
            raise ValueError("weo_identity_or_unit_changed:" + table)
        header = ("2018 2019 2020 2021 2022 2023 2024 2025 2026 2027 2031"
                  if spec["series"] == "current_account" else
                  "2008–17 2018 2019 2020 2021 2022 2023 2024 2025 2026 2027 2031")
        yearline = next((line for line in lines if line.startswith(header)), None)
        if yearline is None:
            raise ValueError("weo_annual_year_columns_changed:" + table)
        expected_tail = (" 2025:Q4 2026:Q4 2027:Q4" if table == "A2" else
                         " 2025 2026 2027" if table in ("A6", "A7") else "")
        if yearline != header + expected_tail:
            raise ValueError("weo_annual_vs_end_period_ambiguous:" + table)
        if table == "A1":
            lines = [line for line in lines if not line.startswith("World Growth Rate")]
        if table == "A2":
            start = lines.index("Real GDP") + 1
            end = next((i for i, line in enumerate(lines) if line.lower() == "real total domestic demand"), None)
            if end is None:
                raise ValueError("weo_gdp_section_missing")
            lines = lines[start:end]
        if table == "A11":
            # The first euro-area row is adjusted for intra-area discrepancies;
            # the memorandum sum of country balances is a different measure.
            end = next((i for i, line in enumerate(lines) if line.lower() == "memorandum"), None)
            if end is None:
                raise ValueError("weo_current_account_scope_missing")
            lines = lines[:end]
        rows = []
        for cc in spec["economies"]:
            if table == "A8":
                markers = [i for i, line in enumerate(lines) if line.lower() == labels[cc].lower()]
                if len(markers) != 1:
                    raise ValueError("weo_fiscal_country_section_missing:" + cc)
                start = markers[0] + 1
                section = lines[start:start + 6]
                for key, label in (("fiscal_balance", "Net Lending/Borrowing"), ("government_debt", "Gross Debt")):
                    values, line_hash = _row(section, label, spec["columns"])
                    rows.append((cc, key, values, line_hash))
            else:
                values, line_hash = _row(lines, labels[cc], spec["columns"])
                rows.append((cc, spec["series"], values, line_hash))
        for cc, key, values, line_hash in rows:
            years = list(range(2018, 2028)) + [2031]
            annual = values if spec["series"] == "current_account" else values[1:12]
            if len(annual) != len(years):
                raise ValueError("weo_annual_period_count")
            selected = {str(year): value for year, value in zip(years, annual) if year >= 2023 and value is not None}
            if not all(str(year) in selected for year in (2026, 2027)):
                raise ValueError("weo_expected_projection_missing:" + cc + ":" + key)
            fiscal_month = FISCAL_SERIES.get((cc, key), 1)
            basis = "fiscal_year" if fiscal_month != 1 else "calendar_year"
            unit = "percent" if key in ("real_gdp_growth", "inflation_average") else "percent_gdp"
            note = None
            if key == "inflation_average":
                note = "Annual-average consumer-price inflation; not the latest monthly year-over-year CPI."
                if cc == "EZ":
                    note += " Euro-area prices use the harmonised index of consumer prices."
            elif key == "current_account" and cc == "EZ":
                note = "Euro-area aggregate adjusted for reporting discrepancies in intra-area transactions."
            elif key in ("fiscal_balance", "government_debt"):
                note = "General government. Sector and instrument coverage can differ across countries; this is not a sovereign-risk ranking."
                if cc == "JP" and key == "government_debt":
                    note += " Japan gross debt is reported on a nonconsolidated basis."
            raw = {**release, "cc": cc, "series_id": key, "kind": "sourced_forecast",
                   "unit": unit, "period_basis": basis, "fiscal_start_month": fiscal_month,
                   "values": selected, "precision": 1,
                   "source_table": table, "source_page": spec["page"] + 1,
                   "source_row_sha256": line_hash, "source_sha256": source_sha256,
                   "retrieved_at": retrieved_at, "first_observed_at": retrieved_at,
                   "admitted_at": retrieved_at, "coverage_note": note}
            record = normalize_publication(raw, observed_at=retrieved_at)
            if record is None:
                raise ValueError("weo_publication_admission_failed:" + cc + ":" + key)
            records.append(record)
    return records


def parse_weo_statistical_tables(blob, *, release, retrieved_at):
    if not isinstance(blob, bytes) or len(blob) > release["max_bytes"] or not blob.startswith(b"%PDF"):
        raise ValueError("weo_pdf_size_or_format")
    import pdfplumber  # Existing declared collector dependency; never loaded on render.
    with pdfplumber.open(io.BytesIO(blob)) as pdf:
        if not 21 <= len(pdf.pages) <= 60:
            raise ValueError("weo_pdf_page_count")
        texts = {table: pdf.pages[spec["page"]].extract_text() or "" for table, spec in TABLES.items()}
    return parse_weo_table_texts(texts, release=release, retrieved_at=retrieved_at,
                                source_sha256=sha256(blob).hexdigest())


def collect_registered_weo(fetch_bytes, *, releases, retrieved_at):
    records, sources, errors = [], [], []
    day = date.fromisoformat(retrieved_at[:10])
    if type(releases) is not list or len(releases) > 8:
        raise ValueError("invalid_weo_release_catalogue")
    for release in releases:
        published = date.fromisoformat(release["published"])
        if published > day:
            continue
        try:
            parsers = {"weo_statistical_tables": parse_weo_statistical_tables,
                       "weo_fiscal_datamapper": parse_weo_fiscal_datamapper}
            parser = parsers.get(release.get("format"))
            if parser is None:
                raise ValueError("unsupported_registered_weo_format")
            blob = fetch_bytes(release["dataset_url"], max_bytes=release["max_bytes"])
            parsed = parser(blob, release=release, retrieved_at=retrieved_at)
            records.extend(parsed)
            sources.append({"provider": "IMF", "edition": release["edition"],
                            "published": release["published"], "information_cutoff": release["information_cutoff"],
                            "source_url": release["source_url"], "dataset_url": release["dataset_url"],
                            "sha256": sha256(blob).hexdigest(), "records": len(parsed), "status": "verified", "retrieved_at": retrieved_at})
        except Exception as exc:
            errors.append({"source": "IMF WEO " + release["edition"], "error": type(exc).__name__,
                           "detail": str(exc)[:180], "published": release["published"],
                           "source_url": release["source_url"], "status": "new_release_not_verified"})
    return {"forecast_archive": records, "sources": sources, "errors": errors}

# DataMapper is a transport for the same WEO edition, not a second forecaster.
# Only the four missing fiscal economies are admitted from this route. The API
# currently returns a wider panel even when country/period filters are requested.
FISCAL_ECONOMIES = {
    "KOR": ("KR", 1, "CG_LG_SS:accrual",
            "Central and local government, including social security funds; accrual basis. The overall balance differs from Korea's managed fiscal balance.",
            "中央与地方政府，含社会保障基金；权责发生制。整体收支不同于韩国的管理财政收支。"),
    "TWN": ("TW", 1, "CG_LG:cash",
            "Central and local government; cash basis. General-government coverage is not the whole public sector.",
            "中央与地方政府；现金收付制。政府部门口径不等于整个公共部门。"),
    "IND": ("IN", 4, "CG_SG:cash",
            "Central and state governments; cash basis, April–March fiscal years. This is not the central government's budget deficit target.",
            "中央与邦政府；现金收付制，财年为4月至次年3月。该口径不同于中央政府预算赤字目标。"),
    "AUS": ("AU", 1, "CG_SG_LG:accrual",
            "Central, state and local government; accrual basis. WEO reports calendar years here, distinct from Australian July–June budget years.",
            "中央、州及地方政府；权责发生制。此处WEO采用自然年，与澳大利亚7月至次年6月的预算财年不同。"),
}
FISCAL_INDICATORS = {
    "GGXCNL_NGDP": ("fiscal_balance", "General government net lending/borrowing"),
    "GGXWDG_NGDP": ("government_debt", "General government gross debt"),
}
WEO_DATABASE_DOCUMENTATION = (
    "https://data.imf.org/-/media/iData/External-Storage/Documents/"
    "C4182C5C54794FC48892DE8F6C74FF82/en/October-2026-WEO-Database-Appendix.pdf"
)
WEO_FISCAL_RELEASES = [
    {**WEO_OCTOBER_2026, "format": "weo_fiscal_datamapper",
     "parser_version": "weo_fiscal_datamapper_v1", "max_bytes": 2_000_000,
     "dataset_url": "https://www.imf.org/external/datamapper/api/v2/" + indicator
                    + "/KOR/TWN/IND/AUS?periods=2026,2027",
     "documentation_url": WEO_DATABASE_DOCUMENTATION,
     "indicator_id": indicator}
    for indicator in FISCAL_INDICATORS
]


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("weo_datamapper_duplicate_key")
        result[key] = value
    return result


def _invalid_json_number(value):
    raise ValueError("weo_datamapper_nonfinite_number")


def parse_weo_fiscal_datamapper(blob, *, release, retrieved_at):
    """Validate edition, measure, government coverage and exact annual periods."""
    import json
    import math

    if type(release) is not dict:
        raise ValueError("unregistered_weo_fiscal_contract")
    indicator = release.get("indicator_id")
    registered = next((r for r in WEO_FISCAL_RELEASES if r["indicator_id"] == indicator), None)
    if registered is None or any(release.get(k) != v for k, v in registered.items()):
        raise ValueError("unregistered_weo_fiscal_contract")
    if not isinstance(blob, bytes) or not 0 < len(blob) <= registered["max_bytes"]:
        raise ValueError("weo_datamapper_size_or_format")
    try:
        data = json.loads(blob, object_pairs_hook=_unique_json_object,
                          parse_constant=_invalid_json_number)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("weo_datamapper_invalid_json") from exc
    if type(data) is not dict or data.get("api") != {"version": "2", "output-method": "json"}:
        raise ValueError("weo_datamapper_api_changed")
    indicators, values = data.get("indicators"), data.get("values")
    if (type(indicators) is not dict or set(indicators) != {indicator}
            or type(values) is not dict or indicator not in values
            or set(values) - {indicator, ""} or values.get("") is not None):
        # Original v2 responses include an unnamed null series. Only that
        # observed null placeholder is harmless; another measure is not.
        raise ValueError("weo_datamapper_measure_changed")
    metadata = indicators[indicator]
    series_id, label = FISCAL_INDICATORS[indicator]
    expected = {"label": label, "source": "World Economic Outlook (October 2026)",
                "dataset": "WEO", "unit": "Percent of GDP", "projection-year": 2026}
    if (type(metadata) is not dict or any(metadata.get(k) != v for k, v in expected.items())
            or type(metadata.get("projection-year")) is not int):
        raise ValueError("weo_datamapper_edition_or_unit_changed")
    # The server's last-modified field is transport metadata. It never becomes
    # the publication date, statistical cutoff or first observation clock.
    panel = values[indicator]
    if type(panel) is not dict:
        raise ValueError("weo_datamapper_missing_panel")
    records = []
    for iso, (cc, month, coverage, note_en, note_zh) in FISCAL_ECONOMIES.items():
        row = panel.get(iso)
        if type(row) is not dict:
            raise ValueError("weo_datamapper_country_missing:" + cc)
        selected = {year: row.get(year) for year in ("2026", "2027")}
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in selected.values()):
            raise ValueError("weo_datamapper_period_missing_or_invalid:" + cc)
        basis = "fiscal_year" if month != 1 else "calendar_year"
        raw = {**registered, "cc": cc, "series_id": series_id, "kind": "sourced_forecast",
               "unit": "percent_gdp", "period_basis": basis, "fiscal_start_month": month,
               "definition_id": indicator + ":general_government:" + coverage + ":" + basis,
               "values": selected, "actual_through": None, "precision": 1,
               "coverage_note": note_en, "coverage_note_zh": note_zh,
               "source_sha256": sha256(blob).hexdigest(),
               "source_row_sha256": sha256(json.dumps(
                   {"indicator": indicator, "economy": iso, "values": selected},
                   sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest(),
               "source_table": "DataMapper · " + indicator,
               "retrieved_at": retrieved_at}
        record = normalize_publication(raw, observed_at=retrieved_at)
        if record is None:
            raise ValueError("weo_datamapper_admission_failed:" + cc)
        records.append(record)
    return records
