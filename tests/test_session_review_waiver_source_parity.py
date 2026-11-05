"""Guard attended Web review waiver discoverability in Macro native entrypoints.

This source check does not prove Project UI save, native client loading, or release.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _entrypoints():
    return (
        (ROOT / "AGENTS.md").read_text(encoding="utf-8"),
        (ROOT / "CLAUDE.md").read_text(encoding="utf-8"),
    )


def test_review_waiver_is_protected_accepted_not_a_future_adoption_gate():
    agents, claude = _entrypoints()
    for source in (agents, claude):
        assert "#2026" in source and "#2030" in source
        assert "protected-merged" in source
        assert "#2018" in source and "not" in source
        assert "FAST" in source and "STANDARD" in source and "CRITICAL" in source
        assert "no blanket independent technical/source-review" in source.lower() or (
            "removes blanket independent technical/source-review" in source.lower()
        )
        assert "#2026's session-local review page is a **proposed** source" not in source
        assert "keep incumbent review requirements until its and #2018" not in source


def test_waiver_preserves_formal_native_controls_and_install_honesty():
    agents, claude = _entrypoints()
    for source in (agents, claude):
        assert "GitHub/CODEOWNERS" in source
        assert "security/release holds" in source
        assert "self-approval/merge" in source
        assert "CI" in source
        assert "default-OFF signed AUTOMATIC" in source or (
            "signed AUTOMATIC review host remains default OFF" in source
        )
        assert "ChatGPT Project settings" in source
        assert "Fabric" in source and "Dot" in source
    assert "HOLD-FOR-SOL" in agents
    assert "merge-on-green" in agents
    assert "Author self-check != independent child != formal" in claude
