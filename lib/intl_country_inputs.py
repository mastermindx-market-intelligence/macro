"""Read-only country research inputs for the existing International publisher.

Network acquisition belongs to IntlMacroAdapter. This module combines the
reviewed initial source snapshot with its last successful refresh and retains
every source vintage. It does not write data, issue signals, or create a ledger.
"""
from __future__ import annotations

import json
from pathlib import Path
from collectors.intl_country_sources import SCHEMA, merge_country_inputs

MAX_INPUT_BYTES = 1_500_000


def _read(path):
    try:
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError("country_input_size_limit")
        result = json.loads(path.read_text(encoding="utf-8"))
        return result if type(result) is dict else {}
    except (OSError, ValueError):
        return {}


def load_country_inputs(data_root, source_root):
    source_root, data_root = Path(source_root), Path(data_root)
    baseline = _read(source_root / "config/intl_country_baseline.json")
    refreshed = _read(data_root / "intl_macro/country_inputs.json")
    inputs = merge_country_inputs(baseline, refreshed, preserve_custody=True)
    commentary = _read(source_root / "config/intl_country_commentary.json")
    inputs["commentary"] = (commentary.get("countries") or {}) if commentary.get("schema") == "intl_country_commentary.v1" else {}
    return inputs
