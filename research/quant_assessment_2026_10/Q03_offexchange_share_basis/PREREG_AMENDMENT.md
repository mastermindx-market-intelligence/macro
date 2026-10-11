# Q03 PREREG_AMENDMENT 1 (written BEFORE any evaluation stage ran)

PREREG.md stays frozen (sha256 `ca5e84bd6dc3fe074bcfc777707b55889e3dcb7f90da64d862c7ac6a8f1443f9`).
This amendment was written after the freeze and before evaluate.py had been run even
once. It therefore reflects no outcome. It adds no gate and changes no gate.

## A1.1 Incumbent break-fire comparator (descriptive, §6 item 2)

I re-read the incumbent's `share_break_index` while implementing evaluate.py.
- It returns only the LAST index i at which the rolling-20 median ratio,
  med[i] / med[i−20], crosses 1.8 or 1/1.8.
- For a level break at row k, that ratio stays crossed for i roughly in [k, k+39].
- So the returned index sits AFTER k, not within ±3 rows of it.
- The preregistered "fires within ±3 rows of the effective row" count therefore
  understates the incumbent's detection.

evaluate.py reports BOTH:
- (i) the preregistered literal count (returned index within ±3 rows of the effective row);
- (ii) a non-confirmatory count: the returned index falls anywhere in [k, k+39] of the event
  window.

Both are descriptive comparators only. Neither enters the KEEP/REJECT rule (§10).

## A1.2 Implementation clarifications (no parameter change)

- **Vintage actions with effective date ≤ the first joined row** are dropped before calling
  the adapter. They cannot affect any row (the adapter applies an action only to rows
  strictly before its effective date). Eligibility rule 5 still uses the full action list.
- **Store entry without a `fetched` stamp**: the attestation horizon is undefined. The ticker
  is reported as attrition `NO_FETCHED_STAMP` and is never used as an event or a control.
- **Control post rows** are restricted to rows ≤ H_c (the general §2 clock rule).

---

# Q03 PREREG_AMENDMENT 2 (POST-RUN provenance note; FINISHER role)

Written after both preregistered runs and after the independent audit (PASS_WITH_FIXES,
0 blockers / 0 majors / 6 minors). It records provenance only. It adds no gate, changes no gate
and no parameter, and triggers no rerun: the PREREG §11 stop rule allows one baseline run and
one primary run, and both already happened (RUNS.log lines 1–2, exit 0). Amendment 1 above is
unchanged. Its sha256 before this section was appended was
`49ba88d63f8211ed3193c5803241d6a986e45ede0caecf2ba404682678326413`.

## A2.1 Module bytes: the shipped module is the evaluated module

- FREEZE.log, PREREG.md header and both RUNS.log lines record module sha256
  `193c006ceba46274a20cab03d74a831801af96189300e6f6865a3e7a0d52d6ca`.
- At 09:44:08Z, after the primary run, the author rewrote only the module `__doc__` text to embed
  the verdict numbers. That produced sha256
  `0b36697890a16af2999471b61be026b85a1083b381aa87d046a7d693a6e9c729`, and that file was
  the one handed off.
- The finisher restored the module to the evaluated bytes `193c006c…d6ca`. The source was the
  author's saved copy of the module as it was at run time. The restored file's sha256 was
  re-checked as `193c006c…d6ca`.
- Transition: `193c006c` (freeze and runs) → `0b36697` (post-run docstring edit, never
  evaluated) → `193c006c` (shipped).
- The verdict numbers now live only in VERDICT.md, not in the module. The module docstring points
  to VERDICT.md.

## A2.2 evaluate.py hash trail (post-freeze edits before the first run)

The independent audit's 30-second witness saw these evaluate.py states after the freeze
(09:38:13Z) and after Amendment 1 (09:39:50Z), before the first logged run:

| state | sha256 prefix (witness) | seen at |
|---|---|---|
| 1 | `03310f17` | 09:40:50Z |
| 2 | `7b8dbda2` | 09:42:50Z |
| 3 | `48dea05f7eb518468f0434d1fda6010a29937046e6d4bfbdf0ece4657ca756d5` | baseline at 09:43:07Z; both runs |

The author recorded no reason for edits 1→2→3. These were implementation edits made while
evaluate.py was being written, before it had produced any logged output. RUNS.log began at
952 bytes holding only the baseline line, so no earlier logged run exists. The 30-second witness
cannot exclude an unlogged run between 09:42:50Z and 09:43:07Z, and that remains a stated gap.

The shipped evaluate.py is byte-identical to the run version, `48dea05f…56d5`. The finisher did
not edit it. Editing it would have required a third run, which the stop rule forbids.

## A2.3 Binding module hash for any future rerun (not enforced in code)

evaluate.py refuses only when the PREREG hash changes. It records the module sha256 but does
not compare it. Any future rerun of this evaluation is valid only if
`sha256(engine/offexchange_share_basis.py)` equals `193c006c…d6ca` as recorded in FREEZE.log.
Any other module sha requires a new hashed amendment naming it.

## A2.4 Gate (c) is a construction invariant, not an empirical test

For controls with an empty action list, corrected participation is `num*1.0/den` and raw is
`num/den`, so they are equal by construction and gate (c) cannot fail. It is relabelled in
VERDICT.md and REQUIREMENTS.md as a construction invariant that confirms the adapter leaves
nonsplit names untouched. It is not independent empirical evidence. The KEEP rule is
unchanged, because gates (a), (b) and (d) are discriminating.
