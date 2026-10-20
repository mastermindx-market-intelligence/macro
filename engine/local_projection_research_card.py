"""Closed, read-only display of the registered ALFRED LP diagnostic study.

No estimation, ledger writes, source refresh, discovery or promotion occurs here.
The frozen panel and all three prespecified results are receipts, not a forecast.
"""
from __future__ import annotations

import json
from pathlib import Path

from engine.research_implication_card import (
    AUTHORITY_KEYS, CARD_SCHEMA, CardContractError, _localized, _metric,
    _read_json, _source_artifact, compute_card_id, validate_card,
)

FAMILY = "f10_lp_alfred_cpi_payroll_descriptive"
VERSION = "local_projections_alfred/v1"
SPEC = "research/local_projections/ALFRED_CPI_PAYROLL_V2_STUDY_SPEC.json"
PREFIX = "data/experiments/local_projection_alfred_cpi_payroll_v2"
RESULT = PREFIX + "_results.json"
REGISTRATION = PREFIX + "_registration.json"
# Filled from the actual retained native run, never generated or estimated here.
PINS = {}


def adapt_local_projections(root: Path) -> dict:
    """Read only the exact registered native result; refuse incomplete custody."""
    root = Path(root)
    if not PINS:
        raise CardContractError("LP native result has not been frozen and adopted")
    receipts = {}
    code = []
    for path, (role, digest) in PINS.items():
        receipt = _source_artifact(root, role=role, path=path,
                                   expected_sha256=digest, as_of="2026-10-17")
        if role in {"estimator", "harness", "panel_assembler"}:
            code.append(receipt)
        else:
            receipts[path] = receipt
    bundle = _read_json(root / RESULT)
    spec = _read_json(root / SPEC)
    registration = _read_json(root / REGISTRATION)
    _verify_owner_bundle(bundle, spec, registration)
    configs = [row["config"] for row in registration["new_rows"]]
    try:
        verify_registration(registration, (root / "data/trial_ledger.jsonl").read_bytes(),
                            family=FAMILY, configs=configs)
    except (ValueError, OSError) as exc:
        raise CardContractError(f"LP canonical registration is not intact: {exc}") from exc
    primary = bundle["runs"][0]["envelope"]["result"]
    outputs, uncertainty, diagnostics, robustness, nulls = [], [], [], [], []
    points = []
    unit = "log_payroll_change_per_cpi_percentage_point"
    for row in primary["irf"]:
        h = row["h"]
        source = f"runs.primary.envelope.result.irf.h{h}"
        if row.get("abstained"):
            nulls.append({"code": f"horizon_{h}", "reason": row["reason"],
                          "detail": _localized(f"Native horizon {h} abstained: {row['reason']}.",
                                               f"原生第{h}期拒绝估计：{row['reason']}。")})
            continue
        outputs.append(_metric(f"beta_h{h}", f"Payroll log-change coefficient, horizon {h}",
                               f"工资单对数变化系数，第{h}期", row["beta"], unit, source + ".beta"))
        for field, en, zh, value_unit in (
            ("ci_low", "95% HAC interval lower bound", "95% HAC 区间下限", unit),
            ("ci_high", "95% HAC interval upper bound", "95% HAC 区间上限", unit),
            ("p", "Raw two-sided normal p value", "原始双侧正态 p 值", "probability"),
            ("hac_lags", "Actual HAC lag count", "实际 HAC 滞后数", "lags"),
            ("hac_lags_requested", "Requested HAC lag count", "请求的 HAC 滞后数", "lags"),
            ("n", "Usable regression rows", "可用回归行数", "observations"),
        ):
            uncertainty.append(_metric(f"{field}_h{h}", f"{en}, horizon {h}", f"{zh}，第{h}期",
                                       row[field], value_unit, source + "." + field))
        q = primary["fdr"].get(str(h))
        if q is not None:
            uncertainty.append(_metric(f"by_q_h{h}", f"BY horizon-panel q value, horizon {h}",
                                       f"BY 期限组 q 值，第{h}期", q["q"], "q_probability", source + ".BY_q"))
        points.append({"horizon": h, "value": row["beta"], "n": row["n"]})
    for run in bundle["runs"][1:]:
        lag = run["envelope"]["registration"]["config"]["lags"]
        row = run["envelope"]["result"]["irf"][3]
        if row.get("abstained"):
            nulls.append({"code": f"robustness_lags_{lag}_h3", "reason": row["reason"],
                          "detail": _localized(f"Prespecified lag-{lag} horizon 3 abstained: {row['reason']}.",
                                               f"预定滞后{lag}阶第3期拒绝估计：{row['reason']}。")})
        else:
            robustness.append(_metric(f"robustness_lags_{lag}_h3", f"Prespecified lag-{lag} coefficient, horizon 3",
                                      f"预定滞后{lag}阶系数，第3期", row["beta"], unit,
                                      f"runs.{run['role']}.envelope.result.irf.h3.beta"))
    diagnostics.extend([
        _metric("registered_search_n", "All prespecified configurations registered before estimation",
                "估计前登记的全部预定配置数", 3, "configurations", REGISTRATION + ":effective_n"),
        _metric("requested_months", "Originally requested months", "原始请求月份", 345, "months", SPEC + ":coverage"),
        _metric("included_months", "Contiguous available months", "连续可用月份", 332, "months", SPEC + ":coverage"),
        _metric("excluded_months", "Recent months excluded by source availability", "因来源可用性排除的近期月份",
                13, "months", SPEC + ":coverage"),
        _metric("primary_any_by_rejection", "Primary horizon-panel BY rejection (no promotion authority)",
                "主配置期限组 BY 拒绝结果（无晋级权限）", primary["null"]["any_horizon_rejects"],
                "boolean", "runs.primary.envelope.result.null.any_horizon_rejects"),
    ])
    nulls.append({"code": "effective_n", "reason": "INDEPENDENT_EPISODES_NOT_IDENTIFIED",
                  "detail": _localized("332 monthly rows are not 332 independent episodes. The three-configuration search count is reported separately.",
                                       "332个月度行不等于332个独立事件期。三组配置的搜索计数单独报告。")})
    path = None
    if len(points) == 4:
        path = {"owner_supplied": True, "x_unit": "monthly_observation_horizon",
                "y_unit": unit, "points": points, "source": "runs.primary.envelope.result.irf",
                "evidence_status": "RESEARCH_DIAGNOSTIC", "selected_horizon": 3,
                "sample_basis": _localized("One row per month, January 1998–August 2025; per-horizon usable regression counts are shown.",
                                           "每月一行，1998年1月至2025年8月；显示各期限可用回归行数。"),
                "comparison_note": _localized("Fixed lag-4 primary specification; lag-2 and lag-8 results are retained without winner selection. The target is log payroll at t+h minus t−1.",
                                              "固定滞后4阶主配置；保留滞后2阶和8阶结果，不择优。目标为t+h与t−1之间的工资单对数变化。"),
                "accessible_name": _localized("Descriptive CPI–payroll local-projection coefficient path",
                                              "描述性 CPI 与工资单局部投影系数路径")}
    limits = [
        _localized("Association does not identify a causal CPI effect: common macro drivers and endogenous releases can bias either sign.",
                   "相关性不能识别 CPI 因果效应：共同宏观因素和内生发布可令任一方向偏移。"),
        _localized("Nonstationary payroll levels and regime changes may produce unstable or spurious coefficients; the three lag variants are sensitivity diagnostics, not validation.",
                   "非平稳工资单水平和制度变化可能产生不稳定或伪系数；三种滞后配置属于敏感性诊断，并非验证。"),
        _localized("Date-only ALFRED vintage anchors use a conservative two-day UTC availability bound. Earliest retained vintage is not certified as the original first release; no intraday or forecast claim follows.",
                   "仅含日期的 ALFRED 版本锚点采用保守的两日 UTC 可用性上界。最早保留版本未经认证为原始首发；不能据此声称日内或预测能力。"),
        _localized("The original 345-month request failed source qualification. The availability-only amendment keeps 332 contiguous months and excludes September 2025–September 2026; current-regime validity is unknown.",
                   "原始345个月请求未通过来源资格检查。仅根据可用性修订后保留332个连续月份，排除2025年9月至2026年9月；当前制度有效性未知。"),
        _localized("BY adjusts the dependent horizons within each run. The registered search count of three is disclosure, not a specification-search p-value adjustment; no best specification was selected.",
                   "BY 校正每次运行内相依期限。已登记的三组搜索计数属于披露，并非配置搜索 p 值校正；未选择最佳配置。"),
        _localized("Research-only diagnostic; no forecast, ranking, gating, sizing or trading authority. No scientific-utility acceptance is implied by a fitted coefficient or rejection.",
                   "仅限研究诊断；无预测、排名、门控、仓位或交易权限。拟合系数或拒绝结果不代表科学效用获认可。"),
    ]
    card = {"schema": CARD_SCHEMA,
            "card_id": compute_card_id(adapter_version=VERSION, method_family="local_projections",
                                       study_run_id=spec["id"], result_artifact_path=RESULT,
                                       verified_result_artifact_sha256=receipts[RESULT]["sha256"],
                                       selected_result_id="primary/lags4/h0_3"),
            "adapter_version": VERSION, "method_family": "local_projections", "study_run_id": spec["id"],
            "selected_result_id": "primary/lags4/h0_3", "question": _localized(spec["question"],
                "按每次 CPI 版本锚点当时可知的数据，CPI 月度变化一个百分点与工资单对数变化有何描述性关联？"),
            "estimand": _localized("OLS coefficient on one percentage point of monthly CPI change for log(PAYEMS[t+h]) − log(PAYEMS[t−1]), controlling for four lagged y and shock values; h=0…3.",
                                    "在控制工资单对数与冲击各四阶滞后后，CPI 月度变化一个百分点对应的 log(PAYEMS[t+h])−log(PAYEMS[t−1]) OLS 系数；h=0至3。"),
            "method_revision": "sha256:" + bundle["estimator_sha256"], "code_identity": code,
            "population": {"series": ["CPIAUCSL", "PAYEMS"], "start": "1998-01", "end": "2025-08",
                           "observation_unit": "monthly source period; conservative CPI-vintage availability anchor"},
            "sample_n": 332, "effective_n": None, "cutoff": "2026-10-17",
            "outputs": outputs, "uncertainty": uncertainty, "diagnostics": diagnostics,
            "placebos_or_counterexamples": robustness, "ordered_effect_path": path,
            "evidence_tier": "DIAGNOSTIC", "quality": "ARTIFACT_INCOMPLETE", "limitations": limits,
            "exclusions": [{"code": "recent_unavailable_months", "count": 13, "detail": limits[3], "source": SPEC}],
            "missingness": [{"code": "requested_recent_source_window", "reason": "ASOF_SOURCE_COMPONENT_UNAVAILABLE",
                             "detail": limits[3], "source": SPEC}],
            "null_reasons": nulls, "source_artifacts": list(receipts.values()),
            "authority": {key: False for key in AUTHORITY_KEYS}}
    return validate_card(card)


def _verify_owner_bundle(bundle: dict, spec: dict, registration: dict) -> None:
    """Validate study intent and full prespecified family before projection."""
    def require(condition, message):
        if not condition:
            raise CardContractError(message)
    require(bundle.get("schema") == "f10.lp.native_study_results/v1", "unsupported LP result schema")
    require(bundle.get("authority") == spec.get("authority") and
            bundle["authority"].get("research_only") is True and
            all(value is False for key, value in bundle["authority"].items() if key != "research_only"),
            "LP result must retain research-only zero authority")
    require(bundle.get("scientific_acceptance") is False, "LP scientific acceptance is not established")
    require(bundle.get("study_spec_sha256") == PINS[SPEC][1] and
            bundle.get("input_sha256") == PINS[PREFIX + "_panel.csv"][1] and
            bundle.get("registration_receipt_sha256") == PINS[REGISTRATION][1], "LP custody binding mismatch")
    require(bundle.get("estimator_sha256") == PINS["engine/local_projections.py"][1] and
            bundle.get("harness_sha256") == PINS["scripts/run_local_projections.py"][1], "LP released code binding mismatch")
    require(bundle.get("coverage") == spec["coverage"], "LP source exclusions changed")
    runs = bundle.get("runs", [])
    require([run.get("role") for run in runs] == ["primary", "robustness_lags_2", "robustness_lags_8"],
            "LP must retain all three prespecified configurations in fixed order")
    configs = [spec["primary"], *spec["robustness_family"]]
    rows = registration.get("new_rows", [])
    require(len(rows) == 3, "LP requires all three original generated registrations")
    for run, settings, original in zip(runs, configs, rows):
        env = run["envelope"]
        reg = env["registration"]
        require(env.get("schema") == "mastermind.local_projection_run/v1", "LP native harness envelope required")
        require(reg.get("family") == FAMILY and reg.get("effective_n") == 3 and
                reg.get("new_trial_logged") is False, "LP estimation must follow the complete preregistration")
        config = reg["config"]
        require(config == original["config"] and all(config[k] == v for k, v in settings.items()), "LP registered configuration changed")
        require(config["input_sha256"] == bundle["input_sha256"] and config["estimator_sha256"] == bundle["estimator_sha256"] and
                config["n_rows"] == 332 and config["cutoff"] == spec["cutoff"], "LP input/estimator/cutoff binding mismatch")
        result = env["result"]
        require([r.get("h") for r in result["irf"]] == [0, 1, 2, 3], "LP horizon panel must preserve typed abstentions")
        mt = result["multiple_testing"]
        require(mt.get("family") == FAMILY and mt.get("effective_n") == 3 and mt.get("method") == "benjamini_yekutieli",
                "LP multiplicity disclosure changed")
        require(env.get("authority") == {"research_only": True, "causal": False, "signal": False,
                                       "sizing": False, "execution": False, "publication": False}, "LP native authority changed")
