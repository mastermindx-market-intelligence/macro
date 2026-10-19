"""Read-only composition of native companion qualifications and view metering.

No production qualification is synthesized. The default factory binds the
concrete root-sealed policy adapter; absent real policy/records refuse admission.
The private reader needs bounded get only, never qualification write custody.
"""
from engine.research_intelligence.comparison_qualification import load_qualification
from engine.research_vault.comparison import (
    ComparisonOwners, QualifiedBasis, QualifiedRevision, QualifiedPair,
)


def _legs(legs):
    return [{"report_id": x["id"], "source_pdf_sha256": x["extracted"]["source_pdf_sha256"],
             "extracted_text_sha256": x["extracted"]["extracted_text_sha256"],
             "rio_artifact_sha256": x["artifact_sha"], "published_at": x["item"]["published_at"]}
            for x in legs]


def _bindings(record):
    return tuple(tuple(leg[k] for k in ("report_id", "source_pdf_sha256", "extracted_text_sha256", "rio_artifact_sha256", "claim_index")) for leg in record["legs"])


def build_comparison_owners(store, *, authority=None):
    """Construct without I/O. Authority is server-only dependency injection."""
    from engine.research_vault import view_ratelimit

    def read(ctx, legs, ref=None):
        return load_qualification(store, _legs(legs), caller=ctx, authority=authority, expected_ref=ref)

    def pair(ctx, legs):
        got = read(ctx, legs)
        if got is None: return None
        ref, record = got
        return QualifiedPair(ref, tuple(x["claim_index"] for x in record["legs"]), ref if record["revision"] is not None else None)

    def basis(ctx, ref, legs):
        got = read(ctx, legs, ref)
        if got is None: return None
        _, record = got
        return QualifiedBasis(_bindings(record), tuple(record["bases"]), tuple(record["subjects"]), record["review"]["provenance"], tuple(record["families"]))

    def revision(ctx, ref, legs):
        got = read(ctx, legs, ref)
        if got is None or got[1]["revision"] is None: return None
        record = got[1]; rev = record["revision"]
        return QualifiedRevision(_bindings(record), rev["kind"], rev["support_quote"], rev["provenance"])

    return ComparisonOwners(
        semantic=None,  # pair-scoped admission never blesses a whole RIO
        preflight=lambda ctx, ids, now: view_ratelimit.preflight_many(ctx.principal_id, ids, now=now),
        commit=lambda ctx, ids, now: view_ratelimit.commit_many(ctx.principal_id, ids, now=now),
        basis=basis, revision=revision, pair=pair,
    )
