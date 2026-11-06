# Review harness preflight correction

The first independent review execution (terminal chunk `e93919`, exit 1) selected the earlier tuple assignment `prior_date, prior = _first_populated(prior_slice)` when extracting the scalar default statement `prior = prior or {}`. The selector searched nested target names, so it matched both forms. The later isolated stored-row fixture lacked `_first_populated`, exposing the mistaken extraction as a `NameError`.

This attempt stopped before producing `REVIEW_RESULTS.json`. Its intermediate checks are not accepted evidence. The review now selects a direct scalar `Name` target for the prior default; tuple-aware selection remains appropriate for the native current and prior lookup assignments. The corrected harness executes the native stored-row construction with the supplied prior pair and then invokes the pinned consumer.

This was an extraction error in the independent review harness. The sealed collector, probe, results, memo, and earlier review packages were not edited. Final validation records the corrected execution separately.

The first pre-seal custody check (`06d3ce`, exit 1) also caught a one-character transcription error in the independent verifier's expected vintage-acceptance manifest hash (`...842e8513...` instead of the previously sealed `...842d8513...`). The expected constant was corrected to `8fa6b5fdcc7cea12842d8513e07c05088df15f0f0c2c0b1bf014e98e9381256e`. The vintage package was unchanged. This custody precheck does not alter the 39 semantic review results.
