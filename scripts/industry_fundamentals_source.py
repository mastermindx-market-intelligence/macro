#!/usr/bin/env python3
"""Bounded acquisition of public author-shared lagged characteristics.

This is an offline research adapter, not a source warehouse or PIT attestation.
No post-2002 characteristic value is converted to a number. Raw inputs remain
local; publish aggregate provenance only. No downloaded code is executed.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import zipfile

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests

URL = "https://dachxiu.chicagobooth.edu/download/datashare.zip"
MAX_ARCHIVE_BYTES = 2_000_000_000
MAX_SELECTED_BYTES = 768_000_000
CUTOFF = "20021231"
COLUMNS = ("permno", "DATE", "mvel1", "mom1m", "mom6m", "mom12m", "idiovol",
           "roaq", "roavol", "roeq", "nincr", "sgr", "rsup", "gma", "cashdebt", "lev", "operprof", "sic2")
MISSING_TOKENS = {"", "nan", "NaN", "NA", "N/A", ".", "null", "None"}


def file_hash(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()


def acquire(path: Path) -> dict:
    if path.exists():
        if path.stat().st_size > MAX_ARCHIVE_BYTES: raise ValueError("existing archive exceeds size guard")
        if not zipfile.is_zipfile(path): raise ValueError("existing source is not a ZIP; reconcile before reuse")
        return {"url": URL, "archive_bytes": path.stat().st_size, "archive_sha256": file_hash(path), "reused": True}
    partial = path.with_suffix(".part")
    if partial.exists(): raise FileExistsError("partial download exists; no automatic replay or overwrite")
    if shutil.disk_usage(path.parent).free < MAX_ARCHIVE_BYTES + MAX_SELECTED_BYTES:
        raise OSError("insufficient free space in the admitted research workspace")
    received = 0; h = sha256(); next_report = 256 * 1024 * 1024
    with requests.get(URL, headers={"Accept-Encoding": "identity"}, stream=True, timeout=(10, 30)) as response:
        response.raise_for_status()
        declared = int(response.headers.get("Content-Length", "0"))
        if not 0 < declared <= MAX_ARCHIVE_BYTES: raise ValueError("missing or excessive declared archive length")
        metadata = {"url": URL, "declared_bytes": declared, "last_modified": response.headers.get("Last-Modified"),
                    "etag": response.headers.get("ETag"), "reused": False}
        with partial.open("xb") as output:
            for chunk in response.iter_content(4 * 1024 * 1024):
                if not chunk: continue
                received += len(chunk)
                if received > declared or received > MAX_ARCHIVE_BYTES: raise ValueError("archive exceeded declared length")
                output.write(chunk); h.update(chunk)
                if received >= next_report:
                    print("DOWNLOADED_BYTES", received, flush=True); next_report += 256 * 1024 * 1024
        if received != declared: raise ValueError("incomplete source download")
    if not zipfile.is_zipfile(partial): raise ValueError("download is not a valid ZIP archive")
    os.replace(partial, path)
    return metadata | {"archive_bytes": received, "archive_sha256": h.hexdigest()}


def extract(archive_path: Path, destination: Path, chunk_size: int = 50000) -> dict:
    if destination.exists(): raise FileExistsError("preserve the existing selected panel")
    partial = destination.with_suffix(".parquet.part")
    if partial.exists(): raise FileExistsError("reconcile existing partial extraction")
    schema = pa.schema([pa.field("source_date", pa.timestamp("ns")), pa.field("permno", pa.int64()),
                        pa.field("sic2", pa.int32())] + [pa.field(c, pa.float64()) for c in COLUMNS if c not in {"DATE", "permno", "sic2"}])
    total = retained = invalid_dates = 0
    counts = {c: 0 for c in COLUMNS if c != "DATE"}
    invalid_numeric = {c: 0 for c in COLUMNS if c != "DATE"}
    first = last = None
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if "datashare.csv" not in names or "readme.txt" not in names:
            raise ValueError("author source members missing")
        info = archive.getinfo("datashare.csv")
        if info.file_size > 5_000_000_000: raise ValueError("unexpected uncompressed size")
        readme = archive.read("readme.txt")
        with archive.open("datashare.csv") as stream, pq.ParquetWriter(partial, schema, compression="zstd") as writer:
            chunks = pd.read_csv(stream, usecols=list(COLUMNS), dtype="string", keep_default_na=False, chunksize=chunk_size)
            for chunk in chunks:
                total += len(chunk)
                dates = chunk.DATE.str.strip()
                valid_dates = dates.str.fullmatch(r"\d{8}")
                invalid_dates += int((~valid_dates).sum())
                selected = chunk.loc[valid_dates & dates.le(CUTOFF)].copy()
                if selected.empty: continue
                # This is the first numerical conversion; later-date rows were removed.
                output = pd.DataFrame({"source_date": pd.to_datetime(selected.DATE, format="%Y%m%d", errors="raise")})
                for column in COLUMNS:
                    if column == "DATE": continue
                    text = selected[column].str.strip()
                    numeric = pd.to_numeric(text, errors="coerce").astype(float)
                    nonfinite = ~np.isfinite(numeric)
                    invalid_numeric[column] += int((nonfinite & ~text.isin(MISSING_TOKENS)).sum())
                    numeric[nonfinite] = np.nan
                    if column in {"permno", "sic2"}:
                        wrong = numeric.notna() & numeric.ne(numeric.round())
                        invalid_numeric[column] += int(wrong.sum()); numeric[wrong] = np.nan
                        output[column] = numeric.astype("Int64" if column == "permno" else "Int32")
                    else: output[column] = numeric
                    counts[column] += int(output[column].notna().sum())
                retained += len(output)
                start, end = output.source_date.min(), output.source_date.max()
                first = start if first is None else min(first, start)
                last = end if last is None else max(last, end)
                table = pa.Table.from_pandas(output, schema=schema, preserve_index=False, safe=True)
                writer.write_table(table)
                if partial.stat().st_size > MAX_SELECTED_BYTES:
                    raise ValueError("selected panel exceeded size guard")
                if total % (chunk_size * 10) == 0:
                    print("ROWS_SCANNED", total, "PRE2003_RETAINED", retained, flush=True)
    if retained == 0: raise ValueError("no pre-2003 records")
    if last > pd.Timestamp("2002-12-31"): raise AssertionError("date fence violated")
    if partial.stat().st_size > MAX_SELECTED_BYTES: raise ValueError("selected panel exceeds final size guard")
    os.replace(partial, destination)
    metadata = pq.ParquetFile(destination).metadata
    if metadata.num_rows != retained: raise AssertionError("Parquet row-count mismatch")
    return {"source_rows_scanned_as_strings": total, "pre2003_rows": retained,
            "first_source_date": str(first.date()), "last_source_date": str(last.date()),
            "invalid_date_strings": invalid_dates, "numeric_conversion_after_date_filter": True,
            "numeric_nonmissing": counts, "invalid_nonempty_numeric_strings": invalid_numeric,
            "readme_sha256": sha256(readme).hexdigest(), "selected_bytes": destination.stat().st_size,
            "selected_sha256": file_hash(destination), "schema": str(schema),
            "evidence_mode": "RECONSTRUCTED_AUTHOR_LAGGED_CHARACTERISTICS",
            "return_data_claim": "NO_CRSP_RETURN_SERIES_INCLUDED; MOM1M_PROXY_NOT_YET_QUALIFIED",
            "commercial_production_rights_claim": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args(); root = args.output_directory.resolve(); root.mkdir(parents=True, exist_ok=True)
    result_path = root / "FUNDAMENTAL_SOURCE_MANIFEST.json"
    if result_path.exists(): raise FileExistsError("source manifest already exists; inspect before another run")
    acquired = acquire(root / "datashare.zip")
    print("ARCHIVE", json.dumps(acquired), flush=True)
    selected = extract(root / "datashare.zip", root / "gkx_pre2003_selected.parquet")
    result = {"schema": "prophet.industry_fundamental_source.v1", **acquired, **selected,
              "script_sha256": file_hash(Path(__file__))}
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print("MANIFEST", json.dumps(result), flush=True)


if __name__ == "__main__": main()
