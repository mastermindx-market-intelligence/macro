---
key: DESIGN-SPEC-LANES-BIND-INVENTED-FIELDS-AUDIT-AGAINST-THE-LIVE-SCHEMA-FIRST
claim: >
  A fabric design-spec lane given a prose field list plus a frozen visual binds fields
  the contract does not have (and paints payload into static Jinja) instead of stopping
  at GAPS; a read-only audit against the LIVE schema must run before any mockup or shell
  lane consumes the spec.
evidence:
  - PR #7903 head 469e932e — about fifteen invented or wrong-path bindings (driver_label, earnings_label, falsifier_horizon, node.evidence_state, source.effective_at, fin.* entry fields), a pivoted macro shape, conflict label keyed on conflict_id; audit recorded in PR #7903 comment 5810133462
  - The spec's own sentence "any field the schema lacks is logged under GAPS, never invented" was broken inside the same document
falsifier: >
  python3 -c "import json;t=open('research/finance/implementation/FINANCE_DOSSIER_DESIGN_SPEC_2026-09-24.md').read();print([k for k in ('driver_label','earnings_label','falsifier_horizon','effective_at','top_domains') if k in t])"
  printing a non-empty list on the branch head AFTER the repair lane, or an audit of a
  future spec lane commissioned with the schema as the only field authority finding zero
  invented bindings on its first pass, would refute the claim's generality.
so_what: >
  Commission design specs with the schema path as the ONLY field authority (no prose
  field list), require a label-map closure script and greppable self-checks in the packet,
  and gate mockup/shell lanes on an Opus read-only audit — the mockup dispatched on the
  unaudited spec would have rendered every defect.
kind: landmine
confidence: verified
verified_at: 2026-09-24T08:05:00Z
verified_by: >
  gh pr view 7903 --json headRefOid; python3 -c "import json;s=json.load(open('contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json'));print(s['$defs']['rerating']['required'], s['$defs']['rerating']['additionalProperties'])"
scope:
  - macro
---

Repair pattern that worked: seat rulings R-A..R-K with concrete CSS/markup plus fourteen greppable self-checks the lane must quote (scratchpad packet fin_d1a_repair, lane on mb 08:19Z).
