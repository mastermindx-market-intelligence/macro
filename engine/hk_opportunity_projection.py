"""Pure HK Opportunities projection.

Zero-authority presentation contract. Implementation intentionally follows the
tests on this branch.
"""
SCHEMA = "mastermind.hk_opportunities_projection.v1"
ENTRY_OPEN = "ENTRY_OPEN"
PREPARING = "PREPARING"
MONITOR = "MONITOR"
WAIT_CONFLUENCE = "WAIT_CONFLUENCE"
WAIT_PULLBACK = "WAIT_PULLBACK"
RAN_DONT_CHASE = "RAN_DONT_CHASE"
BLOCKED = "BLOCKED"
UNAVAILABLE_DATA = "UNAVAILABLE_DATA"


def project_opportunities(
    *,
    incumbent_asof,
    discovery_asof,
    attention_asof,
    incumbent_buy,
    discovery_rows,
    attention_picks,
):
    return {
        "schema": SCHEMA,
        "market": "HK",
        "available": False,
        "reason": "not_implemented",
        "source_asof": {
            "incumbent": incumbent_asof,
            "discovery": discovery_asof,
            "attention": attention_asof,
        },
        "lanes": {ENTRY_OPEN: [], PREPARING: [], MONITOR: []},
        "diagnostics": {},
    }
