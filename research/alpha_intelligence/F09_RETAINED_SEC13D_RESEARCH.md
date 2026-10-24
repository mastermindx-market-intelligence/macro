# Retained Schedule 13D research read

The native research consumer reads an operator-qualified retained SEC submission,
its acquisition record, a retained SEC registration and a pinned native security
master. It exposes source assertions and an unpublished, assertion-day security
match. It creates no catalog, canonical alias, ownership epoch, compiler recipe,
account grant or public holdings feed. PR9771's authenticated holding response is
unchanged; this is an explicit separate research contract.

Run from the repository containing the admitted source:

```sh
python3 -m lib.dataos.sec13d_research \
  --bundle-root "$QUALIFIED_BUNDLE_ROOT" \
  --repository . \
  --decision-cutoff 2026-10-19T20:00:00Z \
  --security-on 2026-04-30
```

The bundle contains the previously retained files, not URLs to fetch:

| Record | Retained input |
| --- | --- |
| `acquisition.json` | SEC submission filename in its exact archive URL |
| `registration-acquisition.json` | Registration filename in its exact SEC archive URL |
| `master-source.json` | `security_master.parquet`, with its native commit, fixed `data/reference/security_master.parquet` path, digest and actual retention clock |

The reader refuses symlinks, oversized/changed files, duplicate/nonfinite JSON,
non-UTC or reversed acquisition clocks, unsuccessful/foreign-origin acquisitions,
wire accession/issuer conflicts, digest mismatches and master bytes differing
from the pinned native Git blob. Git reads disable lazy fetching and credential
prompts. No network collection, pipeline, store write or alias publication runs.
SEC bytes are bounded to 2 MiB for the submission and 8 MiB for registration;
the master is bounded to 16 MiB. Acquisition JSON is bounded to 16 KiB.

**Custody limit:** matching local files and records proves their integrity and
the pinned master relationship. It does not independently authenticate a local
operator's acquisition timestamps or grant source-use rights. The assigning
principal must qualify the actual acquisition and repository custody. Output
keeps that distinction visible and never labels the bundle a canonical owner
receipt, collector adoption or K1 authorization. This local operator interface
must not be exposed as an HTTP endpoint accepting caller-controlled paths.

**Two clocks:** `security-on` asks which security the filing asserted on a
supported date; `decision-cutoff` asks whether the actual retained inputs were
then available. Filing facts remain unavailable before the submission was
retained. If registration or the master was retained later, already available
filing assertions remain readable while security identity is unavailable. The
native SEC alias helper supports the half-open filing-acceptance day only;
the event date and March/June quarter ends do not acquire continuity from it.

The retained PIF/Ayar source is accession `0001104659-26-053223`, event April 28,
accepted April 30, actually retained October 19. Its Item 2 states PIF's sovereign
wealth fund role and Ayar's wholly owned relationship. The consumer exposes that
control statement verbatim with its source field and receipt, preserving the
source's qualifications. Cover-page persons retain their own CIK or explicit
absence; issuer/filer CIKs never replace missing person identifiers.

Cover-page beneficial aggregates and Item 5 text can include common-equivalent
convertible interests. They remain separate source fields and canonical decimal
strings. The consumer performs no group sum, common-only conversion or ownership
delta. In particular, arithmetic equality with a June 13F quantity is not proof
of continuity or a selected economic sleeve.

`AVAILABLE_UNQUALIFIED` is useful delayed research, never current ownership or an
eligible investment strategy. Economic vehicle class, decision mode, ownership
continuity and purpose/source use remain unknown. PIF's legal SWF identity does
not select one of the nine K2B investment-style classes. Every authority stays
false, K2C/K3E admissibility stays false, and recipe/compiled remain null even
when an assertion-day security is matched. Actual K2C owner composition requires
separately supported epochs, mode and purpose; no callback or provenance dict
can bypass its existing native refusal.

Affected checks include the original 13G regression, strict 13D parser, class-A
registration/master binding and retained research boundary suites. Fixture
acquisition records exercise mechanics; the release proof separately invokes
this native consumer against the principal's actual retained objects and pinned
master with their original clocks. No fixture result is production authentication.

The native master pin also rejects a commit date later than its claimed retention. Repository dates are mutable, so this detects an internal contradiction and does not authenticate the clock. Non-regular bundle entries, including FIFOs, are opened without blocking and refused before a read; native master size, blob and chronology refusals retain their specific reason.
