---
workstream: "WS:GMI-FINANCE-INTELLIGENCE"
session: claude/finance-t11-connected-conformance, claude/finance-freshness-fail-closed and claude/finance-metric-closed-vocabulary (seat 938d17d6, worktree .claude/worktrees/finance-intelligence-e2e-7c27cd); T10 on claude/finance-t10-registration-adapter; follow-ups on claude/finance-composer-totality, claude/finance-evidence-refs-owner-only, claude/finance-valuation-anchor-scope and claude/finance-knowledge-cutoff-gate
model: opus
ended_because: complete
mission: >
  Seat 938d17d6 holds gmi-finance-fable-ceo-e2e-20260924-chairman-001 end to end. This wave
  closed the four Finance lanes that the Chairman hold on T4-T7 leaves open:
  - T10, the registration adapter onto the shared research shell (#8006).
  - T11, connected-state conformance of the dossier page on a contract-valid read model (#8009).
  - An inbound fail-open fix in the T2 projection's freshness coercion (#8113), reported by the
    Consumer Cyclical seat.
  - A latent owner-content leak at the read-model boundary (#8121). Round 1 closed the KEY channel
    (owner metric keys copied wholesale), found by making that seat's dead-guard finding reachable.
    Round 2 closed the TEXT channel that the independent Opus review found: str() or list() of an
    owner structure validates against the 91 schema sites typed only as a non-empty string.
  Four composer follow-ups then closed what those reviews left open:
  - #8130: the composer looks an owner value up only as a string, so a malformed owner value
    is refused by the contract, never by a crash.
  - #8134: the composer never mints an evidence ref. A slice no owner ref backs publishes no
    reading and no date (DEC:FINANCE-COMPOSER-NEVER-MINTS-AN-EVIDENCE-REF).
  - #8135: a slice publishes only its own valuation anchor and constraints, and a conflict
    reads the reading its plane publishes
    (DSC:A-SLICE-WIDE-REF-LIST-VOUCHES-FOR-A-VALUE-BORROWED-FROM-ANOTHER-SLICE).
  - #8138: the knowledge cutoff binds every reader. One gate where the inputs enter withholds a
    row that a knowledge clock dates past the cutoff, read both as the instant the contracts read
    and as the date the composer publishes. The registration adapter names and selects theme
    evidence through the same gate, a receipt reads DEGRADED when the cutoff withheld every row
    of its input, and a cutoff that names no instant is refused (DSC:A-KNOWLEDGE-CUTOFF-BINDS-ONLY-THE-READERS-THAT-APPLY-IT).
  Every lane except #8130 shipped through independent Opus review. Every lane carries a seat
  red-proof; #8130's is an in-suite positive control.
state_before: >
  At the 2026-09-25 checkpoint (WS next_action), the following were in place:
  - T1/T2/T3 (contract, composer and overlap) were merged.
  - The T8 shell, with its hydration and four live-proof fixes, was merged and production-proven
    at 1440/390 x dark/light x EN/ZH with keyboard.
  - The T9 Theme Tracker entry was live.
  The page stayed NOT CONNECTED behind FI_READ_URL = "". T4 store, T5 staging, T6 publish and T7
  route were HELD by the Chairman directive: integrate into #7870's shared base, never rebuild it.
  T10 and T11 were open lane PRs.
changed:
  - path: engine/sector_intelligence/finance_research_registration.py
    what: "T10 (#8006, MERGED 977dca136032). An adapter from an owner research bundle to the Finance evidence envelope, through the shared shell (#7870) when present. Owner omissions are a closed vocabulary. Evidence embeds the validator's returned copy. A broken validator fails as itself (DEC:FINANCE-REGISTRATION-OMISSIONS-ARE-A-CLOSED-VOCABULARY-AND-EVIDENCE-EMBEDS-THE-VALIDATORS-COPY). #8138 (MERGED fbd78d1242a3): compose and select_evidence name and select theme evidence only through the composer's theme_evidence_known_at, so an assertion the cutoff withheld is never named or selected, even when it shares a curation revision with one the composer read. _parse_seal_clock returns None on OverflowError, so a run clock outside a datetime's range is refused as sealed_input_unavailable:run_context; on main before #8138 the OverflowError escaped it."
  - path: tests/test_finance_research_registration.py
    what: "T10 suite. It includes the client_acme privacy probe, the closed-vocabulary test and the broken-validator parametrization. The owner-bundle round trip is a strict xfail until the spec's §8 sector_profile is adjudicated. #8138: test_a_withheld_assertion_sharing_a_consumed_revision_is_never_named_or_selected (two assertions on one curation revision, one retained after the run's cutoff) and test_compose_run_context_with_no_instant_is_sealed_input_unavailable (two clocks, each field)."
  - path: contracts/sector_intelligence/finance_intelligence_research.v1.schema.json, contracts/sector_intelligence/finance_intelligence_research.evidence.v1.schema.json
    what: "T10: the Finance research bundle and evidence-envelope contracts that the adapter validates against."
  - path: .github/ci/legacy-jobs.yml
    what: "T10: adds the adapter and its suite to the Finance job's scope and to its contract-tests step. This makes #8006 authority-changed, so its post-merge freeze clears only through a green ci.yml on a main descendant."
  - path: templates/finance_intelligence.js (+ site copy, stamp)
    what: "T11 (#8009, MERGED c58fdc16f116). Painters and drawer conformed to the contract-valid read model: correction shown as words; methodology from reported_derived_estimated; the Value row as an exact receipt (plain digits, any class); exposure-state and identity chips on the table and the phone card; card cells in column order; no sideways scroll at 390 px."
  - path: templates/finance_intelligence.css (+ site copy)
    what: "T11: the light chip base rule is wrapped in :where() so state colours win; slice-select overflow fix; house control radius token."
  - path: tests/test_finance_intelligence_hydration.py, tests/test_finance_intelligence_page.py
    what: "T11: paint tests on a composer-built, contract-valid document; a const+enum word guard over all 62 schema paths; per-call temp directories in the node harness."
  - path: mockups/evidence/finance-t11-conformance/
    what: "T11 connected-state evidence receipt: 24/24 cells (dark/light x EN/ZH x 1440/390, plus interaction cells) on a contract-valid synthetic document."
  - path: engine/sector_intelligence/finance_projection.py
    what: "#8113 (MERGED 740554259f51): _public_freshness publishes an unknown or absent freshness as NO_EVIDENCE, never FRESH; the conflict detector's internal flags keep their FRESH mapping. #8121 (MERGED 808432ecfb28): an owner metric crosses into primary_metric only through _METRIC_FIELDS, pinned to the schema's closed $defs/metric (it was dict(metric_in)); the docstring-advertised _FORBIDDEN_KEY_RE, which had no call site, now walks the whole document at emit with .search, authority_caps exempt, and names sections only. Round 2: owner text crosses only through _owner_text/_owner_ref (str, int, float or date, else absent) and owner reference lists only through _owner_refs (a real list or tuple, never a mapping), at every free-text site; both key walks recurse into tuples."
  - path: engine/sector_intelligence/finance_projection.py (follow-ups)
    what: "#8130 (MERGED f6dae649ee6d): owner values are looked up only through _owner_key, which returns a string or None, so a structure given as a source_family, a slice_id, a price_basis or a metric name no longer raises. #8134 (MERGED 88ca79a3f407): _slice_evidence_refs never mints a slice:<id> ref. A slice no owner ref backs publishes an empty list, and _withhold_unevidenced publishes its planes with no reading: an OBSERVED plane becomes MISSING, in words. None of its dates reach its freshness or common_as_of. The three helpers with no call sites are deleted. #8135 (MERGED 2a93791563bb): the valuation anchor is the slice's freshest dated observation filed under it (tagged, or untagged where only an absent or null tag is untagged), on or before the cutoff, tagged over untagged on one date. Constraints are published under business_scope. Each plane selects its reading once, and _conflicts_for reads the direction of those same readings. #8138 (MERGED fbd78d1242a3): the composer reads its inputs through _known_at_cutoff once, before any reader runs. A row is withheld when a knowledge clock (as_of, observed_at, published_at; a cell's evidence_date; a source's published_at, observed_at, retained_at) dates it past the cutoff, read as the instant contracts._parse_temporal reads and as the date the composer publishes. World clocks are never gated. The digest still covers the owner's whole snapshot. The packet, expectation and market receipts read DEGRADED when the cutoff withheld every row the owner supplied. A row clock that names no instant is judged by the date written in it, if any, and never raises. A knowledge_cutoff that names no instant (a time of day, or an offset that carries it outside a datetime's range) is refused with ValueError. The dates derived from the cutoff (common_as_of, staleness) are its date in UTC. theme_evidence_known_at is the public form of the theme-evidence gate, for readers outside the composer."
  - path: templates/finance_intelligence.js (+ site copy), templates/finance_intelligence.html.j2
    what: "#8134: the evidence drawer shows an evidence-none mount ('No evidence on file.' / '暂无证据。') when a reading cites no ref. The shell's show() skips a missing mount, so the new JS is safe on a page rendered before the template change."
  - path: tests/test_finance_intelligence_projection.py
    what: "#8113: five freshness tests. #8121: test_no_forbidden_keys walks with search and carries a positive control; a vocabulary drift pin against $defs/metric; a unit test for the projection; the plant-every-owner-record fence over all six fixtures; a positive control proving that both fences fire on a key the composer admits. Round 2: _extended_owner_inputs fills the four owner fields no committed fixture carries and two owner keys none carries (constraints, conflict_ids), SYNTHETIC and in memory; field-level and key-level coverage pins; the value fence (delete, empty or replace every owner value); a positive control restoring str() at the seam. #8130: test_a_malformed_owner_value_is_refused_by_the_contract_never_by_a_crash (the value fence has zero crash outcomes) and its positive control on an ungated owner lookup; the sparse-failing page test is marked needs_full_checkout(\"site\"). #8134: test_a_reading_no_owner_ref_backs_is_withheld across the conflict fixtures, test_a_withheld_reading_publishes_no_date, and the per-slice ref oracle _refs_outside_their_slice. #8135: nine scope tests, each red against f6dae649ee6d's composer (anchor slice, freshest, undated, null-only untagged, same-date tie, cutoff, the valuation and price conflict readings, constraints). #8138: eight cutoff tests, which with #8135's anchor cutoff test make the record falsifier's 59 cases: nothing dated past the cutoff reaches the document, across the fixtures; a late row in any gated input changes nothing but the digest, for each knowledge clock; a row known by the cutoff is read however far ahead it holds; the cutoff is an instant, and no published date passes it on either side of UTC; the zone the cutoff is written in changes only the cutoff published; a cutoff that names no instant is refused (three cutoffs); rows in any sequence (a deque, a tuple) are gated; and an input the cutoff withholds entirely is received as DEGRADED."
  - path: agentos/decisions/, agentos/discoveries/
    what: "Records for this wave: DEC:FINANCE-DOSSIER-SPEC-T11-ERRATA, DEC:FINANCE-ZH-MARKS-UNTRANSLATED-SOURCE-PROSE-NEVER-MACHINE-TRANSLATES and DEC:FINANCE-REGISTRATION-OMISSIONS-ARE-A-CLOSED-VOCABULARY-AND-EVIDENCE-EMBEDS-THE-VALIDATORS-COPY (this PR); six FINANCE DSC records (this PR); DSC:A-LEAK-TEST-OVER-A-CLEAN-FIXTURE-CANNOT-FAIL-PLANT-THE-OWNER-KEYS, DSC:A-SEALED-CONTRACT-CANNOT-SEE-A-STRUCTURE-STRINGIFIED-INTO-FREE-TEXT and DSC:PYTEST-EXPLAINS-A-FAILED-NOT-IN-OVER-A-LONG-STRING-WITH-A-SUPERLINEAR-DIFF (#8121); DEC:FINANCE-COMPOSER-NEVER-MINTS-AN-EVIDENCE-REF and DSC:A-MINTED-REF-SATISFIES-A-MIN-ITEMS-RULE-THE-EVIDENCE-DOES-NOT (#8134); DSC:A-SLICE-WIDE-REF-LIST-VOUCHES-FOR-A-VALUE-BORROWED-FROM-ANOTHER-SLICE (#8135); DSC:A-KNOWLEDGE-CUTOFF-BINDS-ONLY-THE-READERS-THAT-APPLY-IT (#8138). #8130 and #8134 also amended sibling records (DSC:A-SEALED-CONTRACT-CANNOT-SEE-A-STRUCTURE-STRINGIFIED-INTO-FREE-TEXT; DSC:TWO-ENDS-OF-ONE-POINTER-VALIDATED-IN-ISOLATION-BOTH-PASS-WHILE-IT-DANGLES)."
verified:
  - claim: "Before any of #8006, #8009 and #8113 merged, the combined tree passes every Finance suite. The tree was the T11 head plus the #8113 head (which includes main 46963311ba19) plus the T10 head. #8113's NO_EVIDENCE freshness breaks neither the T10 adapter nor the T11 composer-built paint documents, and no test is lost."
    command: "git checkout --detach 97583ec5ec08 && git merge eda7a47cf7cb && git merge 92e2df941d10 (throwaway 3015d8253927, never pushed); python3 -m pytest tests/test_finance_research_registration.py tests/test_finance_intelligence_projection.py tests/test_finance_intelligence_contract.py tests/test_finance_intelligence_hydration.py tests/test_finance_intelligence_page.py -q -p no:cacheprovider"
    result: "224 passed, 1 xfailed. Accounting: 126 + 1 xfailed (T10 command) + 5 new projection tests (21 -> 26 by --co) + 93 (T11) = 224."
  - claim: "#8113 merged and holds on main: the _public_freshness catch-all returns NO_EVIDENCE."
    command: "gh pr view 8113 --json state,mergeCommit; python3 -m pytest tests/test_finance_intelligence_projection.py -q -p no:cacheprovider at 740554259f51"
    result: "MERGED 2026-09-28T01:05:19Z -> 740554259f51 (ci.yml 36362985366 success on eda7a47cf7cb, an update-branch of 8ae77aec47c2); 26 passed."
  - claim: "#8009 merged and holds on main: template and site JS/CSS are byte-identical, and the stamps match."
    command: "gh pr view 8009 --json state,mergeCommit; shasum -a 256 templates/finance_intelligence.{js,css} site/finance_intelligence.{js,css}; python3 -m pytest tests/test_finance_intelligence_hydration.py tests/test_finance_intelligence_page.py -q -p no:cacheprovider at c58fdc16f116"
    result: "MERGED 2026-09-28T01:07:58Z -> c58fdc16f116 (ci.yml 36361941648 success on 97583ec5ec08); JS 5d792d0f131e, CSS 10d611672a38, stamps js?v=5d792d0f css?v=10d61167; 93 passed."
  - claim: "#8009 is live: the served page carries the merged assets and passes the connected-state shell checks in every theme, language and viewport."
    command: "seat t11_live.py (Playwright) against the production finance_intelligence.html at 1440x900 and 390x844, dark/light x en/zh"
    result: "2026-09-28T01:18:32Z: served css v=10d61167 and js v=5d792d0f byte-identical to committed; 35 PASS / 0 FAIL / 8 INFO; pageerrors 0, console errors 0, bad responses 0; theme and lang applied; scrollWidth == innerWidth at 390; the page shows the designed NOT-CONNECTED notice. A first check at about 01:10Z still served f286c5a4 (main@11022da936af, before #8009): pull timing, not a hold."
  - claim: "#7977, the 09-25 fix giving the Theme Tracker's Finance card a Chinese accessible name, is live. The WS record's former next step (1) is closed."
    command: "curl -s https://www.mastermind-x.com/state_of_themes.html | grep -o 'sector-deep-dive[^>]*>'"
    result: "2026-09-28T01:53Z: HTTP 200, 375,677 bytes; the card anchor carries aria-labelledby=\"fi-sdd-name fi-sdd-cta\" aria-describedby=\"fi-sdd-story\" and no literal aria-label, matching templates/_finance_sector_deep_dive.html.j2 on main."
  - claim: "#8006 merged and holds on main: the T10 suite passes from main's own bytes."
    command: "seat pr_fence.py 8006 de276a13f6d8 (FENCE: PASS, only the name-excluded merge-queue-pilot red); gh pr merge 8006 --squash --match-head-commit de276a13f6d82aba7f039e66f09e20db1a11afea; git checkout --detach origin/main; python3 -m pytest tests/test_finance_research_registration.py tests/test_finance_intelligence_projection.py tests/test_finance_intelligence_contract.py -q -p no:cacheprovider"
    result: "MERGED 2026-09-28T02:34:51Z -> 977dca136032 (ci.yml 36367915033 success on de276a13f6d8, a sweeper update-branch of fc9bf3497f62); 131 passed, 1 xfailed at 977dca136032. The xfail is the strict owner-bundle round trip pinned to #7870 (spec §8 sector_profile pending)."
  - claim: "Before #8121 merged, the owner-key leak was real and reachable on main, and the fix closes it."
    command: "seat probe $S/probe_forbidden_reach.py on 740554259f51 and on 6c78279feacb: plant peer_rank into every owner record, one FinanceOwnerInputs field at a time, across the default fixture and the five conflict fixtures; then compose and validate_contract"
    result: "Base: 35 planted, 35 composed, 0 refused, 4 leaked, all through financial_packets into primary_metric; the sealed contract raised on each. Fix: 0 leaked."
  - claim: "Each #8121 guard can fail: six mutations, each caught by a named test."
    command: "seat red-proof $S/redproof_metric.py: apply each mutation to the working tree, run the projection suite with -x, restore the bytes (sha256 verified)"
    result: "6/6 RED. M1 dict(metric_in) restored; M2 emit guard removed; M3 guard under fullmatch; M4 oracle under fullmatch; M5 vocabulary drops currency; M6 guard skips nested lists. The fence alone fails exactly the 4 metric-routing fixtures under M1."
  - claim: "Round 2 of #8121: the text channel was real on the round-1 composer and is closed on the round-2 head, and the fence's dedup hides no site."
    command: "seat census $S/value_fence_census.py and $S/redproof_r1_composer.py (6c78279feacb swapped in with inert _owner_text/_owner_refs shims, restored and checked with git diff --quiet); $S/nodedup_census.py with the per-fixture shape dedup disabled"
    result: "Round-2 head bc63cacac823: 847 mutations, 657 clean, 183 sealed, 7 refused, 0 LEAKED (11 owner fields, 121 field/key pairs). Round-1 composer: 29 LEAKED at 10 composer sites, each in a contract-valid document. Without dedup: 8,243 mutations; head 0 LEAKED; round-1 composer 52 LEAKED at the same 12 document paths. Reverting economic_effect to str() or conflict_ids to list() gives exactly one LEAKED at that site."
  - claim: "#8121 and #8130 merged and hold on main: the five Finance suites pass from main's bytes after both."
    command: "gh run view <run> --json conclusion,headSha; git archive f6dae649ee6d into a scratch directory; python3 -m pytest tests/test_finance_intelligence_projection.py tests/test_finance_intelligence_hydration.py tests/test_finance_intelligence_page.py tests/test_finance_intelligence_contract.py tests/test_finance_research_registration.py -q -p no:cacheprovider"
    result: "#8121 MERGED 2026-09-28T03:30:02Z -> 808432ecfb28 (ci.yml 36372329172 success on a37094ff1756). #8130 MERGED 2026-09-28T03:56:28Z -> f6dae649ee6d (ci.yml 36374358827 success on f54f654eb74f). 244 passed, 1 xfailed at f6dae649ee6d."
  - claim: "#8134 merged and holds on main."
    command: "gh pr view 8134 --json state,mergedAt,mergeCommit; gh run view 36378286865 --json conclusion,headSha; git archive 88ca79a3f407; the five-suite command above; then the eight Finance suites (adds test_finance_intelligence_site_wiring.py, test_finance_entry_points.py and test_finance_overlap.py)"
    result: "MERGED 2026-09-28T04:57:36Z -> 88ca79a3f407 by the merge sweeper (ci.yml 36378286865 success on 06810f844337, a sweeper update-branch of d275a9e72654; ci-gate passed and the only red was the name-excluded merge-queue-pilot). Five suites: 269 passed, 1 xfailed. Eight suites: 336 passed, 1 skipped, 1 xfailed."
  - claim: "#8134 is served: the script and the page equal main's bytes."
    command: "curl -sL https://www.mastermind-x.com/finance_intelligence.js | shasum -a 256; curl -sL https://www.mastermind-x.com/finance_intelligence.html | grep -o 'finance_intelligence\\.js?v=[0-9a-f]*'; grep -c 'data-fi-mount=\"evidence-none\"'"
    result: "Re-read 2026-09-28T08:14:20Z. The served finance_intelligence.js hashes to sha256 adca49e8e3c6c4b6..., equal to main's site/ and templates/ copies. The page stamps ?v=adca49e8, and its 55 data-fi-mount attributes equal main's site/finance_intelligence.html in order, including the one evidence-none mount. The render that covered it is bd02938891be (2026-09-28T06:03:55Z), a descendant of 88ca79a3f407. The page is not connected to a served read model, so no owner document rendered there, and no browser run was made."
  - claim: "#8135 merged and holds on main."
    command: "gh pr view 8135 --json state,mergedAt,mergeCommit; gh run view 36381519014 --json conclusion,headSha; the eight Finance suites on 2a93791563bb's bytes; the record's falsifier (DSC:A-SLICE-WIDE-REF-LIST-VOUCHES-FOR-A-VALUE-BORROWED-FROM-ANOTHER-SLICE) on those bytes, then with engine/sector_intelligence/finance_projection.py from 88ca79a3f407, then with only the constraints scope reverted"
    result: "MERGED 2026-09-28T05:53:26Z -> 2a93791563bb, merged by hand after the sweeper refused it on base_sha (ci.yml 36381519014 success on 42fdaa529a5e). Eight suites: 345 passed, 1 skipped, 1 xfailed. Falsifier: 9 passed on main; all 9 fail with 88ca79a3f407's composer; reverting only the constraints scope fails only test_a_constraint_is_published_under_the_slice_its_record_is_filed_under. The record named f6dae649ee6d as the composer to swap in, but with it the selection does not collect (1 error), so its falsifier now names 88ca79a3f407."
  - claim: "#8138 merged and holds on main."
    command: "gh pr view 8138 --json state,mergedAt,mergeCommit; gh run view 36399288335 --json conclusion,headSha; git diff --binary 2a93791563bb fbd78d1242a3 applied over 2a93791563bb's bytes, then every tracked file outside data/, site/, mockups/ and verify_shots/ (and every Finance-named data/ file) hashed against fbd78d1242a3's tree; the eight Finance suites on those bytes; the record's falsifier (DSC:A-KNOWLEDGE-CUTOFF-BINDS-ONLY-THE-READERS-THAT-APPLY-IT) on those bytes, then with engine/sector_intelligence/finance_projection.py from 2a93791563bb"
    result: "MERGED 2026-09-28T09:50:13Z -> fbd78d1242a3, merged by hand at the fenced head 7226623a7ecb once the round-3 review passed and every check had concluded (ci.yml 36399288335 success on 7226623a7ecb; the only red was the name-excluded merge-queue-pilot). Overlay: the 14817 tracked files outside the bulk trees, and every Finance-named data/ file, hash to fbd78d1242a3's blobs. Eight suites: 411 passed, 1 skipped, 1 xfailed. Falsifier: 59 passed on main; with 2a93791563bb's composer 49 fail and 10 pass, the ten the record names, and all three cutoffs that name no instant fail. DSC:A-SLICE-WIDE-REF-LIST-VOUCHES-FOR-A-VALUE-BORROWED-FROM-ANOTHER-SLICE still selects 9, and all 9 fail with 88ca79a3f407's composer; no other record's -k selection over the projection suite changed."
unverified:
  - claim: "The connected page renders a real owner document end to end."
    what_would_verify: "A production read route (T7, HELD) and FI_READ_URL set; then the 1440/390 x dark/light x EN/ZH + keyboard proof on live data, re-reading the ZH aria-labels."
unresolved:
  - "T4-T7 stay HELD by the Chairman directive until #7870 (the Semiconductors shared base) merges. The integration wave adapts Finance onto source_record.v1 / evidence_claim.v1 / sector_intelligence_packet.v1."
  - "The T10 adapter does not adopt #7870's owner-bundle wire grammar ^[a-z0-9_]+(?::[A-Za-z0-9_.-]+)?$. This is recorded as a gap on #8006."
  - "T10 _try_resolve_assertion still swallows any resolver failure. This was accepted in rounds 1-2."
  - "The Financials launch partial stays DORMANT until #7669 (basket_detail owner) merges."
  - "At 390 px the phone card omits basis, retained risk and evidence date. It shows populated cells only, like the spec's macro cards. Parity with the table row is out of T11's scope."
  - "The composer is stdlib-only. At emit it validates nothing beyond the change_pct/delta and score/rank key walks. The sealed contract is a complete KEY check and no check at all on owner content the composer has turned into a string, which is why owner text crosses only through the scalar gate (DSC:A-SEALED-CONTRACT-CANNOT-SEE-A-STRUCTURE-STRINGIFIED-INTO-FREE-TEXT). The forbidden-key pattern does not match camelCase (peerRank) or plural (scores) keys; on the metric path the closed vocabulary is the real closure."
  - "The composer is still not total over a malformed CONTAINER: a non-list observations value raises TypeError, and the macro matrix fallback refuses the whole document. #8130 closed the malformed scalar lookups (the value fence's crash outcomes are zero)."
  - "The operating plane still selects by as_of alone: an undated reading counts as the freshest and publishes a null clock over a dated one, and ties fall to owner order. #8135 moved that selection into _operating_reading, so conflicts read it, and changed only its tag rule: an operating observation with a falsy non-null tag no longer counts as company data, so no slice publishes it and no conflict reads it. The price plane counts an undated reading as the oldest. Since #8138 no reading a knowledge clock dates past the cutoff reaches either plane."
  - "An untagged observation reaches every slice from whichever packet it sits in. Right for one company; a composition carrying several companies' packets would need a company scope too."
  - "Between two valuation observations at the same specificity on one date, the later in the owner's order anchors."
  - "A one-shot row sequence (a generator) is gated once into a list, but the receipts count rows with len(), so a generator whose every row the cutoff withholds still reads READ over a MISSING plane. The digest serializes with json.dumps(default=str): a nested generator hashes by its address, so the digest is not deterministic, and a deque hashes unlike the same rows in a list. Both predate #8138; the round-2 review accepted deferring them to a container-totality lane."
  - "A knowledge_cutoff padded with whitespace is read by the gate, which strips it, and refused by the contract, which does not. The document is refused, so nothing leaks (#8138 round-3 review, NIT)."
  - "When the cutoff withholds every theme-evidence row, the registration envelope's limitations omit owner_input_absent:theme_evidence, because _build_limitations reads the raw inputs (#8138 round-3 review, NIT; next_actions)."
  - "A plane's evidence_refs is its slice's union, not the refs of the reading it publishes. Per-reading evidence waits for the shared base's evidence_claim.v1 (#7870) in the integration wave."
  - "Fleet tooling, routed rather than fixed here: python3 scripts/worktree_sparse.py clean --force deleted paths a sparse tree had added back with worktree_sparse.py add; git restore -- <path> recovered them."
  - "generation.rights_profile lists every family in the rights snapshot by name, including internal_only families. That is T2's accepted design, and family names are taxonomy identifiers, not research content. The integration wave should confirm with the shared rights owner that its family names are publishable."
next_actions:
  - "When #7870 merges, open the integration wave: first the adapter to the shared base's contracts, then the T7 serving route once it is accepted, then set FI_READ_URL. Nothing else in the shell changes."
  - "In that wave, the T6 publish step MUST call validate_contract on the composed document before anything is served. The composer does not run the contract, and the contract is the only complete KEY check (DSC:A-LEAK-TEST-OVER-A-CLEAN-FIXTURE-CANNOT-FAIL-PLANT-THE-OWNER-KEYS)."
  - "Optional, before the integration wave: one PR giving _operating_reading the anchor's rule (dated only, tagged over untagged on one date; the cutoff is one gate since #8138), and the price plane a stated undated rule. The conflicts follow, since they read those readings. Pin each rule the way #8135 pins the anchor: plant the reading the plane must pass over, with the opposite direction, in both orders, and a published reading that states no direction beside a passed-over one that does."
  - "Follow-up to #8138: compute owner_input_absent:theme_evidence in _build_limitations from _known_assertions, pinned by a test whose cutoff withholds every assertion."
  - "A container-totality lane: derive the receipts from the rows the gate kept and dropped instead of len(), and canonicalize unsized containers (a generator, a deque) before the digest hashes them. Pin both with a generator and a deque input."
  - "When #7669 merges, wire the Financials launch include as a one-line guarded include."
  - "Carry the deferred review MINORs into the integration wave: the 09-24 handoff list plus the T10 gaps above."
do_not_redo:
  - "T11 rounds 1-3d are accepted work. Do not re-spec the drawer receipt, the chips, the card column order or the enum/const word guard; the errata DEC records why the page departs from the spec's letter."
  - "Do not reintroduce QUALITATIVE as 'no number' on any receipt surface (DSC:FINANCE-QUALITATIVE-CLASS-DOES-NOT-MEAN-NO-NUMBER)."
  - "Do not replace the omission closed vocabulary with a shape filter (DEC:FINANCE-REGISTRATION-OMISSIONS-ARE-A-CLOSED-VOCABULARY-AND-EVIDENCE-EMBEDS-THE-VALIDATORS-COPY)."
  - "Do not let an owner mapping cross into the read model through dict(), ** or copy. It crosses through a closed vocabulary such as _METRIC_FIELDS, the way source records cross through allowed_top_level."
  - "Do not publish owner text through str(), an f-string, join or list(). Owner text crosses through _owner_text/_owner_ref and owner reference lists through _owner_refs; a new str() on an owner value is a leak until shown otherwise."
  - "Never mint an evidence ref. A slice no owner ref backs publishes an empty list, no reading and no date: withhold the reading's date too, not only its value (DEC:FINANCE-COMPOSER-NEVER-MINTS-AN-EVIDENCE-REF)."
  - "Use one scope rule per input kind: source records by business_scope, observations by slice tag, where only an absent or null tag is untagged (DSC:A-SLICE-WIDE-REF-LIST-VOUCHES-FOR-A-VALUE-BORROWED-FROM-ANOTHER-SLICE)."
  - "Apply the knowledge cutoff once, where the inputs enter (_known_at_cutoff); a reader outside the composer walks theme evidence through theme_evidence_known_at. Never add a cutoff check inside one reader, never select assertions by the curation revisions a document publishes (a revision does not identify one row), and never gate a world clock: a report period, effective_at or business validity (DSC:A-KNOWLEDGE-CUTOFF-BINDS-ONLY-THE-READERS-THAT-APPLY-IT)."
  - "Conflicts read the readings the planes publish. Never re-select observations inside _conflicts_for; a second selection drifts from the first."
  - "Look an owner value up only through _owner_key (a string or None). Never index a map or compare against a set with a raw owner value (#8130)."
  - "Do not build a Finance store, staging, publish or route (T4-T7) outside the integration wave. Never build a second identity, valuation, basket or rights owner, nor a theme graph or ledger."
danger_areas:
  - "templates/finance_intelligence.js is a PAIRED plain-copy asset. Every edit needs the byte-identical site copy and a restamped ?v= in site/finance_intelligence.html (python -m scripts.check_template_site_sync --fix)."
  - "The capture tool drives hover/focus/class/attribute only. The evidence drawer has no capture cell, so drawer changes are proven by the hydration suite, and an EVIDENCE.yml header must not claim byte-identity for assets changed after capture."
  - "An evidence receipt that claims coverage of a state family needs a schema walk over the capture document; the capture tool validates nothing (DSC:FINANCE-A-LABEL-MAP-ENTRY-IS-NOT-A-PAINTED-WORD)."
  - "Never write assert needle not in <composed document json> in these suites. A failing case takes about 130 s under pytest -q and reads as a hang; assert a precomputed bool (DSC:PYTEST-EXPLAINS-A-FAILED-NOT-IN-OVER-A-LONG-STRING-WITH-A-SUPERLINEAR-DIFF)."
  - "The plant fence skips maps keyed by data (rights_snapshot by name, and any dict whose values are all containers). A new scalar-valued map keyed by data makes it fail loudly with a false leak; skip it by name with the reason, never by weakening the plant."
  - "The value fence reaches only keys the fixture records carry. A new owner key the composer reads must be carried by _extended_owner_inputs or named in _COMPOSER_READ_KEYS_NOT_OWNER_CARRIED with its reason; test_every_owner_key_the_composer_reads_is_planted enforces it for .get(\"literal\") reads only. Its per-fixture dedup was verified to hide no site on 2026-09-28; if the composer starts selecting a later record of a list, re-run the no-dedup census."
  - "A per-slice REF oracle (_refs_outside_their_slice) cannot see a VALUE that crossed slices. Each per-slice read path needs its own scope test that plants an input filed under another slice and asserts this slice does not publish it."
  - "finance_projection.py is edited by several lanes at once. Two PRs that both touch the compose loop conflict textually (#8134 x #8135); resolve on the second, and re-run the eight suites on the merged bytes, never on a sparse tree."
  - "The Finance read-model contract compares no date with knowledge_cutoff. A reader that takes an owner input before _known_at_cutoff publishes late dates the contract accepts, and a sweep that moves every clock past the cutoff cannot see it, because every plane is then withheld as unevidenced. Only the per-row differential tests catch it."
  - "A cutoff is an instant, and the date it is written in can fall a day after that instant (2026-09-25T01:00:00+08:00 is 2026-09-24T17:00Z). Every date derived from the cutoff is its UTC date; the contract accepts a common_as_of after the cutoff, so only the composer's zone test catches the written date creeping back."
  - "All fixture numbers are SYNTHETIC. Never copy live research values into fixtures, static HTML or browser storage."
---

# Finance Intelligence — wave checkpoint 2026-09-27 (seat 938d17d6)

T10, T11, the freshness fix and the metric-vocabulary fix all closed through independent Opus
review, and four composer follow-ups (#8130, #8134, #8135, #8138) closed what those reviews left open. The page remains NOT CONNECTED by design until the integration wave, and the Chairman
hold on T4-T7 stands.

## Merges

| PR | lane | merged | main SHA | binding CI | proof rung |
|---|---|---|---|---|---|
| #8113 | freshness fails closed | 2026-09-28T01:05:19Z | 740554259f51 | ci.yml 36362985366 | MERGED + verified on main (no production reader) |
| #8009 | T11 connected-state conformance | 2026-09-28T01:07:58Z | c58fdc16f116 | ci.yml 36361941648 | PRODUCTION_PROOF 01:18:32Z |
| #8006 | T10 registration adapter | 2026-09-28T02:34:51Z | 977dca136032 | ci.yml 36367915033 | MERGED + verified on main (no production reader) |
| #8121 | metric closed vocabulary | 2026-09-28T03:30:02Z | 808432ecfb28 | ci.yml 36372329172 | MERGED + verified on main (no production reader) |
| #8130 | composer totality over malformed owner values | 2026-09-28T03:56:28Z | f6dae649ee6d | ci.yml 36374358827 | MERGED + verified on main (no production reader) |
| #8134 | the composer never mints an evidence ref | 2026-09-28T04:57:36Z | 88ca79a3f407 | ci.yml 36378286865 | MERGED + served bytes equal main (page not connected; no browser run) |
| #8135 | valuation anchor, constraints and conflict scope | 2026-09-28T05:53:26Z | 2a93791563bb | ci.yml 36381519014 | MERGED + verified on main (no production reader) |
| #8138 | the knowledge cutoff binds every reader | 2026-09-28T09:50:13Z | fbd78d1242a3 | ci.yml 36399288335 | MERGED + verified on main (no production reader) |

## The E2BIG episode (#8006)

#8006's first CI run (36360866211) went red on the self-mod fence. The failure was an E2BIG from
a depth-32 deepen that put about 372 KB of trailers on one argv. It was a CI-side defect, not the
PR's code. The head was refreshed by merging origin/main only: 92e2df941d10 -> fc9bf3497f62, with
the PR's hunks byte-identical. The fence passed locally, and the new run (36365425338) carried the
merge. The CI root defect was routed as a separate task rather than fixed inside a Finance PR.
The merge sweeper later update-branched the PR once more (fc9bf3497f62 -> de276a13f6d8), so a
merge bound to the old head failed with "Head branch was modified"; the seat re-fenced the new
head and merged it on its own concluded run (36367915033).

## The metric leak (#8121)

The Consumer Cyclical seat reported that the Finance docstring advertised `_FORBIDDEN_KEY_RE`
while the constant had zero call sites, and left reachability open. The seat's probe answered it:
four of 35 single-field plants reached the emitted document through `primary_metric`. Three things
looked like protection and none fired: the dead constant, a test oracle that used fullmatch on a
boundary-stem pattern, and a sealed contract that only a test ever ran. The fix is a closed
vocabulary at the one passthrough, plus the guard actually running. The integration wave inherits
one obligation from it: T6 validates the contract before serving.

Round 2 came from the independent Opus review, not from the round-1 fence. With the private keys
dropped, an owner metric mapping with no name fell back to `str()` of the whole mapping, and that
document now PASSED the contract: 91 schema sites are typed only as a non-empty string, so a
stringified structure (or `list()` of a mapping, which yields its key names) is invisible to it.
The class was closed, not the line: every free-text site goes through the scalar gate. The fence
became a value plant that deletes, empties or replaces every owner value in turn, and it was
extended until it reaches every owner field and every owner key the composer reads. The key-level
pin found two more unreached free-text keys (constraints, conflict_ids) on its first run.

## The follow-ups (#8130, #8134, #8135, #8138)

Each follow-up closed a gap that a review of the previous lane named but left open.

- **#8130.** The value fence's seven crash outcomes came from owner lookups that indexed a map
  with a raw owner value. Every such lookup now goes through `_owner_key`, which returns a string
  or None. A malformed owner value is refused by the contract, never by a crash.
- **#8134.** The composer minted a `slice:<id>` ref to satisfy the contract's rule that an
  OBSERVED plane cites evidence. It pointed at no record, so that rule could never fail. Now a
  slice no owner ref backs publishes no reading and no date. The page says "No evidence on file."
- **#8135.** The round-1 review of #8134 found constraints filed by a non-schema extra. A census
  then found the valuation anchor unscoped: a probe made one slice publish another slice's P/E,
  citing only its own ref, and #8134's per-slice ref oracle stayed green. Round 1 of #8135's own
  review found that the conflict detector still chose its own observation, so each plane now
  selects its reading once and the conflicts read it.
- **#8138.** A census after #8135 asked every other reader of a dated owner row whether it
  applied the knowledge cutoff. None did, and the contract accepted every document that
  published a late date. One gate now applies the cutoff where the inputs enter. The
  independent review took three rounds:
  - Round 1, FIX_REQUIRED. Theme evidence was ungated, the gate compared calendar dates where
    the contracts read an instant, a deque passed through, and receipts read READ over an input
    the gate had emptied. The seat's own review of round 2 then found that reading a clock as an
    instant could raise on an extreme offset.
  - Round 2, FIX_REQUIRED. The registration adapter filtered the raw assertions by the curation
    revisions the document published, so an assertion the cutoff withheld was named and
    selectable when it shared a revision with one the composer read (BLOCKING). common_as_of
    was the date the cutoff was written in, after its instant in a zone ahead of UTC (MAJOR). An
    extreme cutoff crashed (MINOR). A generator's receipt read READ (MINOR, deferred: the digest
    mishandles one-shot containers on main as well).
  - Round 3, PASS. The adapter reads the composer's own gate, the dates derived from the cutoff
    are its UTC date, and a cutoff that names no instant is refused. The adapter's seal clock no
    longer raises OverflowError, a defect main carried too. Two NITs remain, listed under
    unresolved.

#8134 and #8135 conflict textually in the compose loop. The resolution keeps #8134's
withholding after #8135's selection. Every conflict rule also requires the published plane, so
a withheld plane still draws no conflict; #8134's withheld-reading test pins it.
