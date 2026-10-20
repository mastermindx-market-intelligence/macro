---
key: A-PATH-LOOKUP-IS-NOT-AN-OBJECT-LOOKUP
claim: >
  A document named in a plan can be absent at every path on every ref a session
  checks and still be present in that host's git object store as an unreferenced
  blob, so "not vendored anywhere" is a statement about the NAMESPACE and never
  about the STORE. `git ls-tree`, `git show <ref>:<path>` and a recursive grep all
  answer one question - is this object reachable from this ref under this name -
  and an object written by a fetch of another branch, or by a commit whose ref was
  later deleted, answers no to all of them while sitting on local disk. A blobless
  promisor clone biases the reading further toward absence: path-based history
  walks need contents they do not have, so they are slow, lossy, and fail offline.
  Measured on GMI Industrials 2026-09-29: the frozen plan named its three
  requirement sources as exact paths (r1/r2 under `docs/superpowers/specs/`, W12
  under `research/industrials/`); none resolved on `origin/main`, the directory
  `docs/superpowers/specs/` did not exist there at all, and 41 of 56 requirement
  ids appeared nowhere in the tree. Every one of those readings was correct. All
  three specification blobs were nevertheless already in the local object store,
  and `git cat-file -s 40fd1e3783102c28fe748fe35b927484d4f3dddb` returned 28,638
  bytes instantly - no fetch, no checkout, no network.
falsifier: >
  For any sha an authority quotes anywhere - a ruling, a carrier comment, a
  handoff, a branch listing - run `git cat-file -t <sha>` and `git cat-file -s
  <sha>` in the checkout that reported the absence. A type and a size prove the
  object is local and the absence was positional; an error proves it genuinely is
  not here, which is a fetchable state (`git fetch origin <ref>`) and still not
  deletion. Second instrument, slower, for when no sha is quoted:
  `git log --all --find-object=<sha>` names a carrying commit - background it on a
  promisor clone. This record is refuted for a given document if `cat-file` errors
  AND fetching every ref the authority names still does not produce it.
so_what: >
  It changes what a session REPORTS when it cannot find a specification, and
  therefore what the commissioning authority is asked for. Report "not vendored at
  any path on `main`" - true, useful, and bounded - never "missing" or "gone", and
  run the object-store lookup before writing either. On GMI Industrials the wrong
  report ("41 requirements have no retrievable authority") was one minute from
  merging a PAUSE gate into the two records a future seat reads first, and it
  invited a re-specification of 41 obligations that nobody needed; the authority's
  actual answer was three blob shas already on the host. The asymmetry is the
  whole point: a path lookup that finds nothing costs you nothing to escalate, but
  a claim of deletion licenses fabrication downstream - a seat authorized to
  re-specify writes obligations that describe what the code already does, and the
  defect the original wording would have caught stays. Recovering the original
  text of IND-R214 immediately exposed a real defect in merged code; a
  re-specification, written by the same seat that wrote that code, would not have.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  Claude Opus 5 seat c6467452 (GMI Industrials first vertical, operation
  gmi-industrials-fable-ceo-e2e-20260924-chairman-001). Absence measured with
  `git ls-tree -r origin/main` plus one `grep -rl <id> --exclude-dir=.git .` per
  requirement id (41 with zero hits). Presence measured with `git cat-file -s` on
  each of the three blobs named by Sol ruling `5894127980` on carrier #7789 -
  40fd1e3783102c28fe748fe35b927484d4f3dddb (28,638 B, 30 IND-D ids),
  9c98e106b954d0a48610afad418de2a9eeb1e58b (20,947 B, 18 IND-R),
  b343cbd7bc1f52cfc6fbb5e18ab8d9e9f9392f6c (21,187 B, 8 IND-SF) - all reachable
  from 40d91e50a38c604e26255c1451eda5ddc95fb9cc on
  sol/industrials-sector-research-20260923, and each id count taken from the blob's
  own bytes rather than from the ruling.
scope: [macro, agentos, all-programs]
confidence: verified
---

## The two questions, and why only one of them was asked

| instrument | question it answers | answer here |
|---|---|---|
| `git ls-tree -r <ref>` / `git show <ref>:<path>` | is this object reachable from this ref under this NAME | no |
| `grep -rl <id> --exclude-dir=.git .` | does this text appear in the checked-out tree | no |
| `git cat-file -t/-s <sha>` | does this object EXIST in this store | **yes, instantly** |

The first two are namespace queries. Nothing about their answers constrains the third, and
the third is the cheap one. The session that measured the absence also pinned a salvage ref
for a related blob to protect it — which felt like a second, independent line of evidence and
was in fact the same evidence class applied twice.

## Why the promisor clone makes this worse

This clone carries `remote.origin.partialclonefilter=blob:none`. Path-based history walks
(`git log -- <path>`, `--find-object`) need blob contents they do not hold, so they fetch
lazily, run slowly, and fail outright offline. Every failure mode of a path lookup here
points the same direction — toward "absent" — while `cat-file` on a sha the store already
holds is unaffected. The instrument that is least reliable is the one a session reaches for
first, because it is the one that takes a human-readable path as its argument.

## The rule, stated so it survives the session

Before writing the word "missing" about any named document: if a sha is quoted anywhere, ask
the store. If no sha is quoted, ask the authority that named the document where it lives —
the branch it was authored on is usually still fetchable, and here it was a `sol/*` research
line that had never been merged. Then report the scope of what you checked, and never let a
correctly-scoped caveat sit next to a conclusion the caveat forbids.

Related: `DSC:A-VENDORED-TRACEABILITY-MAP-STILL-HAS-NO-REQUIREMENT-TEXT` is the record whose
inference this refutes, amended at source; `DSC:ALTERNATES-SHARE-OBJECTS-NOT-THE-PROMISOR`
and `DSC:CI-PROMISOR-OBJECT-FETCH-TRUNCATION` are the other two places this clone's object
model has already surprised a session.
