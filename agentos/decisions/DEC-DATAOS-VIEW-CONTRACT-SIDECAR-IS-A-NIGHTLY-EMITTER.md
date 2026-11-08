---
key: DATAOS-VIEW-CONTRACT-SIDECAR-IS-A-NIGHTLY-EMITTER
question: >
  Who writes the `_view_contract.json` sidecar that Terminal ingest (U01, `ingest/polygon_bars.py`
  `load_view_contract`) reads beside Macro's OHLC bars, and when does it first appear in production?
answer: >
  A Macro NIGHTLY step (package C04, consumer wave): `scripts/emit_view_contract.py` builds the
  `dataos.view_contract.v1` document from C01's pure ViewContract → v1 JSON mapping (purpose,
  identity_namespace, field_units, adjustment_reference = tradj, evidence_mode, coverage, listings,
  refusal_reasons) and writes `data/stocks/_view_contract.json` atomically (tmp + rename) as a
  `daily.yml` step in the `collect` job, after the OHLC bake and the security-master refresh; the
  existing nightly data commit carries the file. Tests run on tmp_path only; no lane tree ever writes
  `data/`. The production file first exists after the first nightly following the merge (~02:30Z), so
  Terminal charts read the unknown state (VIEW_CONTRACT_ABSENT) until then — by design, never a
  fabricated contract.
rationale: >
  The contract must come from the writer that owns the bars' basis: only the nightly knows the
  generation, coverage and listing set it just baked. Terminal re-deriving the basis would recreate the
  raw == adjusted coincidence D00 forbids; a lane writing `data/` violates the nightly-sole-advancer law;
  an R2 artifact adds a fetch path and a second truth.
alternatives:
  - option: Terminal-local re-derivation of the basis from the bars themselves.
    why_not: >
      Re-derives what the contract exists to declare; D00.D4 says computation refuses rather than guesses.
  - option: A lane (PR) writes data/stocks/_view_contract.json directly.
    why_not: >
      The nightly is the sole advancer of `data/`; a sparse lane tree cannot even hold the directory.
  - option: Publish the contract as an R2 artifact fetched by Terminal.
    why_not: >
      Second transport, second truth, new fetch/auth surface — the masterplan forbids new stores and
      publishers.
evidence:
  - "ORCH-3 return 2026-10-13T18:12Z: the sidecar gap named; U01 reads the file verbatim and refuses VIEW_CONTRACT_ABSENT / VIEW_CONTRACT_INVALID / VIEW_BASIS_UNSUPPORTED."
  - "Terminal PR #996 (squash fdc7c7f96f56) ingest/polygon_bars.py: VIEW_CONTRACT_FILE = '_view_contract.json', VIEW_CONTRACT_SCHEMA = 'dataos.view_contract.v1', VIEW_PURPOSE = 'terminal_daily_ohlc', VIEW_MIC_SCOPE = {XNYS, XNAS, XASE, ARCX}; load_view_contract requires schema, purpose, identity_namespace, field_units, adjustment_reference, evidence_mode, coverage, listings, refusal_reasons and adjustment_reference.basis == 'tradj'."
  - "Output path pinned to data/stocks/_view_contract.json: Terminal ingest/build_universe.py STORES[0] maps the US store to data/stocks and joins VIEW_CONTRACT_FILE (#996 lineage)."
  - "Listing/MIC source: data/reference/security_master.parquet (mic, listing_key, superseded_by, country) joined through data/reference/vendor_aliases.parquet; both committed and refreshed nightly by scripts/build_security_master.py --nightly in the collect job. data/polygon_universe/reference.parquet carries no exchange column."
  - "Step placement: collect job, after the security-master refresh and before the market-commit-push timing mark; the existing nightly data commit carries the file — no new commit step, store or publisher. Byte-stable no-op (skip the write when bytes match) mirrors the security-master refresh; coverage carries counts only, no timestamps."
  - "Seat gate notes (scratchpad P05C01_GATE_NOTES.md, 'Seat decision — the _view_contract.json sidecar WRITER'): C01 freezes the ViewContract → v1 JSON mapping as a pure function plus test and writes NO file; C04 is commissioned only after C01 lands, with its contract fields taken from C01's merged mapping."
affects:
  - "WS:DATA-OS-COMPLETION"
  - "scripts/emit_view_contract.py"
  - "tests/test_emit_view_contract.py"
  - ".github/workflows/daily.yml"
  - "terminal:ingest/polygon_bars.py"
confidence: high
reversibility: easy
decided_by: coo-fable
decided_at: 2026-10-13
---

# The view-contract sidecar is a nightly emitter

The nightly writes `data/stocks/_view_contract.json`; nothing else does. Terminal ingest reads it verbatim
and refuses (typed) when it is absent, invalid or not `tradj`, so the live chart readout shows the unknown
state until the first nightly after C04 merges — a truthful gap, not a fabricated contract. C04 edits
`.github/workflows/daily.yml`, which is CI authority: its merged head is frozen until the next green `ci.yml`
run on a main descendant, and the step runs only inside the nightly (no lane tree writes `data/`).
