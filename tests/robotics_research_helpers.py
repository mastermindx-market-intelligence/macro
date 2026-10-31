"""tests/robotics_research_helpers.py — shared loader for the robotics theme
research synthetic fixture corpus.

Every fixture file under ``tests/fixtures/robotics_theme_research/`` is a
synthetic case built for operation
gmi-robotics-fable-ceo-e2e-20260923-chairman-001 (R1). The corpus cites real
PUBLIC vendor pages and exchange filings as ``source_uri`` anchors (URLs the
acceptance/research documents name), but every payload, stamp, review and
identity row is synthetic: no paid data, no private retention keys, no
canonical identity claims. Any helper function here MUST refuse to hand back
a value whose ``synthetic`` flag is not explicitly ``True``; that refusal is
what keeps a future native fixture from being mistakenly loaded in tests
that promise "synthetic only".
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE_ROOT = Path(__file__).parent / 'fixtures' / 'robotics_theme_research'


def load_case(name: str) -> dict:
    """Load a synthetic fixture case by file stem.

    Raises ``ValueError`` if the name is not a safe alphanumeric slug, and
    raises ``ValueError`` if the loaded payload is not explicitly marked
    ``{"synthetic": true}``. Both refusals are loud on purpose: a real
    fixture whose ``synthetic`` flag is missing or false is a contract
    violation, not a soft warning.
    """
    if not name.replace('_', '').isalnum():
        raise ValueError('invalid test case name')
    value = json.loads((FIXTURE_ROOT / (name + '.json')).read_text())
    if not isinstance(value, dict) or value.get('synthetic') is not True:
        raise ValueError('fixture must explicitly be synthetic')
    return value


def load_bundle_case(name: str):
    """Load a synthetic bundle-bearing fixture and build the R2 objects.

    The lazy import inside the function body is intentional — the
    ``engine.market_ontology.robotics_theme_research`` module is owned by a
    later task (R2) and does not yet exist. Tests that only exercise the
    JSON shape should call :func:`load_case` instead.
    """
    from engine.market_ontology.robotics_theme_research import ResearchQuery, OwnerBundle
    value = load_case(name)
    source = value['bundle']
    bundle = OwnerBundle(
        revision_tuple=tuple(tuple(x) for x in source['revision_tuple']),
        rights_revision=source['rights_revision'],
        assertions=tuple(source['assertions']),
        identity_results=tuple(source['identity_results']),
        event_workspaces=tuple(source['event_workspaces']),
        financial_packets=tuple(source['financial_packets']),
        interpretation_blocks=tuple(source['interpretation_blocks']),
        native_refs=tuple(source['native_refs']),
        omissions=tuple(source['omissions']),
    )
    return ResearchQuery(**value['query']), bundle
