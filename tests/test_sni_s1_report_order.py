"""test_sni_s1_report_order.py — every block carries the ten REG §5 fields in
order, in REPORT.md and in results/<Pxx>.json; every block names its split."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"))

from s1_report import FIELD_ORDER  # noqa: E402
from s1_synth import RUNS_REL, synth_frames, write_synthetic_repo  # noqa: E402
import run_s1  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def _produce(tmp_path):
    frames = synth_frames(leak=False)
    store = write_synthetic_repo(tmp_path, frames)
    run_s1.DETECTED_AT = "2026-10-11T16:59:47-05:00"
    out = tmp_path / "out"
    run_s1.run_pipeline(store, tmp_path, out, str(tmp_path / "trial_ledger.jsonl"))
    return out


def test_json_field_order_all_protocols(tmp_path):
    out = _produce(tmp_path)
    import json
    for pid in ("P01", "P02", "P03"):
        doc = json.loads((out / "results" / f"{pid}.json").read_text("utf-8"))
        assert doc["protocol_id"] == pid
        assert doc["blocks"]
        for key, block in doc["blocks"].items():
            assert list(block.keys()) == FIELD_ORDER, (pid, key)


def test_every_block_names_its_split(tmp_path):
    out = _produce(tmp_path)
    import json
    for pid in ("P01", "P02", "P03"):
        doc = json.loads((out / "results" / f"{pid}.json").read_text("utf-8"))
        for key, block in doc["blocks"].items():
            # the key carries the split and so does analysis_set
            assert "|TRAIN|" in key or "|TUNE" in key
            assert "split=" in block["analysis_set"]


def test_report_md_renders_the_ten_fields_in_order_per_block(tmp_path):
    out = _produce(tmp_path)
    md = (out / "REPORT.md").read_text("utf-8")
    sections = re.split(r"^### ", md, flags=re.M)[1:]
    assert sections, "no blocks rendered"
    for sec in sections:
        nums = re.findall(r"^(\d+)\. ", sec, flags=re.M)
        assert nums == [str(i) for i in range(1, 11)], sec.splitlines()[0]
        labels = [sec.split(f"{i}. ", 1)[1].split(":", 1)[0] for i in range(1, 11)]
        assert labels == FIELD_ORDER


def test_report_block_order_matches_json(tmp_path):
    out = _produce(tmp_path)
    import json
    md = (out / "REPORT.md").read_text("utf-8")
    for pid in ("P01", "P02", "P03"):
        doc = json.loads((out / "results" / f"{pid}.json").read_text("utf-8"))
        section = md.split(f"## {pid} —", 1)[1]
        section = section.split("\n## ", 1)[0]          # this protocol only
        for key in doc["blocks"]:
            assert f"### {key}" in section, key
        keys_in_md = re.findall(r"^### (\S+)$", section, flags=re.M)
        assert keys_in_md == list(doc["blocks"].keys())
