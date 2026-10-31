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
PINS = {'data/experiments/local_projection_alfred_cpi_payroll_v2_results.json': ('result',
                                                                          '1c463e2ec8e8ab98399b40c176899d1fcf5b94d8969280212037adb321e90604'),
 'data/experiments/local_projection_alfred_cpi_payroll_v2_registration.json': ('registration',
                                                                               'a869ad712edc598b4b1faaadc9b08573beda62e4246015a1c3a6e83fd0776545'),
 'data/experiments/local_projection_alfred_cpi_payroll_v2_panel.csv': ('input',
                                                                       '4456ebeff9ebd0e218d5d3b58b643c9a4fdc2e96b8cecabca55736287e7d14a6'),
 'data/experiments/local_projection_alfred_cpi_payroll_v2_custody.json': ('custody',
                                                                          '54c8fe8220ea323829817b23cac983469c0de459ee0d2c8610333f1aebaa52d0'),
 'research/local_projections/ALFRED_CPI_PAYROLL_V2_STUDY_SPEC.json': ('preregistration',
                                                                      'd70bbc156dc892dfbcf538dc712a5772ec2fb43cb5a3af3c41b7d0a5af7c4871'),
 'research/local_projections/ALFRED_CPI_PAYROLL_V1_STUDY_SPEC.json': ('original_preregistration',
                                                                      '9b70d444ba75d01db7460c86f970d1626a2df553c07dea17a8aa5dac4072edb5'),
 'research/local_projections/ALFRED_CPI_PAYROLL_V1_SOURCE_REFUSAL.json': ('original_source_refusal',
                                                                          '3e2d9c93d46b4683b5251c4b80744e38ceb9c401abecf1cd7126af10957c2b4e'),
 'research/local_projections/ALFRED_CPI_PAYROLL_V2_APPENDIX.md': ('report',
                                                                  '3d4ca68f63cbdc467866fcc121f0b2d4f7281236151feae54f5342c6302afd91'),
 'engine/local_projections.py': ('estimator',
                                 'fe6112dff9ba2caf0ebb89634421ac1b7ecf6418ed96ec9558e81fa8e3d07a9e'),
 'scripts/run_local_projections.py': ('harness',
                                      '22a1cc05996efdc430ebfd0f7787d35ff2ac0dcbaed3263af385dd2ceb9e9d45'),
 'scripts/local_projection_alfred_panel.py': ('panel_assembler',
                                              '4756b2857905f28960f8b07d771b97e1a59dd86e7b8b74b08bfe05defe87f4b6'),
 'research/local_projections/reproduce_alfred_cpi_payroll_v2.py': ('run_driver',
                                                                   '020a134a41e22c86f91e8eb34c96db9684e9a46e224da8b432b40b1c6d6d606a')}


def adapt_local_projections(root: Path) -> dict:
    """Read only the exact registered native result; refuse incomplete custody."""
    root = Path(root)
    if not PINS:
        raise CardContractError("LP native result has not been frozen and adopted")
    receipts = {}
    code = []
    for path, (role, digest) in PINS.items():
        dated = role in {"result", "registration", "preregistration", "report"}
        reason = None if dated else _localized(
            "This immutable receipt asserts no single publication date; use its per-row availability bounds, frozen specification and native run clocks.",
            "此不可变凭据不主张单一发布日期；请使用各行可用性上界、冻结计划与原生运行时间。")
        receipt = _source_artifact(root, role=role, path=path, expected_sha256=digest,
                                   as_of="2026-10-20" if dated else None, as_of_reason=reason)
        if role in {"estimator", "harness", "panel_assembler", "run_driver"}:
            code.append(receipt)
        else:
            receipts[path] = receipt
    bundle = _read_json(root / RESULT)
    spec = _read_json(root / SPEC)
    registration = _read_json(root / REGISTRATION)
    _verify_owner_bundle(bundle, spec, registration)
    configs = [row["config"] for row in registration["new_rows"]]
    try:
        with (root / "data/trial_ledger.jsonl").open("rb") as stream:
            ledger_raw = stream.read(_MAX_LEDGER_BYTES + 1)
        verify_registration(registration, ledger_raw, family=FAMILY, configs=configs)
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
        _metric("information_cutoff_utc", "Exact information cutoff (UTC)", "精确信息截止时间（UTC）",
                spec["cutoff"], "utc_instant", SPEC + ":cutoff"),
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
    require(registration.get("driver_sha256") == PINS["research/local_projections/reproduce_alfred_cpi_payroll_v2.py"][1],
            "LP original execution driver binding mismatch")
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



import copy
import json

from engine.trial_ledger import _hash, _legacy_record, _strict_row


_MAX_LEDGER_BYTES = 64 * 1024 * 1024  # exact read bound on canonical ledger bytes
_EXPECTED_N = 3  # a research card registers exactly three trials


def _canon_text(value):
    """Strict canonical JSON text for value comparison; never coerces."""
    try:
        return json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return None


def _unchanged(live, expected):
    """True when ``live`` is the identical JSON value as the receipt's row.

    Canonical-form equality keeps the check tamper-evident without depending
    on byte-level formatting: key order and whitespace cannot fake a match,
    while any changed scalar -- ts, source, note, info_cutoff -- or a changed
    numeric/bool type compares unequal.
    """
    live_text, expected_text = _canon_text(live), _canon_text(expected)
    return live_text is not None and expected_text is not None and live_text == expected_text


def _reject_constant(token):
    raise ValueError(f"non-finite JSON constant {token!r} refused in ledger")


def _reject_duplicate_keys(pairs):
    seen = set()
    for key, _value in pairs:
        if key in seen:
            raise ValueError(f"duplicate JSON key {key!r} refused in ledger")
        seen.add(key)
    return dict(pairs)


def _parse_record(line, lineno):
    try:
        record = json.loads(line, object_pairs_hook=_reject_duplicate_keys,
                            parse_constant=_reject_constant)
    except ValueError as exc:
        raise ValueError(f"malformed ledger JSON at line {lineno}: {exc}") from exc
    if not isinstance(record, dict):
        raise ValueError(f"ledger record at line {lineno} is not a JSON object")
    return record


def _split_records(ledger_raw):
    """Parse bounded ledger bytes into ``(line number, record)`` pairs."""
    if len(ledger_raw) > _MAX_LEDGER_BYTES:
        raise ValueError("ledger exceeds the 64 MiB exact read bound")
    try:
        text = ledger_raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("ledger bytes are not valid UTF-8") from exc
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # one final newline is the normal form, not a record
    records = []
    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            raise ValueError(f"blank ledger row at line {lineno}")
        records.append((lineno, _parse_record(line, lineno)))
    return records


def verify_registration(receipt: dict, ledger_raw: bytes, *, family: str,
                        configs: list) -> list:
    """Verify a pinned registration receipt against canonical ledger bytes.

    Returns a defensive copy of the three receipt rows, in supplied ``configs``
    order. Raises ``ValueError`` on every failure; inputs are never mutated.
    """
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be a dict")
    if type(family) is not str or not family:
        raise ValueError("family must be a non-empty string")
    if not isinstance(ledger_raw, bytes):
        raise ValueError("ledger_raw must be exact bytes")
    if not isinstance(configs, list) or len(configs) != _EXPECTED_N:
        raise ValueError("configs must be a list of exactly three configs")

    digests = []
    for index, config in enumerate(configs):
        if not isinstance(config, dict):
            raise ValueError(f"configs[{index}] must be a dict")
        if "cutoff" not in config:
            raise ValueError(f"configs[{index}] must carry the source 'cutoff' field")
        try:
            digests.append(_hash(family, config))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"configs[{index}] is not canonically hashable: {exc}") from exc
    if len(set(digests)) != _EXPECTED_N:
        raise ValueError("configs must be three distinct trial configurations")

    if receipt.get("family") != family:
        raise ValueError("receipt family does not equal the requested family")
    effective_n = receipt.get("effective_n")
    if type(effective_n) is not int or effective_n != _EXPECTED_N:
        raise ValueError("receipt effective_n must be the literal integer 3")
    new_rows = receipt.get("new_rows")
    if not isinstance(new_rows, list) or len(new_rows) != _EXPECTED_N:
        raise ValueError("receipt new_rows must hold exactly three rows")

    expected_rows = []
    for index, row in enumerate(new_rows):
        where = f"receipt new_rows[{index}]"
        if not isinstance(row, dict):
            raise ValueError(f"{where} must be a dict")
        if row.get("family") != family:
            raise ValueError(f"{where} does not name family {family!r}")
        if row.get("kind") == "declared_budget":
            raise ValueError(f"{where} is a declared budget row; "
                             "registration verifies generated trials only")
        if _legacy_record(row):
            raise ValueError(f"{where} is a legacy record, not a generated trial")
        try:
            (_row_family, row_digest), _canon_config = _strict_row(row)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{where} fails native strict row law: {exc}") from exc
        if row_digest != digests[index]:
            raise ValueError(f"{where} does not correspond to configs[{index}] in order")
        if row.get("info_cutoff") != configs[index]["cutoff"]:
            raise ValueError(f"{where} info_cutoff does not equal configs[{index}]['cutoff']")
        expected_rows.append(row)
    if len({row["config_hash"] for row in expected_rows}) != _EXPECTED_N:
        raise ValueError("receipt new_rows must be three distinct rows")

    live = []
    for lineno, record in _split_records(ledger_raw):
        if record.get("family") != family:
            continue  # unrelated appends: other families and family-less legacy records
        if record.get("kind") == "declared_budget":
            raise ValueError(f"declared budget row for family {family!r} at ledger line {lineno}")
        if _legacy_record(record):
            raise ValueError(f"legacy annotation for family {family!r} at ledger line {lineno}")
        try:
            _strict_row(record)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"corrupt row for family {family!r} at ledger line {lineno}: {exc}") from exc
        live.append((lineno, record))

    if len(live) < _EXPECTED_N:
        raise ValueError(f"ledger holds only {len(live)} rows for family {family!r}; "
                         f"registration requires exactly {_EXPECTED_N}")
    by_digest = {row["config_hash"]: row for row in expected_rows}
    seen = set()
    for lineno, row in live:
        digest = row["config_hash"]
        if digest not in by_digest:
            raise ValueError(f"extra same-family row at ledger line {lineno} is not in the receipt")
        if digest in seen:
            raise ValueError(f"duplicate same-family config hash at ledger line {lineno}")
        seen.add(digest)
        if not _unchanged(row, by_digest[digest]):
            raise ValueError(
                f"ledger row at line {lineno} differs from its immutable receipt row "
                "(ts/source/note/info_cutoff and every other field must match, "
                "not just the config hash)")
    missing = len(by_digest) - len(seen)
    if missing:
        raise ValueError(f"ledger is missing {missing} registered row(s) for family "
                         f"{family!r}; registration requires exactly {_EXPECTED_N} unchanged rows")

    return [copy.deepcopy(row) for row in expected_rows]
