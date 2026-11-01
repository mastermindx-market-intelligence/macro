# Completed verification

The core runner passed all 13 recorded checks in
`local_verification/verification.json`. The waiting-policy diagnostic passed
all 7 checks in `local_verification/mechanics_verification.json`. The exact
checks can be rerun through `study.py --self-test --out verification` and
`verify_mechanics.py`.

The final selection-lock SHA matches the original main-run record. The core
study code SHA matches the code recorded at selection. The transferred original
input manifest matches the original manifest hash from the main-run record.

Independent methodological review examined the protocol, core and diagnostic
code, primary/sensitivity results, and final narrative. It required repairs to
subgroup recall denominators, original-candidate retest credit in the waiting
policy, and one-block bootstrap handling. It also required that explicit-
opposition standardization use the full qualified base target distribution in
common-support cells. Those repairs were made and the affected diagnostics
rerun. The final review found no blocking factual, denominator or interpretation
error. No signal threshold or selection identity changed after outcome review.

The final PDF was rendered and checked for table overflow, orphaned pages,
page boundaries and figure legibility. Source numerical tables remain the
authoritative machine-readable record. The figures and report are derived
presentation artifacts.

The independent external data-audit worker failed its admission check before
task execution (`canonical_source_unreadable`, rc78); no audit result from that
worker was used. Direct source checks and native methodological review are
described separately and are not presented as that worker's output.
