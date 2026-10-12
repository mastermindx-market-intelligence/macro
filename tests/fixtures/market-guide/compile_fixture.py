"""Synthetic fixture composition for Python/Node tests, never production qualification."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib.market_guide import compile_guide


def manifest() -> dict:
    raw = json.loads((Path(__file__).parent / 'synthetic-source.json').read_text())
    presentation = json.loads((ROOT / 'research/reference_rethink_20260921/guide-presentation.json').read_text())
    return compile_guide(raw, presentation, validate_registry=lambda source: source['entries'],
                         validate_coverage=lambda source, entries: source.get('coverage_exceptions', []))


if __name__ == '__main__':
    print(json.dumps(manifest(), ensure_ascii=False))
