# Owner-captured independent CI and current-main materiality review
Reviewer: native read-only /root/intl_ci_composition_review. The following is an owner-captured summary of the reviewer's returned findings; no GitHub review submission or release approval is implied.

## Published 9bf hosted failure
Exact source9bf7161b6c856a8df5eaa18a0b9ef8fbb1e206bb; CI39840840690; pack10 job120042966591. validated-claims-source found two comments in templates/intl_workspace.js (“validated state, serializedQuery, inspector attachment” and “the validated state stands”). Actual tested merge49be308c7644c3adb097aa07b721a57327f639af has parents039ee33cc084e7f94d45b90e68f66d4750c05ce9 and9bf. Candidate gate failed19:40:13UTC; exact-base replay passed20:02:02UTC. Only this logical job is listed failed in pack10. Checker unchanged; minimal two-comment wording correction is appropriate. Source gate command: python -m scripts.check_validated_claims --scope source. Checker blob e1da01abb84ba230a0d4ee9840975af0c5257997.
https://github.com/mastermindx-market-intelligence/macro/actions/runs/39840840690/job/120042966591

## Main651 and subsequent4f7
At20:05:57UTC, observed main651aacf064441f1db01fd716fa402182df065a84. Both main2d334 and651 manifests contain349jobs. Removing four added lines (phase:browser_setup and timeout-minutes:10 in ontology-explorer and unrun-brain-gateway) makes the new manifest byte-identical to the old. All8 International/Screener job blocks unchanged between those main revisions. New run_ci_pack supports the setup annotations and conservatively preserves uncertain process settlement; ordinary unannotated Intl job successful execution/digests unchanged. Manifest and runner must remain paired if composed. These changes alone do not require a fresh product-proof cycle or another ancestry-only main merge.

The source exporter adds an opt-in inventory-ref contract. Its default pinned path remains unchanged; it is outside this normal builder/actual-parent path.

At20:13:39UTC observed main4f7af93b28bf8883b0e531c67e2faa639ce3d14a. Its complete two-commit/five-file delta from651 is only Chronicle/marketing data. Concurrent PR9596 readback showed mergeable:true/unstable; an earlier false read was not reproduced and its cause is unproven.

## Generated Screener overlap
Compared complete immutable files:
- Common2d334 blobff8ce97ee19e07d7d8a42f0d310f67fb00931ba1.
- Candidate9bf blob74680ee1158327f92e6d2bf83b983cadce679630.
- Incoming651/4f7 blob13393e810aa19c434fbd33eea5f98adb7fe2de56.
Candidate changes only bridge048314d5→24d7bb10 and theme29ec9caa→d7be48a7 cache references. Incoming changes only title and bilingual Data as of caption2026-10-20→2026-10-21. No other bytes change. Company content/watchstoredd730491 remain unchanged; a date caption is not independent acquisition proof.
Expected disjoint composition:73864bytes, Gitblob39fc21b1f553bf23c87ebcd84895e7b23cc01ce1, SHA256f751e17df163fea1e92fcf4345817851472eafb5a25dae39e7314d5d98038997. Root's later exact bdeb+4f7 prospective tree191f19fcd08e7719b3052ff5f4de28aa9096026e matches this independent expectation.
https://github.com/mastermindx-market-intelligence/macro/compare/651aacf064441f1db01fd716fa402182df065a84...4f7af93b28bf8883b0e531c67e2faa639ce3d14a

## Other carriers and limits
Separate PR8754 remains Draft with overlapping source paths and scoped unresolved obligations; no permission to consume or overwrite. Separate PR9477 selected Compare-count correction is not present9bf; it is a source-confirmed UI gap, not a fresh browser reproduction or established mandatory dependency for9596. Preserve its separate carrier.
Review actions were GitHub reads and native in-memory calculations only. No Studio, edits, tests, external messages, review submissions, Ready transitions, commits, pushes, merges or deployments.
This review does not waive new immutable corrected-head review, exact-head hosted CI, RELEASE-INTL-FX-CUSTODY or RELEASE-INTL-SERVED.
