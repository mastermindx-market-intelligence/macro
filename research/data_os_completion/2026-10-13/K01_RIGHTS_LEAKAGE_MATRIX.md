# K01 — Rights and leakage test matrix for the Data OS read surfaces

**Lane:** O2-K01 (package K01, programme DATA-OS-COMPLETION). **Status:** complete at base
`0939fbfc9ea767c0d297a746d16c8a9930396391` (`origin/main` fetched 2026-10-13; ORCH-2's judge
base `f2a21e8d7f28` is an ancestor of it). **Frozen decisions:** `D00.D1`–`D00.D6`, `D00.01`
(`research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md`); the rights split is
`D00.D6` lines 128–130.
**New discriminators:** `tests/test_dataos_rights_matrix.py` (22 cases, all green).
**Evidence class:** synthetic + static (tmp_path fixtures, sentinel strings, real public
functions, no network, no `data/` reads).

## Method and sentinel discipline

Surfaces × principal state {granted, ungranted, revoked/expired} × channel {value, path,
artifact location, cached result, error text, evidence metadata, request-selected
root/credential/grant/entitlement, rights equivalence}. Principal identity is **not** a
request field on any surface (by design: `web_api.py:4`, `scripts/data_workspace.py:8-10`),
so a principal row whose enforcement lives outside the repo says so and names the transport;
no principal concept is invented in tests.

Every negative discriminator asserts the **absence** of the sentinels, of the host path and
of any `://` URL in the **full serialized response** (`json.dumps` of what the CLI prints),
not merely `status == "error"`; positive controls in the same file prove the sentinels DO
reach a granted read, so an always-refusing surface cannot pass. Sentinels:
`SENTINEL_PRIVATE_VALUE_9f3` (bound-root content), `SENTINEL_OUTSIDE_ROOT_2c8` (outside all
roots), `SENTINEL_REBOUND_SOURCE_7d1` (post-replacement content),
`SENTINEL_ENTITLEMENT_4b7` (request-injected value).

Test-path legend (each maps to `path::test_name` in this tree):

| abbrev | path |
|---|---|
| MX | `tests/test_dataos_rights_matrix.py` |
| WS | `tests/test_dataos_web_workspace.py` |
| API | `tests/test_dataos_web_api.py` |
| RD | `tests/test_dataos_web_readers.py` |
| LAB | `tests/test_dataos_web_lab.py` |
| LW | `tests/test_dataos_web_lab_worker.py` |

## Measured allow-lists (K01.03 — real, cited)

- Request envelope: `action` must be a str; whole request ≤ 16 384 bytes — `web_api.py:37-42`
  (`validate_request`), `MAX_REQUEST_BYTES` `web_api.py:21`.
- Per-action field allow-lists (`_fields`, `web_api.py:25-28`, error
  `INVALID_REQUEST_FIELDS`): search `{query, limit}` (`web_api.py:206-207`); browse
  `{root, path, offset, limit, expected_directory_version}`, `root` required
  (`web_api.py:208-210`); describe `{ref}` (`web_api.py:211-212`); **read**
  `{ref, columns, time_column, start, end, equals, offset, limit, expected_version}`, `ref`
  required (`web_api.py:213-216`); lab_signals `{query, limit}` (`web_api.py:217-219`);
  lab_plan `{signal_id, refs, horizon_bars, cost_bps, n_configs_searched}`
  (`web_api.py:220-223`); capabilities `{}` (`web_api.py:227`); unknown action
  `UNKNOWN_ACTION` (`web_api.py:240`).
- Lab execution outer fields `{request, time_column, column_map, start, end,
  expected_versions, bar_frequency}` (`web_api.py:46-47`) and inner request fields
  `{signal_id, refs, horizon_bars, cost_bps, n_configs_searched}` (`web_api.py:53`);
  column map closed to OHLCV roles (`web_api.py:58-66`); versions must be `statv1:`-sha'd
  and subset of refs (`web_api.py:67-71`).
- `web_lab.execute` request fields: `_REQUEST_FIELDS` `web_lab.py:33-35`, enforced
  `web_lab.py:280-284`.
- Host binding config: unknown fields refused (`web_workspace.py:353-354`), root rows closed
  to `{alias, path, evidence_kind, note, required_mount}` (`web_workspace.py:359-361`),
  alias charset `[a-z0-9_-]` ≤ 64 (`web_workspace.py:50-52`), config ≤ 64 KiB
  (`web_workspace.py:348-349`).
- A body key named `config`, `config_path`, `credential`, `token`, `grant`, `entitlement`,
  `root_path` or `source_url` is **refused, not ignored** on every action — measured by
  `MX::test_credential_shaped_request_keys_are_refused_not_ignored` (read) and
  `MX::test_lab_run_rejects_credential_shaped_outer_key_before_artifacts` (lab outer
  request, refused before any artifact exists).

## The matrix

Cell values: enforcement point → discriminating test; `GAP`; or `N/A` with the structural
reason. "transport" = the Studio Direct / authenticated MCP transport that fronts
`scripts/data_workspace.py` (declared at `web_api.py:239` capabilities
`access="host bindings and the existing Studio account-scoped transport"` and
`scripts/data_workspace.py:8-10`).

### S1 `lib/dataos/web_workspace.py` (DataWorkspace: search/browse/describe/read)

| channel | granted | ungranted | revoked/expired |
|---|---|---|---|
| value | permitted class served — `read` `web_workspace.py:320-342` → WS::test_read_filters_actual_rows_preserves_nulls_and_reproducible_query_receipt; MX::test_allowed_read_returns_sentinel_and_evidence_stays_alias_relative | no read occurs: alias miss refuses before any open — `_root` `web_workspace.py:113-118` → WS::test_unbound_root_and_malformed_ref_have_closed_errors | mid-flight root replacement discards the read — `ROOT_BINDING_CHANGED` `web_workspace.py:150-152` → WS::test_root_inode_replacement_is_detected; no stale value after re-source → MX::test_rebound_source_refuses_pinned_old_version_without_stale_value |
| path | `source` block carries alias-relative fields only; root's real location never serialized — `web_workspace.py:182-192` → WS::test_describe_reports_real_footer_clocks_and_unqualified_provenance (`str(root) not in json.dumps`); MX::test_allowed_read_returns_sentinel_and_evidence_stays_alias_relative | refused refs never echoed — `_parts` `web_workspace.py:79-90` + code-only error `web_workspace.py:34-38` → WS::test_traversal_hidden_and_sensitive_paths_are_refused; symlink escape `web_workspace.py:143-148` → WS::test_leaf_and_ancestor_child_symlinks_cannot_escape_root, WS::test_symlink_as_configured_root_is_refused; MX::test_path_escape_refusal_returns_closed_response (full CLI response closed) | same closed codes; volume-off refusal precedes any path work — `web_workspace.py:140-141` → MX::test_unmounted_required_volume_refuses_before_any_read |
| artifact location | N/A — the workspace exposes no run/artifact concept; bounded response builder only `web_workspace.py:120-136`; absence asserted in MX::test_allowed_read_returns_sentinel_and_evidence_stays_alias_relative | N/A — same; absence asserted in MX::test_path_escape_refusal_returns_closed_response | N/A — same |
| cached result | N/A — request-local service, no store ("Request-local observation service", `web_workspace.py:100`; no instance state besides roots/registry `web_workspace.py:104-111`) | N/A — same | no stale serve after re-source: old pin refused, fresh content only via a fresh read — MX::test_rebound_source_refuses_pinned_old_version_without_stale_value; in-flight change refused `SOURCE_CHANGED`/`SOURCE_VERSION_MISMATCH` `web_workspace.py:180-181,196-199` → WS::test_expected_source_version_refuses_changed_source, WS::test_open_source_change_is_detected_before_return |
| error text | `WorkspaceError` carries the code only — `web_workspace.py:34-38` → WS::test_traversal_hidden_and_sensitive_paths_are_refused (`str(root)` absent); MX::test_path_escape_refusal_returns_closed_response | same enforcement → WS::test_unbound_root_and_malformed_ref_have_closed_errors; MX::test_request_cannot_select_a_root_by_path | same enforcement → MX::test_unmounted_required_volume_refuses_before_any_read |
| evidence metadata | relative_path/evidence_kind/file_version only; mtime explicitly labelled not-freshness; `registry_admission=NOT_INFERRED_FROM_FILE_PRESENCE` `web_workspace.py:182-192` → WS::test_describe_reports_real_footer_clocks_and_unqualified_provenance; search/browse carry names+codes, never values — MX::test_discovery_surfaces_return_names_and_codes_never_values_or_paths | root states degrade to codes (`SOURCE_NOT_FOUND`) `web_workspace.py:266-267` → WS::test_search_distinguishes_contract_declarations_physical_files_and_missing_roots; sensitive-named entries silently dropped from listings `web_workspace.py:219-223` → WS::test_hidden_entries_count_toward_scan_budget_without_being_returned | mount-off state is a code, no metadata — MX::test_unmounted_required_volume_refuses_before_any_read |
| request-selected root/credential/grant | grant = the host-owned binding allowlist itself — `load_workspace_config` `web_workspace.py:345-371` → WS::test_host_config_loads_only_explicit_roots_and_relative_registry | alias-only selection; a path-shaped alias is an alias miss — `web_workspace.py:113-118` → MX::test_request_cannot_select_a_root_by_path; config fields closed → WS::test_host_config_rejects_unknown_fields_and_unsafe_bindings | binding is fixed at construction; replacement detected — `web_workspace.py:150-152` → WS::test_root_inode_replacement_is_detected |
| rights equivalence | file presence ≠ admission: `production_qualification=NOT_ESTABLISHED_BY_THIS_ADAPTER` `web_workspace.py:127`, `registry_admission` `web_workspace.py:191,265` → WS::test_describe_reports_real_footer_clocks_and_unqualified_provenance, WS::test_search_distinguishes_contract_declarations_physical_files_and_missing_roots; K01.02 full split → GAP deferred to R00 (see GAPS) | same | same |

### S2 `lib/dataos/web_api.py` (validate_request, `_fields`, dispatch, run_lab)

| channel | granted | ungranted | revoked/expired |
|---|---|---|---|
| value | bounded workspace/worker results only; worker result admitted only as a dict ≤ `MAX_RESPONSE_BYTES` — `web_api.py:181-191` → API::test_zero_exit_requires_valid_result_before_success; end-to-end MX::test_allowed_read_returns_sentinel_and_evidence_stays_alias_relative | unknown action/fields refused before any workspace call — `web_api.py:25-28,240` → API::test_dispatch_rejects_unknown_or_missing_action_fields | GAP (owner: transport) |
| path | run status carries run_id + relative artifact names only — `web_api.py:169-180` → API::test_process_contract_scrubs_environment_bounds_wait_and_preserves_artifact_result; launch-failure host text absent — API::test_launch_failure_retains_reviewable_run_and_seals_status; worker env scrubbed (no env inheritance) `web_api.py:132-138` → API::test_process_contract_scrubs_environment_bounds_wait_and_preserves_artifact_result | same refusals; invalid types never escape as Python errors — API::test_invalid_field_types_do_not_escape_as_python_type_errors | GAP (owner: transport) |
| artifact location | test-root binding strict: absolute, mount-contained, no dot parts — `_host_test_root` `web_api.py:78-101` → API::test_test_workspace_binding_is_strict_before_any_process; symlink component refused `web_api.py:96-97` → MX::test_test_workspace_symlink_component_is_refused; `artifact_root_alias` is an alias, not a path `web_api.py:196-197` | no artifacts created on refusal — `web_api.py:115-119` → API::test_dispatch_rejects_unknown_or_missing_action_fields (`not case.runs.exists()`), API::test_lab_budget_and_arbitrary_calculation_fields_fail_before_run_artifacts | GAP (owner: transport) |
| cached result | N/A — dispatch is a stateless single request→response (`web_api.py:202-240`); per-request freshness through dispatch shown by MX::test_rebound_source_refuses_pinned_old_version_without_stale_value | N/A — same | N/A — same |
| error text | failure codes only; raw OSError text never serialized — `web_api.py:165-180` → API::test_launch_failure_retains_reviewable_run_and_seals_status; invalid worker result → closed code — API::test_zero_exit_requires_valid_result_before_success; timeout never claims success — API::test_timed_out_worker_is_stopped_and_sealed_without_claiming_success | `INVALID_REQUEST_FIELDS`/`UNKNOWN_ACTION` codes only → API::test_unknown_action_and_oversized_request_have_closed_errors | GAP (owner: transport) |
| evidence metadata | status: request sha256, run_id, wall limit, artifact names — `web_api.py:120-130,169-180` → API::test_process_contract_scrubs_environment_bounds_wait_and_preserves_artifact_result; capabilities declares its access model — `web_api.py:239` | N/A — nothing emitted on refusal (asserted in API::test_dispatch_rejects_unknown_or_missing_action_fields) | GAP (owner: transport) |
| request-selected root/credential/grant | allow-lists are the grant surface: measured above (K01.03) → API::test_dispatch_rejects_unknown_or_missing_action_fields; MX::test_credential_shaped_request_keys_are_refused_not_ignored; MX::test_lab_run_rejects_credential_shaped_outer_key_before_artifacts; refs resolved before any artifact `web_api.py:117-118` | same enforcement → API::test_lab_source_versions_are_validated_before_execution; API::test_lab_column_map_is_explicit_unique_and_closed | GAP (owner: transport) |
| rights equivalence | computation ≠ production: `research_only`, ledger owner declared, `production_ledger_written=False` — `web_api.py:196-199` → API::test_process_contract_scrubs_environment_bounds_wait_and_preserves_artifact_result; plan-not-execution → LAB::test_plan_keeps_missing_budget_visible_and_does_not_execute; K01.02 full split → GAP deferred to R00 | same | same |

### S3 `lib/dataos/web_readers.py` (inspect_file, read_rows)

| channel | granted | ungranted | revoked/expired |
|---|---|---|---|
| value | stored values returned to the already-authorized handle — `read_rows` `web_readers.py:552-592` → RD::test_real_parquet_projection_filters_and_absolute_positions (positive control) | structurally upstream: the API takes an open binary stream, never a path — `web_readers.py:552-556`; admission is `web_workspace.py::_file` (S1) → RD::test_real_parquet_metadata_keeps_source_columns_and_clocks (position retained, handle not owned) | structurally upstream (S1 `SOURCE_VERSION_MISMATCH`/`SOURCE_CHANGED`) → RD::test_admitted_length_must_match_current_handle (size guard `web_readers.py:71-93`) |
| path | N/A — no path parameter exists in the module (signature `web_readers.py:552-556`) | N/A — same | N/A — same |
| artifact location | N/A — result schema is rows/positions/scan bookkeeping only `web_readers.py:519-549` → RD::test_real_parquet_projection_filters_and_absolute_positions (`json.dumps` clean) | N/A — same | N/A — same |
| cached result | N/A — stateless; every call re-reads under the size guard `web_readers.py:71-93` → RD::test_admitted_length_must_match_current_handle | N/A — same | N/A — same |
| error text | `ReaderError` is a closed code; `str(err) == code` — `web_readers.py:45-50` → RD::test_malformed_sources_have_no_raw_error_text (13 malformed fixtures), RD::test_invalid_time_controls_are_closed, RD::test_argument_bounds | same enforcement (bad query args are the same closed codes) → RD::test_argument_bounds | same enforcement |
| evidence metadata | schema/count/stored-statistics ranges only; no freshness invented — `web_readers.py:336-344` → RD::test_real_parquet_metadata_keeps_source_columns_and_clocks (asserts no mtime/fresh keys) | N/A — a refused read returns no metadata at all | same as granted (metadata derives from the opened source only) |
| request-selected root/credential/grant | N/A — query vocabulary is closed and validated against the actual source schema — `web_readers.py:442-476` → RD::test_argument_bounds (`INVALID_COLUMNS`, `INVALID_FILTER`, `INVALID_FILTER_COLUMN`, offset/limit/scan bounds) | same enforcement → RD::test_argument_bounds | N/A |
| rights equivalence | N/A — pure reader; admission decided upstream — unsupported formats metadata-only (`USE_EXISTING_OWNER_DECODER`) → WS::test_raw_archive_is_metadata_only, RD::test_unsupported_compression_is_not_automatically_opened; K01.02 → R00 | same | same |

### S4 `lib/dataos/web_lab.py` (list_signals, plan, execute)

| channel | granted | ungranted | revoked/expired |
|---|---|---|---|
| value | catalog metadata only; the callable `fn` is stripped — `web_lab.py:155-168` → LAB::test_catalog_metadata_is_searchable_bounded_and_callable_free; plan echoes the validated request only — `web_lab.py:245-268` → LAB::test_plan_keeps_missing_budget_visible_and_does_not_execute | GAP (owner: transport) — the catalog listing is not principal-gated in-repo (`list_signals` has no principal argument, `web_lab.py:171-193`) | GAP (owner: transport) |
| path | supplemental-input declarations are repo-relative literals, disclosed as discovery-only and never bound — `web_lab.py:135-152` → LAB::test_implicit_supplemental_inputs_remain_discovery_only | GAP (owner: transport) — same disclosure reaches any caller that reaches the surface | GAP (owner: transport) |
| artifact location | N/A — plan/result schemas carry scopes, never filesystem paths — `web_lab.py:245-268,309-341` → LAB::test_execute_forwards_exact_contract_and_preserves_full_trial | N/A — same | N/A — same |
| cached result | N/A — stateless; no engine import before budget — LAB::test_execute_requires_budget_before_importing_calculation_engine | N/A — same | N/A — same |
| error text | `WebLabError` message may echo the caller's own `signal_id` — `web_lab.py:224-226` (caller input, never host state); the message layer does not cross the CLI boundary — `scripts/data_workspace.py:85-94` → LAB::test_unknown_signal_is_not_a_dynamic_import_or_expression; MX::test_web_lab_error_message_text_does_not_cross_the_cli_boundary | same enforcement | same enforcement |
| evidence metadata | `supported_by_web_lab`/`discovery_only` flags + closed limitation strings — `web_lab.py:36-50,155-168` → LAB::test_catalog_metadata_is_searchable_bounded_and_callable_free, LAB::test_plan_keeps_missing_budget_visible_and_does_not_execute | GAP (owner: transport) — flags disclose which signals are executable, ungated in-repo | GAP (owner: transport) |
| request-selected root/credential/grant | request fields closed — `_REQUEST_FIELDS` `web_lab.py:33-35`, enforced `web_lab.py:280-284` → LAB::test_execute_rejects_arbitrary_overrides_before_engine; `signal_id` cannot become code — `web_lab.py:223-226` → LAB::test_unknown_signal_is_not_a_dynamic_import_or_expression; direction + reviewed-module admission gates — `web_lab.py:227-244` → LAB::test_plan_does_not_invent_direction_from_unknown_metadata, LAB::test_unreviewed_callable_module_cannot_use_reviewed_family_label | same enforcement | same enforcement |
| rights equivalence | research ≠ production: verdict is not admission; `to_ledger` never called — `web_lab.py:329-341` → LAB::test_execute_forwards_exact_contract_and_preserves_full_trial (`assert_not_called`); budget is caller-declared, not self-granted — `web_lab.py:287-291` → LAB::test_execute_requires_budget_before_importing_calculation_engine; K01.02 full split → GAP deferred to R00 | same | same |

### S5 `lib/dataos/web_lab_worker.py` (side-effect guard, limits, _materialize, execute_worker)

| channel | granted | ungranted | revoked/expired |
|---|---|---|---|
| value | universe materialized only from pinned refs' pages — `web_lab_worker.py:67-130` → API::test_materialize_binds_actual_parquet_columns_and_clock_without_rebasing; result carries only canonical trial + sources — `web_lab_worker.py:156-170` → LAB::test_execute_forwards_exact_contract_and_preserves_full_trial | audit hook refuses `.env`/`.aws`/`.ssh` reads and ALL writes/mutations/network/subprocess outside the run dir — `web_lab_worker.py:36-57` → LW::test_side_effect_guard_is_confined_to_child_process_and_its_run. Residual (accepted boundary, not a K01 cross-principal channel): read scope of the *admitted* catalog modules is not path-confined (`web_lab_worker.py:4-5`; caller-supplied code is never accepted, `web_api.py:4-5`); owner: the existing catalog input review | GAP (owner: transport) |
| path | `sources` metadata is alias-relative — `web_lab_worker.py:123-129` → API::test_materialize_binds_actual_parquet_columns_and_clock_without_rebasing | worker error payload is code+type only — `web_lab_worker.py:172-177` → LW::test_materialization_never_guesses_an_epoch_or_ambiguous_date (and every LW refusal: `str(err) == code`) | same enforcement |
| artifact location | writes confined to the run dir — `web_lab_worker.py:46-49` → LW::test_side_effect_guard_is_confined_to_child_process_and_its_run | same hook → same test (write/remove/mkdir/rename refused outside run) | ledger enumeration confined + symlink/size-guarded `web_lab_worker.py:149-155` — no dedicated discriminator (see GAPS) |
| cached result | per-page version pinning; mixed-version combination refused — `web_lab_worker.py:74-93` → LW::test_changed_file_between_pages_fails_instead_of_combining_versions, LW::test_selected_version_and_source_row_offset_are_used_on_continuation, LW::test_materialization_refuses_nonadvancing_page_cursor | same enforcement → LW::test_caller_selected_version_is_required_on_the_first_page | same enforcement |
| error text | closed payload (code + type name only) — `web_lab_worker.py:172-177` → LW::test_materialization_never_guesses_an_epoch_or_ambiguous_date and every LW refusal (`str(err) == code`); parent seals invalid results — API::test_zero_exit_requires_valid_result_before_success | same enforcement | same enforcement |
| evidence metadata | sources block carries declared basis/limitations ("preserved as stored; no rebasing…") — `web_lab_worker.py:123-129` → API::test_materialize_binds_actual_parquet_columns_and_clock_without_rebasing | N/A — refusal payload has no source metadata | same as granted |
| request-selected root/credential/grant | execution dict re-validated inside the worker — `web_lab_worker.py:143-145` → API::test_lab_column_map_is_explicit_unique_and_closed, API::test_lab_source_versions_are_validated_before_execution; run dir/TMPDIR pinning required — `web_lab_worker.py:133-136` (no dedicated discriminator — see GAPS) | input/row budgets enforced — `web_lab_worker.py:20-22,86-89` → LW::test_materialization_checks_per_source_row_limit, LW::test_materialization_checks_total_rows_across_sources, LW::test_materialization_checks_scanned_rows_even_when_no_row_matches | GAP (owner: transport) |
| rights equivalence | `research_only`, `production_ledger_written=False` in the worker payload — `web_lab_worker.py:160-170` → API::test_process_contract_scrubs_environment_bounds_wait_and_preserves_artifact_result; K01.02 full split → GAP deferred to R00 | same | same |

### S6 `scripts/data_workspace.py` (CLI entry; host-owned `--config`)

| channel | granted | ungranted | revoked/expired |
|---|---|---|---|
| value | end-to-end positive control through the real entrypoint — `main` `scripts/data_workspace.py:70-94` → MX::test_allowed_read_returns_sentinel_and_evidence_stays_alias_relative | refusals precede any read → MX::test_path_escape_refusal_returns_closed_response, MX::test_credential_shaped_request_keys_are_refused_not_ignored, MX::test_request_cannot_select_a_root_by_path | volume-off refusal → MX::test_unmounted_required_volume_refuses_before_any_read; principal revocation → GAP (owner: transport) |
| path | host paths never serialized — closed error serializer `scripts/data_workspace.py:85-94` → MX::test_cli_error_response_never_carries_exception_detail_or_config_path | same enforcement → MX::test_path_escape_refusal_returns_closed_response | same enforcement |
| artifact location | N/A — this layer creates no artifacts (lab artifacts owned by S2/S5); absence asserted across all MX CLI responses | N/A — same | N/A — same |
| cached result | N/A — one stateless process per request (`scripts/data_workspace.py:70-84`) | N/A — same | N/A — same |
| error text | only `{schema_version, error, error_type}` is printed; exception text, paths, tracebacks never cross — `scripts/data_workspace.py:85-94` → MX::test_cli_error_response_never_carries_exception_detail_or_config_path, MX::test_web_lab_error_message_text_does_not_cross_the_cli_boundary | same enforcement → MX::test_request_cannot_select_a_root_by_path | same enforcement |
| evidence metadata | `implementation_revision` from host git/RELEASE.json only — `scripts/data_workspace.py:28-55` → MX::test_allowed_read_returns_sentinel_and_evidence_stays_alias_relative | N/A — error responses carry no evidence block | N/A — same |
| request-selected root/credential/grant | `--config` is argv/host-owned, never a request field — docstring `scripts/data_workspace.py:8-10`, argparse `scripts/data_workspace.py:72-74`; a body key named `config` is refused → MX::test_credential_shaped_request_keys_are_refused_not_ignored | same enforcement; `--lab-worker` is host-supplied only (`scripts/data_workspace.py:74`) | GAP (owner: transport) |
| rights equivalence | N/A — transport entry; authorization declared outside request args (`scripts/data_workspace.py:8-10`) → GAP (owner: transport) for any principal-level distinction; K01.02 → R00 | same | same |

### Channel-level synthesis

- **K01.01 (bounded reads):** enforced on every surface (S1 `_parts`/`_root`/`_file`/`_directory`;
  S2 allow-lists; S3 structural no-path; S6 closed serializer). Traversal, `..`, dot/hidden
  segments, SENSITIVE_MARKERS segments (`credential`, `secret`, `apikey`, `api_key`,
  `access_token`, `refresh_token`, `private_key` — `web_workspace.py:30-31`), symlink escape,
  hardlink/FIFO, path-shaped root aliases and escaped paths all refuse with codes that carry
  neither the sentinel value, nor any absolute path, nor the root's real location. Positive
  controls: MX::test_allowed_read_returns_sentinel_and_evidence_stays_alias_relative (CLI),
  WS::test_read_filters_actual_rows_preserves_nulls_and_reproducible_query_receipt,
  RD::test_real_parquet_projection_filters_and_absolute_positions.
- **K01.02 (rights non-equivalence, D00.D6):** the additive `rights` field does **not** exist
  in `lib/dataos/registry.py::DatasetContract` (`registry.py:115-155`) at this base → recorded
  as **covered by R00 tests (planned: `tests/test_dataos_registry_consumers.py`)**; no registry
  test added here, per packet. What the read surfaces already enforce today is the adjacent
  non-equivalence: physical discovery ≠ registry admission ≠ production qualification
  (`web_workspace.py:127,191,265`) and research computation ≠ production ledger
  (`web_lab.py:329-341`, `web_api.py:196-199`, `web_lab_worker.py:160-170`).
- **K01.03 (allow-lists):** measured above; unknown and credential-shaped keys are refused
  (`INVALID_REQUEST_FIELDS`) before any workspace call, artifact or read.
- **K01.04 (rebinding / staleness):** `ROOT_BINDING_CHANGED` (in-flight root replacement,
  `web_workspace.py:150-152`), `SOURCE_VERSION_MISMATCH` (pinned stale read,
  `web_workspace.py:180-181`), `SOURCE_CHANGED` (in-flight file change,
  `web_workspace.py:196-199`), and per-page pinning in the lab worker
  (`web_lab_worker.py:74-93`). New end-to-end discriminator:
  MX::test_rebound_source_refuses_pinned_old_version_without_stale_value — after the source is
  replaced, the pinned old binding serves **neither** the old nor the new sentinel and the
  serialized error carries no path; the new content is served only through a fresh read.
  Error text and evidence metadata carry no source URL, absolute path or SENSITIVE_MARKERS
  word (asserted on full serialized responses).

## GAPS

1. **Revoked/expired principal — UNENFORCED in-repo → GAP (owner: the Studio Direct /
   authenticated MCP transport;** declared at `web_api.py:239` and
   `scripts/data_workspace.py:8-10`). No surface carries a principal identity, so revocation
   cannot be expressed in-repo. Nearest in-repo analogs, now discriminated:
   `REQUIRED_VOLUME_NOT_MOUNTED` (MX::test_unmounted_required_volume_refuses_before_any_read —
   previously untested) and `ROOT_BINDING_CHANGED` (WS::test_root_inode_replacement_is_detected).
2. **K01.02 registry `rights` split — deferred to R00** (planned
   `tests/test_dataos_registry_consumers.py`); field absent at base `0939fbfc9e`.
3. **web_lab catalog discovery is not principal-gated in-repo** (catalog metadata, executable
   flags and repo-relative supplemental-input declarations reach any caller that reaches the
   transport) → GAP (owner: transport), S4 value/path/evidence-metadata ungranted+revoked rows.
4. `web_lab_worker.py::_limits` (rlimits) and the ledger-enumeration guard
   (`web_lab_worker.py:149-155`) have no dedicated discriminator; low leakage relevance
   (same-principal artifacts). `DEDICATED_LAB_RUN_DIRECTORY_REQUIRED`
   (`web_lab_worker.py:133-136`) is likewise enforced but untested.
5. The new test file is **not yet wired into any CI job** (the seat wires it).

## Boundary notes (accepted, not gaps)

- SENSITIVE_MARKERS gate path **segments** only; sensitive-named *columns inside a bound
  file* are returned to a granted read by design (original field names preserved,
  `web_readers.py:3-6`). The grant boundary is the root binding, owned by the host config
  owner — a credential-bearing root must never be bound.
- The lab worker's audit hook is defense against accidental side effects in trusted catalog
  code, not a sandbox (`web_lab_worker.py:4-5`); caller-supplied code is never accepted
  (`web_api.py:4-5`), and admitted modules are closed-vocabulary
  (`_PRICE_ONLY_MODULES`, `web_lab.py:32`).
