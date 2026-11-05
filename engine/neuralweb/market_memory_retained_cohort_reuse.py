"""Incumbent site owner composition for bounded exact cohort reuse.

Fresh generation/query checks stay in the request composition; each retained
capability still passes the original current-rights disclosure gate on use.
"""
from engine.neuralweb.market_memory_retained_cohort_cache import BoundedCohortCache


_CACHE = BoundedCohortCache()


def read_exact_retained_cohort(reader, generation, *, subject_id: str,
                              query_cutoff: str, policy, method):
    """Reuse only owner-sealed evidence for an exact site comparison.

    The composition caller still freshly pins the generation with the original
    active-head/max-capture/ancestry checks before entering here. Query feature,
    retrieval and selected evidence construction remain fresh on every request.
    This is neither a response cache nor the catalog's distinct raw closure.
    Existing capability disclosure is explicitly independent of disk replay;
    current application policy, including every original's retention and source
    rights, remains mandatory. No authorization decision is retained here.
    """
    from engine.neuralweb import market_memory_retained_context_cohort as cohort
    from engine.neuralweb import market_memory_retained_use as use
    from engine.neuralweb import market_memory_episode_retrieval as retrieval

    if (type(policy) is not use.RetainedHouseUsePolicy
            or type(method) is not retrieval.RetainedContextMethodSpec):
        # The Factory and other existing application-policy paths stay intact.
        return cohort.read_retained_context_cohort(
            reader, generation, subject_id=subject_id,
            query_cutoff=query_cutoff, policy=policy)
    resource = {"store_id": generation.store_id,
                "generation_id": generation.generation_id,
                "generation_sha256": generation.generation_sha256,
                "subject_id": subject_id, "query_cutoff": query_cutoff}
    policy.check("read_retained_generation_metadata", resource)
    # disclosure() includes the live fixed descriptor and imported scientific
    # source identities. Never memoize that validation or its resulting grant.
    method_identity = method.disclosure()["method_spec_id"]
    key = (str(reader.root), str(policy.root), policy.user_id, policy.policy_id,
           generation.profile, generation.store_id, generation.generation_id,
           generation.generation_sha256, subject_id, query_cutoff, method_identity)
    capability = _CACHE.get(key)
    if capability is not None:
        try:
            cohort.disclose_retained_context_cohort(capability, policy=policy)
        except cohort.RetainedContextCohortError:
            _CACHE.discard(key, capability)
            raise  # A refused hit cannot trigger another source read/fallback.
        return capability
    capability = cohort.read_retained_context_cohort(
        reader, generation, subject_id=subject_id,
        query_cutoff=query_cutoff, policy=policy)
    # Owner issuance already enforces the full-generation declared material
    # bounds. Existing lexical budgets continue charging all actual owner I/O;
    # retained bytes are separately bounded here, never fictitiously read/billed.
    _CACHE.put(key, capability)
    return capability
