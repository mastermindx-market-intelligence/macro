#!/usr/bin/env bash
set -Eeuo pipefail

EXPECTED_MAIN='9fbfe11e8cec40e6133a30e214c7521c9c527435'
EXPECTED_SOURCE='f09a4f078be714b1eb026d7a4178540f7a63b494'
EXPECTED_TREE='3386b6d77673eeb1888a0e01db2f62ac08d04d56'
ARCHIVE_URL='https://4dq90n7e.basicdeploy.com/candidate.tar.gz'

rm -rf candidate /tmp/mmx-candidate.tar.gz /tmp/mmx-china-build.log
curl --fail --show-error --silent --location \
  --retry 5 --retry-all-errors --connect-timeout 30 \
  "$ARCHIVE_URL" -o /tmp/mmx-candidate.tar.gz
ARCHIVE_SHA=$(sha256sum /tmp/mmx-candidate.tar.gz | awk '{print $1}')
ARCHIVE_BYTES=$(wc -c < /tmp/mmx-candidate.tar.gz | tr -d ' ')
mkdir -p candidate
tar -xzf /tmp/mmx-candidate.tar.gz -C candidate
cd candidate

python - <<'PY'
import json
from pathlib import Path
m = json.loads(Path('MMX_PROOF_META.json').read_text())
expected = {
    'current_main': '9fbfe11e8cec40e6133a30e214c7521c9c527435',
    'reviewed_source_head': 'f09a4f078be714b1eb026d7a4178540f7a63b494',
    'candidate_tree': '3386b6d77673eeb1888a0e01db2f62ac08d04d56',
    'owned_path_count': 9,
}
for k, v in expected.items():
    if m.get(k) != v:
        raise SystemExit(f'candidate identity mismatch: {k}={m.get(k)!r}, expected {v!r}')
print('candidate identity: PASS', json.dumps(expected, sort_keys=True))
PY
sha256sum -c MMX_CRITICAL_SHA256.txt
BEFORE=$(sha256sum site/china.html | awk '{print $1}')
META_BEFORE=$(python -c "import json; print(json.load(open('MMX_PROOF_META.json'))['baseline_china_sha256'])")
[ "$BEFORE" = "$META_BEFORE" ] || { echo "baseline mismatch: $BEFORE != $META_BEFORE" >&2; exit 61; }

python -m pip install --upgrade pip
python -m pip install --no-cache-dir \
  'pandas>=2.2' 'pyarrow>=16' 'requests>=2.31' 'jinja2>=3.1' \
  'plotly>=5.20' 'yfinance>=0.2.50' 'pyyaml>=6.0' 'lxml>=5.0' \
  'beautifulsoup4>=4.12' 'tabulate>=0.9' 'openpyxl>=3.1' \
  'scipy>=1.11' 'scikit-learn>=1.4' 'hmmlearn>=0.3' 'akshare==1.18.64'

set +e
env \
  OPENBLAS_NUM_THREADS=1 \
  OMP_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 \
  NUMEXPR_MAX_THREADS=1 \
  STOCK_LIB_WORKERS=1 \
  MALLOC_ARENA_MAX=1 \
  PYTHONUNBUFFERED=1 \
  CHINA_FAST_RENDER=1 \
  python -m scripts.build_china 2>&1 | tee /tmp/mmx-china-build.log
BUILD_RC=${PIPESTATUS[0]}
set -e
AFTER=$(sha256sum site/china.html | awk '{print $1}')
SIZE=$(wc -c < site/china.html | tr -d ' ')

[ "$BUILD_RC" = 0 ] || { echo "build command failed rc=$BUILD_RC" >&2; exit "$BUILD_RC"; }
[ "$BEFORE" != "$AFTER" ] || { echo 'site/china.html was not rewritten' >&2; exit 62; }
! grep -Eqi 'ERROR china engine failed|ERROR china page render failed|skipping china page|Traceback' /tmp/mmx-china-build.log || {
  echo 'fatal producer signature found' >&2
  grep -Eni 'ERROR china engine failed|ERROR china page render failed|skipping china page|Traceback' /tmp/mmx-china-build.log >&2 || true
  exit 63
}
grep -Eq 'wrote .*/china\.html' /tmp/mmx-china-build.log || { echo 'missing positive china.html write log' >&2; exit 64; }

cp /tmp/mmx-china-build.log site/mmx-proof-build.log
export ARCHIVE_SHA ARCHIVE_BYTES BEFORE AFTER SIZE BUILD_RC EXPECTED_MAIN EXPECTED_SOURCE EXPECTED_TREE
python - <<'PY'
import hashlib
import json
import os
from pathlib import Path
page = Path('site/china.html').read_text(errors='replace')
forbidden = ['Begin scaling exposure back', 'risk easing on its own', '风险自行回落']
required = [
    'Liquidity support unconfirmed — this does not establish a recovery.',
    '流动性支持尚未确认 — 不能据此判定市场修复。',
    'Recovery not confirmed',
]
for text in forbidden:
    if text.casefold() in page.casefold():
        raise SystemExit(f'forbidden recovery copy rendered: {text}')
missing = [text for text in required if text not in page]
if missing:
    raise SystemExit(f'missing required fail-closed copy: {missing}')
meta = json.loads(Path('MMX_PROOF_META.json').read_text())
receipt = {
    **meta,
    'transport_archive_sha256': os.environ['ARCHIVE_SHA'],
    'transport_archive_bytes': int(os.environ['ARCHIVE_BYTES']),
    'builder_rc': int(os.environ['BUILD_RC']),
    'before_china_sha256': os.environ['BEFORE'],
    'after_china_sha256': os.environ['AFTER'],
    'after_china_bytes': int(os.environ['SIZE']),
    'output_rewritten': os.environ['BEFORE'] != os.environ['AFTER'],
    'forbidden_copy_absent': True,
    'required_fail_closed_copy_present': True,
    'build_log_sha256': hashlib.sha256(Path('/tmp/mmx-china-build.log').read_bytes()).hexdigest(),
    'proof_state': 'BUILT_NOT_PROVEN_LIVE',
}
Path('site/mmx-proof-receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(receipt, indent=2, sort_keys=True))
PY

echo "MMX_RENDER_PROOF_PASS before=$BEFORE after=$AFTER bytes=$SIZE archive=$ARCHIVE_SHA"
