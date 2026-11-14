"""Record renderers must never emit YAML anchors/aliases into frontmatter.

PyYAML emits ``&idNNN`` anchors and ``*idNNN`` aliases whenever one shared
dict object is serialized under two keys. Agent OS frontmatter readers
reject aliased frontmatter, and on 2026-11-02 (PR #10593) one anchored
record — WS-CHAIRMAN-CONTROL-ROOM — made every Stop hook report
HANDOFF_UNAVAILABLE until the anchors were dereplicated. These tests pin
the record renderers so the hazard class cannot recur.
"""
from __future__ import annotations

import yaml


def _anchor_tokens(frontmatter: str) -> list:
    return [type(token).__name__ for token in yaml.scan(frontmatter)
            if isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken))]


def test_shared_objects_would_anchor_under_plain_safe_dump():
    shared = {"repo": "macro"}
    text = yaml.safe_dump({"a": shared, "b": shared}, sort_keys=False)
    assert _anchor_tokens(text)  # the hazard the no-alias dumpers remove


def test_canonical_frontmatter_writer_inlines_shared_reference_objects():
    from scripts import agentos
    shared = {"repo": "macro", "path": "docs/spec.md", "commit": "a" * 40}
    data = {"key": "ANCHORS", "commission_ref": shared,
            "proof_contract_ref": shared,
            "waves": [{"id": "W1", "source_ref": shared}]}
    text = agentos._yaml_frontmatter(data)
    front = text.split("---")[1]
    assert _anchor_tokens(front) == []
    assert yaml.safe_load(front) == data


def test_direction_acceptance_render_inlines_shared_reference_objects():
    from scripts import agentos_direction_acceptance as acceptance
    shared = {"repo": "macro", "path": "docs/spec.md", "commit": "b" * 40}
    data = {"key": "ANCHORS", "commission_ref": shared,
            "proof_contract_ref": shared}
    text = acceptance._render(data, "Body prose.\n")
    front = text.split("---")[1]
    assert _anchor_tokens(front) == []
    assert yaml.safe_load(front) == data
