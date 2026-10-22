# Published14ed hosted CI — owner-captured independent review

Reviewer:/root/intl_release_scope_adjudication, GitHub reads only. Snapshot delivered2026-10-22 about07:47Z. No rerun, mutation, message or reviewer artifact write.

Subject14ed4f12f31b71c63bbabd969aebbf9c4305ccaa; DraftPR9596.
ci39735499640 attempt1 remains in progress:10/12packs succeeded,pack11 failed,pack0 in progress. ci-plan and contract-delta succeeded. fences39735499502 completed success. ci-authority39735494186 completed success for active main context; inactive codex/merge-queue-pilot context rejection is recorded, not waived.

Concrete candidate failure: research-screener in ci-pack-11 job119681137422. tests/test_research_screener.py::test_fresh_bake_matches_committed_site_html atline668 compares a fresh bake with committed HTML after allowed banner removal. Committed shared_shell_bridge.js?v=048314d5 differs from fresh v=31b150d8. Candidate1failed50passed; replay on exactbaseaf0ba2d50a32c7a422508b442f35010dcdf154a2 passes51. CI_PACK_FAILED_JOBS=["research-screener"]. Reviewer verified testedmerge HTMLline9 independently.

Testedmerge edde354dd25b475028023ec854e2605b7e7fcb55:
firstparent af0ba2d50a32c7a422508b442f35010dcdf154a2
secondparent14ed4f12f31b71c63bbabd969aebbf9c4305ccaa
tree e9757429c9a677cceab635c9f10d1939c7012b64
semanticplan SHA256ce5649de842f0542cbe7b0da8ad9811474f1a807cc8a1a515b073dae52622b74.
Planner136/278 jobs,12packs,2336changedpaths.
Planartifact12406239726 ci-semantic-plan-39735499640-1 ZIPdigest6df35e0da0a8962dead1cb1a43957b785645237e5c0f3047216bd0b364efa0c6 (distinct from semanticplan hash).
PR/eventbase25051144947f027c698cd1ce10e3c8824ee6ade9 is not the executed base.
contract-delta job119680102285 passed06:49:55Z:0introduced0inherited againstaf0ba2d50a32.

Inactivepilotcheck119681053141: allowedtrue,reason same_repo_admin_authority_change,context_activefalse,context_allowedfalse,context_reason inactive_base_context.
Activemaincheck119681055343: context_activetrue,context_allowedtrue,success.

Observed protectedmain advanced to8182ec04c37adb44a698f1c1296f45b4d9ae960a timestamp07:31:47Z. Existing14ed CI neither covers local build-suite enrollment/query repair nor future main composition. Final generated outputs must match final bridge bytes via ordinary no-acquisition build/stamping. Newhead needs its own CI and testedmerge-firstparent contractdelta.

The prior same-head pack6 log confirmed1414 numerical/custody tests and416 countryevidence/publication tests passed. It did not execute the previously unrun tests/test_intl_build.py. Whole-run success is not claimed.
