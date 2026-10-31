# Fixed-source release focus: dependency and import review

Date: 2026-10-18 UTC. Reviewer: `/root/all_date_admission`, organizational research/release reviewer, actual GPT-6 Astra Pro. Assignment: parent-supplied local extracts only.

## Disposition

**Accept the bounded static characterization below. Startup effects, installed dependency realization, full source closure, and production admission remain unestablished by these extracts.** This review grants no release permission and changes no existing writer, custody, test, research, or release hold.

All four supplied dependency diffs, all 14 dynamic contexts, and all 189 import statements from `app/main.py` and `app/web.py` were read. Local standard-library parsing and hashing checked the extract identities, counts, and matching dynamic-site metadata. No inspected first-party source, catalogue, test, helper, provider, installer, Git operation, native process, or network request was executed. Only this new report was written for this task. The earlier stalled W5 query was not replayed.

The useful distinction is lexical execution timing. There are **29 import statements outside a function/class scope and 160 inside functions** in the two root files. All **14 dynamic sites are inside ten functions in nine source files**; six sites are the three stages of each of two file-loading sequences. A function body is deferred until invocation. The snippets do not establish whether its callers invoke it during module initialization, application startup, a request, or a scheduled job. Empty enclosing-scope metadata also omits conditional guards and is not proof of unconditional execution. These are import-site counts, including two `__future__` directives, rather than counts of realized module loads or effects.

## Evidence identities

The following hashes were recomputed from the local input files. Nested source-file hashes below are identities supplied by the extractor; full source bytes were not independently reacquired here.

| Local input | Bytes | SHA256 |
|---|---:|---|
| `release_review/full_release_static_extract_20261018.json` | 15,620 | `aefa7f67580e518b86a5c5b9022ab7425a9d20c7a153a76921dcf935a2e8566f` |
| `release_review/full_release_fixed_source_focus_20261018.json` | 76,602 | `ede83fc78f739731d6b42466457274e3c9b030860a1175ffe484c329e07af902` |

The focus extract binds source catalogue SHA256 `4c5e5f9046016ae917f4a311905aa09b98605384b27aaa02155699d6021d05bb`. That is a supplied identity for its parent catalogue, not the SHA256 of the 15,620-byte reduced extract. Both extracts bind candidate **`797c760f3e18eb6993579f56986103de9d9fdcb4`** against **`732cf7be88e7159b4995a8885fbd381cd1484e3e`**, the earlier observed live source. This is not a fresh observation of live deployment.

| Git object | Candidate | Earlier comparison |
|---|---|---|
| Parent | `d65414e89ad3b930d84d614196a91d3cce8ba589` | `64e9016c90a561a2017d2f2fd2ff75368df7397a` |
| Tree | `bf349e67f62c768babed1b661cf4f1424aae5380` | `2791b1299a2a31aa2204377545282adcffa1f761` |
| Commit bytes SHA256 | `6735da7987af3c2e33a72563a6f073cebb398317194c7578f22617523ad10ab4` | `08430391d246fcf810cb5e6598d95fe3a4cffafd45e8b3cae5972975d8ff0acc` |

The supplied catalogue records 1,546 changed tracked paths, 920 changed Python paths, 556 reached modules, 555 reached source paths, and 180 reached changed paths. Its parser-error list is empty. Those counts describe the conservative catalogue, not all executable effects or evidence that unreached files are inert. All 14 focus site records exactly match the reduced catalogue's path, line, column, loader, literal-name, reason, and source-module records.

## Dependency changes: exactly what the diffs establish

| Path | Actual supplied diff | Practical interpretation |
|---|---|---|
| `pyproject.toml` | Adds a comment and `uvicorn[standard]==0.52.4` to the dependency list. | An explicit manifest pin is added. No installed-package, wheel compatibility, server invocation, or production environment receipt is present in these inputs. |
| `requirements/gate-linux-x86_64-py312.lock` | Changes header comments only. Updates source-manifest hash and generation account; recorded generator interpreter changes from CPython 3.12.14 to 3.12.3. | The supplied diff contains no changed package/version/hash lines. The changed file digest reflects documentation bytes; it does not demonstrate dependency churn or a realized runtime change. |
| `requirements/gate-macos-arm64-py312.lock` | Changes header comments only. Updates source-manifest hash and generation account; recorded interpreter remains CPython 3.12.13. | Again, no changed package/version/hash lines appear in the supplied diff. The claims about regeneration and isolation are comments, not independent execution receipts in this review. |
| `requirements/research-producer-macos-arm64-py312.lock` | New 14-line file: two comments and 12 exact, hashed dependency pins. | Its own header explicitly identifies a Mac arm64 Python 3.12 producer candidate and states that the offline wheel set is not installed in the recurring runner. It neither proves runner activation nor realizes the Linux VPS environment. |

The new producer file pins `boto3`, `botocore`, `certifi`, `charset-normalizer`, `idna`, `jmespath`, `python-dateutil`, `PyYAML`, `requests`, `s3transfer`, `six`, and `urllib3`. Exact versions and distribution hashes remain in the supplied full diff. No dependency install, security advisory lookup, or compatibility test was part of this assignment.

| Path | Before bytes / SHA256 | After bytes / SHA256 |
|---|---|---|
| `pyproject.toml` | 2,504 / `f26dbfe12683bdd7eeb3cd15e9fbfe114f76c04e0b71bd650047001f22f58a2c` | 2,615 / `aa93b0eddf900fc48791595f9966b3cfc9fad50883c8f5149b961a615051b250` |
| Linux gate lock | 137,921 / `0d9f246c8728712aa87c763ac24f25161920db53d969fc497af2a4950e034c67` | 137,393 / `1097e341587f85d0c0bda526889678f7aec1a05bdd3fdad82c16e3653e701d89` |
| macOS gate lock | 137,560 / `6d2913d65b89ceeb78a893204910cc7e83e17a839a582740526a1cf818eb5940` | 137,392 / `e4effedf53eab59a93470a83b83aa77175a4ce79dc95dbd315bb29dab4e1543d` |
| New producer lock | Absent | 1,331 / `0c43d2132a6afaba75e5b5720c234d1b565679b650d7c04c024a1a12d711206a` |

## Root imports: startup candidates and deferred surfaces

| Source | All import statements | Outside function/class scope | Function-body statements |
|---|---:|---:|---:|
| `app/main.py` | 59 | 15 | 44 |
| `app/web.py` | 130 | 14 | 116 |
| Total | **189** | **29** | **160** |

Seven module-lexical statements import first-party code. In `app/main.py`, they import `app.deps` at line 16, `brain.cli_bridge` at 92, `app.web` at 100, `app.pfolio` at 101, `app.response_cache` at 117, and `app.auth` at 125. In `app/web.py`, `portfolio.registry` is imported at line 20. If these statements execute during root-module import, the imported modules' own top-level code can execute. Those complete module bodies and their guards are absent from these inputs. Imports of `subprocess`, `ThreadPoolExecutor`, or `threading` alone do not establish a subprocess, executor, or thread being started.

`app/main.py` has one function-body import in `_startup_flags` and nine in `_start_scheduler`, counting the nested `_scheduler_watchdog` import within the latter. The latter inventory includes `app.auth`, `app.scheduler`, `control_plane.run_events`, `control_plane.governance`, logging, threading, and nested time support. Three more imports are in `watchdog_check_once`. These names identify the highest-value startup slice to resolve; the inventory omits lifecycle decorators/registration, call order, serve-only or governance gates, scheduler construction, and job activation. The claim “function-local, therefore excluded from startup” is not supported.

The remaining function-local imports expose distinct deferred capabilities. `app/main.py` contains daily/book-run, chat, runtime-health, and archive checks. `app/web.py` contains price/provenance helpers, portfolio and self-directed functions, research and model summaries, macro/desk functions, scheduler health, and provenance functions. Examples include Yahoo/Terminal price modules in `_dash_mark_usd`, `_live_prices`, `_book_marks`, and `api_live_marks`; Polygon in `_company_meta` and `api_self_directed_search`; and `brain.mastermind_ai` in functions named for settings, directives, nudges, and runs. The inventory establishes imports in those bodies, not what the callees do, whether data is fetched, whether state is written, or whether an endpoint is reachable or authorized.

Neither root file appears in the supplied 180-path reached-changed list. Their positive downstream import edges still matter: the list includes changed worker-adapter, executive incident, provider-readiness, and acceptance code. This review has not examined the bodies of all 180 changed paths.

## All dynamic contexts

The site numbering below follows the two extracts. Every listed call is function-local. Known target names recoverable from the nearby text improve the catalogue, but do not prove target-module effects or runtime reachability.

| Sites and source | Visible binding and action | Bounded conclusion / exact remaining gap |
|---|---|---|
| **1** — `app/web.py:358`, `_brain_book_module` | Looks up a module in `_BRAIN_BOOK_MODULES` and imports it when nonempty. The visible mapping names `bot.autonomous`, `bot.heavyweight`, `bot.china`, `bot.hk`, and `bot.etf`. | Five initial target names are recoverable; this helper imports a selected module without visibly invoking its run function. Callers, any later mapping mutation, and the imported modules' top-level effects are not supplied. The comment that mapping grants no run authority is not an execution gate by itself. |
| **2** — `brain/improvement_agenda.py:590`, `_load_matured_experiments` | Tries `brain.experiment_registry`, `portfolio.experiments`, then `brain.experiments`; retrieves `matured` and calls it with `asof`. Exceptions fall through; absent results return `[]`. | Three target names and the function invocation are visible. Callee effects and callers are missing. Empty output can reflect swallowed exceptions as well as absence; it is not a clean runtime-health proof. |
| **3** — same file, line **856**, `_from_model_drift` | Iterates over `student` and `distill`, imports the corresponding `brain` modules, and calls `summary()`. Exceptions skip the model. | Two targets are recoverable. This is a summary invocation, not a visible training call. Summary implementations, callers, and function lines 866–880 are absent; read-only behavior cannot be assumed from the name or docstring. |
| **4** — `bot/settle.py:1130`, `_republish` | Imports `bot.{pid}` and calls `republish(asof, submission=..., settlement_prices=...)` when present. Exceptions produce an error object. | A publication-related call is explicit. The accepted `pid` domain, caller validation, and republisher effects are not included. The helper's name and docstring do not establish when it runs. |
| **5** — `bot/overnight.py:121`, `watch` | Visible preceding code calls `overnight.tape(force=force)`. Unless forced, it returns for a nonmaterial tape; otherwise it resolves `_RUNNERS[pid]`, imports the module, and invokes the function with an overnight directive. | The excerpt includes a potential tape acquisition and runner invocation path, not just import resolution. It does not prove that either occurred. `_RUNNERS`, earlier `watch` lines 68–111, callers, and runtime scheduling/gates are absent. `force` bypasses the visible materiality condition. |
| **6** — `control_plane/worker_adapter.py:103`, `adapter_implementation` | Obtains a descriptor, splits its implementation string, imports the module, retrieves an attribute, and checks that it is a class. Import/attribute failures become `AdapterBindingError`. | The excerpt resolves a class; no instance construction is visible. The descriptor binding, class/module top-level effects, callers, and function lines 113–119 are missing. “Reviewed descriptor” in the docstring is not independent custody evidence. |
| **7, 8, 9** — `ops/executive_os/git_handoff_preflight.py:61,64,66`, `_acceptance_module` | On a `sys.modules['executive_acceptance']` cache miss, constructs a spec for sibling `acceptance.py`, constructs a module, stores it in `sys.modules`, and executes it with `exec_module`. | These are three stages of one file load, not three independent target modules. On the miss path, interpreter module state is changed and the sibling's top-level code executes. On a hit, the cached object is returned. Full acceptance top-level code and helper callers are not supplied. |
| **10** — `control_plane/chairman_control_room.py:130`, `_optional_control_plane_module` | Checks specs for `name` and `requires`, returns `None` when a dependency spec is unavailable, then imports `control_plane.{name}`. | Actual target/call-site bindings and function lines 99–120 are absent. The visible check precedes an actual import and is not a side-effect sandbox. The static-dependency test described in a nearby comment was not examined or run here. |
| **11, 12, 13** — `ops/executive_os/acceptance.py:317,320,321`, `_provider_readiness_module` | Constructs a spec for `release / ops / executive_os / provider_readiness.py`, creates a module, and calls `exec_module`. | Three stages of one release-rooted file load. The selected file's top-level code executes if this helper runs. The caller's `release` binding, full `provider_readiness.py` top-level code, and call chain are missing. A source hash elsewhere in the catalogue does not itself bind this runtime path. |
| **14** — `control_plane/executive_incident_composition.py:60`, `_resolve_production_forward_host_guard` | The local variable fixes the target to `ops.executive_os.provider_incident_forward`. Only `ModuleNotFoundError` naming that exact optional module returns `None`; internal missing-import errors are re-raised. | This narrow absence-versus-broken-import distinction is present in source. The context ends at line 69 on `if forward.PRODUCTION_FORWARD_RECOVERY_POLICY is None:`. Its body, remaining lines 70–77, full optional-module top-level code, constructor/call sequence, and startup callers are absent. No conclusion about activated policy or constructor effects follows. |

The supplied reached-changed list includes the site-owning files `control_plane/worker_adapter.py`, `control_plane/executive_incident_composition.py`, and `ops/executive_os/acceptance.py`, plus dynamic targets `ops/executive_os/provider_incident_forward.py` and `ops/executive_os/provider_readiness.py`. Other dynamic site owners are not in that list. An unchanged loader can still load a changed target.

## Concrete unresolved evidence

1. **Startup path:** root-module executable statements, lifecycle registration, `_startup_flags` and `_start_scheduler` bodies, their effective guards, and `app.scheduler` startup callees. These are needed to distinguish a deferred callable from an actual startup effect. The present imports identify this gap precisely but do not close it.
2. **Dynamic call and target binding:** the missing caller/descriptor/runner mappings identified in the table, complete file-loader target top-level code, and the tail of the production-forward guard. The visible finite target names can be retained as positive edges; missing targets or callees must stay missing.
3. **Environment realization:** the actual release launch command and dependency installation/activation evidence for its interpreter/platform. Neither a manifest pin nor comment-only lock changes establish the installed environment. The producer candidate's own noninstallation statement remains part of the evidence.

These are gaps in the supplied evidence, not a new approval procedure or a demand to execute every function. Parent retains the choice of the smallest next read or existing receipt that closes a relevant gap. Static catalogue admission and companion-test review remain narrower than full backend-to-user or production proof. Existing failed checks and prior limitations are preserved.

## Nested source identities used

| Candidate source | Bytes | Supplied SHA256 |
|---|---:|---|
| `app/main.py` | 34,012 | `7fcdcbb9e9affeede32caa993df796c31fdf0de56ea7b062f519dfdf970c71f8` |
| `app/web.py` | 167,964 | `721b792941160c962adf99c28febd048163be5c39eb8a5c8d67786c93fdc8a2d` |
| `brain/improvement_agenda.py` | 80,626 | `22f9e0d264f31d73c7fed92b78abaf307dce9911ff57936e9741f09616e81c87` |
| `bot/settle.py` | 49,282 | `3aef6a0d8f4501a110bb4af240e9cc12988a11754128d50d3ae105c11cab7915` |
| `bot/overnight.py` | 7,427 | `6a8252980c483880561352334fd9706569f3d40d709fe44a97fc6356d68169a2` |
| `control_plane/worker_adapter.py` | 10,074 | `657c05c3c273ae886aa82c02f31173c0d948885577840724974bbc4c4775cf74` |
| `ops/executive_os/git_handoff_preflight.py` | 35,301 | `c22fd816af7bec7a0d8e086ea2645adc05421e44a188c36e542055799b720130` |
| `control_plane/chairman_control_room.py` | 102,477 | `ff3377e2ddae26f1cd84e2f3d8ce72102dae4ba7096804af2e0ed81e2d6506c7` |
| `ops/executive_os/acceptance.py` | 138,200 | `54cbcfa7379efec31ec909256603ef04e9658b0d9cfb2b584470b4e6bcf8de35` |
| `control_plane/executive_incident_composition.py` | 7,936 | `9a896d764c0f056df88db6513bb7335f3464ab05e426705a42935690727f3fe8` |

Evidence references are the two exact local inputs above, specifically `dependencies`, `dynamic_contexts`, `root_imports`, `dynamics`, `reached_changed_paths`, and `source`. No broader source or runtime claim is made.
