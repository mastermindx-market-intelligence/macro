#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CACHE=$(npm config get cache)
find_playwright_162() {
  find "$CACHE/_npx" -path '*/node_modules/@playwright/test/package.json' -type f 2>/dev/null \
    | while IFS= read -r package; do
        if grep -q '"version": "1.62.0"' "$package"; then
          printf '%s\n' "$package"
          break
        fi
      done
}
PW_PACKAGE=$(find_playwright_162 || true)
if [ -z "$PW_PACKAGE" ]; then
  npx -y @playwright/test@1.62.0 --version >/dev/null
  PW_PACKAGE=$(find_playwright_162 || true)
fi
if [ -z "$PW_PACKAGE" ]; then
  echo 'Unable to locate @playwright/test after bounded npm bootstrap.' >&2
  exit 2
fi
NODE_MODULES=${PW_PACKAGE%/@playwright/test/package.json}
NODE_PATH="$NODE_MODULES" exec node "$NODE_MODULES/@playwright/test/cli.js" \
  test --config="$HERE/playwright.config.cjs" "$@"
