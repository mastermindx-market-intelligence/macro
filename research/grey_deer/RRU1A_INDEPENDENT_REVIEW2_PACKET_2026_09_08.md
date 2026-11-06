# Direct bounded independent review

Operation: risk-radar-rru1a-static-review2-20260908-sol-001.
RECEIVER_MODE: DIRECT_TARGETED; the one native Claude print invocation receiving this packet.
ROUTE: review; worker Opus, Claude Code subscription surface, no tools or repository effects.
WHY: independent cross-model review of aggregation, missingness and calibration implications.
WHY NOT FABLE: narrow mathematical/code review; no principal architecture or orchestration.
The parent Sol remains on existing Chat; this does not provision or select another Chat mode.
Verified native auth: claude.ai / Max. No API route or automatic account/model failover.

SECTION: MISSION
Review the one-line arithmetic candidate and its tests. Is it mathematically correct,
what does its evidence actually prove, and what must precede a production release?
SECTION: WHY IT MATTERS
Users need honest risk readings and timely recovery, not false confidence from missing inputs.
SECTION: AUTHORITY
Current Chairman continuation permits this bounded review. Protected Mastermind
2bf0266d5476c8e75dae4afa87cca67a8f12a838 governs; no merge/deploy/policy authority.
SECTION: ARTIFACT TO ATTACK
Immutable research candidate at Macro 8fb7d6d6f1a9182dde5b5bf1d5e70391cc762352;
production baseline eb9e91961ddc4f3043d0dad358602525e66eccda. Exact inputs follow.
SECTION: REVIEW STANDARD
Review evidence against declared scope. Do not claim tests you did not run. Separate
mathematical correctness, complete-input parity, current-vintage sensitivity, PIT
forecast validation and user proof. Treat historical corrections and model calibration
as separate. No claim that the candidate fixes null-to-calm or stale-source dating.

SECTION: SCOPE AND NON-GOALS
Text-only static review. No tools, data reads, source writes, policy changes, new
workers, GitHub/Slack actions or attempts to reproduce any platform-blocked operation.
Do not read or request the later real-data diagnostic output; it is outside this review.
SECTION: USER JOURNEY
Regional inputs -> existing composite -> percentile/band -> existing consumer. Missing
inputs must not inject phantom weight; complete-input paths must remain unchanged.
SECTION: DATA TIME NULL CORRECTION
Original issued predictions stay preserved. A corrected historic component can change
today's rank. No point-in-time claim from a current-vintage series. Coverage changes
must not silently inherit a probability table fitted to a different composition.
SECTION: METHOD
Deterministic code and static analysis. The model supplies critique only, no risk score.
SECTION: FAILURES
Missing packet evidence -> report the exact limitation. Never invent a PASS or test result.
SECTION: ORDER
Acknowledge this exact operation, separately state read-only review START, inspect the
provided code/tests, and return findings. No source execution is requested.
SECTION: ACCEPTANCE
Return STATUS, RESULT, EVIDENCE, GAPS, DEVIATIONS. Each finding has severity, exact
source and a minimal discriminating repair/test. A clean static review is not release.
SECTION: STOP AND CONTINUATION
One finite non-watcher invocation only. Return the review, stop, and create no watcher
or follow-on task. Sol owns any subsequent adjudication outside this child.

## research/grey_deer/RRU1A_MISSINGNESS_CANDIDATE.patch
```
--- a/engine/risk_radar_intl.py
+++ b/engine/risk_radar_intl.py
@@ -267,7 +267,7 @@
     # blended composite → trailing percentile → 0-1 risk score
     num = den = None
     for ser, w in comp_series_parts.values():
-        col = ser.fillna(0.5) * w
+        col = ser.fillna(0.0) * w
         av = ser.notna().astype(float) * w
         num = col if num is None else num + col
         den = av if den is None else den + av

```

## research/grey_deer/RRU1A_MISSINGNESS_TESTS_2026_09_08.py
```
"""Synthetic arithmetic regression over all actual international profile definitions.
Optional --patch applies one textual delta IN MEMORY ONLY. No source file is edited.
The identity percentile exposes the pre-rank aggregation, not a live radar score.
"""
from __future__ import annotations
import argparse
import ast
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import RISK_RADAR_INTEGRITY_PROBES_2026_09_08 as probes

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "engine/risk_radar_intl.py"
RAW = SOURCE.read_bytes()
CANDIDATE = RAW

def profiles():
    env = dict(dataclass=dataclass, field=field)
    wanted = {"_BANDS", "_DISCLAIMER", "_INTL_7_DISCLAIMER"}
    selected = []
    for node in ast.parse(RAW.decode()).body:
        if isinstance(node, ast.ClassDef) and node.name == "RadarProfile":
            selected.append(node)
        elif isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if names & wanted or any(name.endswith("_PROFILE") for name in names):
                selected.append(node)
    env["__name__"] = __name__
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, *selected], type_ignores=[])), str(SOURCE), "exec"), env)
    result = sorted((value for name, value in env.items() if name.endswith("_PROFILE")), key=lambda p: p.key)
    assert {p.key for p in result} == {"cn", "hk", "ca", "kr", "jp", "tw", "in", "au", "gb", "ez"}
    return result

PROFILES = profiles()
INDEX = pd.bdate_range("2023-01-02", periods=601)

def output(profile, series, candidate=CANDIDATE):
    bench = pd.Series(np.linspace(100.0, 140.0, len(INDEX)), index=INDEX)
    env = dict(pd=pd, np=np, _PCT_WIN=504, _read=lambda *args: bench,
               _sub_legs=lambda *args: series,
               pct_rank_window=lambda s, window: s,
               _gate_series=lambda *args: pd.Series(False, index=INDEX))
    read_bytes = Path.read_bytes
    def isolated_read(path):
        return candidate if path == SOURCE else read_bytes(path)
    with patch.object(Path, "read_bytes", isolated_read):
        probes.load(ROOT, "engine/risk_radar_intl.py", ["composite_series"], env)
    return env["composite_series"](profile)[2]

def sample(profile, partial=False):
    codes = sorted({code for _, group, _ in profile.comp_legs for code in group})
    rng = np.random.default_rng(20260908)
    result = {}
    for code in codes:
        values = rng.uniform(0.05, 0.95, len(INDEX))
        if partial:
            missing = rng.random(len(INDEX)) < 0.20
            missing[:100] = False
            values[missing] = np.nan
        result[code] = pd.Series(values, index=INDEX)
    return result

def reference(profile, series):
    values = []
    for position in range(len(INDEX)):
        weighted = []
        for _, codes, weight in profile.comp_legs:
            available = [float(series[c].iloc[position]) for c in codes
                         if c in series and pd.notna(series[c].iloc[position])]
            if available:
                weighted.append((sum(available) / len(available), weight))
        value = sum(x * w for x, w in weighted) / sum(w for _, w in weighted) if weighted else np.nan
        values.append(value)
    return pd.Series(values, index=INDEX).dropna()

class MissingnessRegression(unittest.TestCase):
    pass

def make_test(profile, case):
    def test(self):
        series = sample(profile, partial=(case == "partial"))
        first_group = profile.comp_legs[0][1]
        if case == "missing_group":
            for code in first_group:
                series[code].iloc[-50:] = np.nan
        elif case == "all_missing":
            for value in series.values():
                value.iloc[-10:] = np.nan
        actual = output(profile, series, candidate=CANDIDATE)
        expected = reference(profile, series)
        self.assertEqual(list(actual.index), list(expected.index))
        np.testing.assert_allclose(actual.to_numpy(), expected.to_numpy(), rtol=1e-12, atol=1e-12)
        self.assertTrue(((actual >= 0.0) & (actual <= 1.0)).all())
        if case == "complete":
            original = output(profile, series, candidate=RAW)
            np.testing.assert_array_equal(actual.to_numpy(), original.to_numpy())
    return test

for profile in PROFILES:
    for case in ("complete", "partial", "missing_group", "all_missing"):
        setattr(MissingnessRegression, f"test_{profile.key}_{case}", make_test(profile, case))

def main():
    global CANDIDATE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patch", type=Path, help="One-line unified patch, applied only in memory")
    args = parser.parse_args()
    expected = "1596e1da4794bf97d49f6f0ae42eaabff7226fa812fb0a96bfb0a6242faf7cd7"
    if hashlib.sha256(RAW).hexdigest() != expected:
        raise SystemExit("Source pin changed: re-review before transferring this receipt.")
    if args.patch:
        lines = args.patch.read_text().splitlines()
        removed = [s[1:] for s in lines if s.startswith("-") and not s.startswith("---")]
        added = [s[1:] for s in lines if s.startswith("+") and not s.startswith("+++")]
        if len(removed) != 1 or len(added) != 1 or RAW.decode().count(removed[0]) != 1:
            raise SystemExit("Candidate must contain exactly one unique source-line replacement.")
        CANDIDATE = RAW.decode().replace(removed[0], added[0]).encode()
    print("SOURCE_SHA256", hashlib.sha256(RAW).hexdigest(), flush=True)
    print("CANDIDATE_SHA256", hashlib.sha256(CANDIDATE).hexdigest(), flush=True)
    print("PROFILE_KEYS", ",".join(p.key for p in PROFILES), flush=True)
    print("SCOPE synthetic arithmetic only; no engine file, ledger, or production mutation", flush=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MissingnessRegression)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)

if __name__ == "__main__":
    main()

```

## research/grey_deer/RRU1A_MODULE_COMPATIBILITY_2026_09_08.py
```
"""Run the actual owning pytest suite with the candidate function in memory only.
No engine source is written. Tests keep their existing synthetic-store/data guards.
This is module regression proof, not historical replay or production acceptance.
"""
from __future__ import annotations
import ast
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT / "engine/risk_radar_intl.py"
raw = SOURCE.read_bytes()
expected = "1596e1da4794bf97d49f6f0ae42eaabff7226fa812fb0a96bfb0a6242faf7cd7"
if hashlib.sha256(raw).hexdigest() != expected:
    raise SystemExit("Source pin changed; do not transfer the old receipt.")
patch_path = Path(__file__).with_name("RRU1A_MISSINGNESS_CANDIDATE.patch")
lines = patch_path.read_text().splitlines()
removed = [s[1:] for s in lines if s.startswith("-") and not s.startswith("---")]
added = [s[1:] for s in lines if s.startswith("+") and not s.startswith("+++")]
if len(removed) != 1 or len(added) != 1 or raw.decode().count(removed[0]) != 1:
    raise SystemExit("Candidate is not one unique line replacement.")
text = raw.decode().replace(removed[0], added[0])

from engine import risk_radar_intl as radar
import pytest

node = next(n for n in ast.parse(text).body
            if isinstance(n, ast.FunctionDef) and n.name == "composite_series")
future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
module = ast.fix_missing_locations(ast.Module(body=[future, node], type_ignores=[]))
exec(compile(module, str(SOURCE), "exec"), radar.__dict__)
print("SOURCE_SHA256", expected, flush=True)
print("CANDIDATE_SHA256", hashlib.sha256(text.encode()).hexdigest(), flush=True)
print("PATCH_SHA256", hashlib.sha256(patch_path.read_bytes()).hexdigest(), flush=True)
print("MODE in-memory candidate; actual module, percentile and owning tests", flush=True)
result = pytest.main([str(ROOT / "tests/test_risk_radar_intl_profiles.py"), "-q"])
if SOURCE.read_bytes() != raw:
    raise SystemExit("Unexpected source mutation during test execution.")
print("SOURCE_UNCHANGED", True, flush=True)
raise SystemExit(int(result))

```

## research/grey_deer/RISK_RADAR_RRU1A_MISSINGNESS_PLAN_2026-09-08.md
```
# RRU-1A: available-weight arithmetic implementation plan

Goal: missing input groups cannot inject phantom risk into any international profile's composite.
Architecture: repair the existing `composite_series` function; preserve the profile, weights, state gates, probability tables and producer/consumer owners. No new scoring module or data plane.
Tech stack: existing Python, pandas, NumPy and pytest; no new dependency.
Spec: `research/grey_deer/RISK_RADAR_ALL_REGIONS_UPGRADE_FREEZE_2026-09-08.md`.
Status: PREPARED / research candidate only. The production source has not been changed. The full path census remains incomplete for PR #6657 after a platform refusal; this plan does not authorize evasion of that refusal or a competing source writer.

## 0. Acceptance gates

Not done unless the same mathematical availability mask governs numerator and denominator; complete-input windows remain byte/numerically unchanged; missingness tests cover all ten actual international profile definitions; the exact candidate passes existing owning tests and independently reviewed real-data impact analysis; calibration applicability is disclosed; the real consumer receives and displays the correct source/quality state after normal publication. Green synthetic arithmetic alone is not production acceptance.

The candidate is not permitted to edit risk weights, probability tables, score thresholds, market-state ceilings, policy, UI layout, auth, CI workflow permissions or existing forward-history rows. Finite-value/freshness behavior beyond the already-defined missing-value arithmetic is RRU-1B, not a hidden addition to this line change.

## 1. Current reproducible evidence

Base: Macro `eb9e91961ddc4f3043d0dad358602525e66eccda`.
Source: `engine/risk_radar_intl.py`, SHA256 `1596e1da4794bf97d49f6f0ae42eaabff7226fa812fb0a96bfb0a6242faf7cd7`.
The old numerator uses `ser.fillna(0.5) * w`, while the denominator excludes missing weight. Two equal-weight 0.9 inputs become 1.4 when one becomes missing, rather than the available-input mean 0.9. This is the raw blend before percentile conversion, not a claim of a live 140/100 reading.

The committed research harness loads the actual ten `RadarProfile` definitions and the source `composite_series` function. Its controlled benchmark/series and identity percentile isolate the arithmetic. An independent row-wise oracle computes the available-weight mean; it does not copy the vectorized implementation. All groups and weights come from the real profile definitions.

Baseline: 40 named tests, 20 expected assertion failures (partial and missing-group cases for each of ten profiles), 20 passing controls. Candidate: 40/40 pass, including exact full-window complete-input parity. Inputs are synthetic; they are not ten historical market backtests. Receipts: `RRU1A_BASELINE_RED_2026_09_08.txt` and `RRU1A_CANDIDATE_GREEN_2026_09_08.txt`.

## 2. Exact bounded source delta

Owned production file for the future source wave: `engine/risk_radar_intl.py`, aggregation loop only. Existing owning test home: `tests/test_risk_radar_intl_profiles.py`, verified with the tracked-file census at this base. The research harness remains a separately labelled reproducibility asset, not a second production engine.

The prepared `RRU1A_MISSINGNESS_CANDIDATE.patch` contains exactly:

```diff
-        col = ser.fillna(0.5) * w
+        col = ser.fillna(0.0) * w
```

This does not turn missing data into a risk value of zero: its weight remains absent from the denominator. Zero is the neutral additive contribution to the numerator. With all groups missing, the zero denominator remains masked and the row remains absent; the separate public-compute null/calm defect is not repaired by this line.

## 3. Test-first execution sequence

- [x] Read and pin the existing construction and all ten profile definitions.
- [x] Reproduce the 0.9/1.4 arithmetic defect without production I/O.
- [x] Run the 40-case source-function suite before authoring the candidate; observe 20 expected failures.
- [x] Prepare the one-line candidate only after that red result.
- [x] Apply the candidate only in the research harness's memory and observe 40/40 pass.
- [ ] Complete the release's exact-path collision/owner census lawfully; do not bypass the blocked #6657 read.
- [ ] Bind one source worker on one operation/carrier, re-pin source and current law, and run the actual owning suite before editing.
- [ ] Port the missingness cases into the owning pytest suite using its existing isolated-store fixtures; preserve the source-function research reproduction.
- [ ] Apply the one-line delta to the owned source branch, not the shared checkout.
- [ ] Run owning tests, historical-impact diagnostics and canonical consumer proof; obtain independent review before release.

Reproduce the research evidence from the repository root:

```bash
python3 research/grey_deer/RRU1A_MISSINGNESS_TESTS_2026_09_08.py
# Expected baseline: 40 tests, 20 failures, exit 1.
python3 research/grey_deer/RRU1A_MISSINGNESS_TESTS_2026_09_08.py --patch research/grey_deer/RRU1A_MISSINGNESS_CANDIDATE.patch
# Expected candidate-in-memory: 40 tests, all pass, exit 0.
```

## 4. Production-suite and real-data impact proof

The tracked owning file is `tests/test_risk_radar_intl_profiles.py`; this was verified with `git ls-files`, not inferred from a directory response. It provides synthetic store readers for the real module. Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_risk_radar_intl_profiles.py -q
```

The isolated 40-case harness is not a substitute for this suite. Its percentile stub deliberately does not assess rank-window behavior, real input composition, calibration, or rendering. The exact candidate still needs the actual module/percentile path and regional consumer tests under the existing no-network/data-write guards.

Historical impact analysis must run read-only on pinned data copies. For each of ten profiles report first affected raw-blend date, rows with missing component groups, changed percentile dates, changed bands/probabilities, and current score implications. Preserve original issued forecasts and evaluation rows. Diagnostic reconstruction is not prospective evidence. Report sample gaps rather than replacing unavailable history with another market.

Important propagation effect: a corrected historical raw blend can change today's trailing percentile even when today's inputs are complete. The passing complete-input test covers an entirely complete window; it does not prove that the latest complete row is unchanged after repairing missing values earlier in its window. Explicitly test that case and explain any difference instead of suppressing it.

A changed composition or corrected training sample must not inherit an old calibration claim unexamined. Sol's review decides whether existing probabilities remain applicable, need uncertainty disclosure, or must be withheld pending recalibration under the frozen evaluation law. Do not silently tune a new table within this arithmetic PR.

## 5. Consumer and operational acceptance

Trace `composite_series -> compute -> existing market_state radar projection -> regional card/dialog` using the same profile and source clocks. Confirm that missing all groups does not become a current calm claim; that known separate RRU-1B defect remains an explicit release consideration, not hidden as repaired here. A partial-input number must not be labelled full-evidence calibrated risk.

Use real canonical production input after normal publication, with benchmark/session/bundle identity and visible regional consumer output. Test complete, partially missing, all missing, restored input and stale source scenarios. Observe rather than change the settled ledger; no intraday append, fixture row or recalculated history may enter the prospective log. Independent reviewer must identify what this one-line change does not prove.

## 6. Handoff and stop

Future source operation owns only the named arithmetic repair and its directly related tests/evidence. No source writer is assigned by reading this file. Before execution load the then-current same-commit Skillpack and applicable routing/dialogue laws, reconcile current source ownership, and bind one eligible worker/carrier. Unbound placement is WAITING_CAPACITY, not Chairman account-allocation work.

Return exact branch/head/tree, changed paths/blobs, baseline/red/green receipts, real-data impact, calibration disposition, current checks and production evidence or its exact missing gate. Stop before null-policy repair, recovery redesign, arbitrary signal improvements or another region's independent feature. Sol retains release and acceptance; a prepared patch is not a deployed fix.

## 7. Additional module compatibility receipt

The unchanged owning suite passed 12/12. The candidate then passed the same 12/12 tests with the real module and percentile implementation, replacing only `composite_series` in the isolated test process. `RRU1A_MODULE_COMPATIBILITY_2026_09_08.py` reproduces that check; `RRU1A_OWNING_BASELINE_2026_09_08.txt` and `RRU1A_OWNING_CANDIDATE_2026_09_08.txt` preserve the outputs. Source bytes were checked unchanged after execution. This adds module regression evidence, not production or historical-data proof.

Candidate source SHA256: `d33e7425be4981f731fa5ec5d6bac6f70a117c419cbd1bfdac4c4d350ea63b38`; patch SHA256: `180eddd157dc4a98901c9437461b9923d0632a441af41c48c812080b0c23ec0e`.

Evidence formatting: the baseline unittest log retains every failure and assertion;
only trailing whitespace on its 20 `AssertionError:` lines was normalized for the
repository whitespace check. No result, comparison, count or traceback was removed.

```

## Original engine/risk_radar_intl.py:198-315
```python
198: def _calib(profile: "RadarProfile", root=None) -> dict:
199:     """Per-market calibration = the baked profile surface, OPTIONALLY overlaid by the bounded
200:     tuner (data/risk_radar_intl/<key>_calibration.json, engine/risk_radar_intl_tune.py). The
201:     overlay may adjust the prob surface only (the displayed odds become measured from the
202:     radar's own track record); the bands stay structural. Absent file ⇒ baked defaults."""
203:     cal = {"prob_cal": {h: dict(v) for h, v in profile.prob_cal.items()},
204:            "prob_base": dict(profile.prob_base), "bands": dict(profile.bands)}
205:     try:
206:         base = config.data_dir() if root is None else (Path(root) / "data")
207:         p = base / "risk_radar_intl" / f"{profile.key}_calibration.json"
208:         if p.exists():
209:             ov = json.loads(p.read_text())
210:             for h, d in (ov.get("prob_cal") or {}).items():
211:                 if h in cal["prob_cal"]:
212:                     cal["prob_cal"][h].update({k: float(v) for k, v in d.items()})
213:             if ov.get("prob_base"):
214:                 cal["prob_base"].update({k: float(v) for k, v in ov["prob_base"].items()})
215:     except Exception as e:  # noqa: BLE001
216:         log.warning("risk_radar_intl calib overlay(%s) failed: %s", profile.key, e)
217:     return cal
218:
219:
220: def _probs(cal: dict, state: str) -> dict:
221:     pc, base = cal["prob_cal"], cal["prob_base"]
222:     out = {h: pc[h].get(state, base[h]) for h in ("h5", "h10", "h21")}
223:     out["base_h5"], out["base_h10"], out["base_h21"] = base["h5"], base["h10"], base["h21"]
224:     out["lift_h21"] = round(out["h21"] / base["h21"], 2) if base["h21"] else None
225:     out["measure"] = ">=5% index pullback within h business days (measured on this market's own history)"
226:     return out
227:
228:
229: def _gate_series(B: pd.Series, sub: dict, profile: "RadarProfile") -> pd.Series:
230:     """True where the context gate is OPEN (loud tiers allowed). Causal. Legacy mode:
231:     index below its 200dma ("all boats" confirmation). Melt-up mode additionally opens
232:     while the extension percentile has printed parabolic (>= _EXT_PARABOLIC) within the
233:     last _GATE_MEMORY sessions — at a parabolic top the index is far ABOVE its 200dma,
234:     so the legacy gate would structurally silence the radar exactly when it matters
235:     (KOSPI 2026-06; INTL-50 ruling: no macro gate, only price/extension context gate)."""
236:     ma = B.rolling(200, min_periods=120).mean()
237:     gate = (B < ma).fillna(False)
238:     if profile.gate_mode == "below_or_recent_parabolic" and profile.ext_sources:
239:         e = sub.get(profile.ext_sources[0][2])
240:         if e is not None:
241:             recent_para = e.rolling(_GATE_MEMORY, min_periods=1).max() >= _EXT_PARABOLIC
242:             gate = gate | recent_para.reindex(B.index).fillna(False)
243:     return gate
244:
245:
246: def composite_series(profile: "RadarProfile", root=None):
247:     """(B, sub, comp, gate) — bench closes, sub-leg percentile dict, blended composite
248:     trailing percentile (0-1), and the boolean context-gate series. None when no data.
249:     THE single construction compute() and scripts/calibrate_risk_radar_intl.py share."""
250:     B = _read(*profile.bench)
251:     if B is None or len(B) < 300:
252:         return None, None, None, None
253:     idx = B.index
254:     sub = _sub_legs(idx, profile)
255:     if not sub:
256:         return None, None, None, None
257:
258:     # composite-leg latest percentiles + series (the calibrated structure)
259:     comp_series_parts: dict[str, tuple] = {}
260:     for comp_key, sub_codes, w in profile.comp_legs:
261:         members = [sub[c] for c in sub_codes if c in sub]
262:         if not members:
263:             continue
264:         ser = pd.concat(members, axis=1).mean(axis=1)
265:         comp_series_parts[comp_key] = (ser, w)
266:
267:     # blended composite → trailing percentile → 0-1 risk score
268:     num = den = None
269:     for ser, w in comp_series_parts.values():
270:         col = ser.fillna(0.5) * w
271:         av = ser.notna().astype(float) * w
272:         num = col if num is None else num + col
273:         den = av if den is None else den + av
274:     if num is None:
275:         return None, None, None, None
276:
277:     comp = pct_rank_window((num / den.replace(0, np.nan)).dropna(), _PCT_WIN)
278:     gate = _gate_series(B, sub, profile)
279:     return B, sub, comp, gate
280:
281:
282: def _trajectory(comp, B, cal, window: int = 30, gate: pd.Series | None = None) -> dict | None:
283:     """Recent PATH of this market's composite radar — has it peaked + started rolling over, and how
284:     fast are the pullback odds dropping? Powers the de-escalation panel (engine/risk_radar_recovery).
285:     Reuses the SHARED classifier (engine/risk_radar._trajectory_from_series) so the phase logic is
286:     identical to the US radar. Leak-free (comp is a causal trailing percentile). Never raises.
287:
288:     gate: when given, use it in place of the internally-computed below series. For legacy profiles
289:     the passed gate equals the internally-computed below → identical output."""
290:     try:
291:         from engine.risk_radar import _trajectory_from_series
292:         intensity = (comp.dropna() * 100.0)
293:         if len(intensity) < 10:
294:             return None
295:         bands = cal["bands"]
296:         if gate is not None:
297:             below = gate.reindex(intensity.index).fillna(False)
298:         else:
299:             ma = B.rolling(200, min_periods=120).mean()
300:             below = (B < ma).reindex(intensity.index).fillna(False)   # context gate: index < 200dma
301:         win = intensity.tail(window)
302:         states, odds = [], []
303:         for d, v in win.items():
304:             st = _band(v, bands)
305:             if not bool(below.get(d, False)) and _STATE_ORDER.index(st) > _STATE_ORDER.index("caution"):
306:                 st = "caution"                                     # gate caps the loud tiers
307:             states.append(st)
308:             odds.append(_probs(cal, st)["h21"])
309:         return _trajectory_from_series(win, states, pd.Series(odds, index=win.index), bands["caution"])
310:     except Exception as e:  # noqa: BLE001 — additive, never fatal
311:         log.warning("risk_radar_intl trajectory failed: %s", e)
312:         return None
313:
314:
315: def compute(profile: "RadarProfile", root=None) -> dict:
```

Prior native review invocation ended without a recovered result during a transport restart. Its separate reconciliation record is RRU1A_REVIEW_INTERRUPTION_RECONCILIATION_2026-09-08.md. This is a new finite review assignment on the same native carrier, not a source retry or account failover.
