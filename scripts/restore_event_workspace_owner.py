"""Restore the exact complete published Event Workspace generation before build.

Read-only upstream: existing Company Intelligence public reader, no SEC intake,
financial calculation, admission, R2 writes, or per-request network. The local
mirror keeps owner bytes/IDs/clocks; it is a build dependency, not a truth store.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from hashlib import sha256
import json
from datetime import datetime,timezone

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.neuralweb import company_intelligence_reader as reader
from engine.company_intelligence.event_workspace import (
    _atomic_write,validate_workspace_manifest,validate_event_workspace,
    validate_generation_clocks,select_current_event_from_aliases,
)


def _assert_local_owner_paths(root, targets):
    # The configured root is the trusted boundary; no descendant may redirect
    # exact owner bytes through an existing or dangling symlink. Check the
    # whole candidate set before the first local write, including marker.
    anchor=Path(root).absolute()
    for target in targets:
        target=Path(target).absolute()
        try:relative=target.relative_to(anchor)
        except ValueError:raise ValueError('local_owner_destination_outside_root')
        current=anchor
        if current.is_symlink():raise ValueError('local_owner_symlink_destination')
        if current.exists() and not current.is_dir():raise ValueError('local_owner_root_not_directory')
        for index,part in enumerate(relative.parts):
            current=current/part
            if current.is_symlink():raise ValueError('local_owner_symlink_destination')
            if index<len(relative.parts)-1 and current.exists() and not current.is_dir():
                raise ValueError('local_owner_ancestor_not_directory')
        if current.exists() and not current.is_file():raise ValueError('local_owner_leaf_not_file')


def restore_event_workspace_owner(root,*,base_url=None,required_tickers=(),
    fetch_marker=None,fetch_manifest=None,fetch_workspace=None):
    """Validate all remote bytes and marker stability before any local mutation.

    A failed/moved/partial source refuses the build restore and leaves the
    existing marker intact. No retry, recollection, synthetic generation or
    four-row replacement. Required issuers are a consumer dependency fence;
    every other current owner row is restored as well.
    """
    marker_reader=fetch_marker or reader.fetch_current_workspace_marker_raw
    manifest_reader=fetch_manifest or reader._fetch_generation_manifest_raw
    workspace_reader=fetch_workspace or reader._fetch_raw_workspace_bytes
    first=marker_reader(base_url=base_url)
    if first is None:raise ValueError('owner_current_marker_not_published')
    marker_raw,marker=first;validate_workspace_manifest(marker)
    generation=marker['generation_id'];digest=sha256(marker_raw).hexdigest()
    manifest_raw,manifest=manifest_reader(generation,base_url=base_url)
    validate_workspace_manifest(manifest)
    if manifest_raw!=marker_raw or manifest!=marker:raise ValueError('owner_marker_immutable_manifest_mismatch')
    files={};rows={}
    for relative,receipt in manifest['files'].items():
        # Reader accepts an event ID and generation, never an arbitrary URL.
        parts=Path(relative).parts
        if len(parts)!=2 or parts[0]!='workspaces' or not parts[1].endswith('.json'):
            raise ValueError('owner_manifest_workspace_path_invalid')
        event_id=parts[1][:-5]
        body=workspace_reader(event_id,generation,base_url=base_url)
        if not isinstance(body,bytes) or sha256(body).hexdigest()!=receipt['sha256'] or len(body)!=receipt['bytes']:
            raise ValueError('owner_workspace_receipt_mismatch')
        row=json.loads(body);validate_event_workspace(row)
        if row['event_id']!=event_id or row['generation_id']!=generation:raise ValueError('owner_workspace_subject_generation_mismatch')
        if event_id in rows:raise ValueError('duplicate_owner_workspace')
        files[relative]=body;rows[event_id]=row
    if len(rows)!=manifest['event_count'] or any(event_id not in rows for event_id in manifest['aliases'].values()):
        raise ValueError('owner_complete_nest_or_alias_coverage_mismatch')
    validate_generation_clocks(manifest,rows)
    for ticker in required_tickers:
        selected=select_current_event_from_aliases(ticker,manifest['aliases'])
        row=rows[selected.event_id]
        if not any(v.get('ticker')==ticker for v in row['issuer']['listings']):raise ValueError('required_owner_listing_unqualified')
    last=marker_reader(base_url=base_url)
    if last is None or last[0]!=marker_raw or last[1]!=marker:raise ValueError('owner_marker_moved_during_restore')
    nest=Path(root)/'data/company_intelligence/event_workspaces';immutable=nest/'generations'/generation
    _assert_local_owner_paths(root,[immutable/relative for relative in {**files,'manifest.json':manifest_raw}]+[nest/'manifest.json'])
    # Check every immutable destination BEFORE writing the first byte.
    for relative,body in {**files,'manifest.json':manifest_raw}.items():
        target=immutable/relative
        if target.exists() and target.read_bytes()!=body:raise ValueError('local_owner_immutable_collision')
    for relative,body in files.items():
        target=immutable/relative
        if not target.exists():_atomic_write(target,body)
    if not (immutable/'manifest.json').exists():_atomic_write(immutable/'manifest.json',manifest_raw)
    # Exact marker last, after a complete immutable generation is restored.
    local_marker=nest/'manifest.json'
    if not local_marker.exists() or local_marker.read_bytes()!=marker_raw:_atomic_write(local_marker,marker_raw)
    return {'owner_contract':manifest['schema'],'generation_id':generation,'manifest_sha256':digest,
        'source_clock':manifest.get('source_clock'),'owner_generated_at':manifest['generated_at'],
        'restored_event_ids':sorted(rows),'event_count':len(rows),
        'source_bindings':{name:{'sha256':manifest['files'][name]['sha256'],'bytes':len(body)} for name,body in files.items()},
        'required_tickers':list(required_tickers),'restored_at':datetime.now(timezone.utc).isoformat(),
        'upstream_effect':'read_only','preserved_owner_bytes_and_clocks':True}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--base-url')
    parser.add_argument('--require-ticker',action='append',default=[])
    parser.add_argument('--receipt',type=Path)
    args=parser.parse_args(argv)
    result=restore_event_workspace_owner(args.root,base_url=args.base_url,required_tickers=tuple(args.require_ticker))
    if args.receipt:_atomic_write(args.receipt,(json.dumps(result,sort_keys=True,indent=2)+'\n').encode())
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=='__main__':raise SystemExit(main())
