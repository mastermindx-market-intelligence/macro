"""Private offline browser projection of a hash-bound Market Memory archive.

This is a research artifact, not a public publisher or authorization boundary.
No external resources, source prices copied into Git, or new runtime are needed.
By default the export contains NO outcomes. An explicit education export may
include a separately compressed outcome payload; that is not blind evaluation.
"""
from __future__ import annotations
import base64
import gzip
import hashlib
import json
from pathlib import Path

from engine.neuralweb.market_memory_history import HistoricalExperienceError
from engine.neuralweb.market_memory_history_archive import (
    MODE, MAX_FILE_BYTES, MAX_TOTAL_ROWS, _bytes, _regular_file, _write_exclusive, read_manifest,
)

MAX_BROWSER_BYTES = 64 * 1024 * 1024


def _columnar(root: Path, manifest: dict, kind: str, manifest_sha: str) -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq
    rows=[]; columns=None
    for record in manifest['files']:
        if record['kind'] != kind:
            continue
        payload=_regular_file(root,record['name'],MAX_FILE_BYTES)
        if len(payload)!=record['bytes'] or hashlib.sha256(payload).hexdigest()!=record['sha256']:
            raise HistoricalExperienceError('browser source file digest mismatch')
        try:
            pf=pq.ParquetFile(pa.BufferReader(payload),pre_buffer=False)
            try:
                if pf.metadata.num_rows != record['rows']:
                    raise HistoricalExperienceError('browser source row count mismatch')
                if sum(pf.metadata.row_group(i).total_byte_size for i in range(pf.metadata.num_row_groups)) > MAX_BROWSER_BYTES:
                    raise HistoricalExperienceError('browser decoded source exceeds budget')
                table=pf.read(use_threads=False)
            finally:
                pf.close()
            if columns is None: columns=table.column_names
            if table.column_names!=columns:
                raise HistoricalExperienceError('historical browser schema drift')
            for row in table.to_pylist():
                row['missing']=json.loads(row['missing'])
                rows.append([row.get(c) for c in columns])
            if len(rows)>MAX_TOTAL_ROWS:
                raise HistoricalExperienceError('browser row budget exceeded')
        except HistoricalExperienceError:
            raise
        except (ValueError,TypeError,KeyError,OSError) as exc:
            raise HistoricalExperienceError('invalid browser source payload') from exc
    if kind=='states' and any(c.startswith(('forward_','outcome')) for c in columns or []):
        raise HistoricalExperienceError('future outcomes cannot enter browser state payload')
    result={'mode':MODE,'manifest_sha256':manifest_sha,'columns':columns or [],'rows':rows}
    if kind=='states':
        result['metadata']={k:manifest[k] for k in ('artifact_id','coverage','basis','request','sources','limitations','calculations')}
    return result


def _packed(payload: dict) -> tuple[str,str]:
    raw=_bytes(payload)
    if len(raw)>MAX_BROWSER_BYTES:
        raise HistoricalExperienceError('browser payload exceeds decoded byte budget')
    return base64.b64encode(gzip.compress(raw,compresslevel=6,mtime=0)).decode(),hashlib.sha256(raw).hexdigest()


def export_browser(root: Path, destination: Path, *, expected_manifest_sha256: str,
                   include_outcomes: bool=False, macro_path: Path | None=None,
                   expected_macro_sha256: str | None=None, filings_path: Path | None=None,
                   expected_filings_sha256: str | None=None, transcripts_catalog_path: Path | None=None,
                   expected_transcripts_catalog_sha256: str | None=None) -> dict:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    if type(include_outcomes) is not bool:
        raise HistoricalExperienceError('explicit boolean outcome export required')
    if (macro_path is None) != (expected_macro_sha256 is None):
        raise HistoricalExperienceError('macro source path and exact digest must be supplied together')
    if (filings_path is None) != (expected_filings_sha256 is None):
        raise HistoricalExperienceError('filing source path and exact digest must be supplied together')
    if filings_path is not None and Path(filings_path).name != 'earnings_8k_dates.parquet':
        raise HistoricalExperienceError('exact earnings filing source filename required')
    if (transcripts_catalog_path is None)!=(expected_transcripts_catalog_sha256 is None):
        raise HistoricalExperienceError('transcript catalogue and exact digest must be supplied together')
    root,destination=Path(root),Path(destination)
    if destination.exists(): raise FileExistsError(destination)
    if destination.is_symlink() or any(p.is_symlink() for p in destination.parents):
        raise HistoricalExperienceError('browser export cannot traverse symlinks')
    manifest=read_manifest(root,expected_manifest_sha256=expected_manifest_sha256)
    states=_columnar(root,manifest,'states',expected_manifest_sha256)
    state_data,state_sha=_packed(states)
    outcome_data=outcome_sha=None
    if include_outcomes:
        result=_columnar(root,manifest,'outcomes',expected_manifest_sha256)
        outcome_data,outcome_sha=_packed(result)
    macro_data=macro_payload_sha=None
    macro_events=0
    if macro_path is not None:
        from engine.neuralweb.market_memory_history_macro import read_macro_chronology
        macro=read_macro_chronology(macro_path,expected_sha256=expected_macro_sha256)
        columns=['calendar_date','series','period','value','source_units']
        macro_events=len(macro['events'])
        payload={'mode':MODE,'manifest_sha256':expected_manifest_sha256,
                 'macro_sha256':expected_macro_sha256,'columns':columns,
                 'rows':[[r[c] for c in columns] for r in macro['events']],
                 'metadata':{**{k:macro[k] for k in ('chronology_id','source','source_rows_sha256','coverage','limitations')},
                     'revision_end_metadata':'withheld_from_daily_projection',
                     'declared_archive_window':{'start':macro['start'],'end':macro['end']},
                     'calendar_completeness_proven':False}}
        macro_data,macro_payload_sha=_packed(payload)
    filing_data=filing_payload_sha=None
    filing_events=0
    if filings_path is not None:
        from engine.neuralweb.market_memory_history_filings import read_filing_timeline_path
        timeline=read_filing_timeline_path(filings_path,expected_sha256=expected_filings_sha256)
        timeline.update(manifest_sha256=expected_manifest_sha256,filings_sha256=expected_filings_sha256)
        filing_events=len(timeline['rows'])
        filing_data,filing_payload_sha=_packed(timeline)
    transcript_data=transcript_payload_sha=None
    transcript_records=0
    if transcripts_catalog_path is not None:
        from engine.neuralweb.market_memory_history_transcripts import read_transcript_catalog_path
        catalog=read_transcript_catalog_path(transcripts_catalog_path,expected_sha256=expected_transcripts_catalog_sha256)
        catalog.update(manifest_sha256=expected_manifest_sha256,transcripts_catalog_sha256=expected_transcripts_catalog_sha256)
        transcript_records=len(catalog['rows'])
        transcript_data,transcript_payload_sha=_packed(catalog)
    templates=Path(__file__).resolve().parents[2]/'templates'
    css='\n'.join((templates/name).read_text(encoding='utf-8') for name in ('theme.css','market_memory_retained.css','market_memory_history.css'))
    js=(templates/'market_memory_history.js').read_text(encoding='utf-8')
    env=Environment(loader=FileSystemLoader(templates),undefined=StrictUndefined,autoescape=True)
    html=env.get_template('market_memory_history.html.j2').render(
        css=css,js=js,state_data=state_data,state_sha=state_sha,
        outcome_data=outcome_data,outcome_sha=outcome_sha,
        macro_data=macro_data,macro_payload_sha=macro_payload_sha,
        filing_data=filing_data,filing_payload_sha=filing_payload_sha,
        transcript_data=transcript_data,transcript_payload_sha=transcript_payload_sha).encode()
    if len(html)>MAX_BROWSER_BYTES:
        raise HistoricalExperienceError('browser file exceeds byte budget')
    _write_exclusive(destination,html)
    return {'schema':'market_memory.history_browser.v1','artifact_id':manifest['artifact_id'],
            'manifest_sha256':expected_manifest_sha256,'html_sha256':hashlib.sha256(html).hexdigest(),
            'html_bytes':len(html),'state_rows':len(states['rows']),
            'outcomes_included':include_outcomes,'public_publication':False,
            'point_in_time_evaluation':False,'macro_events':macro_events,
            'macro_sha256':expected_macro_sha256,'filing_events':filing_events,
            'filings_sha256':expected_filings_sha256,'transcript_records':transcript_records,
            'transcripts_catalog_sha256':expected_transcripts_catalog_sha256}
