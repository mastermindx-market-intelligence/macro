"""Reproduce the exact a7362d0 + 72038ba generated-page integration.

Run only in a clean worktree at PRE_MERGE_HEAD after starting the pinned
``git merge --no-commit --no-ff MAIN``.  The script resolves generated detail
pages through the incumbent renderer while preserving the selected embedded
input for every page.  It does not collect or rescore market data.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[4]
PRE_MERGE_HEAD = 'a7362d01e3b7609c7c7b59c6ad61ba0cccbf6b8a'
MAIN = '72038badf7e309dfbdd00120fd0f0e523623fe75'
OUT_DIR = ROOT / 'research/sector_pulse/recommendation_reasons_20260921/continuation_20260924'
OUT_PATH = OUT_DIR / 'current-base-integration-proof.json'

sys.path.insert(0, str(ROOT))
from engine import basket_score
from lib.pages import write_page, externalize_css_text, externalize_js_text, dbase_prefix
from scripts.externalize_css import MIN_BYTES
from scripts.optimize_assets import make_optimizer


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_bytes(ref: str, path: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{ref}:{path}'])


def git_text(ref: str, path: str) -> str:
    return git_bytes(ref, path).decode()


def detail_from(text: str) -> dict:
    marker = 'const DETAIL = '
    assert text.count(marker) == 1
    detail, _ = json.JSONDecoder().raw_decode(text.split(marker, 1)[1])
    return detail


def generation_stamp(text: str) -> str:
    stamps = re.findall(
        r'<span>([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2} UTC)</span>',
        text,
    )
    assert len(stamps) == 1, stamps
    return stamps[0]


def main() -> int:
    assert subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip() == PRE_MERGE_HEAD
    merge_head = (ROOT / '.git' / 'MERGE_HEAD')
    if not merge_head.exists():
        # worktree .git is a file; resolve the actual git dir.
        git_dir = Path(subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--git-dir'], text=True).strip())
        if not git_dir.is_absolute():
            git_dir = ROOT / git_dir
        merge_head = git_dir / 'MERGE_HEAD'
    assert merge_head.read_text().strip() == MAIN

    conflict_paths = {
        line[3:]
        for line in subprocess.check_output(
            ['git', '-C', str(ROOT), 'status', '--porcelain=v1'], text=True
        ).splitlines()
        if line[:2] == 'UU'
    }
    assert conflict_paths
    assert all(path.startswith(('site/basket/', 'site/basket_china/', 'site/basket_hk/')) for path in conflict_paths)

    roots = ('basket', 'basket_china', 'basket_hk', 'basket_canada', 'basket_intl')
    branch_pages = sorted(
        path for root in roots for path in (ROOT / 'site' / root).glob('*.html')
    )
    # Conflicted pages are present with markers; non-conflicted pages are usable directly.
    page_paths = sorted({path.relative_to(ROOT).as_posix() for path in branch_pages})
    assert len(page_paths) == 121, len(page_paths)
    assert conflict_paths <= set(page_paths)

    env = Environment(loader=FileSystemLoader(str(ROOT / 'templates')), autoescape=True)
    template = env.get_template('basket_detail.html.j2')
    optimize = make_optimizer(ROOT / 'site')
    created_assets: dict[str, str] = {}
    rows: list[dict] = []
    prepared: list[tuple[Path, str]] = []

    def hashed_asset(page_path: Path, body: str, index: int, media=None, kind='css'):
        data = body.encode()
        if len(data) < MIN_BYTES:
            return None
        digest = sha(data)[:8]
        dest = ROOT / 'site' / 'assets' / kind / f'{digest}.{kind}'
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert dest.read_bytes() == data, dest
        else:
            dest.write_bytes(data)
            created_assets[dest.relative_to(ROOT).as_posix()] = sha(data)
        return dbase_prefix(page_path) + f'assets/{kind}/{digest}.{kind}?v={digest}'

    for relative in page_paths:
        path = ROOT / relative
        if relative in conflict_paths:
            input_source = 'protected_main'
            input_bytes = git_bytes(MAIN, relative)
        else:
            input_source = 'candidate_pre_merge'
            input_bytes = git_bytes(PRE_MERGE_HEAD, relative)
        input_text = input_bytes.decode()
        old = detail_from(input_text)
        new = deepcopy(old)
        new['act_now'] = basket_score.act_now_stocks(new['members'], new['theme'])

        before = deepcopy(old.get('act_now') or {})
        after = deepcopy(new.get('act_now') or {})
        for key in ('status', 'buys', 'uncovered'):
            assert after.get(key) == before.get(key), (relative, key, before.get(key), after.get(key))
        before_explain = deepcopy(before)
        after_explain = deepcopy(after)
        for record in (before_explain, after_explain):
            for key in ('entry_checks', 'entry_summary', 'note_en', 'note_zh'):
                record.pop(key, None)
            for item in record.get('early_turn_watch', []):
                item.pop('blocker_en', None)
                item.pop('blocker_zh', None)
        assert before_explain == after_explain, (relative, 'non-explanation act_now mutation')
        assert {k: v for k, v in new.items() if k != 'act_now'} == {
            k: v for k, v in old.items() if k != 'act_now'
        }

        region = new.get('region', 'us')
        back_en = 'Sector Intelligence' if region == 'us' else 'China Sector Intelligence' if region == 'china' else 'Theme Rotation Desk'
        back_zh = '行业智慧' if region == 'us' else '中国行业智慧' if region == 'china' else '主题轮动台'
        raw = json.dumps(new, separators=(',', ':'), ensure_ascii=False, allow_nan=False).replace('</', '<\\/')
        rendered = template.render(
            detail_json=raw,
            basket_name=new['basket'].get('name', path.stem),
            generated_utc=generation_stamp(input_text),
            back_href=new['back'],
            back_label_en=back_en,
            back_label_zh=back_zh,
        )
        rendered = externalize_css_text(
            rendered,
            lambda body, index, media=None, page_path=path: hashed_asset(page_path, body, index, media, 'css'),
        )
        rendered = externalize_js_text(
            rendered,
            lambda body, index, page_path=path: hashed_asset(page_path, body, index, None, 'js'),
        )
        rendered = optimize(rendered, path.parent)
        prepared.append((path, rendered))
        rows.append({
            'path': relative,
            'input_source': input_source,
            'input_ref': MAIN if input_source == 'protected_main' else PRE_MERGE_HEAD,
            'input_sha256': sha(input_bytes),
            'effective_as_of': new.get('as_of'),
            'generation_stamp': generation_stamp(input_text),
            'members': len(new.get('members') or []),
            'assessed': sum(
                isinstance(item.get('conviction'), dict)
                and item['conviction'].get('score') is not None
                for item in new.get('members') or []
            ),
            'entry_checks_before': len(before.get('entry_checks') or []),
            'entry_checks_after': len(after.get('entry_checks') or []),
            'status_buys_uncovered_unchanged': True,
            'non_explanation_data_unchanged': True,
        })

    for (path, rendered), row in zip(prepared, rows):
        write_page(path, rendered)
        row['output_sha256'] = sha(path.read_bytes())

    proof = {
        'schema': 'theme_detail_current_base_integration.v1',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'candidate_pre_merge_head': PRE_MERGE_HEAD,
        'protected_main': MAIN,
        'template_sha256': sha((ROOT / 'templates/basket_detail.html.j2').read_bytes()),
        'pages': len(rows),
        'conflict_pages_from_protected_main': len(conflict_paths),
        'nonconflict_pages_from_candidate': len(rows) - len(conflict_paths),
        'member_rows': sum(row['members'] for row in rows),
        'assessed_rows': sum(row['assessed'] for row in rows),
        'entry_checks_before': sum(row['entry_checks_before'] for row in rows),
        'entry_checks_after': sum(row['entry_checks_after'] for row in rows),
        'created_assets': created_assets,
        'rows': rows,
        'scope': (
            'Resolve generated-page conflicts by retaining protected-main embedded inputs '
            'where main changed, candidate embedded inputs elsewhere, then render all pages '
            'through the auto-merged canonical template and incumbent act-now owner. No collection, '
            'rescoring, quote refresh, recommendation mutation, stock permission widening, or '
            'alternate publisher.'
        ),
    }
    OUT_PATH.write_text(json.dumps(proof, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k: v for k, v in proof.items() if k != 'rows'}, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
