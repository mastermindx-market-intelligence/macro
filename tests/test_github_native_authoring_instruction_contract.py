"""Guard adoption of accepted GitHub-native authoring in agent instructions.

Mastermind #2118 is merged. The GitHub API branch/file/PR path is not an M2
host-local worktree operation; host-local custody and release fences still bind.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MERGE = "d5b65649a0a880ea1f8080db777f8ed8b0bc3b98"


def test_claude_and_agent_guides_use_accepted_native_source_route():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    for name, text in (("AGENTS.md", agents), ("CLAUDE.md", claude)):
        assert MERGE in text, name
        assert "GitHub-native" in text, name
        assert "worktree" in text.lower(), name
        assert "merge" in text.lower(), name
    assert "**Only after** Mastermind PR #2118" not in agents
    assert "When Mastermind #2118 is actually merged" not in claude
    assert "This conditional pointer does not install unmerged #2118" not in agents
    assert "Until that merge, the candidate #2118 policy is not installed" not in claude
    assert "Never switch an explicitly denied or effect-unknown action" in agents
    assert "Never bypass local hooks" in claude
