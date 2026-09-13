"""Build an explicitly uninstalled, source-bound patch bundle for the research rig."""
from __future__ import annotations
import ast
import difflib
import hashlib
import json
from pathlib import Path
from RRU_COMPOSITION_ACCEPTANCE_2026_09_08 import SOURCES, PATHS, committed
SOURCES = dict(SOURCES)

HERE = Path(__file__).resolve().parent
edited = dict(SOURCES)
bundle = {}

def change(path, old, new, functions=()):
    if edited[path].count(old) != 1:
        raise ValueError(f"Replacement must be unique: {path}: {old[:70]}")
    entry = bundle.setdefault(path, dict(base_sha256=hashlib.sha256(SOURCES[path].encode()).hexdigest(),
                                       replacements=[], functions=[]))
    entry["replacements"].append(dict(old=old, new=new))
    entry["functions"] = sorted(set(entry["functions"]) | set(functions))
    edited[path] = edited[path].replace(old, new, 1)

p = PATHS[0]
helper = (HERE / "RRU_COMPOSITION_HELPER_2026_09_08.txt").read_text()
change(p, "def composite_series(", helper + "def composite_series(", ["_composition_coverage", "composite_series"])
change(p, "    sub = _sub_legs(idx, profile)\n", "    sub = {c: s.reindex(idx).replace([np.inf, -np.inf], np.nan)\n           for c, s in (_sub_legs(idx, profile) or {}).items() if s is not None}\n")
change(p, "        col = ser.fillna(0.5) * w", "        col = ser.fillna(0.0) * w")
old = '''    B, sub, comp, gate = composite_series(profile, root)
    if B is None:
        return null
    if sub is None or comp is None or gate is None:
        return null
    cal = _calib(profile, root)'''
new = '''    B, sub, comp, gate = composite_series(profile, root)
    coverage = _composition_coverage(profile, sub, comp, B.index if B is not None else [])
    null.update(composition=coverage, asof=coverage["asof"])
    if B is None or sub is None or comp is None or gate is None:
        return null
    if not coverage["score_current"]:
        null["degraded_reason"] = "no_current_composite"
        return null
    cal = _calib(profile, root)'''
change(p, old, new, ["compute"])
change(p, "        comp_last[comp_key] = _last(ser)",
       "        comp_last[comp_key] = _last(ser.reindex([B.index[-1]]))")
change(p, "    top = _last(comp)\n", "    top = float(comp.loc[B.index[-1]])\n")
change(p, "if (sub_latest := _last(sub.get(c))) is not None and sub_latest >= 0.55]",
       "if c in sub and (sub_latest := _last(sub[c].reindex([B.index[-1]]))) is not None and sub_latest >= 0.55]")
change(p, '        "market": profile.key,\n        "state": state,',
       '        "market": profile.key,\n        "composition": coverage,\n        "state": state,')
p = PATHS[1]
change(p, '    dp = rr.get("drawdown_prob") or {}\n', '''    dp = rr.get("drawdown_prob") or {}
    composition = rr.get("composition")
    reference_only = bool(composition and composition.get("calibration_status") == "unreviewed_corrected_construction")
    legacy_dp = dp if reference_only else None
    if reference_only:
        dp = {}
''', ["_radar_to_rd"])
change(p, '        "label_en": rr.get("dominant_label_en") or "calm",',
       '        "label_en": ("Current reading unavailable" if composition and not composition.get("score_current") else ("Partial-input risk reading" if composition and composition.get("status") == "PARTIAL" else rr.get("dominant_label_en") or "calm")),')
change(p, '        "label_zh": rr.get("dominant_label_zh") or "平静",',
       '        "label_zh": ("当前读数暂缺" if composition and not composition.get("score_current") else ("输入不完整的风险读数" if composition and composition.get("status") == "PARTIAL" else rr.get("dominant_label_zh") or "平静")),')
change(p, '        "do_en": _RADAR_DO.get(state, ("", ""))[0],',
       '        "do_en": "Review price and breadth alongside this reading." if reference_only else _RADAR_DO.get(state, ("", ""))[0],')
change(p, '        "do_zh": _RADAR_DO.get(state, ("", ""))[1],',
       '        "do_zh": "结合价格与市场广度观察此读数。" if reference_only else _RADAR_DO.get(state, ("", ""))[1],')
change(p, '        "gross": _num(rr.get("gross_factor")),',
       '        "gross": None if reference_only else _num(rr.get("gross_factor")),\n        "composition": composition,\n        "legacy_drawdown_prob": legacy_dp,')
p = PATHS[2]
change(p, '        rr = (latest or {}).get("risk_radar") or {}\n', '''        rr = (latest or {}).get("risk_radar") or {}
        composition = rr.get("composition")
        if composition and not composition.get("comparison_comparable"):
            return {"present": False, "assessment_status": "unavailable",
                    "degraded_reason": "composition_not_comparable"}
''', ["assess"])
change(p, '        # RRX2 WA-3: mirror the drivers block (which scares faded / warm) from trajectory.', '''        if composition and composition.get("calibration_status") == "unreviewed_corrected_construction":
            odds_now = odds_peak = odds_delta = None
            if not suppressed:
                head_en = "Risk reading easing" if receding else "Risk reading stabilizing"
                head_zh = "风险读数回落" if receding else "风险读数趋稳"
                sub_en = "The input-based reading changed; forecast calibration remains under review."
                sub_zh = "输入驱动的读数出现变化；预测校准仍待核验。"
                do_en = "Watch price and participation; this does not confirm a market low."
                do_zh = "观察价格与参与广度；此读数不能确认市场低点。"
            turn_confirmed = False
            turn_confirmed_full = False if market == "us" else None
        # RRX2 WA-3: mirror the drivers block (which scares faded / warm) from trajectory.''')
p = PATHS[3]
change(p, '{% macro risk_radar_card(rd, scares=none, show_threats=true) -%}', '''{% macro risk_radar_card(rd, scares=none, show_threats=true) -%}
{%- set _q = rd.composition if rd.composition is defined else none -%}
{%- set _unknown = _q and not _q.score_current -%}''')
change(p, '{%- set rc = ', "{%- set rc = 'var(--muted)' if _unknown else ")
change(p, '{%- set ic = ', "{%- set ic = '—' if _unknown else ")
change(p, '{{ t(rd.state|upper, rd.state_zh) }}',
       "{{ t('Reading unavailable','读数暂缺') if _unknown else t(rd.state|upper, rd.state_zh) }}")
coverage = '''      {% if _q %}
      <div class="rrx-authority is-advisory" data-composition-status="{{ _q.status }}">
        {{ t('Input coverage','输入覆盖') }}: {{ _q.members_available }} / {{ _q.members_expected }}.
        {% if _q.status != 'COMPLETE' %}{{ t('Some inputs unavailable.','部分输入暂缺。') }}{% endif %}
        {% if not _q.comparison_comparable %}{{ t('Recovery comparison unavailable.','复苏对比暂不可用。') }}{% endif %}
        <details><summary>{{ t('Data details','数据详情') }}</summary>
          <div>{{ t('Groups available','可用输入组') }}: {{ _q.groups_available }} / {{ _q.groups_expected }}.</div>
          {% for group in _q.groups %}
          <div>{% for code in group.expected %}{{ rr_leg(code) }}: {{ t('Available','可用') if code in group.present else t('Unavailable','暂缺') }}{{ '; ' if not loop.last }}{% endfor %}</div>
          {% endfor %}
          <div>{{ t('Availability does not establish freshness.','输入可用不代表来源及时。') }}</div>
        </details>
        {% if _q.calibration_status == 'unreviewed_corrected_construction' %}<div>{{ t('Forecast calibration under review.','预测校准待核验。') }}</div>{% endif %}
      </div>
      {% endif %}
'''
change(p, '      {% if rd.amp and rd.amp > 0 %}', coverage + '      {% if rd.amp and rd.amp > 0 %}')

# The separately reproduced snapshot failure must carry the same unavailable contract.
change(PATHS[0], '                "market": getattr(profile, "key", None), "degraded_reason": "compute_error",',
       '                "market": getattr(profile, "key", None), "degraded_reason": "compute_error",\n                "composition": _composition_coverage(profile, {}, None, []),', ["snapshot"])

# The edge suite rejects a calm checkmark on an incomplete current reading.
p = PATHS[3]
change(p, '{%- set _unknown = _q and not _q.score_current -%}', '''{%- set _unknown = _q and not _q.score_current -%}
{%- set _partial = _q and _q.status == 'PARTIAL' -%}
{%- set _limited = _unknown or _partial -%}''')
change(p, "'var(--muted)' if _unknown else", "'var(--muted)' if _limited else")
change(p, "'—' if _unknown else", "'—' if _limited else")
change(p, "{{ t('Reading unavailable','读数暂缺') if _unknown else t(rd.state|upper, rd.state_zh) }}",
       "{{ t('Reading unavailable','读数暂缺') if _unknown else (t('Partial reading','输入不完整') if _partial else t(rd.state|upper, rd.state_zh)) }}")
change(p, 'class="rrx rrx-{{ rd.state }}',
       'class="rrx rrx-{{ \'unavailable\' if _unknown else (\'partial\' if _partial else rd.state) }}')

# 2026-09-09: close the five reproduced raw-consumer gaps; still research-only.
p = PATHS[0]
inference_helper = (HERE / "RRU_COMPOSITION_INFERENCE_HELPER_2026_09_09.txt").read_text().rstrip("\n") + "\n\n"
change(p, "def compute(profile:", inference_helper + "def compute(profile:",
       ["_qualify_composition_inference"])
change(p, '    return {\n        "schema": "risk_radar_intl.v1",',
       '    return _qualify_composition_inference({\n        "schema": "risk_radar_intl.v1",')
change(p, '        "disclaimer": effective_disclaimer,\n    }\n\n\ndef snapshot',
       '        "disclaimer": effective_disclaimer,\n    })\n\n\ndef snapshot')
change(PATHS[1], '    legacy_dp = dp if reference_only else None',
       '    legacy_dp = ((rr.get("legacy_calibration_reference") or {}).get("drawdown_prob", dp) if reference_only else None)')
old = '''            return {"present": False, "assessment_status": "unavailable",
                    "degraded_reason": "composition_not_comparable"}'''
new = '''            market = rr.get("market") or "us"
            cats = _liquidity_catalysts(latest, market)
            mkt = _market_catalysts(latest) if market == "us" else None
            return {"present": False, "assessment_status": "unavailable",
                    "degraded_reason": "composition_not_comparable",
                    "catalysts": cats, "market": mkt,
                    "n_catalysts": len(cats), "n_fresh": sum(bool(c.get("fresh")) for c in cats),
                    "receding": False, "turn_confirmed": False,
                    "turn_confirmed_full": False if market == "us" else None}'''
change(PATHS[2], old, new)
old = '''        r = snapshot(CN_PROFILE, root)
        state = r.get("state") or "unknown"'''
new = '''        r = snapshot(CN_PROFILE, root)
        quality = r.get("composition") or {}
        if quality.get("calibration_status") == "unreviewed_corrected_construction":
            return {
                "sleeve_factor": None, "sleeve_status": "unavailable",
                "radar_state": r.get("state"), "radar_as_of": r.get("asof"),
                "can_force": bool(r.get("can_force", False)),
                "composition": quality,
                "legacy_calibration_reference": r.get("legacy_calibration_reference"),
                "label_en": "Sizing unavailable — forecast calibration under review",
                "label_zh": "仓位建议暂缺 — 预测校准待核验",
                "dominant_driver_en": r.get("dominant_label_en"),
                "dominant_driver_zh": r.get("dominant_label_zh"),
                "passport": {"basis": "descriptive", "validation": None,
                    "display_only": True, "degraded": True,
                    "note": "Descriptive context only; not a current sizing instruction."},
            }
        state = r.get("state") or "unknown"'''
change(PATHS[0], old, new, ["cn_sleeve_chip"])

# Visual review found a complete-input all-clear despite unreviewed calibration.
p = PATHS[3]
change(p, "{%- set _limited = _unknown or _partial -%}",
       "{%- set _unreviewed = _q and _q.calibration_status == 'unreviewed_corrected_construction' -%}\n{%- set _limited = _unknown or _partial or _unreviewed -%}")
change(p, "else t(rd.state|upper, rd.state_zh)) }}",
       "else (t('Descriptive reading','描述性读数') if _unreviewed else t(rd.state|upper, rd.state_zh))) }}")
change(p, "('partial' if _partial else rd.state)",
       "('partial' if _partial else ('descriptive' if _unreviewed else rd.state))")
change(PATHS[1], 'else rr.get("dominant_label_en") or "calm")),',
       'else ("Input-based reading; forecast calibration under review" if reference_only else rr.get("dominant_label_en") or "calm"))),')
change(PATHS[1], 'else rr.get("dominant_label_zh") or "平静")),',
       'else ("输入驱动的读数；预测校准待核验" if reference_only else rr.get("dominant_label_zh") or "平静"))),')
change(p, "'Pullback-risk gauge. Use high readings to trim risk, not to pick stocks.'",
       "'Descriptive input-based reading; not a calibrated forecast or sizing instruction.' if _unreviewed else 'Pullback-risk gauge. Use high readings to trim risk, not to pick stocks.'")
change(p, "'回撤风险仪表。高读数用于降风险，不用于选股。'",
       "'输入驱动的描述性读数，并非经校准的预测或仓位指令。' if _unreviewed else '回撤风险仪表。高读数用于降风险，不用于选股。'")

# Downstream RED: actual sleeve consumers must understand the new unavailable value.
# These remain source-bound, in-memory edits; no production template is overwritten.
for p in ('templates/china.html.j2', 'templates/baskets_desk.js',
          'templates/cn_reversal_sleeve.html.j2'):
    SOURCES[p] = committed(p)
    edited[p] = SOURCES[p]

p = 'templates/china.html.j2'
change(p, "{% if _sc and _sc.radar_state and _sc.radar_state != 'None' %}", '''{% if _sc and _sc.sleeve_status == 'unavailable' %}
    <div class="muted" data-sleeve-status="unavailable">
      <span>{{ t('Risk backdrop', '风险背景') }}: {{ t(_sc.label_en, _sc.label_zh) }}</span>
      {% if _sc.radar_as_of %}<small> · {{ t('as of', '截至') }} {{ _sc.radar_as_of }}</small>{% endif %}
    </div>
    {% elif _sc and _sc.radar_state and _sc.radar_state != 'None' %}''')

p = 'templates/cn_reversal_sleeve.html.j2'
change(p, '<div class="sleeve-chip" data-state="{{ d.sizing.radar_state or \'unknown\' }}">', '''{% if d.sizing.sleeve_factor is not number %}
<div class="sleeve-chip" data-state="unavailable" data-sleeve-status="unavailable">
  <span>{{ t(d.sizing.label_en or 'Sizing unavailable', d.sizing.label_zh or '仓位建议暂缺') }}</span>
  {% if d.sizing.radar_as_of %}<span class="prov">{{ d.sizing.radar_as_of }}</span>{% endif %}
</div>
{% else %}
<div class="sleeve-chip" data-state="{{ d.sizing.radar_state or 'unknown' }}">''')
change(p, '</div>\n\n<div class="strip">', '</div>\n{% endif %}\n\n<div class="strip">')

p = 'templates/baskets_desk.js'
change(p, "  if(!sc||sc.sleeve_factor==null){ host.innerHTML=''; return; }", '''  if(!sc){ host.innerHTML=''; return; }
  if(sc.sleeve_status==='unavailable'||sc.sleeve_factor==null){
    const explained=sc.sleeve_status==='unavailable';
    const en=explained?(sc.label_en||'Sizing unavailable'):'Sizing unavailable';
    const zh=explained?(sc.label_zh||'仓位建议暂缺'):'仓位建议暂缺';
    host.innerHTML=`<div class="sleeve-chip" data-sleeve-status="unavailable" style="border-left:3px solid var(--muted)">
      <span class="sl-main"><b>${L(esc(en),esc(zh))}</b></span>
      <span class="sl-tag muted">${L('No current sizing instruction.','当前不提供仓位指令。')}</span>
    </div>`;
    return;
  }''')

# Adapt the already-published proposal in PR6989 comment5593201090 to the actual
# pure prospective-entry constructor. This does not call a ledger or eligibility gate.
p = 'engine/risk_radar_intl_audit.py'
SOURCES[p] = committed(p)
edited[p] = SOURCES[p]
change(p, '''    if not snap or not snap.get("asof") or snap.get("state") is None:
        return None
    return {
''', '''    if not snap or not snap.get("asof") or snap.get("state") is None:
        return None
    if "composition" in snap:
        composition = snap["composition"]
        if (not isinstance(composition, dict) or composition.get("score_current") is not True
                or composition.get("status") not in ("COMPLETE", "PARTIAL")):
            return None
        import json
        try:
            json.dumps(composition, allow_nan=False)
        except (TypeError, ValueError):
            return None
    entry = {
''', ['_entry_from_snapshot'])
change(p, '''        "graded": None,
    }


def log_snapshot(''', '''        "graded": None,
    }
    if "composition" in snap:
        from copy import deepcopy
        entry["composition"] = deepcopy(snap["composition"])
    return entry


def log_snapshot(''', ['_entry_from_snapshot'])

# Legacy scorecard and calibration must not silently mix in modern construction rows.
p = 'engine/risk_radar_intl_audit.py'
cohort_helper = (HERE / 'RRU_LEGACY_COHORT_HELPER_2026_09_09.txt').read_text()
change(p, 'def realized_odds(', cohort_helper + 'def realized_odds(', ['_legacy_graded_cohort'])
change(p, '\n    rows = [r for r in _read(_path(market, root)) if r.get("graded")]\n',
       '\n    rows, _excluded = _legacy_graded_cohort(_read(_path(market, root)))\n', ['realized_odds'])
change(p, '        rows = [r for r in _read(_path(market, root)) if r.get("graded")]\n',
       '        rows, excluded = _legacy_graded_cohort(_read(_path(market, root)))\n', ['scorecard'])
change(p, '        rows = []\n    if not rows:\n', '        rows, excluded = [], 0\n    if not rows:\n')
change(p, 'return {"market": market, "n_graded": 0, "can_force": False,',
       'return {"market": market, "n_graded": 0, "can_force": False,\n                "evidence_construction": "legacy_implicit", "excluded_composition_rows": excluded,')
change(p, '        "n_graded": n,\n',
       '        "n_graded": n,\n        "evidence_construction": "legacy_implicit",\n        "excluded_composition_rows": excluded,\n')

p = 'engine/risk_radar_intl_tune.py'
SOURCES[p] = committed(p)
edited[p] = SOURCES[p]
change(p, '        rows = [r for r in A._read(A._path(key, root)) if r.get("graded")]\n',
       '        rows, excluded = A._legacy_graded_cohort(A._read(A._path(key, root)))\n', ['tune'])
change(p, 'return {"status": "accruing", "n_graded": len(rows), "need": MIN_GRADED}',
       'return {"status": "accruing", "n_graded": len(rows), "need": MIN_GRADED,\n                    "evidence_construction": "legacy_implicit", "excluded_composition_rows": excluded}')
change(p, 'return {"status": decision, "n_graded": len(rows),\n',
       'return {"status": decision, "n_graded": len(rows),\n                "evidence_construction": "legacy_implicit", "excluded_composition_rows": excluded,\n')

# Source-bound construction applicability: no modern construction is promoted yet.
p = 'engine/risk_radar_intl_audit.py'
force_helper = (HERE / 'RRU_FORCE_APPLICABILITY_HELPER_2026_09_09.txt').read_text().rstrip() + '\n\n\n'
change(p, 'def scorecard(market:', force_helper + 'def scorecard(market:', ['force_applicable_for_snapshot'])
p = PATHS[1]
change(p, '    composition = rr.get("composition")\n', '''    composition = rr.get("composition")
    if "composition" in rr and not isinstance(composition, dict):
        composition = {"status": "UNAVAILABLE", "score_current": False,
                       "calibration_status": "unreviewed_corrected_construction"}
''')
change(p, '    reference_only = bool(composition and composition.get("calibration_status") == "unreviewed_corrected_construction")',
       '    reference_only = "composition" in rr')
change(p, '    _authority = dict(rr.get("authority") or {', '''    _reported_can_force = _can_force
    from engine.risk_radar_intl_audit import force_applicable_for_snapshot
    _can_force = force_applicable_for_snapshot(rr, _reported_can_force)
    _authority = dict(rr.get("authority") or {''')
change(p, '    # Forward-monitor freshness remains visible in `track`,', '''    if "composition" in rr:
        _authority = {"tier": "descriptive", "can_force": False,
                      "reason": "construction_not_promoted",
                      "note_en": "Descriptive context; no forecast, sizing or binding permission.",
                      "note_zh": "描述性背景；不提供预测、仓位指令或约束权限。"}
    # Forward-monitor freshness remains visible in `track`,''')
change(p, '        "can_force": _can_force,\n        "binding":',
       '        "reported_can_force": _reported_can_force,\n        "can_force": _can_force,\n        "binding":')
change(p, '    if rr.get("can_force") and state in ("caution", "elevated", "risk-off"):',
       '    if out.get("can_force") and state in ("caution", "elevated", "risk-off"):', ['_radar_override_intl'])

# Preserve the original runner/source owners; modify only their scalar attachment.
for p, payload, score in (
        ('engine/intl_run.py', 'rec["risk_radar"]', 'sc'),
        ('scripts/build_china.py', 'latest["risk_radar"]', '_sc'),
        ('scripts/build_hk.py', 'latest["risk_radar"]', '_sc'),
        ('scripts/build_canada.py', 'latest["risk_radar"]', '_sc')):
    SOURCES[p] = committed(p)
    edited[p] = SOURCES[p]
    old = f'{payload}["can_force"] = bool({payload}["forward_log"].get("can_force"))'
    new = f'{payload}["can_force"] = _rra.force_applicable_for_snapshot({payload}, bool({payload}["forward_log"].get("can_force")))'
    change(p, old, new)
    old = f'{payload}["can_force"] = bool({score}.get("can_force"))'
    new = f'{payload}["can_force"] = _rra.force_applicable_for_snapshot({payload}, bool({score}.get("can_force")))'
    change(p, old, new)
p = 'scripts/build_china_risk_state.py'
SOURCES[p] = committed(p)
edited[p] = SOURCES[p]
change(p, 'from engine import live_overlay, live_quotes, market_state, risk_radar_intl',
       'from engine import live_overlay, live_quotes, market_state, risk_radar_intl, risk_radar_intl_audit')
for payload in ('_latest_nightly["risk_radar"]', 'latest_live["risk_radar"]'):
    change(p, f'{payload}["can_force"] = can_force',
           f'{payload}["can_force"] = risk_radar_intl_audit.force_applicable_for_snapshot({payload}, can_force)')

# The prior-method track record must not claim the corrected reading moves a verdict.
p = PATHS[3]
change(p, '    {%- if _fl_n > 0 %}', '''    {%- if rd.authority and rd.authority.reason == 'construction_not_promoted' %}
    <span data-record-applicability="earlier-construction">{{ t('Earlier construction record; not current validation.','旧构造往绩；不构成当前读数的验证。') }}{% if _fl_n > 0 %} {{ _fl_n }} {{ t('graded','已评分') }}.{% endif %}</span>
    {%- elif _fl_n > 0 %}''')

# Keep added reported-grant provenance off unchanged legacy projections.
change(PATHS[1], '        "reported_can_force": _reported_can_force,',
       '        **({"reported_can_force": _reported_can_force} if "composition" in rr else {}),')

# Template-only qualification of a supplied modern RADAR. Adapter/VM repair is held.
p = 'templates/international_macro.html.j2'
SOURCES[p] = committed(p)
edited[p] = SOURCES[p]
change(p, '{% import "_risk_radar_card.html.j2" as rrc %}', '''{% import "_risk_radar_card.html.j2" as rrc %}
{% set _qualified_radar = RADAR and RADAR.authority and RADAR.authority.reason == 'construction_not_promoted' %}''')
change(p, '''{{ t("Odds measured on this market's own history — windows, not certainties, re-drawn nightly.",'概率基于本市场自身历史测算 — 是概率窗口而非定论，每晚重算。') }}''',
       '''{{ t('Read the inputs; a calibrated forecast is not available.','观察输入；当前不提供经校准的预测。') if _qualified_radar else t("Odds measured on this market's own history — windows, not certainties, re-drawn nightly.",'概率基于本市场自身历史测算 — 是概率窗口而非定论，每晚重算。') }}''')
change(p, "{{ t('Calibrated risk monitor','校准风险监测') }}",
       "{{ t('Risk evidence','风险证据') if _qualified_radar else t('Calibrated risk monitor','校准风险监测') }}")
change(p, "{{ t('Forward pullback odds stay separate from the descriptive macro score.','前瞻回撤概率与描述性宏观分数严格分开。') }}",
       "{{ t('Check the observations and what remains unknown.','查看已观测的信息与仍未知的部分。') if _qualified_radar else t('Forward pullback odds stay separate from the descriptive macro score.','前瞻回撤概率与描述性宏观分数严格分开。') }}")
change(p, "{% call dialog('dlg-risk','Calibrated risk receipt','校准风险凭证') %}",
       "{% call dialog('dlg-risk','Risk evidence' if _qualified_radar else 'Calibrated risk receipt','风险证据' if _qualified_radar else '校准风险凭证') %}")

# Detail presentation consumes the same qualified RADAR rather than old VM odds.
change(p, '''<div class="imd-cols">
  <div class="imd-receipt"><h3>{{ t('21-session pullback probability','21交易日回撤概率') }}''', '''<div class="imd-cols">
  {% if _qualified_radar %}
  <div class="imd-receipt"><h3>{{ t('Forecast not available','预测暂不可用') }}</h3><p>{{ t('The current inputs do not provide a calibrated pullback forecast.','当前输入不提供经校准的回撤预测。') }}</p></div>
  <div class="imd-receipt"><h3>{{ t('Input reading','输入读数') }}</h3><p><b>{{ t('Reading unavailable','读数暂缺') if not RADAR.composition.score_current else (t('Partial reading','输入不完整') if RADAR.composition.status == 'PARTIAL' else t('Descriptive reading','描述性读数')) }}</b><br>{{ t(RADAR.label_en,RADAR.label_zh) }}</p></div>
  {% else %}
  <div class="imd-receipt"><h3>{{ t('21-session pullback probability','21交易日回撤概率') }}''')
change(p, '''{{ t(D.risk.dominant_en or 'No dominant scare',D.risk.dominant_zh or '无主导风险') }}</p></div>
</div>
<h3 style="margin-top:18px">{{ t('Active scare families','活跃风险类别') }}''', '''{{ t(D.risk.dominant_en or 'No dominant scare',D.risk.dominant_zh or '无主导风险') }}</p></div>
  {% endif %}
</div>
<h3 style="margin-top:18px">{{ t('Risk drivers','风险驱动') if _qualified_radar else t('Active scare families','活跃风险类别') }}''')
change(p, "{{ t('No calibrated scare data','无校准风险数据') }}",
       "{{ t('Risk observations unavailable','风险观测暂缺') if _qualified_radar else t('No calibrated scare data','无校准风险数据') }}")

# An unavailable modern assessment is not a measured zero active-family count.
change(p, '''        {% if RADAR %}
        {% set _live = (D.risk.scares or []) | rejectattr('band', 'equalto', 'calm') | list %}''', '''        {% if _qualified_radar %}
        <div class="imd-face-kpi"><strong>{{ RADAR.composition.members_available|default('—') }} / {{ RADAR.composition.members_expected|default('—') }}</strong><span>{{ t('Input coverage','输入覆盖') }}</span></div>
        {% elif RADAR %}
        {% set _live = (D.risk.scares or []) | rejectattr('band', 'equalto', 'calm') | list %}''')

# Same-carrier continuation: preserve qualified readings through the real page adapter.
p = 'scripts/build_international_macro.py'
SOURCES[p] = committed(p)
edited[p] = SOURCES[p]
change(p, '''    radar = record.get("risk_radar") or {}
    if not radar.get("state"):
        return None
    if (radar.get("drawdown_prob") or {}).get("h21") is None:
        # No calibrated odds -> the card would carry less than the tile it replaces.
        return None
''', '''    radar = record.get("risk_radar") or {}
    if not isinstance(radar, dict):
        return None
    if "composition" not in radar:
        if not radar.get("state"):
            return None
        if (radar.get("drawdown_prob") or {}).get("h21") is None:
            return None
    # Explicit input quality is a displayable assessment, not a promise of odds.
''', ['_radar_display'])

# Preserve measured macro scoring and construction identity in the existing view.
p = 'engine/international_macro_dashboard.py'
SOURCES[p] = committed(p)
edited[p] = SOURCES[p]
change(p, '''        radar.get("state"),
    )
    return round(max(0.0, min(100.0, sum(parts.values())))), parts''',
       '''        radar.get("state") if "composition" not in radar else None,
    )
    return round(max(0.0, min(100.0, sum(parts.values())))), parts''', ['decision_score'])
change(p, '''    drawdown_prob = radar.get("drawdown_prob") or {}

    metrics = []''', '''    modern = "composition" in radar
    drawdown_prob = {} if modern else (radar.get("drawdown_prob") or {})
    from copy import deepcopy
    composition_fields = {"composition": deepcopy(radar["composition"])} if modern else {}

    metrics = []''', ['build_country_view'])
change(p, '''            "calibrated": _finite(drawdown_prob.get("h21")) is not None,
''', '''            "calibrated": _finite(drawdown_prob.get("h21")) is not None,
            **composition_fields,
''')
change(p, '''"method_en": "50 + growth impulse − inflation pressure − recession stress + liquidity + current calibrated-risk state. Descriptive, not a forecast.",''',
       '''"method_en": ("Growth, inflation, recession stress and liquidity. Risk observations remain separate; no calibrated forecast is available." if modern else "50 + growth impulse − inflation pressure − recession stress + liquidity + current calibrated-risk state. Descriptive, not a forecast."),''')
change(p, '''"method_zh": "50 + 增长脉冲 − 通胀压力 − 衰退压力 + 流动性 + 当前校准风险状态。仅作描述，不是预测。",''',
       '''"method_zh": ("综合增长、通胀、衰退压力与流动性；风险观测单独呈现，当前不提供经校准的预测。" if modern else "50 + 增长脉冲 − 通胀压力 − 衰退压力 + 流动性 + 当前校准风险状态。仅作描述，不是预测。"),''')

# Full-builder negative controls: producer prose cannot restore a green/calm badge.
p = PATHS[3]
change(p, '''{%- set _unknown = _q and not _q.score_current -%}
{%- set _partial = _q and _q.status == 'PARTIAL' -%}
{%- set _unreviewed = _q and _q.calibration_status == 'unreviewed_corrected_construction' -%}''',
       '''{%- set _unreviewed = (rd.authority and rd.authority.reason == 'construction_not_promoted') or (_q and _q.calibration_status == 'unreviewed_corrected_construction') -%}
{%- set _unknown = _unreviewed and (_q is not mapping or _q.score_current is not sameas true or _q.status not in ['COMPLETE', 'PARTIAL']) -%}
{%- set _partial = not _unknown and _q and _q.status == 'PARTIAL' -%}''')
change(p, '{{ _q.members_available }} / {{ _q.members_expected }}.',
       "{{ _q.members_available|default('—') }} / {{ _q.members_expected|default('—') }}.")
change(p, '{{ _q.groups_available }} / {{ _q.groups_expected }}.',
       "{{ _q.groups_available|default('—') }} / {{ _q.groups_expected|default('—') }}.")
