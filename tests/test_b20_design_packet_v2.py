from pathlib import Path


def test_b20_v2_structural_requirements():
    packet = Path("research/prophet_v4/r6_program/wave1/B20_DESIGN_PACKET_V1_2026-09-23.md")
    text = packet.read_text(encoding="utf-8")
    lines = text.splitlines()

    assert lines[2] == "STATUS: V2 COMPLETE"
    assert len(lines) <= 700
    assert text.count("| `ENTRY_OPEN` | Act / 可行动 |") == 1
    assert text.count("SPECIFIED · capture owed at B16") == 40
    assert "Nothing to act on today. Rows appear here when an entry opens." in text
    assert "今日无可行动项。入场窗口开启时会在此显示。" in text
    assert "A pull never resurrects an unwatch tombstone" in text
    assert "--ink-warn" in text
    assert "--ink-warning" not in text
