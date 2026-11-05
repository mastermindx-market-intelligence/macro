"""Synthetic tests for the Massive-distributed Benzinga supplement."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
import requests

from collectors import massive_benzinga_news


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 15, 0, tzinfo=UTC)


def _item(item_id=1, *, title=None, ticker="NVDA"):
    return {
        "benzinga_id": item_id,
        "published": "2026-10-05T14:59:00Z",
        "last_updated": "2026-10-05T14:59:01Z",
        "title": title or f"Story {item_id}",
        "teaser": f"Teaser {item_id}",
        "body": f"<p>Body {item_id}</p>",
        "url": f"https://www.benzinga.com/news/{item_id}",
        "channels": ["news"],
        "tags": ["breaking"],
        "tickers": [ticker],
    }


class FakeResponse:
    def __init__(self, payload, *, status=200):
        self.payload = payload
        self.status_code = status
        self.headers = {}

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            exc = requests.HTTPError(f"HTTP {self.status_code}")
            exc.response = self
            raise exc


class FakeHttp:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, *, params, headers, timeout):
        self.calls.append(
            {
                "url": url,
                "params": dict(params),
                "headers": dict(headers),
                "timeout": timeout,
            }
        )
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)


def test_fetch_pages_normalizes_results_and_marks_supplemental_not_correction_complete():
    http = FakeHttp(
        [
            FakeResponse(
                {
                    "status": "OK",
                    "results": [_item(1)],
                    "next_url": "https://api.massive.com/benzinga/v2/news?cursor=abc",
                    "request_id": "r1",
                }
            ),
            FakeResponse(
                {
                    "status": "OK",
                    "results": [_item(2, ticker="AMD")],
                    "request_id": "r2",
                }
            ),
        ]
    )
    client = massive_benzinga_news.MassiveBenzingaNewsClient(
        api_key="NOT-REAL",
        http_get=http,
        limit=100,
        clock=lambda: T0,
    )

    batch = client.fetch_latest()

    assert [r.source_item_id for r in batch.revisions] == ["1", "2"]
    assert all(r.source == "benzinga" for r in batch.revisions)
    assert all(r.transport == "massive_benzinga_v2" for r in batch.revisions)
    assert all(r.version_clock_domain == "massive_benzinga_system_updated" for r in batch.revisions)
    assert batch.correction_complete is False
    assert batch.gap_unresolved is False
    assert batch.pages == 2
    assert batch.request_ids == ("r1", "r2")
    assert http.calls[0]["url"] == massive_benzinga_news.BASE_URL
    assert http.calls[0]["params"]["sort"] == "published.desc"
    assert http.calls[0]["params"]["limit"] == 100
    assert http.calls[0]["params"]["apiKey"] == "NOT-REAL"
    assert http.calls[1]["url"] == "https://api.massive.com/benzinga/v2/news?cursor=abc"
    assert http.calls[1]["params"]["apiKey"] == "NOT-REAL"


def test_vendor_next_url_api_key_is_removed_and_local_key_is_injected():
    http = FakeHttp(
        [
            FakeResponse(
                {
                    "status": "OK",
                    "results": [_item(1)],
                    "next_url": (
                        "https://api.massive.com/benzinga/v2/news?"
                        "cursor=abc&apiKey=ATTACKER"
                    ),
                    "request_id": "r1",
                }
            ),
            FakeResponse({"status": "OK", "results": [], "request_id": "r2"}),
        ]
    )
    client = massive_benzinga_news.MassiveBenzingaNewsClient(
        api_key="LOCAL",
        http_get=http,
        clock=lambda: T0,
    )

    client.fetch_latest()

    assert "apiKey" not in http.calls[1]["url"]
    assert "ATTACKER" not in http.calls[1]["url"]
    assert http.calls[1]["params"]["apiKey"] == "LOCAL"


@pytest.mark.parametrize(
    "next_url",
    [
        "https://evil.example/benzinga/v2/news?cursor=x",
        "http://api.massive.com/benzinga/v2/news?cursor=x",
        "https://user:pass@api.massive.com/benzinga/v2/news?cursor=x",
        "https://api.massive.com/v3/reference/news?cursor=x",
        "https://api.massive.com/benzinga/v2/news#fragment",
    ],
)
def test_next_url_must_stay_on_exact_massive_origin_and_path(next_url):
    http = FakeHttp(
        [
            FakeResponse(
                {
                    "status": "OK",
                    "results": [_item(1)],
                    "next_url": next_url,
                    "request_id": "r1",
                }
            )
        ]
    )
    client = massive_benzinga_news.MassiveBenzingaNewsClient(
        api_key="LOCAL",
        http_get=http,
        clock=lambda: T0,
    )

    with pytest.raises(massive_benzinga_news.MassiveProtocolError) as exc:
        client.fetch_latest()

    assert exc.value.code == "unsafe_next_url"
    assert len(http.calls) == 1


def test_page_budget_marks_gap_and_never_claims_complete_mirror_snapshot():
    http = FakeHttp(
        [
            FakeResponse(
                {
                    "status": "OK",
                    "results": [_item(1)],
                    "next_url": "https://api.massive.com/benzinga/v2/news?cursor=next",
                    "request_id": "r1",
                }
            )
        ]
    )
    client = massive_benzinga_news.MassiveBenzingaNewsClient(
        api_key="LOCAL",
        http_get=http,
        max_pages=1,
        clock=lambda: T0,
    )

    batch = client.fetch_latest()

    assert batch.gap_unresolved is True
    assert batch.hold_reasons == ("page_budget_exhausted",)
    assert batch.correction_complete is False
    assert batch.next_url == "https://api.massive.com/benzinga/v2/news?cursor=next"


def test_non_ok_status_and_malformed_results_refuse():
    bad_status = FakeHttp(
        [FakeResponse({"status": "ERROR", "results": [], "request_id": "r1"})]
    )
    client = massive_benzinga_news.MassiveBenzingaNewsClient(
        api_key="LOCAL", http_get=bad_status, clock=lambda: T0
    )
    with pytest.raises(massive_benzinga_news.MassiveProtocolError) as exc:
        client.fetch_latest()
    assert exc.value.code == "status_not_ok"

    bad_results = FakeHttp(
        [FakeResponse({"status": "OK", "results": {}, "request_id": "r1"})]
    )
    client = massive_benzinga_news.MassiveBenzingaNewsClient(
        api_key="LOCAL", http_get=bad_results, clock=lambda: T0
    )
    with pytest.raises(massive_benzinga_news.MassiveProtocolError) as exc:
        client.fetch_latest()
    assert exc.value.code == "results_not_array"


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_http_failures_are_sanitized_and_do_not_expose_api_key(status):
    http = FakeHttp([FakeResponse({"apiKey": "SHOULD_NOT_LEAK"}, status=status)])
    client = massive_benzinga_news.MassiveBenzingaNewsClient(
        api_key="SUPERSECRET",
        http_get=http,
        clock=lambda: T0,
    )

    with pytest.raises(massive_benzinga_news.MassiveTransportError) as exc:
        client.fetch_latest()

    assert exc.value.code == f"http_{status}"
    assert "SUPERSECRET" not in str(exc.value)
    assert "SHOULD_NOT_LEAK" not in str(exc.value)


def test_full_body_is_hashed_by_contract_but_not_retained():
    http = FakeHttp(
        [
            FakeResponse(
                {
                    "status": "OK",
                    "results": [_item(1)],
                    "request_id": "r1",
                }
            )
        ]
    )
    client = massive_benzinga_news.MassiveBenzingaNewsClient(
        api_key="LOCAL",
        http_get=http,
        clock=lambda: T0,
    )

    revision = client.fetch_latest().revisions[0]

    assert revision.body_sha256
    assert not hasattr(revision, "body")
    assert "<p>Body 1</p>" not in repr(revision)