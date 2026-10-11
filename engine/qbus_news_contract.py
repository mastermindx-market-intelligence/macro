"""Provider-neutral immutable news revision contract for qbus.

Pure leaf module: no network, filesystem, configuration, or ambient clock reads.
Provider payloads are normalized into source-owned revision observations. The
contract deliberately keeps provider identity/clocks separate from delivery route
and from our receipt time so downstream reducers can remain PIT-honest.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
from typing import Mapping

SCHEMA = "qbus.news_revision.v1"
SUPPORTED_TRANSPORTS = (
    "benzinga_ws",
    "benzinga_rest",
    "massive_benzinga_v2",
    "alpaca_rest",
    "alpaca_ws",
)
MAX_TITLE_CHARS = 4096
MAX_URL_CHARS = 8192
MAX_TEASER_CHARS = 16384
MAX_BODY_BYTES = 5_000_000
MAX_COLLECTION_ITEMS = 512
MAX_TOKEN_CHARS = 512


class NewsContractError(ValueError):
    """Sanitized, stable normalization refusal."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"qbus_news_contract:{code}")


@dataclass(frozen=True, slots=True)
class NewsRevision:
    schema: str
    source: str
    source_item_id: str
    transport: str
    message_id: str | None
    action: str
    action_explicit: bool
    published_at: datetime | None
    updated_at: datetime | None
    source_event_at: datetime | None
    received_at: datetime
    version_at: datetime
    version_clock_domain: str
    title: str
    url: str
    teaser: str
    provider_tickers: tuple[str, ...]
    channels: tuple[str, ...]
    tags: tuple[str, ...]
    body_sha256: str
    content_hash: str
    revision_id: str
    clock_anomalies: tuple[str, ...]


def _aware_utc(value: datetime, code: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise NewsContractError(code)
    return value.astimezone(timezone.utc)


def _parse_clock(value: object, field: str, *, required: bool) -> datetime | None:
    if value is None or value == "":
        if required:
            raise NewsContractError(f"missing_{field}")
        return None
    if isinstance(value, datetime):
        return _aware_utc(value, f"invalid_{field}")
    if not isinstance(value, str):
        raise NewsContractError(f"invalid_{field}")
    try:
        text = value.strip()
        if not text:
            raise ValueError
        if "T" in text or text.endswith("Z"):
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            parsed = parsedate_to_datetime(text)
        return _aware_utc(parsed, f"invalid_{field}")
    except NewsContractError:
        raise
    except Exception as exc:
        raise NewsContractError(f"invalid_{field}") from exc


def _source_id(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise NewsContractError("invalid_source_item_id")
    out = str(value).strip()
    if not out or len(out) > 128:
        raise NewsContractError("invalid_source_item_id")
    return out


def _message_id(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise NewsContractError("invalid_message_id")
    out = str(value).strip()
    if not out or len(out) > 256:
        raise NewsContractError("invalid_message_id")
    return out


def _text(value: object, field: str, cap: int, *, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise NewsContractError(f"invalid_{field}")
    out = value.strip()
    if required and not out:
        raise NewsContractError(f"missing_{field}")
    if len(out) > cap:
        raise NewsContractError(f"{field}_too_large")
    return out


def _body_hash(value: object) -> str:
    if value is None or value == "":
        return ""
    if not isinstance(value, str):
        raise NewsContractError("invalid_body")
    raw = value.encode("utf-8")
    if len(raw) > MAX_BODY_BYTES:
        raise NewsContractError("body_too_large")
    return hashlib.sha256(raw).hexdigest()


def _names(value: object, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise NewsContractError(f"invalid_{field}")
    if len(value) > MAX_COLLECTION_ITEMS:
        raise NewsContractError(f"{field}_too_large")
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        if isinstance(item, Mapping):
            item = item.get("name")
        if not isinstance(item, str):
            raise NewsContractError(f"invalid_{field}")
        token = item.strip()
        if not token:
            continue
        if len(token) > MAX_TOKEN_CHARS:
            raise NewsContractError(f"{field}_too_large")
        if token not in seen:
            seen.add(token)
            out.append(token)
    return tuple(out)


def _action(value: object) -> str:
    if not isinstance(value, str):
        raise NewsContractError("unsupported_action")
    token = value.strip().lower()
    if token in ("created", "updated"):
        return token
    if token in ("deleted", "removed"):
        return "removed"
    raise NewsContractError("unsupported_action")


def _content_digest(*, title: str, url: str, teaser: str, body_sha256: str,
                    tickers: tuple[str, ...], channels: tuple[str, ...],
                    tags: tuple[str, ...]) -> str:
    payload = {
        "body_sha256": body_sha256,
        "channels": channels,
        "tags": tags,
        "teaser": teaser,
        "tickers": tickers,
        "title": title,
        "url": url,
    }
    raw = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _revision_id(*, source_item_id: str, removed: bool, content_hash: str,
                 version_at: datetime, version_clock_domain: str) -> str:
    basis = "|".join((
        "benzinga",
        source_item_id,
        "removed" if removed else "article",
        content_hash,
        version_clock_domain,
        version_at.isoformat(),
    ))
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]


def _clock_anomalies(published: datetime | None, updated: datetime | None,
                     event_at: datetime | None) -> tuple[str, ...]:
    out: list[str] = []
    if published is not None and updated is not None and updated < published:
        out.append("updated_before_published")
    if published is not None and event_at is not None and event_at < published:
        out.append("event_before_published")
    return tuple(out)


def _build(*, source_item_id: str, transport: str, message_id: str | None,
           action: str, action_explicit: bool, published_at: datetime | None,
           updated_at: datetime | None, source_event_at: datetime | None,
           received_at: datetime, version_at: datetime,
           version_clock_domain: str, content: Mapping[str, object] | None,
           massive: bool = False) -> NewsRevision:
    removed = action == "removed"
    content = content or {}
    title = _text(
        content.get("title"), "title", MAX_TITLE_CHARS, required=not removed
    )
    url = _text(content.get("url"), "url", MAX_URL_CHARS)
    teaser = _text(content.get("teaser"), "teaser", MAX_TEASER_CHARS)
    body_sha256 = _body_hash(content.get("body"))
    tickers = _names(
        content.get("tickers") if massive else content.get("stocks"),
        "provider_tickers",
    )
    channels = _names(content.get("channels"), "channels")
    tags = _names(content.get("tags"), "tags")
    content_hash = _content_digest(
        title=title,
        url=url,
        teaser=teaser,
        body_sha256=body_sha256,
        tickers=tickers,
        channels=channels,
        tags=tags,
    )
    revision_id = _revision_id(
        source_item_id=source_item_id,
        removed=removed,
        content_hash=content_hash,
        version_at=version_at,
        version_clock_domain=version_clock_domain,
    )
    return NewsRevision(
        schema=SCHEMA,
        source="benzinga",
        source_item_id=source_item_id,
        transport=transport,
        message_id=message_id,
        action=action,
        action_explicit=action_explicit,
        published_at=published_at,
        updated_at=updated_at,
        source_event_at=source_event_at,
        received_at=received_at,
        version_at=version_at,
        version_clock_domain=version_clock_domain,
        title=title,
        url=url,
        teaser=teaser,
        provider_tickers=tickers,
        channels=channels,
        tags=tags,
        body_sha256=body_sha256,
        content_hash=content_hash,
        revision_id=revision_id,
        clock_anomalies=_clock_anomalies(published_at, updated_at, source_event_at),
    )


def normalize_news(payload: Mapping[str, object], *, transport: str,
                   received_at: datetime) -> NewsRevision:
    """Normalize one provider observation without network/filesystem/clock access."""
    if transport not in SUPPORTED_TRANSPORTS:
        raise NewsContractError("unsupported_transport")
    if not isinstance(payload, Mapping):
        raise NewsContractError("invalid_payload")
    received = _aware_utc(received_at, "received_at_not_aware")

    if transport == "benzinga_ws":
        if payload.get("kind") != "news":
            raise NewsContractError("invalid_kind")
        message_id = _message_id(payload.get("id"))
        data = payload.get("data")
        if not isinstance(data, Mapping):
            raise NewsContractError("invalid_data")
        action = _action(data.get("action"))
        source_item_id = _source_id(data.get("id"))
        event_at = _parse_clock(
            data.get("timestamp"), "source_event_at", required=True
        )
        content = data.get("content")
        if content is not None and not isinstance(content, Mapping):
            raise NewsContractError("invalid_content")
        if action != "removed" and not isinstance(content, Mapping):
            raise NewsContractError("missing_content")
        if isinstance(content, Mapping) and content.get("id") not in (None, ""):
            content_id = _source_id(content.get("id"))
            if content_id != source_item_id:
                raise NewsContractError("source_item_id_mismatch")
        published = _parse_clock(
            content.get("created") if isinstance(content, Mapping) else None,
            "published_at",
            required=action != "removed",
        )
        updated = _parse_clock(
            content.get("updated") if isinstance(content, Mapping) else None,
            "updated_at",
            required=action != "removed",
        )
        version_at = updated or event_at
        domain = (
            "benzinga_article_updated"
            if updated is not None
            else "benzinga_stream_event"
        )
        return _build(
            source_item_id=source_item_id,
            transport=transport,
            message_id=message_id,
            action=action,
            action_explicit=True,
            published_at=published,
            updated_at=updated,
            source_event_at=event_at,
            received_at=received,
            version_at=version_at,
            version_clock_domain=domain,
            content=content if isinstance(content, Mapping) else None,
        )

    if transport == "benzinga_rest":
        source_item_id = _source_id(payload.get("id"))
        explicit_action = payload.get("action") not in (None, "")
        action = _action(payload.get("action")) if explicit_action else "updated"
        published = _parse_clock(
            payload.get("created"), "published_at", required=action != "removed"
        )
        updated = _parse_clock(
            payload.get("updated"), "updated_at", required=action != "removed"
        )
        if action == "removed":
            version_at = updated or published or received
            domain = (
                "benzinga_article_updated"
                if updated is not None
                else "benzinga_rest_observed"
            )
        else:
            version_at = updated
            domain = "benzinga_article_updated"
        return _build(
            source_item_id=source_item_id,
            transport=transport,
            message_id=None,
            action=action,
            action_explicit=explicit_action,
            published_at=published,
            updated_at=updated,
            source_event_at=updated,
            received_at=received,
            version_at=version_at,
            version_clock_domain=domain,
            content=payload,
        )

    if transport in ("alpaca_rest", "alpaca_ws"):
        # Alpaca re-distributes Benzinga news: the content source stays
        # "benzinga"; only the transport/provider differs. No body field is
        # mapped so REST (include_content=false) and WS items of the same
        # article hash to the identical content_hash and revision_id.
        if str(payload.get("source") or "").strip().lower() != "benzinga":
            raise NewsContractError("unsupported_source")
        source_item_id = _source_id(payload.get("id"))
        published = _parse_clock(
            payload.get("created_at"), "published_at", required=True
        )
        updated = _parse_clock(
            payload.get("updated_at"), "updated_at", required=True
        )
        return _build(
            source_item_id=source_item_id,
            transport=transport,
            message_id=None,
            action="updated",
            action_explicit=False,
            published_at=published,
            updated_at=updated,
            source_event_at=updated,
            received_at=received,
            version_at=updated,
            version_clock_domain="benzinga_article_updated",
            content={
                "title": payload.get("headline"),
                "teaser": payload.get("summary"),
                "url": payload.get("url") or None,
                "stocks": payload.get("symbols"),
            },
        )

    source_item_id = _source_id(payload.get("benzinga_id"))
    published = _parse_clock(
        payload.get("published"), "published_at", required=True
    )
    updated = _parse_clock(
        payload.get("last_updated"), "updated_at", required=True
    )
    return _build(
        source_item_id=source_item_id,
        transport=transport,
        message_id=None,
        action="updated",
        action_explicit=False,
        published_at=published,
        updated_at=updated,
        source_event_at=updated,
        received_at=received,
        version_at=updated,
        version_clock_domain="massive_benzinga_system_updated",
        content=payload,
        massive=True,
    )
