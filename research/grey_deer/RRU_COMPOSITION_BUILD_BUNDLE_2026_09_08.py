"""Build an explicitly uninstalled, source-bound patch bundle for the research rig."""
from __future__ import annotations
import ast
import difflib
import hashlib
import json
from pathlib import Path
from RRU_COMPOSITION_ACCEPTANCE_2026_09_08 import SOURCES, PATHS

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
