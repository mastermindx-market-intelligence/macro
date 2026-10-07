"""Read-only binding to the existing B1 validator; no parallel validation/store.

The native owner verifies all generation files, events and projections. The Lab
only requires that the validated result also matches its immutable Git snapshot.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re

from engine.us_candidate_episode import (
    EpisodeContractError, load_candidate_episode_store_snapshot,
)


def validate_native_episode_binding(
    *, episode_store: Path, generation_id: str | None,
    head_sha256: str | None, book_sha256: str | None,
) -> dict:
    """Return a bounded receipt, never raw episodes or untrusted filesystem paths."""
    result = {
        'status': 'UNAVAILABLE', 'reason': 'NATIVE_GENERATION_INVALID',
        'generation_id': generation_id,
        'historical_identity_qualified': False,
    }
    if (not isinstance(generation_id, str) or not re.fullmatch(r'peg:[0-9a-f]{64}', generation_id)
            or any(not isinstance(x, str) or not re.fullmatch(r'[0-9a-f]{64}', x)
                   for x in (head_sha256, book_sha256))):
        return result
    root = Path(episode_store)
    try:
        initial_head = (root / 'HEAD.json').read_bytes()
        if sha256(initial_head).hexdigest() != head_sha256:
            result['reason'] = 'NATIVE_HEAD_DIFFERS_FROM_PIN'
            return result
        snapshot = load_candidate_episode_store_snapshot(root)
        if (root / 'HEAD.json').read_bytes() != initial_head:
            result['reason'] = 'NATIVE_HEAD_CHANGED_DURING_READ'
            return result
        if snapshot.generation_id != generation_id:
            result['reason'] = 'NATIVE_GENERATION_DIFFERS_FROM_PIN'
            return result
        hashes = snapshot.generation.receipt.get('projection_hashes', {})
        if hashes.get('all_candidates.json') != 'sha256:' + book_sha256:
            result['reason'] = 'NATIVE_PROJECTION_DIFFERS_FROM_PIN'
            return result
    except (OSError, EpisodeContractError):
        return result
    return {
        'status': 'VALIDATED_CANONICAL_OWNER',
        'generation_id': generation_id,
        'head_sha256': head_sha256,
        'book_sha256': book_sha256,
        'episode_count': len(snapshot.generation.episodes),
        'validator': 'engine.us_candidate_episode.load_candidate_episode_store_snapshot',
        'historical_identity_qualified': False,
    }
