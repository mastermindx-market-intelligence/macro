from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path

import pandas as pd
import pytest
import pyarrow as pa
import pyarrow.parquet as pq

from lib.intl_macro_publication import read_ecb_deposit_materialization


MISSING = {
    "status": "missing",
    "series": None,
    "provenance": None,
    "materialized_identity": None,
}
FAILED = {
    "status": "failed",
    "series": None,
    "provenance": None,
    "materialized_identity": None,
}


def _materialize(
    root: Path, series: pd.Series, provenance: dict
) -> tuple[bytes, bytes]:
    directory = root / "intl_macro"
    directory.mkdir()
    artifact = directory / "ez_depo_rate.parquet"
    sidecar = directory / "provenance.json"
    series.to_frame().to_parquet(artifact)
    artifact_bytes = artifact.read_bytes()
    sidecar_bytes = json.dumps(provenance).encode()
    sidecar.write_bytes(sidecar_bytes)
    return artifact_bytes, sidecar_bytes


def _positive(root: Path) -> tuple[dict, bytes, bytes, pd.Series, dict]:
    series = pd.Series(
        [3.5, 2.5, float("nan"), 4.0],
        index=pd.DatetimeIndex(
            ["2026-10-06", "2026-10-02", "2026-10-05", "2026-10-07"], name="observed"
        ),
        dtype="float32",
        name="ez_depo_rate",
    )
    provenance = {
        "series": {
            "other_rate": {"unit": "irrelevant"},
            "ez_depo_rate": {"unit": "PCPA", "source": "ECB"},
        }
    }
    artifact_bytes, sidecar_bytes = _materialize(root, series, provenance)
    result = read_ecb_deposit_materialization(data_root=root)
    return result, artifact_bytes, sidecar_bytes, series, provenance


def test_positive_preserves_series_hashes_and_provenance(tmp_path: Path) -> None:
    result, artifact_bytes, sidecar_bytes, series, provenance = _positive(tmp_path)

    assert result["status"] == "ready"
    pd.testing.assert_series_equal(result["series"], series)
    assert result["provenance"] == provenance["series"]["ez_depo_rate"]
    assert result["materialized_identity"] == {
        "artifact_sha256": hashlib.sha256(artifact_bytes).hexdigest(),
        "provenance_sha256": hashlib.sha256(sidecar_bytes).hexdigest(),
        "column": "ez_depo_rate",
    }


def test_positive_preserves_numpy_integer_dtype_and_unsorted_duplicate_index(
    tmp_path: Path,
) -> None:
    series = pd.Series(
        [2, 1, 3],
        index=pd.Index([4, 2, 4], name="row", dtype="int16"),
        dtype="int16",
        name="ez_depo_rate",
    )
    _materialize(tmp_path, series, {"series": {"ez_depo_rate": {"unit": "PCPA"}}})

    result = read_ecb_deposit_materialization(data_root=tmp_path)

    assert result["status"] == "ready"
    pd.testing.assert_series_equal(result["series"], series)


def test_missing_artifact_is_missing(tmp_path: Path) -> None:
    directory = tmp_path / "intl_macro"
    directory.mkdir()
    (directory / "provenance.json").write_text(
        json.dumps({"series": {"ez_depo_rate": {}}})
    )

    assert read_ecb_deposit_materialization(data_root=tmp_path) == MISSING


def test_missing_sidecar_is_missing(tmp_path: Path) -> None:
    directory = tmp_path / "intl_macro"
    directory.mkdir()
    pd.Series([1.0], name="ez_depo_rate").to_frame().to_parquet(
        directory / "ez_depo_rate.parquet"
    )

    assert read_ecb_deposit_materialization(data_root=tmp_path) == MISSING


def test_missing_provenance_key_is_missing(tmp_path: Path) -> None:
    series = pd.Series([1.0], name="ez_depo_rate")
    _materialize(tmp_path, series, {"series": {"other_rate": {}}})

    assert read_ecb_deposit_materialization(data_root=tmp_path) == MISSING


def test_missing_series_root_is_missing(tmp_path: Path) -> None:
    series = pd.Series([1.0], name="ez_depo_rate")
    _materialize(tmp_path, series, {})

    assert read_ecb_deposit_materialization(data_root=tmp_path) == MISSING


def test_corrupt_json_is_failed_without_private_details(tmp_path: Path) -> None:
    series = pd.Series([1.0], name="ez_depo_rate")
    _materialize(tmp_path, series, {"series": {"ez_depo_rate": {}}})
    sidecar = tmp_path / "intl_macro" / "provenance.json"
    sidecar.write_bytes(b'{"series":')

    result = read_ecb_deposit_materialization(data_root=tmp_path)

    assert result == FAILED


@pytest.mark.parametrize(
    ("payload", "label"),
    [
        (b'{"series":{"series":1,"series":2}}', "duplicate nested key"),
        (b'{"series":{"series":NaN}}', "nonstandard constant"),
        (b'["not", "an object"]', "non-dict root"),
        (b'{"series":{"ez_depo_rate":[1,2]}}', "non-dict field"),
        (b'{"series":[1,2]}', "non-dict series mapping"),
    ],
)
def test_malformed_sidecar_is_failed(
    tmp_path: Path, payload: bytes, label: str
) -> None:
    series = pd.Series([1.0], name="ez_depo_rate")
    _materialize(tmp_path, series, {"series": {"ez_depo_rate": {}}})
    sidecar = tmp_path / "intl_macro" / "provenance.json"
    sidecar.write_bytes(payload)

    assert read_ecb_deposit_materialization(data_root=tmp_path) == FAILED


def test_wrong_and_multiple_columns_are_failed(tmp_path: Path) -> None:
    directory = tmp_path / "intl_macro"
    directory.mkdir()
    sidecar = directory / "provenance.json"
    sidecar.write_text(json.dumps({"series": {"ez_depo_rate": {}}}))
    wrong = directory / "ez_depo_rate.parquet"
    pd.Series([1.0], name="wrong").to_frame().to_parquet(wrong)
    assert read_ecb_deposit_materialization(data_root=tmp_path) == FAILED

    pd.DataFrame({"other": [1.0], "ez_depo_rate": [2.0]}).to_parquet(wrong)
    assert read_ecb_deposit_materialization(data_root=tmp_path) == FAILED


def test_multiindex_and_duplicate_columns_are_failed(tmp_path: Path) -> None:
    directory = tmp_path / "intl_macro"
    directory.mkdir()
    (directory / "provenance.json").write_text(
        json.dumps({"series": {"ez_depo_rate": {}}})
    )
    artifact = directory / "ez_depo_rate.parquet"
    pd.DataFrame.from_dict({("group", "ez_depo_rate"): [1.0]}).to_parquet(artifact)
    assert read_ecb_deposit_materialization(data_root=tmp_path) == FAILED

    schema = pa.schema(
        [
            pa.field("ez_depo_rate", pa.float64()),
            pa.field("ez_depo_rate", pa.float64()),
        ]
    )
    table = pa.Table.from_arrays([[1.0], [2.0]], schema=schema)
    pq.write_table(table, artifact)
    assert read_ecb_deposit_materialization(data_root=tmp_path) == FAILED


def test_final_symlink_directory_and_permission_failures_are_failed(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "intl_macro"
    directory.mkdir()
    series = pd.Series([1.0], name="ez_depo_rate")
    series.to_frame().to_parquet(tmp_path / "actual.parquet")
    (directory / "provenance.json").write_text(
        json.dumps({"series": {"ez_depo_rate": {}}})
    )
    artifact = directory / "ez_depo_rate.parquet"
    artifact.symlink_to(tmp_path / "actual.parquet")
    assert read_ecb_deposit_materialization(data_root=tmp_path) == FAILED

    artifact.unlink()
    artifact.mkdir()
    assert read_ecb_deposit_materialization(data_root=tmp_path) == FAILED
    artifact.rmdir()
    series.to_frame().to_parquet(artifact)
    artifact.chmod(stat.S_IRWXO)
    try:
        assert read_ecb_deposit_materialization(data_root=tmp_path) == FAILED
    finally:
        artifact.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)


def test_concurrent_fd_mutation_is_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lib import intl_macro_publication

    series = pd.Series([1.0], name="ez_depo_rate")
    _materialize(tmp_path, series, {"series": {"ez_depo_rate": {}}})
    artifact = tmp_path / "intl_macro" / "ez_depo_rate.parquet"
    original = intl_macro_publication._read_bounded

    def mutate_then_read(fd: int, limit: int) -> bytes:
        os.pwrite(fd, b"X", 0)
        return original(fd, limit)

    monkeypatch.setattr(intl_macro_publication, "_read_bounded", mutate_then_read)
    assert read_ecb_deposit_materialization(data_root=tmp_path) == FAILED


def test_path_replacement_is_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lib import intl_macro_publication

    series = pd.Series([1.0], name="ez_depo_rate")
    _materialize(tmp_path, series, {"series": {"ez_depo_rate": {}}})
    artifact = tmp_path / "intl_macro" / "ez_depo_rate.parquet"
    replacement = tmp_path / "replacement.parquet"
    pd.Series([9.0], name="ez_depo_rate").to_frame().to_parquet(replacement)
    original = intl_macro_publication._read_bounded

    def replace_then_read(fd: int, limit: int) -> bytes:
        payload = original(fd, limit)
        os.replace(replacement, artifact)
        return payload

    monkeypatch.setattr(intl_macro_publication, "_read_bounded", replace_then_read)
    assert read_ecb_deposit_materialization(data_root=tmp_path) == FAILED


def test_oversize_sources_are_failed_before_parsing(tmp_path: Path) -> None:
    directory = tmp_path / "intl_macro"
    directory.mkdir()
    (directory / "provenance.json").write_text(
        json.dumps({"series": {"ez_depo_rate": {}}})
    )
    artifact = directory / "ez_depo_rate.parquet"
    artifact.write_bytes(b"0" * (16 * 1024 * 1024 + 1))
    assert read_ecb_deposit_materialization(data_root=tmp_path) == FAILED

    series = pd.Series([1.0], name="ez_depo_rate")
    series.to_frame().to_parquet(artifact)
    prefix = b'{"padding":"'
    suffix = b'","series":{"ez_depo_rate":{}}}'
    target_length = 8 * 1024 * 1024 + 1
    payload = prefix + b"0" * (target_length - len(prefix) - len(suffix)) + suffix
    assert len(payload) == target_length
    (directory / "provenance.json").write_bytes(payload)
    assert read_ecb_deposit_materialization(data_root=tmp_path) == FAILED


def test_acquisition_makes_no_mkdir_or_outside_writes(tmp_path: Path) -> None:
    _positive(tmp_path)
    read_fd, write_fd = os.pipe()
    child_pid = os.fork()
    if child_pid == 0:
        read_open = True
        write_open = True
        try:
            os.close(read_fd)
            read_open = False
            violations: list[object] = []

            def audit(event: str, args: tuple[object, ...]) -> None:
                if event in {
                    "os.mkdir",
                    "os.remove",
                    "os.rename",
                    "os.replace",
                    "os.link",
                    "os.symlink",
                }:
                    violations.append((event, args))
                elif event == "open":
                    if len(args) == 3:
                        path, mode, _flags = args
                        if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
                            violations.append((event, path, mode))

            sys.addaudithook(audit)
            from lib.intl_macro_publication import (
                read_ecb_deposit_materialization as child_reader,
            )

            result = child_reader(data_root=tmp_path)
            exit_code = 0 if result["status"] == "ready" else 2
            if violations:
                exit_code = 3
            os.write(write_fd, repr(violations).encode())
        except BaseException:
            os.write(write_fd, b"child audit failed")
            exit_code = 4
        finally:
            if write_open:
                os.close(write_fd)
            if read_open:
                os.close(read_fd)
            os._exit(exit_code)

    try:
        os.close(write_fd)
        evidence = b""
        while True:
            chunk = os.read(read_fd, 64 * 1024)
            if not chunk:
                break
            evidence += chunk
    finally:
        os.close(read_fd)
        wait_pid, wait_status = os.waitpid(child_pid, 0)
    assert wait_pid == child_pid
    assert os.waitstatus_to_exitcode(wait_status) == 0
    assert evidence == b"[]"



def test_present_null_series_mapping_is_failed(tmp_path):
    series = pd.Series([2.5], index=pd.date_range('2026-10-06', periods=1), name='ez_depo_rate')
    _materialize(tmp_path, series, {'series': None})
    assert read_ecb_deposit_materialization(data_root=tmp_path) == FAILED


def test_fifo_is_rejected_without_waiting_for_writer(tmp_path):
    import subprocess
    root = Path(__file__).resolve().parents[1]
    directory = tmp_path / 'intl_macro'
    directory.mkdir()
    os.mkfifo(directory / 'ez_depo_rate.parquet')
    code = "from lib.intl_macro_publication import read_ecb_deposit_materialization; import sys,json; print(json.dumps(read_ecb_deposit_materialization(data_root=sys.argv[1])))"
    environment = dict(os.environ, PYTHONPATH=str(root))
    try:
        result = subprocess.run([sys.executable, '-c', code, str(tmp_path)], env=environment,
                                cwd=root, capture_output=True, text=True, timeout=15, check=True)
    except subprocess.TimeoutExpired:
        pytest.fail('reader blocked on FIFO before regular-file validation')
    assert json.loads(result.stdout) == FAILED
