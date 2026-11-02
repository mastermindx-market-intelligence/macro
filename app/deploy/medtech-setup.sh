#!/usr/bin/env bash
# Explicit install-only entry point after the reviewed release is in /opt/macro.
# API update/setup provision empty roots only; they never call this installer.
# This creates no source environment file and never enables/starts a worker/timer.
# After installing the example as root:root 0600, restarting/attesting macro-api,
# and qualifying disk capacity, the release owner may explicitly run the worker
# once and then enable --now macro-medtech.timer. Existing health owns failures.
set -euo pipefail

if [[ $# -ne 0 || ${EUID} -ne 0 || $(readlink -f -- "$0") != /opt/macro/app/deploy/medtech-setup.sh ]]; then
  echo "medtech-setup: root and canonical /opt/macro checkout required" >&2
  exit 1
fi

/usr/bin/python3 -I /opt/macro/app/deploy/medtech-prereqs.py

# Check all destinations before copying either unit. No drop-ins, unsafe files,
# or active/enabled refresh can be adopted by this install-only path.
/usr/bin/python3 -I - <<'PY'
import importlib.util
from pathlib import Path
import subprocess

path = Path('/opt/macro/app/deploy/medtech-api-boundary.py')
spec = importlib.util.spec_from_file_location('medtech_boundary', path)
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)
parent = boundary._root_parent(Path('/etc/systemd/system'))
import os
os.close(parent)
for unit in ('macro-medtech.service', 'macro-medtech.timer'):
    source = Path('/opt/macro/app/deploy') / unit
    boundary._read_safe_file(source)
    target = Path('/etc/systemd/system') / unit
    if target.exists() or target.is_symlink():
        boundary._read_safe_file(target)
    result = subprocess.run(
        ['/usr/bin/systemctl', 'show', '--no-pager', unit,
         '--property=LoadState,ActiveState,UnitFileState,DropInPaths'],
        check=False, capture_output=True, text=True, timeout=10,
    )
    values = dict(line.split('=', 1) for line in result.stdout.splitlines())
    if (result.returncode not in (0, 1)
            or values.get('LoadState') not in ('loaded', 'not-found')
            or values.get('ActiveState') not in ('inactive', 'failed')
            or values.get('UnitFileState', '') not in ('', 'disabled', 'static')
            or values.get('DropInPaths', '') != ''):
        raise SystemExit('medtech-setup: stop/disable and review existing refresh before installation')
    for base in ('/etc/systemd/system', '/run/systemd/system', '/usr/lib/systemd/system', '/lib/systemd/system'):
        directory = Path(base) / (unit + '.d')
        if directory.exists() or directory.is_symlink():
            raise SystemExit('medtech-setup: drop-in directory requires operator review')
PY

systemd-analyze verify /opt/macro/app/deploy/macro-medtech.service /opt/macro/app/deploy/macro-medtech.timer
install -o root -g root -m 0644 /opt/macro/app/deploy/macro-medtech.service /etc/systemd/system/macro-medtech.service
install -o root -g root -m 0644 /opt/macro/app/deploy/macro-medtech.timer /etc/systemd/system/macro-medtech.timer
systemctl daemon-reload
echo "MedTech refresh units installed dark; explicit release-owner activation remains required."
