# T1 real-release demonstration: P&G's own releases through the native path (PR #7905)

Tree: the integrated candidate `4278ae834fa57bcad57316efeb8a51073a96405c`. Interpreters: 3.12.13, 3.14.7.

What this shows, from the exact bytes EDGAR serves for each release:

- **Source.** Each exhibit is the document its filing names. Its bytes match the sha256 pinned in `tests/fixtures/pg_envelope/SOURCES.md`, and every receipt names that sha256.
- **Value.** Each present value equals the independent oracle's, and equals the figure printed in the EDGAR bytes at the receipt's span.
- **Period.** Each value carries the quarter's end, or the year-ago quarter's end for the two year-ago EPS figures.
- **Refusal.** A document outside F1-Q, or a release run under the wrong quarter, admits no present fact. The validator refuses every tampered workspace.

The path is the product's own: `bind_release_document` binds the exhibit to its 8-K filing, and `build_event_workspace` builds the event under the P&G profile. `validate_selected_facts` then replays each selected observation from the source bytes.

The witness suite supplies only three things: its frozen release records, its oracle loader, and its stdlib reader (`text`, `literal`). The reader imports nothing from `engine/`.

Result: **0 failures** on every interpreter. The JSON outputs are identical across interpreters: yes.
The same run on the frozen head `e6f49ceccb85` (before R187-R190) gives an output identical to this one: yes. The round-8 repairs change nothing on a real release.

## 1. Source

| release | accession | accepted (UTC) | bytes | sha256 of the served bytes | SOURCES.md | release record |
|---|---|---|---|---|---|---|
| FY25Q4 `fy2425q4amj8-kexhibit991.htm` | 0000080424-25-000067 | 2025-07-29T11:03:15Z | 454,203 | `6c625f3b78ba710da8a682e3ef5d5a57b157fd962f2d486154d9654ae25dcb6a` | match | match |
| FY26Q1 `fy2526q1jas8-kexhibit991.htm` | 0000080424-25-000240 | 2025-10-24T11:04:27Z | 305,212 | `f3c987b34434671b6cad1f09c6fd42aa10701ac3c2a1fc62644b65c44e0dad96` | match | match |
| FY26Q2 `fy2526q2ond8-kexhibit991.htm` | 0000080424-26-000006 | 2026-01-22T12:02:05Z | 296,069 | `f6d79042f16c6131100c6c6e678e96f43dd666b410356cc23cd43d7d1e032503` | match | match |
| FY26Q3 `fy2526q3jfm8-kexhibit991.htm` | 0000080424-26-000056 | 2026-04-24T11:01:47Z | 308,066 | `eeef9d0de613e44ba3e4444c084431100491dd3a28a3b6226f0e8163ca770b84` | match | match |
| FY26Q4 `fy2526q4amj8-kexhibit991.htm` | 0000080424-26-000093 | 2026-07-29T11:03:12Z | 472,455 | `9fe6812066a4ef6a1ca8b53b394ae0dbf2796eaef0c5141d2ae60fe94521dcbc` | match | match |
| CL2Q26 `q22026pressreleasetables.htm` | 0000021665-26-000041 | 2026-07-31T11:58:00Z | 789,706 | `a04042a7d643bea6bb3dc0aea14224e3705a4c56847d6694708897444f72d40e` | match | match |

Each exhibit is served at `https://www.sec.gov/Archives/edgar/data/<CIK as an integer>/<accession without dashes>/<file>`.

**Live re-fetch.** EDGAR refused a re-fetch from this seat with HTTP 403. The request's identity carried no email address, and EDGAR's fair-access policy asks for one. The seat does not send a personal address.

The source claim therefore rests on the sha256 pinned in `SOURCES.md` when the fixtures were committed. The suite checks that pin on every run.

## 2. Admitted releases: FY26 Q1, Q2 and Q3

In each column, the first value is the engine's and the value after `/` is the independent oracle's (GLM, read from the raw bytes with no repository code). Each cell's middle line is the text EDGAR prints at the receipt's byte span.

A cell agrees only if all of the following hold:

- the value equals the oracle's;
- the literal parse of the EDGAR bytes at the span equals the value;
- the unit and basis are the frozen ones;
- the period is the quarter end, or the year-ago quarter end for a year-ago metric;
- the receipt names the exhibit's sha256 and is `byte_replayed`.

| metric | unit / basis | FY26Q1 (period) | FY26Q2 (period) | FY26Q3 (period) |
|---|---|---|---|---|
| `pg_reported_sales_growth_pct` | percent / reported_sales | 3 / 3<br>`3%` bytes 32480-32482<br>2025-09-30 agrees | 1 / 1<br>`1%` bytes 32513-32515<br>2025-12-31 agrees | 7 / 7<br>`7%` bytes 32624-32626<br>2026-03-31 agrees |
| `pg_organic_sales_growth_pct` | percent / organic_sales | 2 / 2<br>`2%` bytes 286878-286880<br>2025-09-30 agrees | 0 / 0<br>`&#8212;%` bytes 278567-278575<br>2025-12-31 agrees | 3 / 3<br>`3%` bytes 288210-288212<br>2026-03-31 agrees |
| `pg_total_volume_growth_pct` | percent / total_volume | 0 / 0<br>`&#8212;%` bytes 31133-31141<br>2025-09-30 agrees | -1 / -1<br>`(1)%` bytes 31164-31168<br>2025-12-31 agrees | 2 / 2<br>`2%` bytes 31277-31279<br>2026-03-31 agrees |
| `pg_organic_volume_growth_pct` | percent / organic_volume | 0 / 0<br>`&#8212;%` bytes 32777-32785<br>2025-09-30 agrees | -1 / -1<br>`(1)%` bytes 32810-32814<br>2025-12-31 agrees | 2 / 2<br>`2%` bytes 32921-32923<br>2026-03-31 agrees |
| `pg_price_contribution_pp` | percentage_points / reported_growth_bridge | 1 / 1<br>`1%` bytes 31673-31675<br>2025-09-30 agrees | 1 / 1<br>`1%` bytes 31700-31702<br>2025-12-31 agrees | 1 / 1<br>`1%` bytes 31811-31813<br>2026-03-31 agrees |
| `pg_mix_contribution_pp` | percentage_points / reported_growth_bridge | 1 / 1<br>`1%` bytes 31940-31942<br>2025-09-30 agrees | 0 / 0<br>`&#8212;%` bytes 31967-31975<br>2025-12-31 agrees | 0 / 0<br>`&#8212;%` bytes 32078-32086<br>2026-03-31 agrees |
| `pg_fx_contribution_pp` | percentage_points / reported_growth_bridge | 1 / 1<br>`1%` bytes 31406-31408<br>2025-09-30 agrees | 1 / 1<br>`1%` bytes 31433-31435<br>2025-12-31 agrees | 4 / 4<br>`4%` bytes 31544-31546<br>2026-03-31 agrees |
| `pg_other_contribution_pp` | percentage_points / reported_growth_bridge | 0 / 0<br>`&#8212;%` bytes 32207-32215<br>2025-09-30 agrees | 0 / 0<br>`&#8212;%` bytes 32240-32248<br>2025-12-31 agrees | 0 / 0<br>`&#8212;%` bytes 32351-32359<br>2026-03-31 agrees |
| `pg_diluted_eps` | usd_per_share / gaap_diluted | 1.95 / 1.95<br>`1.95` bytes 82790-82794<br>2025-09-30 agrees | 1.78 / 1.78<br>`1.78` bytes 82696-82700<br>2025-12-31 agrees | 1.63 / 1.63<br>`1.63` bytes 83341-83345<br>2026-03-31 agrees |
| `pg_prior_diluted_eps` | usd_per_share / gaap_diluted | 1.61 / 1.61<br>`1.61` bytes 83405-83409<br>2024-09-30 agrees | 1.88 / 1.88<br>`1.88` bytes 83311-83315<br>2024-12-31 agrees | 1.54 / 1.54<br>`1.54` bytes 83956-83960<br>2025-03-31 agrees |
| `pg_reported_eps_growth_pct` | percent / reported_eps_growth | 21 / 21<br>`21%` bytes 83814-83817<br>2025-09-30 agrees | -5 / -5<br>`(5)%` bytes 83720-83724<br>2025-12-31 agrees | 6 / 6<br>`6%` bytes 84365-84367<br>2026-03-31 agrees |
| `pg_core_eps` | usd_per_share / core_non_gaap | 1.99 / 1.99<br>`1.99` bytes 236799-236803<br>2025-09-30 agrees | 1.88 / 1.88<br>`1.88` bytes 248066-248070<br>2025-12-31 agrees | 1.59 / 1.59<br>`1.59` bytes 257268-257272<br>2026-03-31 agrees |
| `pg_prior_core_eps` | usd_per_share / core_non_gaap | 1.93 / 1.93<br>`1.93` bytes 13177-13181<br>2024-09-30 agrees | 1.88 / 1.88<br>`1.88` bytes 13430-13434<br>2024-12-31 agrees | 1.54 / 1.54<br>`1.54` bytes 13447-13451<br>2025-03-31 agrees |
| `pg_core_eps_growth_pct` | percent / core_eps_growth | 3 / 3<br>`3%` bytes 13498-13500<br>2025-09-30 agrees | 0 / 0<br>`&#8212;%` bytes 13751-13759<br>2025-12-31 agrees | 3 / 3<br>`3%` bytes 13768-13770<br>2026-03-31 agrees |
| `pg_core_reconciliation_context` | - | absent: `envelope_excluded:pg_core_reconciliation_context` (excluded by the 09-25 ruling) | absent: `envelope_excluded:pg_core_reconciliation_context` (excluded by the 09-25 ruling) | absent: `envelope_excluded:pg_core_reconciliation_context` (excluded by the 09-25 ruling) |
| `pg_beauty_organic_sales_growth_pct` | percent / organic_sales | 6 / 6<br>`6%` bytes 279147-279149<br>2025-09-30 agrees | 4 / 4<br>`4%` bytes 270826-270828<br>2025-12-31 agrees | 7 / 7<br>`7%` bytes 280485-280487<br>2026-03-31 agrees |
| `pg_grooming_organic_sales_growth_pct` | percent / organic_sales | 3 / 3<br>`3%` bytes 280583-280585<br>2025-09-30 agrees | 0 / 0<br>`&#8212;%` bytes 272262-272270<br>2025-12-31 agrees | 1 / 1<br>`1%` bytes 281921-281923<br>2026-03-31 agrees |
| `pg_health_care_organic_sales_growth_pct` | percent / organic_sales | 1 / 1<br>`1%` bytes 282022-282024<br>2025-09-30 agrees | 3 / 3<br>`3%` bytes 273707-273709<br>2025-12-31 agrees | 2 / 2<br>`2%` bytes 283360-283362<br>2026-03-31 agrees |
| `pg_fabric_home_organic_sales_growth_pct` | percent / organic_sales | 0 / 0<br>`&#8212;%` bytes 283466-283474<br>2025-09-30 agrees | 0 / 0<br>`&#8212;%` bytes 275157-275165<br>2025-12-31 agrees | 3 / 3<br>`3%` bytes 284810-284812<br>2026-03-31 agrees |
| `pg_baby_feminine_family_organic_sales_growth_pct` | percent / organic_sales | 0 / 0<br>`&#8212;%` bytes 284932-284940<br>2025-09-30 agrees | -4 / -4<br>`(4)%` bytes 276625-276629<br>2025-12-31 agrees | 3 / 3<br>`3%` bytes 286270-286272<br>2026-03-31 agrees |

- **FY26Q1** (0000080424-25-000240; event `evt_cik0000080424_2026q1_results`): 20 of 20 agree. The validator accepted the workspace and returns exactly the rows built: yes.
- **FY26Q2** (0000080424-26-000006; event `evt_cik0000080424_2026q2_results`): 20 of 20 agree. The validator accepted the workspace and returns exactly the rows built: yes.
- **FY26Q3** (0000080424-26-000056; event `evt_cik0000080424_2026q3_results`): 20 of 20 agree. The validator accepted the workspace and returns exactly the rows built: yes.

`pg_core_reconciliation_context` is outside the first release by the seat's 09-25 ruling (`SEAT_RULING_T1_ENVELOPE_2026-09-25.md`). It is excluded, not read. The oracle's headline prose for it is not compared.

## 3. Refusals

| case | document | run under | rows | present facts | detail every row carries | validator |
|---|---|---|---|---|---|---|
| `fy25_q4_layout` | FY25Q4 | FY25Q4 | 20 | 0 | `envelope_refused:unknown_table:t1` | accepted (20 typed absences) |
| `fy26_q4_layout` | FY26Q4 | FY26Q4 | 20 | 0 | `envelope_refused:unknown_table:t1` | accepted (20 typed absences) |
| `colgate` | CL2Q26 | FY26Q4 | 20 | 0 | `envelope_refused:not_ex_99_1` | accepted (20 typed absences) |
| `q3_under_q2_scope` | FY26Q3 | FY26Q2 | 20 | 0 | `envelope_refused:quarter_mismatch` | accepted (20 typed absences) |

A refused document yields a workspace that claims nothing. Each metric is a typed absence carrying the refusal. The validator accepts that workspace because it asserts no value.

## 4. Tampered workspaces (FY26 Q3)

| tamper | validator |
|---|---|
| reported sales growth 7.0 -> 8.0 | refused: selected observation does not replay from source bytes |
| diluted EPS 1.63 -> 1.64 | refused: selected observation does not replay from source bytes |
| period moved to the year-ago quarter end | refused: fact_id does not follow event, metric, period, and basis identity |
| period moved, fact identity recomputed to match | refused: selected observation does not replay from source bytes |
| unit percent -> percentage_points | refused: selected observation does not replay from source bytes |
| basis reported_sales -> organic_sales | refused: selected observation does not replay from source bytes |
| receipt span shifted one byte | refused: selected observation does not replay from source bytes |
| source byte under the span 7 -> 8 | refused: selected observation does not replay from source bytes |
| validated under FY26 Q2's fiscal scope | refused: workspace fiscal period does not match fiscal_scope |

## Reproduce

```
python t1_real_release_demo.py <tree> <out.json>   # from the tree root; exit 0 = no failure
```

The script's sha256 is `8dafb2c36e5c5a305679a868aac81e658d9e2ae6218a3c599b072d66371c52c3`, and its full source follows. It is a seat scratch script, not part of the product.

```python
"""CDV-1 T1 real-release demonstration: P&G's own EDGAR exhibits through the native path.

usage: python t1_real_release_demo.py <tree> <out.json>

The product path is spelled out below (bind_release_document -> build_event_workspace with the P&G profile ->
validate_selected_facts).  The frozen witness suite (tests/test_pg_envelope_f1.py) contributes only its Release records,
its oracle loader and its stdlib reader (text, literal), which import nothing from engine/.
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
import platform
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

import test_pg_envelope_f1 as t  # noqa: E402
import engine.company_intelligence.pg_profile as pgp  # noqa: E402
from engine.company_intelligence.economic_observations import (  # noqa: E402
    EconomicObservationError,
    _fact_id,
    validate_selected_facts,
)
from engine.company_intelligence.event_workspace_build import build_event_workspace  # noqa: E402
from engine.company_intelligence.events import FiscalPeriod  # noqa: E402
from engine.earnings_release.binding import bind_release_document  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "pg_envelope"
PIN = re.compile(r"^\| `([^`]+)` \| [^|]+ \| (\d{10}-\d{2}-\d{6}) \| (\S+) \| ([\d,]+) \| `([0-9a-f]{64})` \|", re.M)


def pins_from_sources_md() -> dict[str, dict]:
    return {m.group(1): {"accession": m.group(2), "accepted": m.group(3), "bytes": int(m.group(4).replace(",", "")),
                         "sha256": m.group(5)} for m in PIN.finditer((FIX / "SOURCES.md").read_text(encoding="utf-8"))}


def native(rel, body: str, period):
    """The product path: bind the exhibit to its filing, build the event workspace under the P&G profile."""
    filing = {"cik": rel.cik, "accession": rel.accession, "form": "8-K", "filing_date": rel.filed,
              "acceptance_datetime": rel.accepted, "report_date": rel.filed, "exhibit_url": t.exhibit_url(rel)}
    bound = bind_release_document(body=body, content_type="text/html", **filing)
    year, quarter, end = period.fiscal
    ws = build_event_workspace(registry=pgp.pg_private_registry(), ticker="PG", asof=date.fromisoformat(rel.filed),
                               fiscal_period=FiscalPeriod(year=year, quarter=quarter, calendar_end=date.fromisoformat(end)),
                               exhibit_body=bound.source, filing=filing, transcript=None, observed_at=rel.accepted,
                               source_available_at=rel.accepted, profile=pgp.pg_profile(fiscal_scope=period.scope))
    return ws, {bound.revision.document_id: bound.source}, bound


def validate(ws, texts, scope) -> tuple[str, object]:
    try:
        return "accepted", validate_selected_facts(ws, source_texts=texts, fiscal_scope=scope)
    except EconomicObservationError as exc:
        return "refused", str(exc)


def present(row) -> bool:
    return row.get("typed_absence") is None and row.get("value") is not None


report: dict = {"tree": str(ROOT), "python": platform.python_version(), "source": [], "admitted": [], "refused": [],
                "tampered": [], "failures": []}
fail = report["failures"].append

# 1. Source: every fixture decompresses to the bytes SOURCES.md pins, and the Release records agree.
pinned = pins_from_sources_md()
for rel in t.RELEASES.values():
    data = gzip.decompress((FIX / f"{rel.file}.gz").read_bytes())
    got = {"file": rel.file, "key": rel.key, "url": t.exhibit_url(rel), "accession": rel.accession,
           "accepted": rel.accepted, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    pin = pinned.get(rel.file)
    got["matches_sources_md"] = bool(pin) and all(got[k] == pin[k] for k in ("accession", "accepted", "bytes", "sha256"))
    got["matches_release_record"] = (got["sha256"], got["bytes"]) == (rel.sha256, rel.size)
    report["source"].append(got)
    if not (got["matches_sources_md"] and got["matches_release_record"]):
        fail(f"source {rel.file}: {got} vs {pin}")

# 2. Admitted releases: every metric against the independent oracle and against the EDGAR bytes at its receipt span.
for rel in t.F1Q:
    body = t.original(rel)
    ws, texts, bound = native(rel, body, rel)
    verdict, accepted = validate(ws, texts, rel.scope)
    rows, oracle = t.by_metric(ws), t.oracle_doc(rel)["metrics"]
    entry = {"key": rel.key, "accession": rel.accession, "quarter_end": rel.scope[1], "year_ago_quarter_end": rel.scope[3],
             "event_id": ws["event_id"], "validator": verdict,
             "validator_returns_the_built_rows": verdict == "accepted" and accepted == t.pg_rows(ws), "metrics": []}
    if not entry["validator_returns_the_built_rows"]:
        fail(f"{rel.key}: validator {verdict}: {accepted if verdict == 'refused' else ''}")
    raw = body.encode("utf-8")
    for m, (unit, basis) in t.UNIT_BASIS.items():
        row, want = rows[m], oracle[m]["expected"]
        rec = {"metric": m, "oracle_expected": want}
        if not present(row):
            absence = row["typed_absence"]
            rec.update(state="absent", reason=absence["reason"], detail=absence["detail"])
            ok = m == t.REC and (absence["reason"], absence["detail"]) == t.ABSENT[t.EXCLUDED]
        else:
            receipt = row["source_span"]["receipt"]
            start, end = receipt["span_start_byte"], receipt["span_end_byte"]
            printed = raw[start:end].decode("utf-8")
            rec.update(state="present", value=row["value"], unit=row["unit"], basis=row["basis"], period=row["period"],
                       span=[start, end], edgar_bytes=printed, receipt_source_sha256=receipt["source_sha256"],
                       receipt_state=row["source_span"]["receipt_state"])
            ok = (m in t.NUMERIC and abs(row["value"] - want) < 1e-9 and abs(t.literal(t.text(printed)) - row["value"]) < 1e-9
                  and (row["unit"], row["basis"]) == (unit, basis)
                  and row["period"] == (rel.scope[3] if m in t.PRIOR else rel.scope[1])
                  and receipt["source_sha256"] == rel.sha256 and row["source_span"]["receipt_state"] == "byte_replayed")
        rec["agrees"] = ok
        entry["metrics"].append(rec)
        if not ok:
            fail(f"{rel.key} {m}: {rec}")
    report["admitted"].append(entry)

# 3. Refusals: a document outside F1-Q, or the right document under the wrong quarter, admits no present fact.
for name in ("fy25_q4_layout", "fy26_q4_layout", "colgate", "q3_under_q2_scope"):
    rel, rewrite, period, detail = t.REFUSED[name]
    ws, texts, _ = native(rel, t.original(rel), period)
    rows = t.pg_rows(ws)
    details = sorted({r["typed_absence"]["detail"] for r in rows if r.get("typed_absence")})
    verdict, accepted = validate(ws, texts, period.scope)
    matches = all(re.fullmatch(detail, d) if isinstance(detail, re.Pattern) else d == detail for d in details)
    entry = {"case": name, "document": rel.key, "run_under": period.key, "rows": len(rows),
             "present": sum(present(r) for r in rows), "details": details, "validator": verdict,
             "validator_rows": len(accepted) if verdict == "accepted" else accepted}
    report["refused"].append(entry)
    if entry["present"] or not details or not matches or len(rows) != len(t.UNIT_BASIS):
        fail(f"refusal {name}: {entry}")

# 4. Tampered workspaces: the validator replays each selected observation from the source bytes.
rel = t.FY26Q3
ws0, texts0, _ = native(rel, t.original(rel), rel)
doc = next(iter(texts0))


def tamper_row(metric, change):
    def apply(ws, texts):
        change(t.by_metric(ws)[metric])
        return ws, texts, rel.scope
    return apply


def span_shift(row):
    for holder in (row["source_span"]["locator"], row["source_span"]["receipt"]):
        holder["span_start_byte"] += 1
        holder["span_end_byte"] += 1


def source_digit(ws, texts):
    receipt = t.by_metric(ws)[t.SALES]["source_span"]["receipt"]
    raw = bytearray(texts[doc].encode("utf-8"))
    assert raw[receipt["span_start_byte"]:receipt["span_start_byte"] + 1] == b"7"
    raw[receipt["span_start_byte"]] = ord("8")
    return ws, {doc: raw.decode("utf-8")}, rel.scope


TAMPER = {
    "reported sales growth 7.0 -> 8.0": tamper_row(t.SALES, lambda r: r.update(value=8.0)),
    "diluted EPS 1.63 -> 1.64": tamper_row(t.DIL, lambda r: r.update(value=1.64)),
    "period moved to the year-ago quarter end": tamper_row(t.SALES, lambda r: r.update(period=rel.scope[3])),
    "period moved, fact identity recomputed to match": tamper_row(t.SALES, lambda r: r.update(
        period=rel.scope[3], fact_id=_fact_id(r["event_id"], r["metric"], rel.scope[3], r["basis"]))),
    "unit percent -> percentage_points": tamper_row(t.SALES, lambda r: r.update(unit="percentage_points")),
    "basis reported_sales -> organic_sales": tamper_row(t.SALES, lambda r: r.update(basis="organic_sales")),
    "receipt span shifted one byte": tamper_row(t.SALES, span_shift),
    "source byte under the span 7 -> 8": source_digit,
    "validated under FY26 Q2's fiscal scope": lambda ws, texts: (ws, texts, t.FY26Q2.scope),
}
for name, apply in TAMPER.items():
    ws, texts, scope = apply(copy.deepcopy(ws0), dict(texts0))
    verdict, detail = validate(ws, texts, scope)
    report["tampered"].append({"case": name, "validator": verdict, "detail": detail if verdict == "refused" else None})
    if verdict != "refused":
        fail(f"tamper {name}: accepted")

Path(sys.argv[2]).write_text(json.dumps(report, indent=1, default=str) + "\n", encoding="utf-8")
print(f"python {report['python']}: sources {sum(s['matches_sources_md'] for s in report['source'])}/{len(report['source'])}",
      f"| admitted {[(a['key'], sum(m['agrees'] for m in a['metrics']), len(a['metrics']), a['validator']) for a in report['admitted']]}",
      f"| refused {[(r['case'], r['present'], r['validator']) for r in report['refused']]}",
      f"| tampered refused {sum(x['validator'] == 'refused' for x in report['tampered'])}/{len(report['tampered'])}",
      f"| failures {len(report['failures'])}")
for line in report["failures"]:
    print("FAIL", line[:400])
sys.exit(1 if report["failures"] else 0)
```
