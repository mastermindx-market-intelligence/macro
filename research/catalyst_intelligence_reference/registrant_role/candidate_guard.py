"""Capture-only repair experiment. Not imported by production.

The candidate uses the existing `defer` state, retains each raw row and its LLM
annotation, and withholds only an LLM-promoted Going-Private classification
without explicit target role. It does not assert an affected relationship,
resolve transaction identity, repair lifecycle or authorize any recommendation.
"""
ANCHOR = '''        if is_none.any():
            df.loc[is_none, ["status", "category", "stage", "confidence"]] = ["skip", None, None, "high"]
'''
GUARD = '''
        # A category names the event; it does not prove the registrant is its target.
        # Preserve contradictory/unknown-role evidence for relationship adjudication.
        # This annotation gate is not canonical transaction/economic-right identity.
        target_role = df.llm_role.astype("string").str.strip().str.lower().eq("target").fillna(False)
        non_target_gp = valid & llm.eq(GP).fillna(False) & ~target_role
        df.loc[non_target_gp, ["status", "category", "stage"]] = ["defer", None, None]
'''

def patched_source(source: str) -> str:
    if source.count(ANCHOR) != 1:
        raise ValueError('SOURCE_ANCHOR_MISMATCH: require exact source reconciliation')
    return source.replace(ANCHOR, ANCHOR + GUARD)
