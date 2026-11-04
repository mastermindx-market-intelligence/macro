# International Markets — actual Shared Shell reproduction, 22 October 2026

## Result and continuation

**The projected Data & tools link defect is reproduced against the unmodified published International artifact under the real supported Terminal parent.** First and repeated activation accept the parent URL but leave the outer `#intl-analysis-tools` disclosure closed. This is now browser evidence, extending the earlier source-only finding in [SHARED_SHELL_ACCEPTANCE.md](../main_composition_20261021/SHARED_SHELL_ACCEPTANCE.md).

The observation completed with **8 passing controls and 2 failed disclosure assertions**, no page exceptions and no console errors. The driver exits zero when observation completes; that exit is not an all-tests-passed result. `observation.json` explicitly records `reproduced_failure`.

No product repair was attempted. Both owned test servers have stopped, and ports 3100 and 3102 were free on the subsequent read. The interrupted scratch repair remains unresolved on its original run. This evidence generation was independent of that repair and did not consume any uncertain patch.

## Exact binding

| Item | Identity |
| --- | --- |
| Published International subject | `64c1903c0e3193314b27edca3b662263783a9302` |
| Product build source | `c2b0562234abbec883ea91b934ac3d09fa3bae8b` |
| International HTML SHA-256, including actual child responses | `0d8beabc188333c4bb12d420c4de92c4a7ecaa9e52400fcc577067b7f4f41df8` |
| Bridge response SHA-256 | `048314d5a56e2eb639262829b2b54a5419fd92532c392b85668d3c717c0b653d` |
| Shared Shell CSS response SHA-256 | `b1918ccaa2294f18c0fd5bca123e38267251c7e9d9a7c4fce1f296ef9e4c3c1e` |
| Terminal parent source | `e45bde2cac07ac3b29285ff70c40d68900fad62c`, isolated detached worktree |
| Parent tracked source | Clean before and after execution; no source overlays |
| Parent lockfile SHA-256 | `c8bd178646d6ee83c463c6c8f77a6b277ddfd2e5d80f60395b4b747a9cecd1c1` |
| Dependencies | Next 16.2.9, React/React DOM 19.2.4, Playwright 1.61.1; copied from an installation with the same lockfile |
| Actual runtime build marker | `development` |
| Actual registry digest | `5307ea5a7964fde609a8f20f1af30b6bf483b7631f7232e5db74f9ef1d710023` |
| Registry file SHA-256 | `cdf744b60adb4c6c88c859389657640984238ff4f9b515443d5c6a78468924f9` |
| Protocol / bridge / document | `mmx.shared-shell.v1` / `20261018.1` / `20261018.1` |

The actual parent status endpoint returned enabled=true and the matching versions/registry. It was not stubbed. The source-owned `next.config.ts` sets its normal development build marker; the requested `NEXT_PUBLIC_SHARED_SHELL_BUILD` environment value in the startup record was overridden by that configuration and is **not** claimed as the observed build identity. Parent client response hashes are retained in `observation.json`.

The parent was `http://127.0.0.1:3100`; the child was `http://127.0.0.1:3102`. Port 3100 is admitted by the unchanged bridge's local-parent allowlist. The parent used its documented development-only `TERMINAL_E2E_FIXTURE`, guest fixture cookies and loopback legacy-origin configuration. No real session or credentials were used. No status response, INIT, NAVIGATE or acknowledgement was fabricated. Passive message listeners recorded the actual exchange. The browser's external-request blocker recorded zero blocked requests.

## Observed journey

| Check | Result |
| --- | --- |
| Parent entry to Japan via `#imc-country-JP` | Pass; Japan opens |
| Child rail selection of Taiwan | Pass; Taiwan opens |
| Country selection creates one parent history entry | Pass; delta 1 |
| Country selection retains child generation | Pass |
| First real projected Data & tools click opens the wrapper | **Fail; closed** |
| Tools click retains child generation | Pass |
| Tools click creates one parent history entry | Pass; delta 1 |
| Repeated projected Tools click opens the wrapper | **Fail; closed**, with no extra history entry |
| Parent Back returns to Taiwan | Pass; Taiwan open in a fresh generation |
| Parent Forward returns to Tools | Pass; wrapper open in a fresh generation |

The failing link was actually projected to `http://127.0.0.1:3100/intl.html#intl-analysis-tools`. Its real `LOCATION_ACCEPTED` acknowledgement was observed for `req-2` in the retained generation. The initial and repeated failure screenshots have identical SHA-256 `3215def408dc8b5efaa2ec90a87e4850cae1c6fe0e14661e07512f3cbdb4fe1d`.

The integration owner inspected `03-tools-first-click.png` and `05-forward-tools.png`. The first visibly confirms the collapsed disclosure. In the Forward screenshot the disclosure is below the viewport; its open state is established by the recorded DOM, not by that image. No full independent visual approval is claimed.

## Verification scope

This is an actual local parent/child integration reproduction at **1440×900, English, dark** in fresh headless Chrome; the exact browser version is in the observation. It is not public beta, DNS/TLS, authenticated or production acceptance. Tablet/mobile, Chinese/light and nested-legacy journeys were not exercised in this slice. They remain in the repair acceptance contract. The source-correct fix should be followed by focused tests and the applicable full parent/child matrix.

The unchanged child is the retained-input build with 510 inputs and 43 assets. This observation does not establish new data acquisition or backfill, and it does not replace the frozen proposal/source trace or its original approval scope.

## Hosted CI on the product subject

[CI 39703692187](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39703692187), all twelve packs and final ci-gate passed for subject `64c1903c0e3193314b27edca3b662263783a9302`. [Fences 39703692091](https://github.com/mastermindx-market-intelligence/macro/actions/runs/39703692091) and the active main authority context also passed.

The retained `ci_semantic_evidence_subject_64c.json` is the decoded final gate receipt: clear, 136 selected logical jobs, 387 passed step classifications, zero infrastructure findings. It binds merge `e6305e3650205af88fc48ff3ce244e235f46cc16`, base `b1db9655d21db67dcc601bff7473f57887593bbf`, plan digest `3ddc87228e0fb8e85ab9cb760161a47895c27d527b084c94048fdb6f40170270` and semantic evidence digest `c857db47cec8cb7e0ef6d60a33ce570191bdc34e0d436330236e5fbd577b8373`. The semantic digest is distinct from the retained pretty-printed file's byte digest in the manifest. These results do not claim that every job in the 348-job manifest ran.

## Custody and exact next action

The original scratch-only repair request remains `intl-20261021-shell-country-repair-r1`, root `01a1101f-2a37-7320-9a9b-5df3ce1b890d`. The existing [effect-fence review](../main_composition_20261021/EFFECT_FENCE_REVIEW.md) still applies. This reproduction neither retries nor supersedes that request.

Separately, the user reported a later accidental resumption of the archived predecessor chat and a worker titled **Release reconciliation 20261021**. Its exact worker identity and terminal/effect receipt remain unrecovered. The older 21 October 01:39 UTC package cannot stand in for that later receipt. The original International workspace and remote were both clean at head 64c before this evidence-only addition; this is a bounded observation, not proof that no older worker executed.

The next modifying action is the bounded country-controller repair for the real projected Tools link, with matching actual-parent regression proof. It requires original repair receipt/custody reconciliation or an applicable explicit owner supersession. No new repair worker, Ready transition, merge, deployment, restart of production, FX acquisition or release watcher was started.

## Reproduction materials

The retained driver `observe.cjs` is the exact executed script. It expects its original location `<isolated Terminal worktree>/intl-proof-evidence/observe.cjs`, resolving Playwright from `../terminal/node_modules/playwright`. The existing child artifact directory is recorded in `runtime.json`. The HTTP qualification, real message/DOM snapshots, response hashes, screenshots, server logs and confirmed shutdown receipt are included. The runtime was intentionally stopped after observation; these files do not imply a live test server.
