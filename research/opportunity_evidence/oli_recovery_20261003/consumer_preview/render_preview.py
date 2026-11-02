"""Render the synthetic consumer's machine values and HTML from the same view."""
from __future__ import annotations
import json
from pathlib import Path
from fixtures import scenarios
from preview_contract import build_view


def render() -> tuple[str, dict]:
    result={}
    for example in scenarios():
        result[example['key']]={
            'public':build_view(example['bundle']),
            'private':build_view(example['bundle'],audience='private',viewer_id='fixture-viewer',private_plan=example['private_plan']),
        }
    encoded=json.dumps(result,sort_keys=True,ensure_ascii=False,allow_nan=False)
    # Script-data escaping is necessary even with textContent-only rendering.
    encoded=encoded.replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    template=Path(__file__).with_name('preview_template.html').read_text()
    if template.count('/*__FIXTURE_DATA__*/')!=1:raise ValueError('data marker count')
    return template.replace('/*__FIXTURE_DATA__*/',encoded),result

if __name__=='__main__':
    html,views=render()
    Path(__file__).with_name('preview.html').write_text(html)
    Path(__file__).with_name('preview_views.json').write_text(json.dumps(views,sort_keys=True,indent=2,ensure_ascii=False)+'\n')
    print(f'{len(views)} scenarios × 2 audiences rendered; synthetic only')
