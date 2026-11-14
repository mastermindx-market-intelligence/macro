"""The single finite-JSON wire encoder used by Sector admission and its API."""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

SCHEMA = "sector_generation.read/v1"
MAX_ENCODED_BYTES = 4 * 1024 * 1024


class SectorGenerationTooLarge(ValueError):
    """The complete HTTP body exceeds the existing response contract."""


def encode_sector_generation(
    *, audience: str, source_session: str, published_at: str,
    qualification: str, projection: Mapping[str, Any],
    max_encoded_bytes: int = MAX_ENCODED_BYTES,
) -> bytes:
    """Encode the actual response wrapper, including all repeated receipt facts.

    This is serialization only. The projection owner qualifies source semantics;
    the API owner checks authorization and agreement with its typed reader result.
    No truncation or alternate representation is permitted at the size boundary.
    """
    body = {
        "schema": SCHEMA,
        "audience": audience,
        "source_session": source_session,
        "published_at": published_at,
        "qualification": qualification,
        "projection": projection,
    }
    encoded = json.dumps(
        body, allow_nan=False, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    if len(encoded) > max_encoded_bytes:
        raise SectorGenerationTooLarge("sector_generation_too_large")
    return encoded


POPULATION_SCHEMA = "sector_population.read/v1"


def encode_sector_population(
    *, audience: str, source_session: str, published_at: str,
    qualification: str, page: Mapping[str, Any],
    max_encoded_bytes: int = MAX_ENCODED_BYTES,
) -> bytes:
    """Encode one population response page under the SAME finite/4 MiB law.

    Same serializer rules as the projection (``allow_nan=False``, no truncation
    at the boundary): a page that would exceed the bound is refused, never cut.
    """
    body = {
        "schema": POPULATION_SCHEMA,
        "audience": audience,
        "source_session": source_session,
        "published_at": published_at,
        "qualification": qualification,
        "page": page,
    }
    encoded = json.dumps(
        body, allow_nan=False, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    if len(encoded) > max_encoded_bytes:
        raise SectorGenerationTooLarge("sector_generation_too_large")
    return encoded
