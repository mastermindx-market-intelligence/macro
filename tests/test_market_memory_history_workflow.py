"""The shipped workflow must carry executable, outcome-isolated request examples."""
from pathlib import Path
import json
import re

from lib.dataos.web_api import dispatch
from tests.test_dataos_web_history import case  # existing descriptor-confined fixture
from tests.test_market_memory_history_dossier import macro

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "plugins/mastermind-data-lab/skills/data-workspace"


def test_history_request_examples_execute_through_existing_dispatch(case):
    text = (WORKFLOW / "references/requests.md").read_text()
    assert "## Historical daily dossier" in text
    section = text.split("## Historical daily dossier", 1)[1].split("\n## ", 1)[0]
    examples = []
    for block in re.findall(r"```json\n(.*?)```", section, flags=re.S):
        for line in block.splitlines():
            if line.strip():
                examples.append(json.loads(line))
    examples = [q for q in examples if q.get("action") == "history_dossier"]
    assert len(examples) >= 2
    macro_path, macro_hash = macro(case.base)
    for q in examples:
        assert q.get("reveal_outcomes", False) is False
        q = {**q, "ref": "fixture:history/manifest.json",
             "manifest_sha256": case.receipt["manifest_sha256"], "date": "2020-01-05"}
        if "macro_ref" in q:
            q.update(macro_ref="fixture:macro.json", macro_sha256=macro_hash)
        result = dispatch(case.ws, q, config_path=case.config)
        assert result["result"]["mode"] == "RETROSPECTIVE_EXPLORATORY"
        assert not result["result"]["outcomes_revealed"]
        assert not any("outcomes-" in source["ref"] for source in result["source_files"])


def test_workflow_preserves_source_discovery_and_truth_boundaries():
    skill = (WORKFLOW / "SKILL.md").read_text()
    for required in ("history_dossier", "manifest_sha256", "macro_sha256",
                     "initial release", "not full revision", "never open outcome"):
        assert required in skill
    assert "Do not silently fall back" in skill


def test_filing_context_workflow_example_is_executable(case):
    from tests.test_market_memory_history_filings import payload
    import hashlib
    text=(WORKFLOW/'references/requests.md').read_text()
    assert '## Filing context' in text
    section=text.split('## Filing context',1)[1].split('\n## ',1)[0]
    examples=[json.loads(block.strip()) for block in re.findall(r'```json\n(.*?)```',section,flags=re.S)]
    assert examples and all(q['action']=='history_dossier' for q in examples)
    raw=payload();(case.base/'earnings_8k_dates.parquet').write_bytes(raw)
    for q in examples:
        q.update(ref='fixture:history/manifest.json',manifest_sha256=case.receipt['manifest_sha256'],
            date='2020-03-16',filings_ref='fixture:earnings_8k_dates.parquet',filings_sha256=hashlib.sha256(raw).hexdigest())
        result=dispatch(case.ws,q,config_path=case.config)
        assert result['result']['filings']['total_events']==1 and not result['result']['outcomes_revealed']
    skill=(WORKFLOW/'SKILL.md').read_text()
    for term in ('filings_sha256','filings_offset','source-claimed','not the original press-release time'):
        assert term in skill



def test_transcript_workflow_examples_are_executable_without_imputed_identity(case):
    from tests.test_dataos_web_history import transcript_source
    path,ref,version=transcript_source(case)
    text=(WORKFLOW/'references/requests.md').read_text()
    assert '## Transcript source context' in text
    section=text.split('## Transcript source context',1)[1].split('\n## ',1)[0]
    requests=[json.loads(block.strip()) for block in re.findall(r'```json\n(.*?)```',section,flags=re.S)]
    assert {q['action'] for q in requests}=={'history_dossier','history_transcript'}
    first=next(q for q in requests if q['action']=='history_dossier')
    first.update(ref='fixture:history/manifest.json',manifest_sha256=case.receipt['manifest_sha256'],
        date='2020-03-16',transcripts_ref=ref,transcripts_version=version)
    listed=dispatch(case.ws,first,config_path=case.config);item=listed['result']['transcripts']['events'][0]
    second=next(q for q in requests if q['action']=='history_transcript')
    second.update(ref=ref,expected_version=version,row_position=item['source_row_position'],expected_metadata_sha256=item['metadata_sha256'])
    result=dispatch(case.ws,second,config_path=case.config)
    assert result['result']['metadata']['transcripts_id'] is None
    assert result['result']['speaker_roles_verified'] is False
    skill=(WORKFLOW/'SKILL.md').read_text()
    for required in ('history_transcript','transcripts_version','not a full content hash','next_cursor','source labels'):
        assert required in skill
