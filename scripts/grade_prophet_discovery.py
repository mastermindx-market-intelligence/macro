#!/usr/bin/env python3
"""Nightly governed outcome evaluator for HK/CA Prophet discovery observations."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import prophet_discovery_grade  # noqa: E402


def main() -> int:
    print(json.dumps(prophet_discovery_grade.grade_all(), sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
