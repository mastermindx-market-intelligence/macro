# Market Memory read-slot diagnostics

The real retained catalog returned HTTP503 BUSY during the saved-source journey. Concurrent memory and swap pressure is evidence, not an established cause. Four existing admitted read paths now emit start, finish and BUSY records using only a closed operation tag, process-local sequence, elapsed time, success and at most two active holder summaries. No request identity, source key, token, URL, path, payload or exception detail is logged.

The registry is bounded by the existing two-permit limit; logging is outside its lock. The observer never acquires/releases a real permit. Original authorization, owner rechecks, budgets, rates, errors and response bytes are unchanged. Cleanup also runs on BaseException, and logging failure cannot alter the outcome. Records inherit the existing Uvicorn INFO handler; no global logging configuration is changed.

## Proof

The assigning parent froze all four route AST digests before implementation. Removing only the observer wrapper and BUSY call reproduces them exactly. The affected route suite passed78tests. An additional isolated default-handler-profile test covers INFO visibility, bringing focused diagnostics to12tests. Temporary-owner API tests are not live production proof.

The M2 worker mm-u1-read-observation-20261014-01a1333c-v1 completed with a consumed retained result but exported source under /home/ubuntu2/artifacts. The installed reader accepts only /tmp/DIR/FILE and refused before transport. No alternate transport, rehome or replay was attempted. This source was independently authored by the assigning parent; worker artifacts are unavailable and not accepted.

After protected delivery, verify installed bytes and use one authenticated journey plus matching service journal events to identify the held operation. Observability alone does not fix latency, admit a study or prove intelligence quality. Concurrency, rights checks and research pins remain binding.

## Python-version oracle repair

Hosted Python3.12 exposed4 differences in ast.dump formatting against the original Python3.14 freeze. Reproducing the same four digests from the untouched pre-instrumentation source proved printer drift. The test now hashes a canonical AST structure that retains semantic None, False, zero, node/field identity and ordering, and omits only empty list fields. Expected hashes were derived from original bbfd64b2 source469222d2, not current instrumentation. All16focused tests pass under both Python3.12 and3.14. Application source is unchanged. The bounded Fabric attempt terminated on provider429weekly/monthlyquota before producing implementation; the assigning parent authored and verified the repair, with no replacement dispatch.
