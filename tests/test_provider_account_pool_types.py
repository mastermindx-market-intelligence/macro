from engine.provider_account_pool_types import CapacityEvidence, CapacityWindow


def test_capacity_evidence_constructs():
    value = CapacityEvidence("a", "2026-09-14T00:00:00Z", CapacityWindow(0), CapacityWindow(0), CapacityWindow(0), 0, 2)
    assert value.account_id == "a"
    assert value.concurrency_limit == 2
