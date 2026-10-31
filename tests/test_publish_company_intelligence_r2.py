from __future__ import annotations

import io
from hashlib import sha256
import json
import traceback

import pytest

from engine.company_intelligence.views import build_bundle, write_generation
from scripts.publish_company_intelligence_r2 import ImmutableAddressIntegrityError, _publish_immutable_object, publish


class _FakeR2:
    def __init__(self, remote_manifest: dict | None = None, objects: dict[str, tuple[bytes, dict]] | None = None) -> None:
        self.remote_manifest = remote_manifest
        self.objects = dict(objects or {})
        self.puts: list[tuple[str, dict]] = []

    def get_object(self, *, Bucket, Key):
        if Key == "company_intelligence/manifest.json" and self.remote_manifest is not None:
            return {"Body": io.BytesIO(json.dumps(self.remote_manifest).encode()), "ETag": "prior-etag"}
        if Key in self.objects:
            body, _metadata = self.objects[Key]
            return {"Body": io.BytesIO(body)}
        if Key == "company_intelligence/manifest.json":
            raise RuntimeError("missing")
        raise RuntimeError("missing")

    def head_object(self, *, Bucket, Key):
        if Key in self.objects:
            body, metadata = self.objects[Key]
            return {"Metadata": metadata, "ContentLength": len(body)}
        raise RuntimeError("missing")

    def put_object(self, **kwargs):
        if kwargs.get("IfNoneMatch") == "*" and kwargs["Key"] in self.objects:
            raise _PreconditionFailed()
        self.puts.append((kwargs["Key"], kwargs))
        body = kwargs["Body"]
        assert isinstance(body, bytes)
        self.objects[kwargs["Key"]] = (body, dict(kwargs.get("Metadata") or {}))


class _PreconditionFailed(RuntimeError):
    response = {"Error": {"Code": "PreconditionFailed"}, "ResponseMetadata": {"HTTPStatusCode": 412}}


def _tree(tmp_path):
    history = [{
        "document_ticker": "AAPL", "fiscal_year": 2026, "fiscal_quarter": 1,
        "call_date": "2026-01-29", "earnings_call_sent": 0.2,
        "raw_source_url": "https://example.test/source",
    }]
    tx = {"schema": "mastermind.tx-index/v1", "documents": [{"ticker": "AAPL", "fiscal_year": 2026, "fiscal_quarter": 1, "present": True}]}
    contexts, manifest = build_bundle(history, tx_index=tx, as_of="2026-02-02")
    write_generation(tmp_path, contexts, manifest)
    return json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))


def test_absent_credentials_is_noop(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("scripts.publish_company_intelligence_r2._client", lambda: None)
    assert publish(tmp_path) == 0


def test_payloads_and_generation_manifest_precede_mutable_marker(tmp_path) -> None:
    manifest = _tree(tmp_path)
    fake = _FakeR2()
    assert publish(tmp_path, s3=fake, bucket="bucket") == 0
    keys = [key for key, _ in fake.puts]
    assert keys[-1] == "company_intelligence/manifest.json"
    assert keys[0].endswith("/companies/AAPL.json")
    assert keys[-2].endswith("/manifest.json")
    assert fake.puts[-1][1]["Metadata"]["generation-id"] == manifest["generation_id"]


def test_last_good_manifest_shrink_rejection_stops_before_writes(tmp_path) -> None:
    _tree(tmp_path)
    fake = _FakeR2({"status": "ready", "company_count": 10, "event_count": 100})
    assert publish(tmp_path, s3=fake, bucket="bucket") == 1
    assert fake.puts == []


def test_identical_remote_root_manifest_is_safe_publish_noop(tmp_path) -> None:
    _tree(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    fake = _FakeR2(manifest)
    assert publish(tmp_path, s3=fake, bucket="bucket") == 0
    assert fake.puts == []


@pytest.mark.parametrize("relative", ["companies/AAPL.json", "manifest.json"])
def test_existing_generation_object_with_mismatched_bytes_is_hard_collision(tmp_path, relative: str) -> None:
    manifest = _tree(tmp_path)
    generation = tmp_path / "generations" / manifest["generation_id"]
    key = f"company_intelligence/generations/{manifest['generation_id']}/{relative}"
    expected_sha = (manifest["files"][relative]["sha256"] if relative.startswith("companies/") else sha256((generation / relative).read_bytes()).hexdigest())
    # A forged matching checksum must still fail: the publisher reads and
    # checks existing bytes rather than trusting mutable object metadata.
    fake = _FakeR2(objects={key: (b"not-the-immutable-object", {"sha256": expected_sha})})

    assert publish(tmp_path, s3=fake, bucket="bucket") == 1
    assert all(written_key != key for written_key, _ in fake.puts)
    assert "company_intelligence/manifest.json" not in [written_key for written_key, _ in fake.puts]


def test_existing_exact_generation_objects_are_safe_noops_before_marker_promotion(tmp_path) -> None:
    manifest = _tree(tmp_path)
    generation = tmp_path / "generations" / manifest["generation_id"]
    prefix = f"company_intelligence/generations/{manifest['generation_id']}"
    company = generation / "companies" / "AAPL.json"
    immutable_manifest = generation / "manifest.json"
    fake = _FakeR2(
        remote_manifest={"status": "ready", "company_count": 1, "event_count": 1},
        objects={
            f"{prefix}/companies/AAPL.json": (company.read_bytes(), {"sha256": manifest["files"]["companies/AAPL.json"]["sha256"]}),
            f"{prefix}/manifest.json": (immutable_manifest.read_bytes(), {"sha256": sha256(immutable_manifest.read_bytes()).hexdigest()}),
        },
    )

    assert publish(tmp_path, s3=fake, bucket="bucket") == 0
    assert [key for key, _ in fake.puts] == ["company_intelligence/manifest.json"]


class ClientError(RuntimeError):
    def __init__(self, response) -> None:
        super().__init__("DO_NOT_RETAIN https://user:password@example.test/?token=DO_NOT_RETAIN")
        self.response = response


class _FailedCreateR2(_FakeR2):
    def __init__(self, failure: Exception, *, write_before_error: bool = False) -> None:
        super().__init__({"status": "ready", "company_count": 1, "event_count": 1})
        self.failure = failure
        self.write_before_error = write_before_error
        self.attempts: list[dict] = []

    def put_object(self, **kwargs):
        self.attempts.append(kwargs)
        if self.write_before_error:
            super().put_object(**kwargs)
        raise self.failure


def test_create_error_retains_sdk_details_without_promoting_marker(tmp_path, caplog) -> None:
    _tree(tmp_path)
    fake = _FailedCreateR2(ClientError({
        "Error": {"Code": "AccessDenied", "Message": "DO_NOT_RETAIN"},
        "ResponseMetadata": {"HTTPStatusCode": 403, "HTTPHeaders": {"secret": "DO_NOT_RETAIN"}},
        "Body": "DO_NOT_RETAIN",
    }))

    assert publish(tmp_path, s3=fake, bucket="bucket") == 1
    message = next(record.message for record in caplog.records if "payload upload failed:" in record.message)
    details = json.loads(message.split("; details=", 1)[1].removesuffix(")"))
    assert details == {
        "operation": "put_object", "exception_class": "ClientError",
        "sdk_error_code": "AccessDenied", "http_status": 403,
    }
    assert "DO_NOT_RETAIN" not in caplog.text
    assert "example.test" not in caplog.text
    assert len(fake.attempts) == 1
    assert fake.attempts[0]["IfNoneMatch"] == "*"
    assert fake.objects == {}
    assert fake.remote_manifest == {"status": "ready", "company_count": 1, "event_count": 1}
    assert "root manifest not promoted" in caplog.text


@pytest.mark.parametrize("response", [
    {"Error": {"Code": "DO_NOT_RETAIN"}, "ResponseMetadata": {"HTTPStatusCode": "https://DO_NOT_RETAIN"}},
    {"Error": {"Code": "AccessDenied\nDO_NOT_RETAIN"}, "ResponseMetadata": {"HTTPStatusCode": True}},
    {"Error": {"Code": {"secret": "DO_NOT_RETAIN"}}, "ResponseMetadata": {"HTTPStatusCode": 403.5}},
    {"Error": "DO_NOT_RETAIN", "ResponseMetadata": "DO_NOT_RETAIN"},
    "DO_NOT_RETAIN",
])
def test_create_diagnostics_reject_untrusted_metadata_and_exception_names(response) -> None:
    unsafe_class = type("DO_NOT_RETAIN", (ClientError,), {})
    fake = _FailedCreateR2(unsafe_class(response))
    key = "company_intelligence/generations/test/companies/AAPL.json"

    with pytest.raises(ImmutableAddressIntegrityError) as caught:
        _publish_immutable_object(fake, "bucket", key, b"payload", sha256(b"payload").hexdigest(), dry_run=False)

    rendered = "".join(traceback.format_exception(caught.value))
    assert "DO_NOT_RETAIN" not in rendered
    assert "example.test" not in rendered
    details = json.loads(str(caught.value).split("; details=", 1)[1])
    assert details == {
        "operation": "put_object", "exception_class": "unavailable",
        "sdk_error_code": "unavailable", "http_status": "unavailable",
    }
    assert caught.value.__cause__ is None
    assert len(fake.attempts) == 1
    assert fake.objects == {}


def test_transport_error_retains_class_without_raw_message() -> None:
    fake = _FailedCreateR2(TimeoutError("DO_NOT_RETAIN"))
    with pytest.raises(ImmutableAddressIntegrityError) as caught:
        _publish_immutable_object(fake, "bucket", "company_intelligence/generations/test/object.json",
                                  b"payload", sha256(b"payload").hexdigest(), dry_run=False)
    details = json.loads(str(caught.value).split("; details=", 1)[1])
    assert details == {
        "operation": "put_object", "exception_class": "TimeoutError",
        "sdk_error_code": "unavailable", "http_status": "unavailable",
    }
    assert "DO_NOT_RETAIN" not in "".join(traceback.format_exception(caught.value))
    assert len(fake.attempts) == 1


def test_write_then_error_preserves_unknown_outcome_without_retry_or_promotion(tmp_path, caplog) -> None:
    _tree(tmp_path)
    fake = _FailedCreateR2(ClientError({
        "Error": {"Code": "InternalError"}, "ResponseMetadata": {"HTTPStatusCode": 500},
    }), write_before_error=True)

    assert publish(tmp_path, s3=fake, bucket="bucket") == 1
    assert len(fake.attempts) == 1
    key = fake.attempts[0]["Key"]
    assert key.endswith("/companies/AAPL.json")
    assert fake.objects[key][0] == fake.attempts[0]["Body"]
    assert "company_intelligence/manifest.json" not in fake.objects
    assert all(not written.endswith("/manifest.json") for written, _ in fake.puts)
    assert fake.remote_manifest == {"status": "ready", "company_count": 1, "event_count": 1}
    assert '"sdk_error_code": "InternalError"' in caplog.text
    assert "DO_NOT_RETAIN" not in caplog.text


def test_precondition_race_still_requires_exact_existing_bytes() -> None:
    class _CompetingCreate(_FakeR2):
        def put_object(self, **kwargs):
            super().put_object(**kwargs)
            raise _PreconditionFailed()

    fake = _CompetingCreate()
    _publish_immutable_object(fake, "bucket", "company_intelligence/generations/test/object.json",
                              b"payload", sha256(b"payload").hexdigest(), dry_run=False)
    assert len(fake.puts) == 1
    assert fake.puts[0][1]["IfNoneMatch"] == "*"
