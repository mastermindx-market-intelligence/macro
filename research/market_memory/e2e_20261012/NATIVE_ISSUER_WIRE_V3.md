# Native issuer wire v3 — qualification before paid admission

Prospective source contract for the existing fixed Linux issuer and protected M2
Memory execution owner. Original root01a1333c-a475-7052-95a8-72c623fb12e1.
This extends the original programme's N3/E1 source composition, without admitting
an experiment, changing a source hold, installing a service or granting a budget.
Frozen v1/v2 request/response codecs, grants and action meanings remain unchanged.

## Version and new read-only action

New requests use schema research_factory.market_memory_e0_native_issuer_request.v3,
responses research_factory.market_memory_e0_native_issuer_response.v3, and protocol
memory.e0.native_issuer.v3. New native service/recipient grants must explicitly
name this version and its permitted actions. A v2 grant cannot be relabeled.
The original four actions keep their meanings under the explicit new version.
The only new action is qualify_current_case.

The new action has EXACT fields schema, action, operation_id, intent. Intent has
EXACT fields study_id, root_id, operator_run_id, child_run_id,
participant_binding_sha256, with the existing bounded identifier/digest rules.
Use the SAME original operation and pre-input protected-recipient intent. No
locator, input, task, slot, role, command, path, clock, grant, callback, future
lease or future packet digest may be supplied. Labels/digests constrain equality;
they do not authenticate the machine service, principal or admission.

The fixed issuer qualifies its actual native peer, source-qualified installation,
current complete access history, active/clean state, typed native service record
from installation.admin_receipt_ref, typed current recipient/source-purpose record
from access.scope_ref, original intent, source purpose and current native rights.
The qualifier must not acquire cohort/cards/observations, inspect accounting or
original-case status, initialize/reserve/finish, create a child row, consume a look
or paid budget, invoke a provider, or repair/reissue an original operation.
Source-purpose qualification is distinct from executing source readers.

A successful response has EXACT fields schema, status, action, operation_id,
intent, issuer, verification, scientific_admission, retry_authorized. Status is
CURRENT_CASE_QUALIFIED; action is qualify_current_case; original operation/intent
are echoed exactly. Issuer has the existing closed installation/epoch/current
selection/service/recipient-reference shape, under explicitly versioned native
record semantics. Verification retains the existing EXACT five booleans, all
false. scientific_admission and retry_authorized are false. There is NO input,
locator, result, reservation status, private condition, assignment, all-arm view
or reusable authorization capability. Existing bounded canonical/framing/error
rules apply; an unknown or refused exchange never becomes qualified.

## Two-owner ordering

M2 first qualifies its genuine current protected owner/Control caller and original
pre-input intent without manufacturing paid admission or a child row. It then
uses this fixed read-only native qualification action through the already
confined machine service. Only a successful exact original/current response
allows the existing M2 paid-admission path to proceed. M2 next acquires its real
incumbent economic admission, then invokes prepare_case on the SAME original
operation and immutable intent. Linux immediately repeats all native current
peer/service/recipient/source checks; the earlier response is no authorization
cache or permission to ignore a revoke. A revoke between these stages withholds
input. The original reservation/unknown/no-replay rules still apply.

A failed, lost or malformed qualification response cannot authorize prepare,
paid budget, a row, a lease, a provider or a replacement operation. It also says
nothing about whether an earlier prepare executed. read_original_case remains
same-original recovery, not an admission preflight. No automatic source reload,
refund, new operation or generic result fallback is introduced.

## Original recipient and completed results

Original provenance/custody and actual intended recipient are separate facts.
Native thread/root/operator/child IDs and Control custody are correlation only.
A valid opaque recipient_grant_ref alone does not establish recipient identity.

The existing private native grant must explicitly identify its original recipient
kind and principal, bind the original operation/pre-input intent and the permitted
service/recipient scope, and be immutable in the stored original envelope. It
must derive from the actual protected native grant selected through existing
owner records, never a client role or a newly supplied principal. The Linux
issuer's current authoritative owner may expose the minimum typed original
recipient fact internally through the existing protected owner contract. No
public generic disclosure or alternate mutable principal is created here.

For prospective v3 only, authorize_result_disclosure extends its existing exact
`authorization` object with one field, `original_recipient`. That fact has EXACT
keys schema, recipient_kind, principal_ref, ssh_key_fingerprint,
original_operation_id, pre_input_intent_sha256. Schema is
research_factory.market_memory_e0_original_recipient.v3; recipient_kind is
native_broker_service. principal_ref is the EXACT native service/admin receipt
reference selected by the original installation, not an owner-seat or arbitrary
principal label. ssh_key_fingerprint is the same original actual authenticated
service key, freshly matched to the current native service/grant. Operation and
pre_input_intent_sha256 bind the SAME original operation and canonical five-field
wire intent. Neither field includes future packet/result or self-dependent grants.
All existing result input/SHA/size/purpose authorization fields remain exact.

The native recipient grant must explicitly contain original_recipient with EXACT
keys recipient_kind, principal_ref, ssh_key_fingerprint and explicit
recipient_permissions EXACT [delegate_original_child_input,
read_original_child_result]. The service is the actual authorized transport
recipient and restricted original-child proxy. Original registered reviewer,
task and private slot remain separately qualified scope, not observed identity or
independence. The original audience is retained immutably in the original case
intent/envelope. A later different recipient or service cannot silently replace it.
The returned fact is derived from that original native owner data and fresh current
qualification, not reconstructed from a client's requested principal.

This deliberately identifies a SERVICE audience, not an arbitrary M2 end user or
Control custody owner. M2 must still establish its actual current protected
service/caller receiver authority and enforce its closed disclosure channel. It
must refuse if that genuine current predicate is absent; it may not invent a
Control permission or issue a capability merely because the fact parses. No new
principal registry or public result API is introduced. Frozen wire2 has no such
fact and is not retroactively upgraded. Original input/result receipts and pending
or unknown operations remain intact; no source reload/reserve/start/refund follows.

## Dedicated composed service profile

The prospective native service record must explicitly name
memory.e0.protected_m2_service_ssh.v2. Older standalone profiles do not match.
The Linux component authenticates the dedicated machine key, exact root-owned
key-file/options, actual successful authentication and key-option forced session,
process/socket/command lineage, approved executable/parser and current rereads.
It does not infer historical daemon environment settings from a new sshd parse.

Client-input confinement is supplied by the OTHER mandatory component: the
qualified protected M2 root owner, exclusive separate service-key custody and
its fixed SSH client. Requests reach only the closed frame, never argv, endpoint,
key path, SSH configuration or environment. The inspected implementation uses
-F /dev/null, literal options/command, no agent/forward/proxy/local-command/TTY
fallback and fixed minimal Popen environment. Current kernel Control/socket,
source and enrollment checks bracket every exchange. Both root OS/admins are
trusted. This profile does not claim safety for arbitrary holders of the key.

The actual inspected client source was LOCAL frozen Mastermind b73e7bbe0, source
return74723384145dd075543bb818f2d948fc1743d552627621599220556b3796c115;
that reference is not a claim of protected publication or installation. The
complete installed composition must prove its real current client source, sole
protected invocation, key custody and failure behavior. Native admin service
selection authorizes the named service; neither a caller verification flag, a
source hash alone nor fixture data proves the installed counterpart. Server
root/PAM/user environment remains part of the trusted Linux OS configuration,
not reclassified as attacker-controlled request input. Original source/review,
scientific, budget and protected-release holds are not waived by this profile.

For V3 continuation, issuer.current_access_ref and
issuer.current_selection_sha256 describe freshly qualified current selection.
They may advance only through the authentic native complete access history and
unchanged immutable source/service/recipient grant. All original locator fields
and input remain exact. The recipient grant and original service audience are
immutable in this version; no blanket field exemption or legacy migration is
allowed. The locator.original_intent_sha256 binds the private native reservation
intent (including immutable native grant/source bindings); it is not the digest
of the five-field public wire intent. In contrast, the typed original-recipient
fact's pre_input_intent_sha256 is EXACTLY the canonical five-field wire intent
digest. M2 cannot recompute private original-intent contents from public metadata;
it checks the original qualified locator unchanged across later disclosures.

## Required joined checks

A genuinely absent/revoked Linux grant must refuse before any M2 paid admission,
child row, look or source acquisition. A current grant followed by actual M2 paid
admission may reach prepare only after a fresh Linux check. A revoke after
qualification, wrong original intent, malformed response and unknown response all
withhold input and never authorize provider execution. Preflight must make zero
calls to cohort/card loaders and ReservationStore inspection or mutation.
Exercise an admitted synthetic source path with honest native primitive fixtures;
fixtures do not establish real identity, installation, current enrollment,
economics, scientific validity or customer acceptance. All five verification
flags and scientific admission remain false; semantic blinding remains false;
adjudicator access remains refused without actual original ratings/disagreements.
