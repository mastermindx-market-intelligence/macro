from pathlib import Path
import zipfile
import pandas as pd
import pytest
from scripts.industry_fundamentals_source import COLUMNS, extract


def _archive(path, rows):
    text = ",".join(COLUMNS) + "\n" + "\n".join(",".join(str(row.get(c, "")) for c in COLUMNS) for row in rows) + "\n"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("datashare.csv", text)
        z.writestr("readme.txt", "fixture: lag assumptions; not actual return data")


def test_date_filter_precedes_numerical_conversion(tmp_path):
    archive = tmp_path / "source.zip"; output = tmp_path / "selected.parquet"
    good = {c: 1 for c in COLUMNS}; good.update(DATE="19570329", permno="10000", sic2="20", mom1m="-0.02")
    later = {c: "DO_NOT_PARSE" for c in COLUMNS}; later["DATE"] = "20030131"
    missing = {c: "" for c in COLUMNS}; missing.update(DATE="20021231", permno="20000", sic2="35", mom1m="NOT_A_NUMBER")
    _archive(archive, [good, later, missing])
    result = extract(archive, output, chunk_size=1)
    data = pd.read_parquet(output)
    assert len(data) == 2 and result["numeric_conversion_after_date_filter"]
    assert data.source_date.max() == pd.Timestamp("2002-12-31")
    assert data.mom1m.iloc[0] == -.02 and pd.isna(data.mom1m.iloc[1])
    assert result["invalid_nonempty_numeric_strings"]["mom1m"] == 1
    assert result["invalid_nonempty_numeric_strings"]["mvel1"] == 0
    assert result["numeric_nonmissing"]["mvel1"] == 1
    with pytest.raises(FileExistsError): extract(archive, output)


def test_missing_members_and_no_eligible_data(tmp_path):
    empty = tmp_path / "bad.zip"
    with zipfile.ZipFile(empty, "w") as z: z.writestr("wrong.csv", "x")
    with pytest.raises(ValueError, match="members"): extract(empty, tmp_path / "bad.parquet")
    future = tmp_path / "future.zip"
    _archive(future, [{"DATE": "20030131"}])
    with pytest.raises(ValueError, match="no pre-2003"): extract(future, tmp_path / "future.parquet")


def test_fractional_identifiers_not_silently_rounded(tmp_path):
    source = tmp_path / "source.zip"; dest = tmp_path / "selected.parquet"
    _archive(source, [{"DATE": "20000131", "permno": "10000.5", "sic2": "20.2"}])
    report = extract(source, dest)
    data = pd.read_parquet(dest)
    assert data.permno.isna().all() and data.sic2.isna().all()
    assert report["invalid_nonempty_numeric_strings"]["permno"] == 1
