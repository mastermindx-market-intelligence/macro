"""Read-only installed USDA planner preflight; no provider or runtime writes.

Records actual ranking, selection and source facts without changing the pool,
hold list, scores, cadence or clocks. A report being eligible is not selection.
The input is a retained list of already-reviewed holds, embedded by the caller.
"""
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from pathlib import Path
import json
import subprocess
import sys

SOURCE_ID = "usda-nass-2026-10-13-crop-progress"
HELD_REFS = ['artifact:data/gex/latest.json', 'artifact:data/market_state/latest.json', 'artifact:data/marketing/hot_tape_pack.json#ABSI', 'artifact:data/marketing/hot_tape_pack.json#ALHC', 'artifact:data/marketing/hot_tape_pack.json#ASTX', 'artifact:data/risk_radar/forward_log.jsonl', 'artifact:site/basketdata/breadth_split.json', 'artifact:site/basketdata/fear_greed.json', 'artifact:site/marketdata/sp500_heatmap.json#CCI', 'artifact:site/marketdata/sp500_heatmap.json#MRNA', 'artifact:site/marketdata/sp500_heatmap.json#TMUS', 'chronicle:TTWO-BULL-20261007', 'official_feed:99354c7bd7561bf9356a1193875243a72ff1d000', 'official_feed:url:cd2747adeed2', 'research_vault:marketdesk-4sbw9xdvesv-09647d', 'research_vault:marketdesk-8inwlunucuj-8950ab', 'research_vault:marketdesk-arbvfsvswas-96701d', 'research_vault:marketdesk-augnhdcr2jm-0cbff4', 'research_vault:marketdesk-dxcjj8lpx8k-75b4af', 'research_vault:marketdesk-ergkmhwhsow-e05c9a', 'research_vault:marketdesk-f4gxuf5mmau-53a7ed', 'research_vault:marketdesk-ioh3cizfpog-b49a47', 'research_vault:marketdesk-qtq09kmuctq-baf3cc', 'research_vault:marketdesk-qvymtn8aohk-00548d', 'research_vault:marketdesk-rc9hi0toy31-75d4dc', 'research_vault:marketdesk-stzblc3lgcn-40b123', 'research_vault:marketdesk-uc6giunqscq-05fcee', 'research_vault:marketdesk-xyyijkslpal-b997fb', 'research_vault:usda-2026-10-09-wasde-676']


def main():
    root = Path(sys.argv[1]).resolve()
    assert root == Path('/opt/macro'), 'installed inspection only'
    sys.path.insert(0, str(root))
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    reads = {}
    hashing = False
    protected = True

    def audit(event, args):
        nonlocal hashing
        if not protected:
            return
        if event in {'socket.connect', 'socket.getaddrinfo', 'subprocess.Popen',
                     'os.remove', 'os.rename', 'os.mkdir', 'os.rmdir', 'os.system'}:
            raise RuntimeError('read-only preflight refused ' + event)
        if event != 'open':
            return
        name, mode, flags = args
        if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or flags & (64 | 512 | 1024):
            raise RuntimeError('read-only preflight refused file write')
        if hashing or not isinstance(name, (str, bytes)):
            return
        path = Path(name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            return
        rel = str(path.relative_to(root))
        if rel not in reads:
            hashing = True
            try:
                reads[rel] = sha256(path.read_bytes()).hexdigest()
            finally:
                hashing = False

    sys.addaudithook(audit)
    from engine.press import desk_planner as p
    from engine.press import validators
    now = datetime.now(timezone.utc)
    as_of = now.date()
    cfg = p.load_config(root)
    dc = cfg['desks']['research_desk']
    catalog = json.loads((root/'data/research_vault/catalog.json').read_bytes())
    items = catalog['items']
    target = [x for x in items if x.get('id') == SOURCE_ID]
    assert len(target) == 1, 'canonical source must exist once'
    lo = as_of - timedelta(days=int(dc['window_days']))
    eligible = [x for x in items if x.get('summary_points') and p._as_date(x.get('published_at'))
                and lo <= p._as_date(x['published_at']) <= as_of]
    order, meta = p._triage_order(cfg, as_of, root, eligible)
    by_id = {x['id']: x for x in eligible}
    ranked = [by_id[k] for k in order if k in by_id]
    ranked_ids = {x['id'] for x in ranked}
    ranked += [x for x in eligible if x['id'] not in ranked_ids]
    if not order:
        ranked.sort(key=lambda x: (0 if x.get('top_pick') else 1,
                    -p._as_date(x['published_at']).toordinal(), x['id']))
    published, _ = p.published_refs(root, cfg)
    staged, _ = p.staged_refs(root, cfg)
    blocked = set(HELD_REFS) | published | staged
    pool = [x for x in ranked if 'research_vault:' + x['id'] not in blocked]
    slots = p.plan(['research_desk'], root=root, cfg=cfg, as_of=as_of,
                   extra_blocked_refs=HELD_REFS)
    usda_slot = next((s for s in slots if 'research_vault:' + SOURCE_ID in s['sources']), None)
    target_ref = 'research_vault:' + SOURCE_ID
    def position(rows):
        return next((i + 1 for i, x in enumerate(rows) if x['id'] == SOURCE_ID), None)
    result = {
        'observed_at': now.isoformat(), 'installed_head': head,
        'source_id': SOURCE_ID, 'published_at': target[0]['published_at'],
        'eligible_count': len(eligible), 'ranked_position': position(ranked),
        'unheld_position': position(pool), 'candidate_pool': dc['candidate_pool'],
        'blocked_target': target_ref in blocked, 'held_refs': sorted(HELD_REFS),
        'triage': meta.get(SOURCE_ID),
        'first_unheld': [{'id': x['id'], 'title': x['title'], 'published_at': x['published_at']}
                        for x in pool[:int(dc['candidate_pool'])]],
        'selected_slots': [{'id': s['id'], 'sources': s['sources']} for s in slots],
        'usda_slot': usda_slot,
        'quantity_index': (sorted((str(v), tier) for v, tier in validators.fact_tier_index(usda_slot))
                           if usda_slot else []),
        'cutover': cfg['cutover'], 'writer_calls': 0, 'runtime_writes': 0,
        'publication_approved': False,
    }
    protected = False
    after_head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    changed = [rel for rel, digest in reads.items()
               if not (root/rel).is_file() or sha256((root/rel).read_bytes()).hexdigest() != digest]
    result.update(input_sha256=reads, changed_inputs=changed,
                  stable_installed_head=head == after_head, head_after=after_head)
    assert not changed and head == after_head, 'input changed during inspection'
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
