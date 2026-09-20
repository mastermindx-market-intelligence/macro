"""tests/test_marketing_media_publish.py — R2 chart-PNG publish (fail-soft).

media_publish.publish_chart_png uploads a rendered PNG to the existing public R2
data plane and returns the public https URL, or None when creds are absent. ZERO
live network: the S3 client is injected as a stub. Covers env-absent → None,
empty bytes → None, the key/url construction on the public data plane, and the
happy-path put_object args.
"""
from __future__ import annotations

import pytest

_R2_ENV = ("R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")


def _clear_r2_env(monkeypatch):
    for e in _R2_ENV:
        monkeypatch.delenv(e, raising=False)


def test_chart_key_shape():
    from engine.marketing.media_publish import chart_key
    assert chart_key("2026-07-23", "chart-001") == "marketing/charts/2026-07-23/chart-001.png"
    # slashes in inputs are neutralized (no key traversal)
    assert "/" not in chart_key("a/b", "c/d").rsplit("/", 2)[-2]


def test_public_url_on_the_data_plane():
    from engine.marketing.media_publish import public_url_for_key, chart_key
    url = public_url_for_key(chart_key("2026-07-23", "chart-9"))
    assert url.startswith("https://pub-") and ".r2.dev/" in url
    assert url.endswith("/marketing/charts/2026-07-23/chart-9.png")


def test_publish_env_absent_returns_none(monkeypatch):
    from engine.marketing.media_publish import publish_chart_png, chart_key
    _clear_r2_env(monkeypatch)
    # No creds → no client → None (fail-soft, no raise).
    assert publish_chart_png(b"\x89PNG-fake-bytes", chart_key("2026-07-23", "c1")) is None


def test_publish_empty_bytes_returns_none():
    from engine.marketing.media_publish import publish_chart_png

    class _NeverCalled:
        def put_object(self, **kw):  # pragma: no cover - must not be reached
            raise AssertionError("put_object called for empty bytes")

    assert publish_chart_png(b"", "marketing/charts/x/y.png", s3=_NeverCalled()) is None


def test_publish_stub_uploads_and_returns_public_url(monkeypatch):
    from engine.marketing.media_publish import publish_chart_png, chart_key
    monkeypatch.setenv("R2_BUCKET", "research")
    calls: dict = {}

    class _StubS3:
        def put_object(self, **kw):
            calls.update(kw)

    url = publish_chart_png(b"\x89PNG payload", chart_key("2026-07-23", "chart-7"), s3=_StubS3())
    assert url is not None
    assert url.endswith("/marketing/charts/2026-07-23/chart-7.png")
    assert calls["Bucket"] == "research"
    assert calls["Key"] == "marketing/charts/2026-07-23/chart-7.png"
    assert calls["ContentType"] == "image/png"
    assert calls["Body"] == b"\x89PNG payload"


def test_publish_bucket_missing_returns_none(monkeypatch):
    from engine.marketing.media_publish import publish_chart_png

    class _StubS3:
        def put_object(self, **kw):  # pragma: no cover
            raise AssertionError("must not upload without a bucket")

    monkeypatch.delenv("R2_BUCKET", raising=False)
    # A client is injected (so creds-check is bypassed) but R2_BUCKET is unset.
    assert publish_chart_png(b"\x89PNG", "marketing/charts/x/y.png", s3=_StubS3()) is None


def test_publish_upload_error_returns_none():
    from engine.marketing.media_publish import publish_chart_png
    import os

    class _BoomS3:
        def put_object(self, **kw):
            raise RuntimeError("network down")

    os.environ["R2_BUCKET"] = "research"
    try:
        assert publish_chart_png(b"\x89PNG", "marketing/charts/x/y.png", s3=_BoomS3()) is None
    finally:
        os.environ.pop("R2_BUCKET", None)


class TestImmutablePublicAssetContract:
    def test_content_addressed_key_prevents_same_id_overwrite(self):
        from engine.marketing.media_publish import content_addressed_chart_key

        first = content_addressed_chart_key("2026-09-20", "chart-001", b"\x89PNG-one")
        same = content_addressed_chart_key("2026-09-20", "chart-001", b"\x89PNG-one")
        second = content_addressed_chart_key("2026-09-20", "chart-001", b"\x89PNG-two")
        assert first == same
        assert first != second
        assert first.startswith("marketing/charts/2026-09-20/chart-001-")
        assert first.endswith(".png")

    def test_content_addressed_key_binds_the_full_sha256(self):
        import hashlib

        from engine.marketing.media_publish import content_addressed_chart_key

        payload = b"\x89PNG-full-digest-contract"
        digest = hashlib.sha256(payload).hexdigest()
        key = content_addressed_chart_key("2026-09-20", "chart-001", payload)
        assert key == f"marketing/charts/2026-09-20/chart-001-{digest}.png"

    @pytest.mark.parametrize(
        ("status", "mime", "body", "reason"),
        [
            (403, "text/html", b"forbidden", "http_403"),
            (200, "text/html", b"\x89PNG-expected", "wrong_mime"),
            (200, "image/png", b"\x89PNG-other", "digest_mismatch"),
        ],
    )
    def test_public_verifier_rejects_unpublishable_responses(
        self, status, mime, body, reason,
    ):
        from engine.marketing.media_publish import verify_public_png

        result = verify_public_png(
            "https://pub.example/card.png", b"\x89PNG-expected",
            fetcher=lambda _url, _timeout: (status, {"content-type": mime}, body),
        )
        assert result["state"] == "public_fetch_failure"
        assert result["reason"] == reason
        assert result["media_url"] is None

    def test_public_verifier_proves_expected_bytes_mime_and_digest(self):
        from engine.marketing.media_publish import verify_public_png

        expected = b"\x89PNG-expected"
        result = verify_public_png(
            "https://pub.example/card.png", expected,
            fetcher=lambda _url, _timeout: (
                200, {"content-type": "image/png; charset=binary"}, expected,
            ),
        )
        assert result["state"] == "complete"
        assert result["media_url"] == "https://pub.example/card.png"
        assert result["observed_sha256"] == result["expected_sha256"]

    def test_ambiguous_public_timeout_does_not_trigger_a_replacement_upload(
        self, monkeypatch,
    ):
        from engine.marketing.media_publish import publish_chart_png_result

        monkeypatch.setenv("R2_BUCKET", "research")
        puts = []

        class _StubS3:
            def put_object(self, **kwargs):
                puts.append(kwargs)

        def _timeout(_url, _timeout_s):
            raise TimeoutError("public edge timed out")

        result = publish_chart_png_result(
            b"\x89PNG-expected",
            "marketing/charts/2026-09-20/chart-001-deadbeef.png",
            s3=_StubS3(), fetcher=_timeout,
        )
        assert result["media_repair"]["state"] == "public_fetch_failure"
        assert result["media_repair"]["reason"] == "fetch_error"
        assert puts == [], "a timeout is not proof that the immutable key is absent"

    def test_absent_key_uploads_once_then_requires_public_byte_proof(
        self, monkeypatch,
    ):
        from engine.marketing.media_publish import publish_chart_png_result

        monkeypatch.setenv("R2_BUCKET", "research")
        expected = b"\x89PNG-expected"
        responses = iter([
            (404, {"content-type": "text/plain"}, b"missing"),
            (200, {"content-type": "image/png"}, expected),
        ])
        puts = []

        class _StubS3:
            def put_object(self, **kwargs):
                puts.append(kwargs)

        result = publish_chart_png_result(
            expected,
            "marketing/charts/2026-09-20/chart-001-deadbeef.png",
            s3=_StubS3(), fetcher=lambda _url, _timeout: next(responses),
        )
        assert result["media_repair"]["state"] == "complete"
        assert result["media_url"].startswith("https://")
        assert result["uploaded"] is True
        assert len(puts) == 1
        assert puts[0]["Body"] == expected


    def test_identical_rerun_reuses_verified_key_without_put(self, monkeypatch):
        from engine.marketing.media_publish import publish_chart_png_result

        monkeypatch.setenv("R2_BUCKET", "research")
        expected = b"\x89PNG-expected"
        puts = []

        class _StubS3:
            def put_object(self, **kwargs):
                puts.append(kwargs)

        result = publish_chart_png_result(
            expected,
            "marketing/charts/2026-09-20/chart-001-deadbeef.png",
            s3=_StubS3(),
            fetcher=lambda _url, _timeout: (
                200, {"content-type": "image/png"}, expected,
            ),
        )
        assert result["media_repair"]["state"] == "complete"
        assert result["uploaded"] is False
        assert puts == []

    def test_publish_card_uses_the_shared_immutable_key(self, tmp_path, monkeypatch):
        from engine.marketing import chart_render, media_publish

        png = b"\x89PNG-card"
        monkeypatch.setattr(chart_render, "rasterize_svg", lambda _svg, **_kw: png)
        captured = {}

        def _publish(payload, key, **_kwargs):
            captured["payload"] = payload
            captured["key"] = key
            return {
                "media_url": "https://pub.example/card.png",
                "media_asset_key": key,
                "media_sha256": __import__("hashlib").sha256(payload).hexdigest(),
                "media_repair": {
                    "state": "complete", "reason": "public_bytes_verified",
                    "repair_process": "", "repairable": False,
                },
            }

        monkeypatch.setattr(media_publish, "publish_chart_png", _publish)
        out = media_publish.publish_card(
            '<svg width="10" height="10">$CLH</svg>',
            chart_id="chart-001", as_of="2026-09-20", root=tmp_path,
        )
        assert captured["payload"] == png
        assert captured["key"] == media_publish.content_addressed_chart_key(
            "2026-09-20", "chart-001", png,
        )
        assert out["media_asset_key"] == captured["key"]
        assert out["media_repair"]["state"] == "complete"
