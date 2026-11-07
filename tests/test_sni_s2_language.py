"""S2 language law (A24 + the CI-enforced 'validated' ban).

Every committed S2 artifact (runner modules + runs/ outputs) must be free of
causal / pre-move / forecast-skill vocabulary and of the word 'validated'.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "event_response"))

PATTERN = re.compile(
    r"impact|caused|because of|driven by|due to|reaction to the news|"
    r"predicts|abnormal because|validated",
    re.IGNORECASE,
)
SCAN_ROOTS = (
    ROOT / "research" / "single_name_intelligence" / "event_response",
    ROOT / "research" / "single_name_intelligence" / "runs"
    / "s2_event_response",
)


def test_no_a24_tokens_and_no_validated_anywhere() -> None:
    hits = []
    for root in SCAN_ROOTS:
        if not root.exists():  # pragma: no cover
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:  # pragma: no cover
                continue
            for m in PATTERN.finditer(text):
                line_no = text.count("\n", 0, m.start()) + 1
                line = text.splitlines()[line_no - 1].strip()
                hits.append(f"{path.relative_to(ROOT)}:{line_no}: {line[:140]}")
    assert not hits, "banned vocabulary found:\n" + "\n".join(hits[:20])
