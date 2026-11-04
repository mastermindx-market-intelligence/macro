# Parent focus-restoration baseline finding

The v7 probe on unchanged Macro head ae6de4e56e2f826beab78f4de29fcaa89f27dbeb, ordinary baseline artifact and unmodified parent e45bde2cac07ac3b29285ff70c40d68900fad62c recorded a genuine pre-existing failure. The parent saved and delivered INIT.restore {x:0,y:3299,focusId:"im-catalogue-library-search"}. After Forward, two samples after the correction window had exact scrollY3299, but focus was BODY with no ID. All source/runtime bindings and error checks passed.

The Library input is static (initially disabled), then enabled synchronously before iframe onLoad initiates INIT. The earlier hypothesis that asynchronous Library mounting explained this result is withdrawn.

Independent principal source review found a missing ordering guarantee: LegacyPageHost keeps a fresh iframe hidden/inert while loading; the bridge posts READY and immediately calls applyRestore in the same synchronous execution. Parent exposure follows receipt/render of READY. The initial focus call has no acknowledgement that exposure has occurred, and delayed restore corrections repeat scroll only. This strongly explains the observed baseline failure, but the artifact does not directly instrument inertness at the individual focus() call.

No parent/protocol/focus repair is added to the already-running R3 scope. Keep baseline_parent_restoration_v7 unchanged. The v8 driver separates exact scroll restoration, focus restoration and absence of a new controller focus steal. It tags only the exact previously observed BODY outcome as known baseline evidence; it still counts that focus outcome as FAILED and keeps the overall exit nonzero. It separately reports repair-scope failures for narrow navigation review. A new/different focus result does not inherit the baseline annotation.

This does not claim full parent focus-restoration acceptance or production readiness. Reconcile the focus defect as a separate bounded follow-up after R3 returns and its source/evidence are reviewed.
