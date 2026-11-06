"""Relationship observation package v2: contracts, derivation and replay.

Shared canonicalization and identity formulas live in the derivation module so
the replayer can never drift from it.  Submodules load lazily (PEP 562) so
``python3 -m ...relationships.replay`` does not double-import the module it is
asked to run.  The v1 module
(``engine.company_intelligence.relationship_observations``) is read-only: only
its purpose/authority/content-boundary dicts are consumed, never mutated.
"""

_LAZY_SUBMODULES = {
    "build_package": "package_v2",
    "canon": "package_v2",
    "ClockRefused": "clock",
    "clock_refusal": "package_v2",
    "et_acceptance_to_utc": "clock",
    "load_manifest_issuers": "package_v2",
    "normalize_span": "package_v2",
    "path_validity": "package_v2",
    "rights_block": "package_v2",
    "sha": "package_v2",
    "SOURCE_TZ": "clock",
    "SPECIES_ROLES": "package_v2",
    "CORRUPT": "package_v2",
    "EXCERPT_PATH_TEMPLATE": "package_v2",
    "FRESHNESS_DAYS": "package_v2",
    "PACKAGE_SCHEMA": "package_v2",
    "EDGES_SCHEMA": "package_v2",
    "observation_identity": "package_v2",
    "assessment_identity": "package_v2",
    "relationship_identity": "package_v2",
    "non_edge_identity": "package_v2",
    "revision_identity": "package_v2",
    "package_identity": "package_v2",
    "verify_excerpt": "replay",
    "replay_fetch": "replay",
}

__all__ = sorted(_LAZY_SUBMODULES)


def __getattr__(name):
    import importlib

    module_name = _LAZY_SUBMODULES.get(name)
    if module_name is None:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        )
    module = importlib.import_module(
        f"engine.company_intelligence.relationships.{module_name}"
    )
    return getattr(module, name)
