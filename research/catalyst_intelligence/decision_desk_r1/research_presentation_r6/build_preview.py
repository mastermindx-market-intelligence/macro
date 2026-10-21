"""Build only the pinned synthetic research preview; never acquire native inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FIXTURES = HERE.parent / "fixtures" / "stock_assessment_r8"
OWNER_HEAD = "13b528d07e52680570a837f27571b64eb8176ca8"
RECEIPT_SHA256 = "7c059aec43adf4514659d8571dcb43ba9e407441a093188c4c2c5c0d275f70e8"
CAPTURE_HASHES = {
    "delayed_reconstruction": "c4799c41792553d19234b9bdd978b27170f11b9e804c1927a36e4f041de651fb",
    "history_missing": "39defcc38d635182c05c1bac28a05ffc357f0f70614fb370aa124572fc7b52b2",
}


def load_captures() -> dict:
    receipt_bytes = (FIXTURES / "capture-receipt.json").read_bytes()
    if hashlib.sha256(receipt_bytes).hexdigest() != RECEIPT_SHA256:
        raise ValueError("Pinned research capture receipt changed")
    receipt = json.loads(receipt_bytes)
    captures = {item["case"]: item for item in receipt["captures"]}
    if set(captures) != set(CAPTURE_HASHES):
        raise ValueError("Unexpected retained research capture")
    result = {}
    for name, expected in CAPTURE_HASHES.items():
        raw = (FIXTURES / (name + ".assessment.json")).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected or captures[name]["stdout_sha256"] != expected:
            raise ValueError("Pinned research capture bytes changed: " + name)
        packet = json.loads(raw)
        if packet["assessment_id"] != captures[name]["assessment_id"]:
            raise ValueError("Captured assessment identity changed")
        if (packet["schema"] != "catalyst.stock_research_assessment.v3"
                or packet["qualification"] != "NONACTIVATED_RESEARCH_CONSUMER"
                or packet["source_admission_established"] is not False
                or packet["decision_availability_established"] is not False
                or not packet["authority"]
                or any(value is not False for value in packet["authority"].values())):
            raise ValueError("Research preview cannot establish admission or action authority")
        result[name] = packet
    return result


def build(output: Path | None = None) -> Path:
    # Validate retained bytes before reading code or producing any output.
    captures = load_captures()
    html = (HERE / "preview_shell.html").read_text(encoding="utf-8")
    replacements = {
        "/* THEME_TOKENS */": (HERE.parent / "theme_excerpt.css").read_text(encoding="utf-8"),
        "/* COMPONENT_CSS */": (ROOT / "templates/biocatalyst_decision_desk.css").read_text(encoding="utf-8"),
        "/* RESEARCH_COMPONENT_JS */": (ROOT / "templates/catalyst_research_assessment.js").read_text(encoding="utf-8"),
        "/* RESEARCH_CAPTURES */": json.dumps(captures, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c"),
    }
    for marker, content in replacements.items():
        if html.count(marker) != 1:
            raise ValueError("Preview marker missing or repeated: " + marker)
        html = html.replace(marker, content)
    target = output or HERE / "Research_Assessment_Contract_Replay.html"
    raw = html.encode("utf-8")
    if target.exists():
        if target.is_symlink() or target.read_bytes() != raw:
            raise FileExistsError("Choose a fresh output; retained previews are not overwritten")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(raw)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    print(build(parser.parse_args().output))
