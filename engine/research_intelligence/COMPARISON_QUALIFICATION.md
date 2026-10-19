# Private source-comparison qualification

The comparison companion record is inside incumbent Research Intelligence
storage (`research_vault/intelligence/v1/comparison_qualifications`). It does not
change the frozen RIO schema, extraction receipt, or their content identities.
There is one current CAS pointer per ordered pair of exact report/PDF/text/RIO
and publication identities, and immutable content-addressed decisions. Claim
indexes, explicit five-axis bases, source-topic or historical-security resolution,
review method/time/provenance and the actual adjudicator are closed record fields.
A replacement or revocation must name its actual predecessor. Ambiguous writes
use same-carrier readback and report unknown outcomes; callers must not replay.

`QualificationAuthority` is a server composition dependency, never a tool argument
or a record field. Its write callback authenticates the actual author and approves
the proposed adjudication; the returned principal supplies the record's author.
Its read callback verifies current admission of the exact record for the actual
caller, including author/provenance trust. Shape validation, an author string,
a content hash, grounding, or a state flag does not authenticate that decision.
The default runtime uses `SealedQualificationPolicy`, the concrete bounded
root-owned file loader following the existing Research Read deployment-grant
custody pattern. Its default path is
`/etc/mastermind/research-comparison-qualification-policy.json`. Missing, expired,
malformed, writable or changed policy refuses; construction opens no file. This
source change creates no policy, production adjudication or authenticated author.
The programme root can independently assess actual development sources and then
bind a real server-side admission owner without granting tool callers that power.

The ordinary and qualified read factories compose read-only resolvers over their
existing Store. They never call the authoring function. The private resolver uses
bounded gets, not object listing or write credentials. It advertises one bounded
opaque basis option for the exact admitted claim pair; other claims do not inherit
semantic acceptance. An optional revision ref binds the same immutable decision
and requires independently supported literal revision wording. Before disclosure,
comparison repeats source/RIO identity, current admission and basis/revision checks,
then the final catalog check and atomic charge. All private text and references
remain inside the existing 12,000-character aggregate budget.

Source readiness and synthetic tests do not establish actual two-source semantic
acceptance. Full F11 ordinary Brain merge/activation still requires the real
common-generation >=95% proof and original writer/auth admission. Provider calls,
production qualification writes, migrations, service activation and grant changes
are separate effects and are not performed by this source implementation.

The sealed policy has schema
`mastermind.research_intelligence.comparison_policy.v1`, fixed policy ID
`research-vault-descriptive-comparison-v1`, actual `authorization_provenance`, and
at most 64 entries. Each entry pins `qualification_sha256`, `adjudicator_id`,
`review_sha256` (canonical review JSON), `audience: brain_pro`, and integer
`expires_at`. Root custody of this exact content approval authenticates the
adjudication admission; a content ref or author string received from a client does
not. It is separate from the MCP content grant and creates no MCP comparison tool.
Policy reload on every admission observes revocation without a process restart.
Existing Brain principal, Pro, surface and scope gates still apply. Optional
expected policy SHA binding is available to the trusted source/runtime owner.

A root operator can use `root_operator_context()` with this same authority and
`publish_qualification`. The adapter rechecks effective UID 0 and requires a
root-sealed entry approving the exact resulting record and full review digest;
it derives the real adjudicator ID from that approval. A service UID, actor JSON,
or guessed author cannot use it. Policy creation/installation and actual semantic
review are explicit operator effects, not performed by the reader or tests. No
second credential or identity store is introduced.
