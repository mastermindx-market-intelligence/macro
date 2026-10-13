"""Robotics Theme Intelligence — the owner-bundle loader the closed
registration hands to the theme-research shell.

Operation gmi-robotics-fable-ceo-e2e-20260923-chairman-001 (carrier #7908).
The shared shell (#7870 hook 1) dispatches on
:data:`~engine.market_ontology.theme_research_registry.REGISTRY`; a vertical's
entry must name a ``load_bundle(query, *, rights_snapshot) -> OwnerBundle``
callable. This is Robotics' — the last Robotics-owned piece between the
composer and a served mount.

What it serves
--------------
NOTHING, and the served response says so. Robotics has no admitted owner
surface in v1:

* The PRIVATE half (``assertions``, ``identity_results``,
  ``financial_packets``, ``interpretation_blocks``, ``native_refs``) is
  unbound — private binding is the open R4/R5 ruling, exactly as it is for the
  semiconductor vertical.
* The PUBLIC half (``event_workspaces``) is unowned. The semiconductor loader
  serves its public half by resolving a DECLARED witness cohort
  (``semiconductor_witness_scope``, ruled by Sol on #7780
  issuecomment-5813801605) and reading each witness's event workspace through
  the Company Intelligence reader. No such declared cohort exists for
  ``precision_motion`` or ``perception``, and declaring one is a Theme
  Graph / Data OS owner's ruling, not this lane's. So this loader resolves no
  cohort, calls no reader, and reads no workspace. It does not invent a
  Robotics-side cohort to fill the hole (master packet §3: no Robotics-
  specific store, ledger, publisher or scheduler).

The honest consequence, measured through the real composer: the response
carries ``authorized_coverage.status = "unavailable"`` with ``selected: 0``
and ``input_refs: []``, ``companies.rows`` empty, ``evidence_refs`` empty,
every ``authority`` flag false, and ``limitations`` ``["slice_scope_unowned"]``.
Every CONTENT section states its own emptiness
truthfully (``companies.status: unavailable`` / ``reason: no_companies``; all
five ``industrial_views`` and all four ``expectations`` ``unavailable``;
``native_subjects: []``). Nothing here ranks, gates, sizes, times or
originates anything.

Two misstatements used to ride on that status, and they are why this mount
was held out of a member-facing page (R4-reg independent review; the claim
that formerly stood here -- "a member sees a mount that states it is serving
nothing yet" -- was refuted on the served bytes):

* ``degraded`` is the PARTIAL state and the shipped client renders it
  "Degraded - partial data" / "降级——部分数据"; there was no partial data
  here, there was none;
* ``rights_partial`` tells a member their ENTITLEMENTS are partial, which on a
  paid-research surface is a false commercial signal -- and the client renders
  limitation slugs verbatim, so the raw token IS the member-facing sentence.
  Neither omission is a rights matter: ``private_assertions_unbound`` is an
  unbound store and ``public_cohort_unowned`` an undeclared cohort.

Both are FIXED, in this lane's OWN composer. The checkpoint that first
recorded them attributed the fix to "the composer owner" and held live
admission on that party; the attribution was wrong and is withdrawn.
``robotics_theme_research.py`` is the only theme-research composer on this
carrier, no other module under ``engine/market_ontology`` computes a coverage
ladder, and ``git log -L`` attributes the ladder to this operation's own R2
commit (37fd0bd35471) -- there was no other owner to wait for. What IS shared
and stays untouched is the client's ``degraded`` label: it is correct for a
genuinely partial payload, and the fix simply stops sending ``degraded`` when
nothing arrived.

Dropping this loader's two omissions would ALSO have bought an honest
"Unavailable" headline, and is still refused -- that trades the diagnosis of
WHICH half is absent for a cosmetic fix. The omissions stay on the bundle,
where tests and operators read them. What changed is that the composer no
longer turns them into a member-facing claim: emptiness outranks omission in
the ladder, and ``rights_partial`` now needs a selection to be partial ABOUT.
One consequence is deliberate and load-bearing -- the served payload for this
bundle is now byte-identical to one composed with ``omissions=()``, so an
empty read cannot disclose that withheld content exists, pinned by
``test_rbv27_the_response_never_names_a_withheld_family``.

Why coverage absence is an omission and not a 503
-------------------------------------------------
:class:`~engine.market_ontology.theme_research_binding.BundleUnavailable` is
the shell's private 503 and its own contract reserves it: "Never raised for
coverage absence — that is a typed omission on the bundle, so the response
says what is missing." An empty Robotics bundle is coverage absence, so it is
served with omissions rather than refused. A 503 would tell a member the
service is broken when it is merely empty, and would hide the mount instead of
letting it state its own emptiness.

Per RBV-27 the Robotics composer collapses every omission that NARROWS a real
answer into the single limitation ``rights_partial``, and never names a
withheld family (a deliberate divergence from the shared owner's
``omitted:<name>`` grammar, recorded at
``robotics_theme_research._Selection``). Because this bundle selects nothing,
neither that token nor a ``degraded`` status is emitted for it at all: the two
tokens below change the served payload in NO way. They are not a wire
vocabulary, no consumer may branch on them, and they exist for the bundle's
own readers -- tests and operators -- to tell which half is absent.

Why there is no ``system_replay`` refusal here
----------------------------------------------
The semiconductor loader refuses ``system_replay`` up front with
``identity_vintage_unsupported``, because it serves public workspaces to which
no as-known identity vintage can be applied. Sol's ruling refuses AFFECTED
``system_replay``. A Robotics bundle carries no identity result and no
assertion, so no request is affected: there is no vintage being applied to
anything, and an empty all-authority-false payload states nothing false under
any time mode. The composer's vintage guard (``_refuse_unsupported_identity_vintage``) does
NOT cover this, and will not begin covering it on its own -- corrected under
independent review, which falsified by experiment the claim that stood here.
The guard iterates ``bundle.identity_results``; this loader hard-codes that
field to ``()``, and so does the semiconductor loader
(``semiconductor_owner_bundle.py:334,392``) -- which is precisely WHY its
author added an up-front refusal rather than relying on the guard. With no
identity row the guard is inert by the composer's own documented design ("a
subject with NO identity row claims no belief and is not affected"). Admitting
assertions does not populate ``identity_results``: they are separate fields.

So R5 must do one of two things explicitly, and
``test_r5_cannot_admit_assertions_without_facing_replay_vintage`` goes red the
moment it does neither: populate ``identity_results`` with real vintages, or
add semiconductor's up-front ``ResearchRefusal(IDENTITY_VINTAGE_UNSUPPORTED)``.
A blanket refusal is NOT added today because Sol's ruling refuses AFFECTED
replay and an empty bundle affects nothing -- over-refusing now would have to
be undone by R5, and would hide the requirement instead of pinning it.

Refusals
--------
``BundleUnavailable`` only, and only for a rights snapshot that carries no
revision — the one genuine "cannot serve": the bundle's ``rights_revision``
feeds the composer's ``generation`` fingerprint, so serving without it would
fingerprint a response against nothing.

Base tolerance
--------------
This module imports wherever
:mod:`engine.market_ontology.robotics_theme_research` imports, and no wider:
that module binds #7870's Task 1 ``engine.theme_graph.curation_assertion``
unguarded, so on the carrier alone every Robotics module is unimportable and
the carrier-alone gate expects strict xfails. What this module does tolerate is
the narrower and real window in which Task 1 is present but the shell's
binding is not — the current review base is exactly that — where
``BundleUnavailable`` resolves to the local mirror. The mirror can only ever be
raised on a base that carries no shell to catch it, so no path exists where the
shell misses a raise. Only the MIRROR resolution is exercised today: on the
review base ``theme_research_binding`` does not exist, so
``BundleUnavailable.__module__`` is this module and nothing stubs the shared
class -- the shared resolution is exercised on no base reachable right now.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# The shared types, resolved exactly once — ``robotics_theme_research`` imports
# them from the shared owner when it is on this base and mirrors them (frozen,
# same field order) when it is not. Importing them from there rather than
# repeating its try/except keeps ONE fallback site for the whole vertical.
from engine.market_ontology.robotics_theme_research import (
    OwnerBundle,
    ResearchQuery,
)

try:  # the shell's private 503, present with #7870
    from engine.market_ontology.theme_research_binding import BundleUnavailable
except ImportError:  # pragma: no cover - carrier base fallback
    class BundleUnavailable(Exception):  # type: ignore[no-redef]
        """Mirror of the shared shell's 503 for a base without the binding.

        Only reachable on a base that carries no shell, so a caller that can
        catch the shared class can never receive this one instead.
        """

__all__ = [
    "PRIVATE_ASSERTIONS_UNBOUND",
    "PUBLIC_COHORT_UNOWNED",
    "load_robotics_owner_bundle",
]

#: The private half is unbound pending the R4/R5 private-binding ruling.
PRIVATE_ASSERTIONS_UNBOUND = "private_assertions_unbound"

#: No declared witness cohort owns the Robotics slices, so there is no public
#: half to read. Not a Robotics-side decision to reverse.
PUBLIC_COHORT_UNOWNED = "public_cohort_unowned"


def _rights_revision(rights_snapshot: object) -> str:
    """The enforced rights revision for this request.

    ``rights_snapshot`` is the ONE rights registry read the shell performs per
    request and also enforces with, so the fingerprinted revision equals the
    enforced one. A direct caller may omit it and this reads the snapshot
    itself; on a base without the snapshot reader there is no revision to
    fingerprint against and the loader cannot serve.
    """
    snapshot: object = rights_snapshot
    if snapshot is None:
        try:
            from engine.theme_graph.rights import (  # noqa: PLC0415 — lazy by design
                load_registry_snapshot,
            )
        except ImportError as exc:  # pragma: no cover - carrier base fallback
            raise BundleUnavailable(
                "rights registry snapshot reader unavailable on this base"
            ) from exc
        snapshot = load_registry_snapshot()
    if not (isinstance(snapshot, tuple) and len(snapshot) == 2
            and isinstance(snapshot[0], str) and snapshot[0]):
        raise BundleUnavailable("rights snapshot carries no revision")
    return snapshot[0]


def load_robotics_owner_bundle(
    query: ResearchQuery,
    *,
    rights_snapshot: tuple[str, Mapping[str, Any]] | None = None,
) -> OwnerBundle:
    """Serve Robotics' owner bundle: both halves declared absent, on the wire.

    Reads NOTHING from ``query`` — not a slice, path, URL, locator, event id,
    ticker or CIK. The anchor and the slice were already resolved and
    validated by the closed registration, and this loader has no surface whose
    selection they could narrow. ``revision_tuple`` is empty because no owner
    input was read; the composer's ``generation`` then moves only with the
    rights revision, the definition version and the request's own time
    scoping, which is exactly the set of things that can change this response.
    """
    return OwnerBundle(
        revision_tuple=(),
        rights_revision=_rights_revision(rights_snapshot),
        assertions=(),
        identity_results=(),
        event_workspaces=(),
        financial_packets=(),
        interpretation_blocks=(),
        native_refs=(),
        omissions=(PRIVATE_ASSERTIONS_UNBOUND, PUBLIC_COHORT_UNOWNED),
    )
