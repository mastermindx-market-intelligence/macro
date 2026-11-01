# SEAL_AND_BUDGET — sni s1_residual v1

HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met. Sealed BEFORE any outcome. Authority flags all false.

- lane: s1_residual vv1
- BASE: 5ef7a7f39f99232bf9b574c7603da1011ee3af66
- branch: claude/sni-s1-residual-20261011
- input_ref: 5ef7a7f39f99232bf9b574c7603da1011ee3af66
- prereg_digest_sha256: c26b09b68737ab86fa076b4a64c7e2d92459d4e8fd140e1e1b2f2e0c3439f7ab
- trial_ledger_path: research/single_name_intelligence/runs/s1_residual/trial_ledger.jsonl

## Labels (D1)
- HISTORICAL-DESCRIPTIVE (non-confirmatory); REG §2 not met; nothing here is a forecast, a signal, or authority
- vintage-unpinned, non-evidential / BLOCKED-AS-EVIDENCE (M0 gap 1)
- identity = RETROSPECTIVE JOIN (A07), identity_resolved_as_of = security_master ingested_at

## Families, budgets, itemized grids, REG §8 mapping

| protocol | family | declared budget (floor) | itemized grid | REG §8 canonical |
|---|---|---|---|---|
| P01 | sni.s1_residual.P01 | 6 | 6 | sni.s0.P01 |
| P02 | sni.s1_residual.P02 | 4 | 12 | sni.s0.P02 |
| P03 | sni.s1_residual.P03 | 4 | 21 | sni.s0.P03 |

Itemized grids: P01 2 baselines x 3 h = 6; P02 2 subjects x 2 baselines x 3 h = 12; P03 6 BABA cohort + 3 challenger + 12 HK-descriptive = 21.

## Membership table (protocol, subject, h, split)

| protocol | subject | h | split | count | membership_sha256 |
|---|---|---|---|---|---|
| P01 | adr_baba | 5 | PURGED_TRAIN | 1 | 1798abe2484709f57a651ebc736a2e2f067a17f00504c3516d7051491329134a |
| P01 | adr_baba | 5 | PURGED_TUNE | 1 | f148db7d204936f33dc5541a628b2702b0f2a08faefc2ea8b5d017b3a9466414 |
| P01 | adr_baba | 5 | QUARANTINE | 1 | b23c04af2dc7d6a0f23fb3f44dcf25e31d1400256d6d92386f5cacac8a3ec77f |
| P01 | adr_baba | 5 | TRAIN | 347 | a74a632314b78a5051ddac6e622f0f74be9d9bd49fa4d4ec1598cd5e3719a097 |
| P01 | adr_baba | 5 | TUNE | 114 | 9bc90c4d68c2a964cd38e756dd249564d221a13f4035600f333bfc94c7f56da5 |
| P01 | adr_baba | 21 | PURGED_TRAIN | 1 | 52467034b45b2c3943e38e976f1f3b9d28e9e2f5749fe0c27c00ac6cb134d46c |
| P01 | adr_baba | 21 | PURGED_TUNE | 1 | 73ceb5ed1cd1fc23536135fd50e84b214dac8d53bbe872cd01fdb37064bb79b9 |
| P01 | adr_baba | 21 | TRAIN | 94 | 8fe185843216059986f5e475ca287c7ce920421f32c60d432485a8c8cb91ba17 |
| P01 | adr_baba | 21 | TUNE | 31 | 06c2446afa46cb68821f5afe928bf7792360de38529698fb6d1aad77e7bda510 |
| P01 | adr_baba | 63 | PURGED_TRAIN | 1 | c49b79c21699c521db1dab2c1cfd6879154739e206070f1b3e0dceb8857822c7 |
| P01 | adr_baba | 63 | PURGED_TUNE | 1 | ba5591caaefde5fcd21e57dede55ad31f01135583b0a195b0fe468fe388d8133 |
| P01 | adr_baba | 63 | TRAIN | 32 | 53f07e57dc5145a79c2e92051e2f4426f759b92571603d111dd58dfa9076e4c3 |
| P01 | adr_baba | 63 | TUNE | 10 | ab7323ec976800473cb14e11bdd64a5535201a88a9edf6fbbe35b9850470526e |
| P02 | hkd_0700 | 5 | ABSTAIN_RESOLVER_NONE | 360 | 4a81498901956b1da38ef3f4b82388ca85c23522484da55fa21565e7bd8b4d8a |
| P02 | hkd_0700 | 5 | PURGED_TRAIN | 1 | af428c49db4625dc5bac9678c6b11d060bef82d035e6762b2b192038a039bacd |
| P02 | hkd_0700 | 5 | PURGED_TUNE | 1 | d88b5df33d374bce2c7785d6e374f4203e66b43a4738c8563745bfa0302b8282 |
| P02 | hkd_0700 | 5 | QUARANTINE | 1 | f74734b50e268fd50a1008e60b8dd8e3109099dcb351e7798a3ed1c73268f178 |
| P02 | hkd_0700 | 5 | TRAIN | 407 | 15e08b13690a345d6a92fdc5bd4dceffd1bc54693bf40607150be1c8bcee5e3e |
| P02 | hkd_0700 | 5 | TUNE | 111 | 85cdf5454f187e53d8c495be313c25b004c33569b93d2d1688065ca413eaa5aa |
| P02 | hkd_0700 | 21 | ABSTAIN_RESOLVER_NONE | 98 | 90a9c9d247da63e4fd1020ca17e16ef8c959d872770f13fddfccd7716181f30c |
| P02 | hkd_0700 | 21 | PURGED_TRAIN | 1 | 6fc2b6ea55bbfaabf942de7b778321c7c31f717f8494df9d2fe457c610b4f2a8 |
| P02 | hkd_0700 | 21 | PURGED_TUNE | 1 | 189432742a8d6ee24c8288b20f9f867c5f94c8fb436e335bb724717a0bdb5c9f |
| P02 | hkd_0700 | 21 | QUARANTINE | 1 | 29ac6969c074d5937d8775eda691ec7f778ccc1056b3313193173de90c028255 |
| P02 | hkd_0700 | 21 | TRAIN | 111 | ea98de67378588d71e43233ece716fe5f1c91f8581899755a55a5bc70a3ebea6 |
| P02 | hkd_0700 | 21 | TUNE | 29 | f34cb11f8b1604082ed66d973497c5382864d89b77a37d38afde3fdd50f1a422 |
| P02 | hkd_0700 | 63 | ABSTAIN_RESOLVER_NONE | 34 | 4b6013553f09b807aa6f9c2cc8fb0be22b670be7ef47424a1cfcf443b9723d8a |
| P02 | hkd_0700 | 63 | PURGED_TRAIN | 1 | b3e3156240694b837b30dc40070489d53bc844884c2e29a54bd019bab6c087aa |
| P02 | hkd_0700 | 63 | PURGED_TUNE | 1 | b369c0a714ced80b83020ff8e581fb2fd081b6f9184deb7dfbe8971dcfa088f7 |
| P02 | hkd_0700 | 63 | TRAIN | 37 | 3f49baee54ff008220872bf37be99f9be9394e976bdd0d635d8d0dd7cf235334 |
| P02 | hkd_0700 | 63 | TUNE | 10 | 41221dbbdae80eb3b0721521f438635a78679f26f8c9977eebdf086c61c286c2 |
| P02 | hkd_9988 | 5 | PURGED_TRAIN | 1 | 49868c0ebcad294bd747f3b07fd0854655c1f120bbb1fe6fc56d742cf83fb764 |
| P02 | hkd_9988 | 5 | QUARANTINE | 1 | d22d961b7ec57ca7e7639ca0a3b0fcd7eff22d0be279a5ed84727b057bc155e7 |
| P02 | hkd_9988 | 5 | TRAIN | 125 | d6813de5b6b4c86490a940d285710593ec579c4f6f18e328a50452627fda7f51 |
| P02 | hkd_9988 | 5 | TUNE | 112 | 9995b84bb3577243ccb8a33f84613fba4d5b1c9fdfb63d672fcd221bf2f41150 |
| P02 | hkd_9988 | 21 | PURGED_TRAIN | 1 | 97a1d35b17a2bdad9c084f858d1c7096617d32bc3af5d8adfad0d5f5e4fc506b |
| P02 | hkd_9988 | 21 | PURGED_TUNE | 1 | 15893dbc2362fcd1eea6ce0fd3da888afde8b3d3837c65d9b693733436e96b08 |
| P02 | hkd_9988 | 21 | QUARANTINE | 1 | 2745941783805cb6038bbcc597da85776b4836030e1cfb47335078495743c4bd |
| P02 | hkd_9988 | 21 | TRAIN | 34 | 09e867fee8dbda33d41af876d1715f7b0bcb195434d9766b9eb482ef019f2889 |
| P02 | hkd_9988 | 21 | TUNE | 29 | 36fbfb97f368e64e9790096395accd141a70500cc88c3c3d79e8bf7324e61765 |
| P02 | hkd_9988 | 63 | PURGED_TRAIN | 1 | afa2efa4658018ae10a16bea17a9ff26f332f533eebaa2e9789d6e11656fe9dd |
| P02 | hkd_9988 | 63 | PURGED_TUNE | 1 | 42b303aad4248cfd2a606e7384ad47a04f58c934433469deb5a2b6eafc15448e |
| P02 | hkd_9988 | 63 | TRAIN | 11 | 5c21991c0971cef2da0faf7798e69eba1bf1518f8466e6e8630b7ec695850b4f |
| P02 | hkd_9988 | 63 | TUNE | 10 | e2695c6bbb7ecdcf80c14ddc7a13031818a93c83b0116386bb48baf095b52163 |
| P03 | adr_baba | 5 | PURGED_TRAIN | 1 | bd7820e5826ceec2e7963b6620e27a6f5890d3aff35a486108c1264a85bcb8f8 |
| P03 | adr_baba | 5 | PURGED_TUNE | 1 | e920026e16114152f4371244ddbc533878a4ca5f73461633e455b68b2c5d0937 |
| P03 | adr_baba | 5 | QUARANTINE | 1 | c165efa2d81f7c0f04ecc95a53946237659b7aad1e2cacbb9458b5f234b48c29 |
| P03 | adr_baba | 5 | TRAIN | 347 | 47e030d3f9012137e5faf8753331343f759ea1e2bf9e94d42c3dda1b8d6cd899 |
| P03 | adr_baba | 5 | TUNE | 114 | a2fbca39f96b83d6b413cc22e182d07566dc078041420857620592db7edbe78a |
| P03 | adr_baba | 21 | PURGED_TRAIN | 1 | 7f5a9316fe1b0496d0d47c2da87cdcf4649c5371114b889f5e1c6064a6d32999 |
| P03 | adr_baba | 21 | PURGED_TUNE | 1 | f97352476521e09479c8d8c07a88214d0e100e3bff9b060e6703cff321025e5a |
| P03 | adr_baba | 21 | TRAIN | 94 | 5ca9bc324eea822c9e311fe1298873cecd2b39666b2552476bdceb179657ef41 |
| P03 | adr_baba | 21 | TUNE | 31 | 2ac08b749e64a0d1a4cbaf70ab15b7a8bc0728ac574a7f30550a5968b3304006 |
| P03 | adr_baba | 63 | PURGED_TRAIN | 1 | 13eb3c7e431f290b2578b6c3310b41511b12554f6b63609aa54ddf0a33107d13 |
| P03 | adr_baba | 63 | PURGED_TUNE | 1 | 1ac0d394fe490a269acd305f1a36b36088da61f7c2addfaf4c0a5ad3340f620f |
| P03 | adr_baba | 63 | TRAIN | 32 | 18565a2f40ad814ed29b01f65067fd4766077ca7eefb8fa5ea7e96c0fa282b04 |
| P03 | adr_baba | 63 | TUNE | 10 | e22a8bdf6e2d7b255b6d9c372ffcb03c44d7fb602a546dea09f803e59c7fbc6e |
| P03 | hkd_0700 | 5 | ABSTAIN_RESOLVER_NONE | 360 | 1f7e7280da9f89e8c6a17b6368c02e134fa4eef3c5b508bafe7975f21905d151 |
| P03 | hkd_0700 | 5 | PURGED_TRAIN | 1 | 777e8fd26a6c53cfdd6f39f448acdc9bae8da9125989f40066c5983138f8f51c |
| P03 | hkd_0700 | 5 | PURGED_TUNE | 1 | 651dc9dc599892c71e6fe92191e19766da724c5d20b5ed3bd3eff8aab9056f1d |
| P03 | hkd_0700 | 5 | QUARANTINE | 1 | a845ce1b37fb398bc910685a087e80a4bfc65fad1df12947a3cdc4a7edc5e655 |
| P03 | hkd_0700 | 5 | TRAIN | 407 | b6e53b540553fb303c082919556f41a8ea8a74c35ad948bec15fd699db775266 |
| P03 | hkd_0700 | 5 | TUNE | 111 | 2b0e8c1580380f9d17f1be8a6db959359b42e83ab5579f81e6af38177bc91d3c |
| P03 | hkd_0700 | 21 | ABSTAIN_RESOLVER_NONE | 98 | 543490aaaf6d19deea45b1743bf9ac487b4fae91a0c5f2f23840f0a7f5e3ecff |
| P03 | hkd_0700 | 21 | PURGED_TRAIN | 1 | 0c4ff6f3320053ec5e502e67cb8e5382e437d1dbb4da86a50de085a2904dca9a |
| P03 | hkd_0700 | 21 | PURGED_TUNE | 1 | c76b230c83cc5228c7383cec2fe7eab19e547234650c871ac500cf7c63b9eaa3 |
| P03 | hkd_0700 | 21 | QUARANTINE | 1 | aa3f5fd7ec5c5e233fa675384d537b5552963f3087e16c89faa7d0f07b2fd1d9 |
| P03 | hkd_0700 | 21 | TRAIN | 111 | 9504143aabf74a2406ae596e7032c6515e8b0b98991c0be41f7947a7fab50f4e |
| P03 | hkd_0700 | 21 | TUNE | 29 | 77633dfcfb05bfb3e5be05d0030357481c8439d95ff697365dae290c393c4729 |
| P03 | hkd_0700 | 63 | ABSTAIN_RESOLVER_NONE | 34 | 8a64184532684491338c827cd56245b95fe2af6ab63f8f90d2c9c531ea8d68ec |
| P03 | hkd_0700 | 63 | PURGED_TRAIN | 1 | 9972c8f716950bcfcc8de85c5c380ecba4dc2edc446780e1c517fa21eb738977 |
| P03 | hkd_0700 | 63 | PURGED_TUNE | 1 | 7b5bbdb414b7ce9047e7d4fe8c9aafe3b5076f8376fb67809effe9f552b2dd3d |
| P03 | hkd_0700 | 63 | TRAIN | 37 | 7968ab0b5ec69d20cc4a1ae13087fd0313ccb39585f94bf4a958b883426cef0a |
| P03 | hkd_0700 | 63 | TUNE | 10 | 0fe9b117e8b35d5e49194c9df90dfdd1cc286900b5cf847cbc89cc33fd73a942 |
| P03 | hkd_9988 | 5 | PURGED_TRAIN | 1 | 908acc1a6a223c11dff37b56a5ef57990d23d21dd4d1c930737680ee29555ea9 |
| P03 | hkd_9988 | 5 | QUARANTINE | 1 | 2253aa4eaa7f4a01646bf301e56b221092b0057620f26c39a0a018a082f51613 |
| P03 | hkd_9988 | 5 | TRAIN | 125 | cddb0e4962176ac2883c15839d68d564d3adefc7d4fab32285e08290a6f1ebc4 |
| P03 | hkd_9988 | 5 | TUNE | 112 | 925dbcd38a54c93ac1178d6d50534ed471f025a71e976d9b754128b92ff510d8 |
| P03 | hkd_9988 | 21 | PURGED_TRAIN | 1 | 24988386417d1c6309892e1c927dea136f811c1fffc9727e2f6f918a96d49aeb |
| P03 | hkd_9988 | 21 | PURGED_TUNE | 1 | 557125db11242c11a8b786f71d07ff1dc432ba21c480deebc0872de31a6f3428 |
| P03 | hkd_9988 | 21 | QUARANTINE | 1 | dc2b45c6420a60eaf6c1353a363aefd227a4a641091d13d7e081bc5add81dadb |
| P03 | hkd_9988 | 21 | TRAIN | 34 | 676ce51fcef5a93bf02bfffbdb44814dd95fd87e52b4a8f4522a4268235fdf03 |
| P03 | hkd_9988 | 21 | TUNE | 29 | bced7731f7d0b36d7be8886ac74ebcbfe4b1a19843925b89537ca365422cff42 |
| P03 | hkd_9988 | 63 | PURGED_TRAIN | 1 | 90a2189d52f442d50123eb6db9c6f718f2243914bb2b84b9f30ac76f6674f63f |
| P03 | hkd_9988 | 63 | PURGED_TUNE | 1 | d2a62ee3b121760a78271c0f899fa0d403b63456d83ef2207e7c732fe946a2b0 |
| P03 | hkd_9988 | 63 | TRAIN | 11 | 38c0dd45d952fe3f77936675b4969be8ae50db5180725a824be7155f966e4c5d |
| P03 | hkd_9988 | 63 | TUNE | 10 | 065f491fcc505e4470dea5ad8d55e618d5403e1810650c94aef99f33bab9f899 |

## Manifest files

- `manifests/P01_adr_baba_21.jsonl`: 127 rows
- `manifests/P01_adr_baba_5.jsonl`: 464 rows
- `manifests/P01_adr_baba_63.jsonl`: 44 rows
- `manifests/P02_hkd_0700_21.jsonl`: 241 rows
- `manifests/P02_hkd_0700_5.jsonl`: 881 rows
- `manifests/P02_hkd_0700_63.jsonl`: 83 rows
- `manifests/P02_hkd_9988_21.jsonl`: 66 rows
- `manifests/P02_hkd_9988_5.jsonl`: 239 rows
- `manifests/P02_hkd_9988_63.jsonl`: 23 rows
- `manifests/P03_adr_baba_21.jsonl`: 127 rows
- `manifests/P03_adr_baba_5.jsonl`: 464 rows
- `manifests/P03_adr_baba_63.jsonl`: 44 rows
- `manifests/P03_hkd_0700_21.jsonl`: 241 rows
- `manifests/P03_hkd_0700_5.jsonl`: 881 rows
- `manifests/P03_hkd_0700_63.jsonl`: 83 rows
- `manifests/P03_hkd_9988_21.jsonl`: 66 rows
- `manifests/P03_hkd_9988_5.jsonl`: 239 rows
- `manifests/P03_hkd_9988_63.jsonl`: 23 rows

## Challenger universe (outcome-free census)

- files examined: 340
- admitted: 150
- rejected by reason: {"cap_break_unclassified": 1, "late_first_date": 187, "low_session_coverage": 0, "no_adjusted_close_column": 0, "skipped_benchmark_or_subject": 0, "stale_last_date": 2}

## Line-number drift noted (S0 never edited)

- S0 cites trial_ledger L48/L126/L159/L210/L214/L242; at BASE the same symbols sit at L49/L146/L202/L253/L257/L287.
- Sidedness GAP recorded: REG did not fix H0_2 sidedness; frozen two-sided at this seal (D6).
- REG §6 seal table stays empty here; the seat integrates the lane seal into REG §6.
- D4 interpretation note: manifests carry one row per (protocol, subject, h); the retirement ledger row cites one membership_sha256 assembled from the affected per-h digests (see run_s1).

## Outcome-free audit

- spy calls: ['index_dates', 'list_dir', 'schema']
- index_only: true (fail-closed otherwise)
