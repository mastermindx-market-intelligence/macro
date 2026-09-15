#!/usr/bin/env bash
set -Eeuo pipefail
exec python -m http.server "${PORT:-10000}" --bind 0.0.0.0 --directory candidate/site
