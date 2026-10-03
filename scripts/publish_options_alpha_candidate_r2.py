"""Fail-closed CAS publisher for the two Options Alpha candidate objects."""

from __future__ import annotations
import base64, fcntl, hashlib, json, os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from engine.options_alpha_candidate_feed import (
    CandidateFeedContractError,
    canonical_bytes,
    validate_publication_receipt_binding,
    validate_publication_receipt_transition,
)

PAYLOAD_KEY = "options_alpha/candidate_feed.json"
RECEIPT_KEY = "options_alpha/candidate_feed.receipt.json"
JOURNAL_SCHEMA = "options.alpha_candidate_feed.publisher_transaction/v1"


class PublicationError(RuntimeError):
    pass


class PublicationConflict(PublicationError):
    pass


@dataclass(frozen=True)
class Pair:
    feed: dict[str, Any]
    payload: bytes
    receipt: dict[str, Any]
    receipt_last_modified: str
    payload_etag: str
    receipt_etag: str


def _not_found(e: Exception) -> bool:
    r = getattr(e, "response", {})
    x = r.get("Error", {}) if isinstance(r, Mapping) else {}
    return str(x.get("Code", "")).lower() in {"404", "nosuchkey", "notfound"}


def _precondition(e: Exception) -> bool:
    r = getattr(e, "response", {})
    x = r.get("Error", {}) if isinstance(r, Mapping) else {}
    return str(x.get("Code", "")) in {"412", "PreconditionFailed"}


def _body(r: Mapping[str, Any]) -> bytes:
    b = r["Body"].read()
    if not isinstance(b, bytes):
        raise PublicationError("provider body is not bytes")
    return b


def _etag(r: Mapping[str, Any]) -> str:
    x = r.get("ETag")
    if not isinstance(x, str) or not x:
        raise PublicationError("provider ETag missing")
    return x


def _stamp(x: object) -> str:
    if not isinstance(x, datetime) or x.tzinfo is None or x.utcoffset() is None:
        raise PublicationError("provider LastModified missing or naive")
    return x.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _get(c: Any, bucket: str, key: str):
    try:
        r = c.get_object(Bucket=bucket, Key=key)
    except Exception as e:
        if _not_found(e):
            return None
        raise PublicationError("provider read failed") from e
    return _body(r), _etag(r), r


def _head(c: Any, bucket: str, key: str):
    try:
        return c.head_object(Bucket=bucket, Key=key)
    except Exception as e:
        if _not_found(e):
            return None
        raise PublicationError("provider head failed") from e


def read_pair(c: Any, bucket: str) -> Pair | None:
    p, r = _get(c, bucket, PAYLOAD_KEY), _get(c, bucket, RECEIPT_KEY)
    if p is None and r is None:
        return None
    if p is None or r is None:
        raise PublicationError("remote pair is partial/unsealed")
    rh = _head(c, bucket, RECEIPT_KEY)
    if rh is None or _etag(rh) != r[1]:
        raise PublicationError("receipt readback raced")
    try:

        def nodup(xs):
            out = {}
            for k, v in xs:
                if k in out:
                    raise ValueError("duplicate JSON key")
                out[k] = v
            return out

        feed, receipt = json.loads(p[0], object_pairs_hook=nodup), json.loads(
            r[0], object_pairs_hook=nodup
        )
        if not isinstance(feed, dict) or not isinstance(receipt, dict):
            raise ValueError()
        if receipt.get("r2", {}).get("etag") != p[1]:
            raise ValueError("receipt payload ETag mismatch")
        modified = _stamp(rh.get("LastModified"))
        validate_publication_receipt_binding(
            feed=feed, payload=p[0], receipt=receipt, receipt_published_at=modified
        )
    except (ValueError, TypeError, CandidateFeedContractError) as e:
        raise PublicationError("remote pair is malformed or unsealed") from e
    return Pair(feed, p[0], receipt, modified, p[1], r[1])


def _record(path: Path, value: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as out:
            out.write(canonical_bytes(value))
            out.flush()
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _load(path: Path) -> dict[str, Any] | None:
    try:
        v = json.loads(path.read_bytes())
    except FileNotFoundError:
        return None
    except (OSError, ValueError, TypeError) as e:
        raise PublicationError("local transaction corrupt") from e
    if not isinstance(v, dict) or v.get("schema") != JOURNAL_SCHEMA:
        raise PublicationError("local transaction schema invalid")
    return v


def _pack(p: Pair | None) -> dict[str, Any] | None:
    return (
        None
        if p is None
        else {
            "payload": base64.b64encode(p.payload).decode(),
            "receipt": p.receipt,
            "receipt_last_modified": p.receipt_last_modified,
            "payload_etag": p.payload_etag,
            "receipt_etag": p.receipt_etag,
        }
    )


def _unpack(v: object) -> Pair | None:
    if v is None:
        return None
    try:
        assert isinstance(v, dict)
        raw = base64.b64decode(v["payload"], validate=True)
        p = Pair(
            json.loads(raw),
            raw,
            v["receipt"],
            str(v["receipt_last_modified"]),
            str(v["payload_etag"]),
            str(v["receipt_etag"]),
        )
        validate_publication_receipt_binding(
            feed=p.feed,
            payload=p.payload,
            receipt=p.receipt,
            receipt_published_at=p.receipt_last_modified,
        )
        return p
    except (
        AssertionError,
        KeyError,
        TypeError,
        ValueError,
        CandidateFeedContractError,
    ) as e:
        raise PublicationError("local predecessor is not an exact sealed pair") from e


def _put(c: Any, bucket: str, key: str, body: bytes, etag: str | None) -> None:
    a = {
        "Bucket": bucket,
        "Key": key,
        "Body": body,
        "ContentType": "application/json",
        "Metadata": {"sha256": hashlib.sha256(body).hexdigest()},
    }
    if etag is None:
        a["IfNoneMatch"] = "*"
    else:
        a["IfMatch"] = etag
    try:
        c.put_object(**a)
    except Exception as e:
        if _precondition(e):
            raise PublicationConflict(key) from e
        raise PublicationError("provider put failed") from e


def _make_receipt(
    feed: dict[str, Any],
    payload: bytes,
    prior: Pair | None,
    etag: str,
    durable: str,
    confirmed: str,
) -> dict[str, Any]:
    digest = hashlib.sha256(payload).hexdigest()
    rid = (
        "oacfr_"
        + hashlib.sha256(
            b"options.alpha_candidate_feed_publication_receipt/v1|" + digest.encode()
        ).hexdigest()[:25]
    )
    cs = {}
    for x in feed["formed_candidates"]:
        cid = x["candidate_id"]
        old = prior.receipt["candidates"].get(cid) if prior else None
        cs[cid] = (
            {"first_receipt_id": rid, "first_consumer_published_at": None}
            if old is None
            else (
                {
                    "first_receipt_id": old["first_receipt_id"],
                    "first_consumer_published_at": prior.receipt_last_modified,
                }
                if old["first_receipt_id"] == prior.receipt["receipt_id"]
                else old
            )
        )
    return {
        "schema": "options.alpha_candidate_feed_publication_receipt/v1",
        "receipt_id": rid,
        "feed_id": feed["feed_id"],
        "feed_schema": feed["schema"],
        "payload_sha256": digest,
        "payload_bytes": len(payload),
        "campaign_prefix": {
            k: feed["source_receipts"]["campaigns"][k]
            for k in ("path", "records", "prefix_sha256")
        },
        "prior_receipt": (
            {k: prior.receipt[k] for k in ("receipt_id", "payload_sha256")}
            if prior
            else None
        ),
        "local_durability_confirmed_at": durable,
        "payload_r2_confirmed_at": confirmed,
        "r2": {"payload_key": PAYLOAD_KEY, "payload_sha256": digest, "etag": etag},
        "candidates": cs,
    }


def _seal_local(
    pair: Pair, prior: Pair | None, cache_path: Path, journal_path: Path
) -> None:
    """Commit only an observed, valid successor; retire its durable journal last."""
    validate_publication_receipt_transition(
        feed=pair.feed,
        payload=pair.payload,
        receipt=pair.receipt,
        **(
            {
                "prior_feed": prior.feed,
                "prior_payload": prior.payload,
                "prior_receipt": prior.receipt,
                "prior_receipt_published_at": prior.receipt_last_modified,
            }
            if prior
            else {}
        ),
    )
    _record(cache_path, {"schema": JOURNAL_SCHEMA, "sealed": _pack(pair)})
    journal_path.unlink(missing_ok=True)
    directory_fd = os.open(str(journal_path.parent), os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def publish_pair(
    *,
    client: Any,
    bucket: str,
    feed: dict[str, Any],
    payload: bytes,
    lock_path: Path,
    now: Callable[[], str],
) -> str:
    """Publish one transaction; any unproven partial state is a hard stop."""
    if payload != canonical_bytes(feed):
        raise PublicationError("payload is not exact canonical feed bytes")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    jp, cp = lock_path.with_suffix(".transaction.json"), lock_path.with_suffix(
        ".sealed.json"
    )
    with lock_path.open("a+b") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        j, cache = _load(jp), _load(cp)
        cached = _unpack(cache.get("sealed") if cache else None)
        try:
            remote = read_pair(client, bucket)
        except PublicationError:
            p, r = _get(client, bucket, PAYLOAD_KEY), _get(client, bucket, RECEIPT_KEY)
            if (
                p is None
                or j is None
                or j.get("payload") != base64.b64encode(payload).decode()
            ):
                raise
            prior = _unpack(j.get("predecessor"))
            if (
                _pack(prior) != _pack(cached)
                or p[0] != payload
                or (
                    r is not None
                    and (prior is None or r[0] != canonical_bytes(prior.receipt))
                )
            ):
                raise PublicationError("unknown foreign transaction")
            remote = None
        if remote is not None:
            if remote.payload == payload:
                if (
                    j is not None
                    and j.get("payload") == base64.b64encode(payload).decode()
                ):
                    predecessor = _unpack(j.get("predecessor"))
                    if _pack(cached) not in (_pack(predecessor), _pack(remote)):
                        raise PublicationError(
                            "sealed recovery has an unrelated local cache"
                        )
                    _seal_local(remote, predecessor, cp, jp)
                return "noop"
            prior = remote
        else:
            prior = cached
        if j is None:
            # A new host may have no local predecessor yet. Retain the exact
            # remote sealed generation before the first payload overwrite.
            if prior is not None:
                _record(cp, {"schema": JOURNAL_SCHEMA, "sealed": _pack(prior)})
            j = {
                "schema": JOURNAL_SCHEMA,
                "payload": base64.b64encode(payload).decode(),
                "predecessor": _pack(prior),
                "durable_at": None,
            }
            _record(jp, j)
        elif j.get("payload") != base64.b64encode(payload).decode() or _pack(
            _unpack(j.get("predecessor"))
        ) != _pack(prior):
            raise PublicationError(
                "pending transaction does not match requested transition"
            )
        if j["durable_at"] is None:
            # The payload and predecessor have already been fsynced. This
            # clock observes that completed effect, rather than predicting it.
            j["durable_at"] = now()
            _record(jp, j)
        # Reject malformed feed/history before the first remote effect; the ETag
        # is rebound to the observed provider value after payload readback.
        try:
            validate_publication_receipt_transition(
                feed=feed,
                payload=payload,
                receipt=_make_receipt(
                    feed, payload, prior, "provisional", str(j["durable_at"]), now()
                ),
                **(
                    {
                        "prior_feed": prior.feed,
                        "prior_payload": prior.payload,
                        "prior_receipt": prior.receipt,
                        "prior_receipt_published_at": prior.receipt_last_modified,
                    }
                    if prior
                    else {}
                ),
            )
        except CandidateFeedContractError as e:
            raise PublicationError("invalid pre-effect transition") from e
        h = _head(client, bucket, PAYLOAD_KEY)
        if h is None or remote is not None:
            try:
                _put(
                    client,
                    bucket,
                    PAYLOAD_KEY,
                    payload,
                    prior.payload_etag if prior else None,
                )
            except PublicationConflict:
                sealed = read_pair(client, bucket)
                if sealed and sealed.payload == payload:
                    _seal_local(sealed, prior, cp, jp)
                    return "noop"
                raise
        check, h = _get(client, bucket, PAYLOAD_KEY), _head(client, bucket, PAYLOAD_KEY)
        if check is None or h is None or check[0] != payload or check[1] != _etag(h):
            raise PublicationConflict("payload readback")
        receipt = _make_receipt(
            feed, payload, prior, check[1], str(j["durable_at"]), now()
        )
        try:
            validate_publication_receipt_transition(
                feed=feed,
                payload=payload,
                receipt=receipt,
                **(
                    {
                        "prior_feed": prior.feed,
                        "prior_payload": prior.payload,
                        "prior_receipt": prior.receipt,
                        "prior_receipt_published_at": prior.receipt_last_modified,
                    }
                    if prior
                    else {}
                ),
            )
        except CandidateFeedContractError as e:
            raise PublicationError("invalid dynamic receipt") from e
        j["receipt"] = receipt
        _record(jp, j)
        try:
            _put(
                client,
                bucket,
                RECEIPT_KEY,
                canonical_bytes(receipt),
                prior.receipt_etag if prior else None,
            )
        except PublicationConflict:
            sealed = read_pair(client, bucket)
            if sealed and sealed.payload == payload and sealed.receipt == receipt:
                _seal_local(sealed, prior, cp, jp)
                return "healed"
            raise
        sealed = read_pair(client, bucket)
        if sealed is None or sealed.payload != payload or sealed.receipt != receipt:
            raise PublicationError("receipt seal readback failed")
        _seal_local(sealed, prior, cp, jp)
        return "published"
