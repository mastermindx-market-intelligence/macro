---
key: VPS-MACRO-SHALLOW-ROOT-PINNED-BY-ISSUER-MANIFEST-CODE-VERSION
claim: >
  The /opt/macro production clone has exactly one shallow boundary, a13962ee (2026-10-12),
  and that commit is also the code_version of the promoted company-intelligence generation
  under /var/lib/macro-company-intelligence; qualify_component checks code_version with
  'git merge-base --is-ancestor' against HEAD, so re-shallowing the clone past a13962ee to
  save disk would make that generation fail with GENERATION_CODE_INVALID.
kind: constraint
verified_at: 2026-11-01
verified_by: >
  Read-only on 146.190.142.17, 2026-11-01 07:31Z-07:40Z: cat /opt/macro/.git/shallow
  (1 line); git -C /opt/macro cat-file -t and merge-base --is-ancestor for each code_version;
  grep -rhoE '"code_version"[^"]*"[0-9a-f]{40}"' /var/lib/macro-company-intelligence | sort
  | uniq -c, then grep -rl per value. Code read at origin/main a7628775265b:
  engine/company_intelligence/issuer_disclosure_owner.py accepts_revision and
  qualify_component.
scope:
  - macro
  - "VPS /opt/macro (146.190.142.17 production pull clone)"
  - engine/company_intelligence/issuer_disclosure_owner.py
  - WS:MARKET-OS
confidence: verified
type: discovery
status: active
workstream: MARKET-OS
summary: >
  Re-shallowing (fetch --depth, or editing .git/shallow) is the obvious way to cap the
  /opt/macro store, and the 2026-11-01 disk work considered and rejected it for this reason.
  (1) THE BOUNDARY: .git/shallow holds one line,
  a13962ee3915e18a8ee21fa8e3a8fa05d475d62f, "Persist Tiingo final capture preparation and
  CI chronology (#9039)", 2026-10-12. Everything the clone keeps is history from that commit
  forward, which is why the store grows with every render.
  (2) THE PIN: code_version a13962ee appears 7 times in 3 files: the promoted generation
  state/generations/040b2f2e....json and publisher/operations/gmi-c01-promote-20261012-001
  .json and .result.json. qualify_component calls source.accepts_revision(code_version),
  which runs 'git merge-base --is-ancestor <code_version> HEAD' and fails the component with
  GENERATION_CODE_INVALID if that does not succeed. With a13962ee as the boundary commit it
  is present and an ancestor (rc 0). A deeper cut would remove it from the clone and the check
  would fail.
  (3) A SECOND VALUE IS ALREADY BROKEN: code_version 82c63351 appears 7 times in 3 files:
  the staged generation state/generations/05811e17....json and
  publisher/operations/gmi-c01-stage-20261012-001 .json and .result.json. That object is not
  in the clone at all ('git cat-file -t' fails, merge-base --is-ancestor exits 128), so the
  same check cannot pass for the staged generation today. Whether anything still qualifies
  that staged generation was not established.
  The boundary can only move after the manifests carry a newer code_version, which is
  MO-A-F04 territory (see agentos/handoffs/MARKET-OS-2026-10-13-f04-git-history.md, which
  records the ancestry refusal a shallow clone caused before).
evidence:
  - >
    'wc -l < /opt/macro/.git/shallow' = 1; the line is
    a13962ee3915e18a8ee21fa8e3a8fa05d475d62f. 'git -C /opt/macro cat-file -t a13962ee...'
    prints "commit"; 'git merge-base --is-ancestor a13962ee... HEAD' exits 0.
  - >
    grep over /var/lib/macro-company-intelligence: "code_version" a13962ee... 7 times, in
    state/generations/040b2f2e50e6611ce6cb4a4fe9e7028f06199e6837bbd436ff1f712ba603d368.json
    (mtime 2026-10-13T00:13:18Z), publisher/operations/gmi-c01-promote-20261012-001.json and
    gmi-c01-promote-20261012-001.result.json.
  - >
    grep over /var/lib/macro-company-intelligence: "code_version"
    82c63351fa8c7dae219f01a833704724bb5aff8f 7 times, in
    state/generations/05811e172eda94d6d07e63ad151284317d68af3781c6635150a586dfedbb22d0.json
    (mtime 2026-10-12T15:21:05Z), publisher/operations/gmi-c01-stage-20261012-001.json and
    gmi-c01-stage-20261012-001.result.json. 'git cat-file -t 82c63351...' prints
    "fatal: git cat-file: could not get object info"; merge-base --is-ancestor exits 128
    ("Not a valid commit name").
  - >
    engine/company_intelligence/issuer_disclosure_owner.py at a7628775265b: accepts_revision
    requires a 40-hex revision then runs self.git._git('merge-base', '--is-ancestor',
    revision, self.git._head()); qualify_component requires
    source.accepts_revision(manifest['code_version']) with error code
    GENERATION_CODE_INVALID.
  - >
    /etc/systemd/system/macro-api.service lines 126-128 mount
    /var/lib/macro-company-intelligence/state and /artifacts read-only into macro-api, so the
    live API reads these generations.
falsifier: >
  On 146.190.142.17: (a) 'cat /opt/macro/.git/shallow' - if the boundary is no longer
  a13962ee, the pin has moved; (b) 'grep -rl a13962ee3915e18a8ee21fa8e3a8fa05d475d62f
  /var/lib/macro-company-intelligence' - if no generation carries it, re-shallowing past it
  is no longer blocked by this check; (c) read accepts_revision in
  engine/company_intelligence/issuer_disclosure_owner.py - if it no longer runs
  merge-base --is-ancestor, the constraint is gone; (d)
  'git -C /opt/macro cat-file -t 82c63351fa8c7dae219f01a833704724bb5aff8f' printing
  "commit" refutes part (3).
so_what: >
  Do not re-shallow /opt/macro, fetch with --depth, or edit .git/shallow to save disk. It
  silently breaks issuer-disclosure qualification for the promoted generation, and the
  failure shows up in company intelligence, not in git. Cap the store with consolidation
  (DEC:VPS-MACRO-GIT-STORE-BOUNDED-BY-NIGHTLY-CRUFT-REPACK) or more disk instead. To move the
  boundary, first regenerate the generation manifests on a newer code_version under
  MO-A-F04, re-check this grep, and only then cut. Separately, the staged generation's
  code_version 82c63351 is not in the clone; anyone working on that generation should expect
  GENERATION_CODE_INVALID from it now.
related:
  - "DSC:VPS-MACRO-STORE-REFILLED-ROOT-IN-12-DAYS-NIGHTLY-REPACK-NEVER-INSTALLED"
  - "DSC:VPS-ROOT-REFILLED-IN-42-DAYS-AND-REPACK-IS-NOW-DISK-BLOCKED"
  - "DEC:VPS-MACRO-GIT-STORE-BOUNDED-BY-NIGHTLY-CRUFT-REPACK"
  - "WS:MARKET-OS"
---

`/opt/macro` on the production VPS is a shallow clone whose single boundary commit is
a13962ee (2026-10-12). Cutting the history deeper looks like an easy way to stop the store
growing, and it was considered and rejected during the 2026-11-01 disk work.

The reason is that a13962ee is also the `code_version` of the promoted company-intelligence
generation in `/var/lib/macro-company-intelligence`, which macro-api reads.
`qualify_component` in `issuer_disclosure_owner.py` accepts a component only if
`git merge-base --is-ancestor <code_version> HEAD` succeeds. If a13962ee left the clone, the
promoted generation would fail with `GENERATION_CODE_INVALID`.

The staged generation from the same day already carries a code_version, 82c63351, that is not
in the clone at all. The boundary can move only after the manifests are regenerated on a
newer commit under MO-A-F04.
