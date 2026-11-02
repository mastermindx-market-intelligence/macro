# Publication preflight correction

Apply runner 016 failed at its control preflight, PID 8024, exit 1 in 14.38 seconds. It compared the branch's existing CI enrollment to the upstream-only manifest. No checkpoint file was written. Read-only reconciliation 017 subsequently verified the clean index/worktree, all 140 prior checkpoint files, 53 source pins, 71 owner pins and every control against both reviewed own candidates cbcc5ee143400af162a252e4faac0f06c7157e37 and 4caf1e2b1e58e3199ba5d63ebfa6563ef098eeff.

The accepted-upstream legacy-jobs.yml is 1,249,172 bytes, SHA-256 3aa5275a608bb9fe9b4c3b98ee42efdf2b06cfd806949752afc8f53dd5506668. The branch's already reviewed observation enrollment is 1,249,336 bytes, SHA-256 5cc24c46e7c4ed8b0b9525366a7069e86f546b32849c72cb8518320842d860cd. These are intentionally different artifacts. The other eight controls equal both upstream and the reviewed branch.

Runner 018 corrects that comparison by retaining the exact reviewed branch hash and requiring equality to both own commits for all nine controls. It changes no CI file, release policy or application source. The original failed runner and terminal tool-result value are preserved separately. The latter is an exact JSON-value serialization of the observed connector result, not a claim about wire-level response bytes. The failed attempt remains failed; the new application outcome is recorded only by its own actual receipt.

No test, provider request, authority promotion, Git reset, force operation or policy waiver accompanies this correction.
