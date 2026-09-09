---
key: POLICY-WATCH-CURRENT-R1-CACHE-ITEMS-JINJA
claim: >
  In Jinja2, dict attribute access on a key named `items` resolves to
  dict.items (the method), so Policy Watch current headlines must be read as
  news['items'] / last_good['items'], never news.items.
falsifier: >
  python3 -c "from jinja2 import Environment; print(Environment().from_string('{% set d={\"items\":[1]} %}{{ d.items }}').render())" yielding a list rather than a method object; or a render of templates/_policy_watch_current.html.j2 with real current.headlines.items raising TypeError on [:4].
so_what: >
  Prefer non-method key names for display lists (e.g. headline_rows), or always
  use bracket access for the key `items`. Do not treat a green unit suite as
  proof of template render until at least one Jinja render path exercises the
  include.
kind: landmine
verified_at: 2026-09-09
verified_by: >
  tests/test_policy_watch_ui.py rendered_page failures at
  templates/_policy_watch_current.html.j2:46
  TypeError: 'builtin_function_or_method' object is not subscriptable;
  fixed by news['items'] / last_good['items'].
scope: [macro]
confidence: verified
---

## Detail

Observed during Policy Watch R1 recovery: `build_current` unit tests were green
while every real-template render failed because `news.items` bound the dict
method. Namespace attribute `items` had the same collision class.
---
