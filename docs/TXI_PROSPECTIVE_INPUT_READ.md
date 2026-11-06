# Prospective TXI input observation

The existing native `engine.transmission_chains.run` now adds an optional
`input_capture` block to its ordinary `data/transmission/chain_state.json` output.
The daily regional-builders stage already invokes `scripts.run_transmission_chains`
after `scripts.build_transmission`; no extra invocation, acquisition, model or trial
is introduced. `scripts/ci/daily_engine_commit_outputs.sh` publishes this artifact
and its existing `data/` inputs through the incumbent broad data commit.

The producer hashes the same bounded bytes it decodes for chain YAML, latest.json
adapters, series parquet and the predecessor episode ledger. It detects missing
inputs and unresolved Git LFS pointers, records the selected YAML file population, actual process capture start/completion,
the on-disk producer source digest, the causal state digest and the proposed
transition digest. Repeated reads and a final recheck reject a changed input or
changed definition population. No new raw source copy, registry, storage namespace,
private CAS or ledger is created. Receipt construction, count/size bounds and source
errors cannot change the incumbent detector's runtime fallback behavior.

The receipt is a CURRENT process-observation record. `observation_asof` remains the
owner's upstream observation date; it does not become the capture date. Provider
availability and first ingestion remain null, historical knowledge stays unavailable,
and scientific acceptance stays false. The source digest identifies an observed
file, not an attestation that the already-loaded code came from a particular commit.
The clock interval ends before the incumbent state write and ledger append; it is
not an output publication or durability clock. A rerun has a new receipt while
same-asof ledger deduplication and native transition calculations remain unchanged.

`verify_prospective_input_capture(root, state)` is a read-only integration surface.
It checks the receipt self-hash, declared clocks, causal output structure and listed
input lengths and hashes. It resolves files from one existing publication, including the
retained producer source and definition population. For the append-only ledger it
checks the exact captured predecessor byte prefix; it does not authenticate later
appends, prove that proposed transitions were committed, or relabel older rows.
A listed input whose bytes are missing (including a never-created predecessor
ledger), an unresolved LFS pointer in a listed input, and an absent, malformed,
stale, oversized or mismatched receipt are
unavailable. A later normal run can bind an actually retained ledger, including an
existing empty ledger; no cold-start bytes are invented. A match means only
`listed_input_bytes_match`, with `verification_scope` limited to listed bytes and the
declared definition population. The generation id is a self-hash, not a signature.
Deleting a causal data read and recomputing that hash can still produce a listed-byte
match. The verifier cannot establish producer execution authenticity or causal-read
completeness; both remain explicitly unqualified, loaded-code authentication stays
unavailable, and `causal_lineage_acceptance` is always false. A receipt claiming an
upgrade is refused. This result must not be used as full causal lineage, scientific,
publication or provider-authentication acceptance. It supplies no publication receipt.
A normal Git publication must retain the same listed input bytes;
a later path that has changed is not a substitute for that publication.

The declared producer capture scope is causal detectors, chain definitions and
predecessor state. The verifier does not independently prove that scope complete.
Company substrate and weekly calibration are display enrichments and are excluded
from the causal output digest. Upstream forex/transmission JSON is an immediate
input: this receipt does not recursively prove the acquisition clocks of its own
inputs. Source-read bytes are capped at 16 MiB, file count at 512, and receipt at
128 kB. If adding metadata would exceed Explorer's existing 2,000,000-byte owner
state limit, the optional block is omitted. Missing metadata never confers eligibility.

A future real-path acceptance needs an ordinary later producer result, its normal
Git publication retaining every referenced input (including producer source and
ledger prefix), a genuine publishing receipt, and consumer access to that exact
generation. Full lineage acceptance additionally needs evidence of genuine producer
execution and complete causal read coverage; this self-hashed receipt and checker
cannot provide that evidence. The current Explorer manifest and `gap_state` behavior
are unchanged;
`owner_transition_unsettled` stays a refusal. Older episodes remain historically
unqualified. No old daily/graph effect is replayed by this change.

The Chairman's standing named-source commercial rights ruling remains in force.
This metadata capture does not request another Yahoo/yfinance license or expand
that attestation to FRED or other providers. It neither creates a source-use grant
nor republishes raw third-party inputs to a new destination.
