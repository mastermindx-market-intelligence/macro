COMMISSION PRO-RUN D - independent re-derivation of the Prophet beta-first evaluation

COGNITION_ROUTE: CHAT_INCLUDED_DEFAULT
CHAT_REASONING_MODE: PRO_MODE_EXCEPTION
WHY_PRO_MODE: an earlier headline from this evaluation was wrong and was reported to the Chairman; the corrected result needs a derivation that shares no code with ours.
WHY_NON_PRO_INSUFFICIENT: the task is a full independent implementation of a frozen protocol on real records, with bootstrap statistics and a judgment on which records are admissible; a short pass cannot do that reliably.
PRO_MODE_TASK_CLASS: ADVERSARIAL_JUDGMENT
EXPECTED_DURATION_MINUTES: 100
STOP_CONDITION: one comment posted on macro issue #11014 beginning "PRO-RUN D", or the full report returned in this chat if posting is impossible.

Commissioned by the Prophet programme CEO under the Chairman's direction of 2026-11-11. Research only, read-only on every repository and host. Authorized: one comment on issue #11014. No pull request, no push, no edit, no change to any plan, ledger or published file. Portfolio analysis here is paper-only and descriptive; nothing in your answer sizes or recommends a trade.

THE QUESTION
Prophet is Mastermind's published record of single-company trade plans. Over its first 64 sessions, did following those plans capture the market's return, beat it, or lag it - once plans that were never actually published on their stated date are removed?

WHAT IS FIXED
Repository (public): mastermindx-market-intelligence/macro
- The frozen protocol: branch fable/prophet-beta-eval-header-20261110, commit 07f1c9cd8c, files research/prophet_v4/beta_first_evaluation/protocol_header_v1.json (sha256 3be32166c7be5170c5153f7c6e66af02e988e88dda52167140e7ac12f30b2ada) and PROTOCOL_HEADER_v1.md. It defines the window (first return close 2026-08-10, last close 2026-11-06, 64 sessions), execution, costs, the comparators C1 to C7, the metrics and the statistics. Follow it exactly. Where it is ambiguous, state the ambiguity, choose the reading least favourable to Prophet, and show the other reading as a sensitivity.
- The data, all at the pinned commit b5a5c846f8b597d4c041e11c624b7fbf74684ffe: site/prophet/index.json and the per-plan files under site/prophet/plans/; data/prophet/ledger.jsonl, ledger_corrections.jsonl, ledger_quarantine.json, plan_corrections.jsonl; data/prophet/backfill_disclosures.json; data/yahoo/<TICKER>.parquet (column close is the adjusted total-return close, close_price is raw); data/breadth/sp1500_pit_membership.parquet. If the repository connector cannot serve a file, read the same path at the same commit from a Macro checkout on the host fleet through the Mastermind connector, read-only, and say which route you used.
- The admissibility rule: research/PROPHET_OUTAGE_BACKFILL_2026_08.md. Plans whose origination was an outage backfill (a replay of an earlier bake, or a reconstruction of a night that produced nothing) did not originate on the date their record names, and a reconstructed pick may never be presented as a live historical call.

INDEPENDENCE
Our own harness and its results exist on other branches and in other files. Do NOT read any file named beta_evaluation.json, any RESULTS file for this evaluation, engine/prophet_beta_evaluation.py or scripts/run_prophet_beta_evaluation.py until your own numbers are final and written down. Write your own code from the protocol. After your numbers are final you may read ours and list every difference, but you may not then change yours without saying so.

WHAT TO COMPUTE
1. Which plans are outage backfills, how you identified each one (which fields, which disclosure rows), and for each: its stated date, when it was actually instantiated, and whether it is a replay or a reconstruction. Say how many there are.
2. The incumbent Prophet book (C6 in the protocol) and passive SPY (C1), three ways: all plans as published; excluding every backfilled plan; excluding only reconstructions. For each: total return, excess over C1 in percentage points with the protocol's bootstrap interval, beta to SPY, average invested fraction, number of positions, worst drawdown.
3. Every other comparator the protocol defines that you can build from the pinned data, and for each one you cannot build, exactly why.
4. Concentration: the result with the single largest contributing position removed, and with the top three removed. Check the largest contributor's prices against a second public source and say whether they agree.
5. The event study the protocol defines, with and without the backfilled plans.
6. Whether the protocol's exposure-matched comparison can separate member selection from simply being invested in this window. If it cannot, say "not shown", and explain why that is different from "no value".

WHAT TO RETURN
One comment on https://github.com/mastermindx-market-intelligence/macro/issues/11014 whose first line is "PRO-RUN D" (or the same text as your final message here):
- Three sentences a non-specialist can act on: what the record shows, how sure we can be, and what it does not show.
- The tables above, with the number of plans and positions behind every figure.
- Every ambiguity in the protocol and the reading you took.
- After unblinding: a line-by-line list of where your numbers differ from ours and your best explanation of each difference.
- Your code, inline or on a gist, and every limitation you know of.
State negatives as plainly as positives. 64 sessions is a short record; say what it can and cannot support.
