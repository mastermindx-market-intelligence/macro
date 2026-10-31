---
key: ITP-R1-DEGRADED-RECEIPT-REFRESH-2026-10-17
question: >
  The R1 upgrade path (DEC:ITP-R1-COMPLETE-DEGRADED-2026-10-07, WS next_action item 2) said: after the
  first nightly that runs the widened security-master builder (#8626), re-run r1_readiness_probe at a
  post-build cutoff and issue the prospective owner receipt upgrading the resolved names to CLOSED.
  The nightlies from 2026-10-11 ran the widened builder. At origin/main 1aeaf6874e4d3ed8d4f76205c236994ec7a3bcb9
  the store-alias lookup resolves 1495 of 1502 universe names (was 779 of 1503). Does that upgrade G1 (or any
  gap) to CLOSED, and what receipt does the owner issue at the new cutoff?
answer: >
  No gap is CLOSED. The owner issues a REFRESHED prospective degraded receipt,
  research/alpha_intelligence/expectation_market_dynamics/R1_OWNER_RECEIPTS_2026-10-17.json
  (schema r1-owner-receipts.v1), at cutoff 2026-10-15T13:32:43Z, the latest spine ingestion clock at the
  measured revision (vendor_aliases ingested_at max). G1, G2 and G3 keep DEGRADED_LABELED_ABSENCE, G4 keeps
  OWNER_REFUSAL_NO_CLASS, G5 keeps CAPTURE_CLOCK_ONLY. Counts at the new cutoff: G1 issuer_id_resolved 1495,
  universe_names 1502, unresolved 7 (BLFS, CENT, CENTA, CWEN-A, HLX, SKYD, TCBI; CENT and CENTA are
  EVIDENCE_CONFLICT in security_master, the other five have no store alias row); G2 alias_rows_dated_le_cutoff 3
  (ECHO, MU, VMRK), undated_alias_rows 1492, prospective_from_undated_rows 0; G3, G4 and G5 unchanged in form
  and value (0 currency/fiscal/basis columns; UNKNOWN on line 363; 0 source clocks). The probe reports
  r1_status COMPLETE_DEGRADED with zero mismatches when run with --cutoff 2026-10-15T13:32:43Z,
  --expected-universe-sha256 dae001f6cfda644ae9c292db5555cca599b7f7cf03455a5d56ec7cc5adc7daec and
  --owner-receipts pointing at the 10-17 file. The 2026-10-07 receipt stays the receipt for its own cutoff;
  nothing at or before 2026-10-03T06:31:51Z is re-labeled. Issuer-level studies at the new cutoff exclude the 7
  unresolved names instead of 724; prospective alias studies still exclude every undated row.
rationale: >
  The spec's G1 gate is issuer_id_resolved == universe.names and its G2 gate is undated_alias_rows == 0. The
  widened builder moved G1 from 779/1503 to 1495/1502, which is a large real improvement, but 7 names still
  have no issuer id and the spec's (f) line forbids closing G1 on anything short of an issuer id per name.
  G2 cannot close while store alias rows are undated by design under the ALIAS ruling
  (DEC:ITP-K3E-ALIAS-CLOCK-BOUNDED-IDENTITY-2026-10-07): the store rows carry no valid_from and the ruling
  forbids minting one. Issuing a CLOSED receipt here would be a fabricated closure. Issuing nothing would leave
  downstream studies bound to the 10-07 exclusion list (724 names) when 717 of those names now resolve. The
  honest act is a refreshed degraded receipt that records the new counts at a cutoff derived from the data,
  so the exclusion lists shrink to what is actually absent. The probe repair that made this measurable is a
  pass-through of known_at, evidence_sha256, binding_sha256 and alias_kind from vendor_aliases into the
  identity library (it had dropped them, and main's lib/dataos/identity.py refuses a polygon row without its
  decision clock); it mints nothing. The --cutoff, --owner-receipts and --expected-universe-sha256 flags leave
  the frozen 2026-10-03 defaults in place so the 10-07 run stays reproducible.
alternatives:
  - option: Issue a CLOSED receipt for G1 on the 1495 resolved names and label only the 7 as absent
    why_not: >
      The spec's gate is all-or-nothing per gap (issuer_id_resolved == universe.names). A partial CLOSED is not
      a form the spec defines; the labeled-absence form already carries exactly this information.
  - option: Resolve the last 7 names by hand (ticker match, acquisition history, CIK rows) to reach CLOSED
    why_not: >
      Forbidden by the spec's (f) line and by program law (no fabricated identity). CENT/CENTA are an
      EVIDENCE_CONFLICT the identity plane owns; a seat assertion does not resolve a conflict.
  - option: Date the store alias rows from first-seen collection dates to close G2
    why_not: >
      A collection date is not a binding effective date. The ALIAS ruling keeps store rows undated; a
      fabricated valid_from is exactly the backfill the degraded path forbids.
  - option: Move the probe's frozen defaults (cutoff, digest, receipts path) to the 10-17 values
    why_not: >
      The 10-07 receipt and readiness artifact are reproducible only against the frozen constants; the audit
      tests pin them. Explicit flags keep both runs reproducible.
  - option: Do nothing until a vendor PIT identity feed or SEC/EDGAR collector exists
    why_not: >
      Procurement is a Chairman money gate and the collector is a recorded future option, not a lane. Neither
      changes the counts at this cutoff, and waiting leaves 717 now-resolvable names excluded for no reason.
evidence:
  - "r1_readiness_probe.py --rev 1aeaf6874e4d3ed8d4f76205c236994ec7a3bcb9 --cutoff 2026-10-15T13:32:43Z --expected-universe-sha256 dae001f6...: universe 1502 sha MATCH issuer_id_resolved 1495 undated 1492 dated 3 cik_map 1497 openfigi 896 identity_resolution 776 source_clocks 0/0 attempts 11790 success 11461 partial 104 null 187."
  - "Widened-builder verification against the pre-widening security_master blob 362a32522f92a7cb180763d4bb5c97de865c4061 (2382 rows) vs main 452fe313fa8d1904539128edbc8fb2fdd7d861d1 (3105 rows): 0 ids removed, 723 added, zero value changes in existing rows. issuer_state at main: RESOLVED 1931, NO_ISSUER_EVIDENCE 1171, EVIDENCE_CONFLICT 2, DEFERRED_IDENTITY_EXCEPTION 1."
  - "Spine clocks at main: security_master ingested_at max 2026-10-15 12:31:14, vendor_aliases ingested_at max 2026-10-15 13:32:43 (the cutoff). Constituent files last changed by 9fd048df0ebf (daily collection 2026-10-15), universe 1503 -> 1502."
  - "Before the pass-through repair the probe raised IdentityError 'known_at: explicit aware decision/evidence clock required' from lib/dataos/identity.py on the polygon MU row (NATIVE_REFERENCE_VENDOR); the repair passes the four fields verbatim."
  - "test_information_to_price_audit.py: 39 passed against the patched probe before the new tests were added."
  - "The refreshed probe run at the PR head is committed as research/alpha_intelligence/expectation_market_dynamics/R1_READINESS_2026-10-17.json."
affects:
  - "WS:ALPHA-INTELLIGENCE-INTEGRATION"
  - "research/alpha_intelligence/expectation_market_dynamics/**"
confidence: high
reversibility: easy
decided_by: "seat: fable program-ceo session 2fc05761 (WS:ALPHA-INTELLIGENCE-INTEGRATION owner), under the Chairman autonomous directive of 2026-10-06/10-07"
decided_at: 2026-10-17
---

# R1 degraded receipt refresh at the post-widening cutoff

The upgrade path written into DEC:ITP-R1-COMPLETE-DEGRADED-2026-10-07 was "issue the prospective owner
receipt upgrading the resolved names to CLOSED". Measured, the widened builder does not reach CLOSED on any
gap, so the lawful act is a refresh of the degraded receipt with the new counts. The refresh is prospective
only, backfills nothing, mints no rights class, and keeps financial_influence, k3e_admissible and
promotion_eligible false. The 7 names that stay unresolved are named in the receipt so a downstream study
can exclude exactly them.
