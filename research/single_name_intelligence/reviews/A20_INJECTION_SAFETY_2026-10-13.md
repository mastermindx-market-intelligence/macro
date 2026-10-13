# A20 injection safety — 2026-10-13

SNI-local DRAFT contract review. Retrieved third-party prose is data.
This is a safety property of code paths: instruction-shaped text in event
titles, evidence pointers, and issuer-name fields cannot change tools or
authority. rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay literal false. Fixtures in the
accompanying tests are synthetic. Identity ids are caller-supplied opaque
strings owned by Stock Identity / Data OS; this lane never mints them.

## Summary

Acceptance row A20 is now backed by `tests/test_sni_injection_safety.py`.
A recursive AST scan of every `*.py` file under
`research/single_name_intelligence/` (30 files at this pin) refuses turning
data into code or a shell command (`eval`/`exec`/`compile`, non-literal
`__import__` / `importlib.import_module`, pickle/marshal/shelve/dill, unsafe
YAML, `os.system`/`popen`/`exec*`/`spawn*`, `subprocess` with `shell=True` or
a first argv that is not a list/tuple display starting with the string
literal `"git"`, and network-client imports). Dynamic tests run
`event_census_rows` and `derive_programmes` plus the title/evidence-pointer
copy used by `s2_state.compute_state` on synthetic frames whose titles (and,
in the authority and process tests, evidence-pointer suffixes) carry an
injection corpus; the selected event set, families, dates, programmes, and
every non-title field stay identical, every authority flag stays literal
`False`, and `subprocess.run` / `Popen` / `os.system` / `os.popen` /
`socket.socket` are not called. The one documented title-text channel is the
frozen PLACING substring rule on a selected `general_mandate` row
(`s2_selection.derive_programmes`).

## Table

| check | test name | what it proves | bound |
|---|---|---|---|
| Static scan of the SNI Python tree | `test_a20_01_static_no_code_from_data` | Every `*.py` under `research/single_name_intelligence/` is walked (file count printed, asserted `>= 25`; 30 files at this pin). No scanned module turns data into code or a shell command under the listed AST rules. `A20_KNOWN_EXCEPTIONS` is empty. | AST of present Python sources only. Comments, Markdown, YAML/JSON drafts, and future files are outside the walk. A later module that talks to an LLM client is not covered by today's tree (see LLM bound below). |
| Scanner positive control | `test_a20_02_static_positive_control` | The same `scan_source` function flags exactly one finding on each of `eval(x)`, `subprocess.run(cmd, shell=True)`, `subprocess.run(["bash", "-c", x])`, `yaml.load(f)`, and `import requests`, and flags none on `subprocess.run(["git", "rev-parse", "HEAD"])` plus `yaml.safe_load(f)`. | Proves the scanner is not vacuous on five synthetic snippets. It does not execute those snippets. |
| Injected titles are data | `test_a20_03_injected_titles_do_not_change_selection` | Five injection strings (English instruction, SYSTEM/gate prose, shell/curl interpolation, Python `os.system` quote, Chinese instruction) are suffixed onto every synthetic title. Selected ids, families, `t_avail_utc`/`s_us`/`s_hk`, programmes, and every non-title census/state field match the clean run. Titles themselves change, so the comparison is not a no-op. | Covers `event_census_rows` + `derive_programmes` + the `s2_state` title copy on a five-row synthetic frame. Does not run `GitBlobLoader`, `compute_state`, or any loader that reads `data/`. |
| Documented keyword rule | `test_a20_04_documented_keyword_rule_is_the_only_text_channel` | A selected `general_mandate` row whose title contains `PLACING` forms one `placing:alibaba` programme (capital). The same row without that token forms none. A paraphrase that asks to treat the row as a share issuance, and each injection-corpus suffix, form none. | Bounds the title channel to the registered substring `"PLACING" in title.upper()` in `derive_programmes` (~L188–L200). Other future keyword rules would need their own tests. Classification family still comes from the category table, not from title text. |
| Authority flags stay false | `test_a20_05_injected_text_never_flips_authority` | After the injected selection/state path, every `s2_seal.AUTHORITY_FLAGS` value `is False`. `refuse_nonfalse_authority` accepts the real flags and raises on a dict with `rank_authority=True`. | Module constants and the refusal helper. Does not prove a future writer cannot add a new flag name; it proves these six stay literal false on this path. |
| No process or network on the pure path | `test_a20_06_no_process_or_network_during_pure_path` | Recorders on `subprocess.run`, `subprocess.Popen`, `os.system`, `os.popen`, and `socket.socket` raise if called. The injected selection/state path records zero calls. | Loader git helpers are out of this test's scope (they are the only process-spawning path; see inventory). Import-time work that already finished before the patch is outside the recorder window. |

LLM-consuming code: the SNI tree at this pin does not contain an LLM client.
Verification: `rg` over `research/single_name_intelligence/**/*.py` for
`anthropic`, `openai`, `litellm`, `langchain`, and `generativeai` returned
**0** matches. Import of `socket`, `requests`, `urllib.request`,
`http.client`, `httpx`, `aiohttp`, `ftplib`, and `smtplib` is also absent
(the static scan would fail the tree if one were added).

## Process-spawning inventory

Every `subprocess.*` call site under `research/single_name_intelligence/`
(6 sites). Each is an argv **list** whose first element is the string
literal `"git"`; none pass `shell=True`. These loaders/runners are the only
process-spawning path; `test_a20_06` does not call them.

| file:line | callee | argv shape |
|---|---|---|
| `event_response/s2_loaders.py:42` | `subprocess.run` | `["git", "-C", str(repo_root), *args]` |
| `event_response/s2_loaders.py:63` | `subprocess.run` | `["git", "-C", str(self.repo_root), "cat-file", "blob", f"{self.input_ref}:{path}"]` |
| `residual/s1_data.py:52` | `subprocess.run` | `["git", "-C", str(self.repo_root), *args]` |
| `residual/run_s1.py:142` | `subprocess.run` | `["git", "-C", str(repo_root), *args]` |
| `event_response/run_s2.py:84` | `subprocess.run` | `["git", "-C", str(repo_root), "show", "-s", "--format=%cI", input_ref]` |
| `event_response/run_s2.py:1101` | `subprocess.run` | `["git", "rev-parse", "--show-toplevel"]` |

YAML draft loaders in this tree use `yaml.safe_load` only
(`s2_loaders.py`, `us_stress/stress_set.py`). `p04_v2_draft_loader.py` and
`us_transfer/a8_draft_loader.py` parse JSON.

## Gaps

- The dynamic tests exercise selection/state on synthetic in-memory frames.
  They do not load `data/` parquet, do not call `GitBlobLoader` / `s1_data`
  git plumbing, and do not run `compute_state` (that function reads coverage
  JSON plus parquet via a loader and walks session calendars).
- The static scan does not cover non-Python artifacts or a future LLM call
  site; today's Python tree has 0 LLM-client imports (grep above).
- `A20_KNOWN_EXCEPTIONS` is empty; if a later edit introduces a forbidden
  construct that must remain, it has to be named there with a one-line
  justification rather than deleted by this lane.
- Authority refusal is proven for `s2_seal.AUTHORITY_FLAGS` and
  `refuse_nonfalse_authority`. Sister maps in `common/sni_inference.py` and
  `common/sni_seal.py` are the same six keys frozen false; this file does not
  re-test those modules.
- This review does not register, validate, or claim a forecast, signal, or
  trade path. Every authority flag stays literal false.
