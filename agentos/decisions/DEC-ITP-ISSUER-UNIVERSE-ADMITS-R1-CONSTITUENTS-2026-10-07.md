---
key: ITP-ISSUER-UNIVERSE-ADMITS-R1-CONSTITUENTS-2026-10-07
question: >
  DEC:ITP-R1-COMPLETE-DEGRADED-2026-10-07 closed R1 as COMPLETE_DEGRADED. Issuer-level studies exclude the 724 R1
  names that have no canonical issuer_id. The DEC's stated upgrade path is that a later prospective owner receipt
  moves that gap from DEGRADED_ACCEPTED to CLOSED at a later cutoff. Orchestrator A's A7 census (2026-10-07) found
  why the 724 are unresolved. They are not ambiguous or conflicting. They are absent from
  data/reference/security_master.parquet, because scripts/build_security_master.py load_universe() admits only the
  S&P 500 breadth constituents and the basket memberships. The S&P 400 and 600 constituent files are collected
  nightly by the same BreadthAdapter collectors but are never read. Should the identity owner admit them? If so,
  under what clock, and with what guarantees about existing identities and nightly cost?
answer: >
  Yes, forward-only. load_universe() also reads data/midcap_breadth/constituents.parquet (source
  "midcap_breadth.constituents") and data/smallcap_breadth/constituents.parquet (source
  "smallcap_breadth.constituents"), exactly as it reads the S&P 500 constituents (exists() guard, first_seen null).
  The two paths are treated as the S&P 500 path is at every input-list site: the receipt inputs and the nightly
  required-input refusal.
  Newly minted security_master and vendor_aliases rows carry ingested_at = the build time of the first nightly that
  runs this code. No valid_from is backdated. Consequences:
  (a) Every consumer that reads identity under a knowledge clock sees the new names only from that build forward.
      This includes the K3E ALIAS gate (DEC:ITP-K3E-ALIAS-CLOCK-BOUNDED-IDENTITY-2026-10-07) and the EVAL-1
      issuer_ref rule ("never repaired by a later identity backfill"). Earlier captures and earlier decision cutoffs
      stay unresolved, counted and ineligible.
  (b) The R1 cutoff exclusions of DEC:ITP-R1-COMPLETE-DEGRADED-2026-10-07 stand for every cutoff before that build.
      For later cutoffs the gap closes for the names that now resolve. The residuals are CENT and CENTA
      (EVIDENCE_CONFLICT: CIK 0000887733 is not in config/issuer_group_allowlist.yml) and CWEN-A and HLX
      (NO_SECURITY). The CLOSED upgrade itself is a separate prospective owner receipt, issued after the first
      widened nightly by re-running r1_readiness_probe at a post-build cutoff.
  (c) The A8 dry run proved four things. No existing identity mutates (S1). No per-name network or site fan-out
      grows on a scheduled path (S2). Builder runtime grows by 0.10 s (S3). R1 issuer resolution reaches
      1,499/1,503 (S4).
  The data-gated coverage pins in tests/test_dataos_security_master.py are widened at the ceiling only, so the
  first widened nightly does not redden data-health. Their floors are unchanged.
rationale: >
  The R1 gap was an admission gap in the identity universe, not an evidence gap. The constituents are already
  collected nightly and already lawful owner inputs of the same shape as the S&P 500 file the builder reads. With
  the forward-only clock, no historical cutoff, capture or ledger changes meaning: identity becomes known when the
  owner first publishes it, the rule DEC:ITP-R4-ISSUER-AXIS-AS-KNOWN-VERSION-CLOCK-2026-10-07 and the ALIAS gate
  already read. Widening at the input boundary reuses the builder's existing evidence, CIK and alias machinery, so it
  mints no new vocabulary, store or rights semantics (#7870 keeps the rights vocabulary).
alternatives:
  - option: "Keep R1 at COMPLETE_DEGRADED and wait for a vendor point-in-time identity purchase"
    why_not: "The gap is curable in-repo from owner-collected inputs. Vendor PIT stays an absolute gate for history, but it is not needed to close the forward gap."
  - option: "Backdate valid_from for the new rows to each name's index-entry date"
    why_not: "A later identity backfill would retroactively resolve past cutoffs. The EVAL-1 issuer_ref rule and the R1 DEC forbid that ('never repaired by a later identity backfill')."
  - option: "Mint a K3E-local or study-local issuer table for the 724 names"
    why_not: "That is a second identity store beside the canonical security master (no new stores), and it would fork the alias semantics the ALIAS gate reads."
  - option: "Wait for Sol-held DRAFT #7299, which also edits the builder"
    why_not: "#7299 carries no midcap/smallcap content, and its hunks do not overlap these. A textual conflict is that PR's rebase, and it stays untouched."
evidence:
  - "Orchestrator A, A7 PHASE_RETURN 2026-10-07, verdict WIDEN_FEASIBLE_IN_REPO. Artifacts: seat scratch orch/A/a7/a7_coverage.json (3ba29c29…, byte-identical on re-run) and a7_xcheck.json (db77fe65…)."
  - "Seat spot-check orch/A/a7/seat_spot.py against origin/main 4fc4589f: 724 unresolved = 243 in S&P 400 + 481 in S&P 600 + CBOE (S&P 500 file, absent from master) + SAM (in no constituent file); security_master has 2,382 rows."
  - "A8 S1 (orchestrator a8_gates.py over main data/reference vs unpatched and patched dry-run outputs at origin/main d6b11b5b): security_master 2,382 -> 3,104 rows. +721 from A8 (RESOLVED 719, EVIDENCE_CONFLICT 2); +1 SEC:US-BATS-CBOE is pre-existing input drift that the unpatched builder also produces. Existing security_ids: 0 missing; 0 changes in security_id, issuer_id, issuer_state, issuer_cik, listing_key or mic; 0 ingested_at moved earlier. vendor_aliases 6,037 -> 8,925; existing (vendor, symbol) pairs: 0 missing, 0 security_id changes. issuer_master 1,213 -> 1,932. One existing row moves forward: ISS:US-XNYS-UAA, n_securities 1 -> 2, because SEC:US-XNYS-UA (CIK 0001336917) groups under it."
  - "A8 S2 (git grep over app collectors engine lib scripts research at origin/main 55e8cf84, 21 readers): 0 added scheduled network calls and 0 added pages. The one network reader, scripts/cell_b_v2_buyback_source_census.py, is dormant: no workflow or cron caller, and it needs operator arguments."
  - "A8 S3 (/usr/bin/time over scripts/build_security_master.py --report): unpatched 1.19/1.18 s, patched 1.28/1.28 s (+0.10 s). The --nightly seam exits 0 twice: 1,620/1,633 resolved, 13 unresolved."
  - "A8 S4 (r1_readiness_probe rule at cutoff 2026-10-03, names sha 441a942e): R1 issuer_id resolution 1,499/1,503 (main 779, unpatched 780). Of the 724: RESOLVED 720, EVIDENCE_CONFLICT 2 (CENT, CENTA), NO_SECURITY 2 (CWEN-A, HLX), AMBIGUOUS 0, DEFERRED 0, NO_ISSUER_EVIDENCE 0."
  - "Narrow gate (patched, full lane checkout): tests/test_build_security_master_universe.py 8/8 pass; 6 failures in tests/test_dataos_security_master.py are pre-existing main failures that fail identically unpatched."
affects:
  - "WS:ALPHA-INTELLIGENCE-INTEGRATION"
  - "DEC:ITP-R1-COMPLETE-DEGRADED-2026-10-07"
  - "scripts/build_security_master.py"
  - "tests/test_dataos_security_master.py"
  - "data/reference/security_master.parquet"
  - "data/reference/vendor_aliases.parquet"
  - "data/reference/issuer_master.parquet"
confidence: high
reversibility: costly
decided_by: "seat: program-ceo session 2fc05761 (WS:ALPHA-INTELLIGENCE-INTEGRATION owner; owns_paths data/reference/** per DEC:ITP-R1-COMPLETE-DEGRADED-2026-10-07; the producer edit is scoped to load_universe input admission and claims no ownership of scripts/build_security_master.py, and Sol-held DRAFT #7299 is untouched), under Chairman directive 2026-10-06/07; census and build by orchestrator A (A7, A8)"
decided_at: 2026-10-07
review_by: 2027-01-07
---

# Issuer universe admits the R1 S&P 400/600 constituents, forward-only

R1 closed as COMPLETE_DEGRADED because 724 R1 names had no canonical issuer_id. The A7 census showed that this was
an admission gap, not an evidence gap: the S&P 400 and 600 constituent files are collected nightly and the identity
builder never read them. This record admits them at the input boundary under the forward-only clock.

**What changes**

- `load_universe()` reads `data/midcap_breadth/constituents.parquet` and `data/smallcap_breadth/constituents.parquet`
  exactly as it reads the S&P 500 file.
- The first nightly that runs this code mints about 721 securities and 2,888 aliases, with ingested_at set to build
  time.

**What does not change**

- No existing identity changes. The only exception is that one issuer row, ISS:US-XNYS-UAA, gains its second share
  class.
- No historical cutoff resolves retroactively.
- No new store or vocabulary is minted.
- No per-name fan-out is added to any scheduled path.

**Upgrade path**

After the first widened nightly, re-run `r1_readiness_probe` at a post-build cutoff and issue the prospective owner
receipt that moves the resolved names from DEGRADED_ACCEPTED to CLOSED. Rows at or before 2026-10-03T06:31:51Z are
never re-labelled.

**Residuals**

- CENT and CENTA are EVIDENCE_CONFLICT. Their shared CIK is not in the issuer-group allowlist; that allowlist belongs
  to the identity owner and is the place to address it.
- CWEN-A and HLX have no security row.
