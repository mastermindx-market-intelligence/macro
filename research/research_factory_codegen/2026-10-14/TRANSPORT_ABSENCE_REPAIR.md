# Container absence protocol repair

Docker CLI 29.1.3's `inspect --type container <full-id>` returns exit code 1 and
`Error response from daemon: No such container: <full-id>` when the container is
absent. The dormant transport previously searched for the generic autodetection
phrase `No such object`. A real read-only sentinel inspection through the existing
Fabric on Ubuntu1 retained 115 bytes: one empty JSON array line followed by one
container-specific error line. Its SHA256 is
`b4898799e911e464a3aa208fcb6f04b7ec00d3681a8f8ac08d9ca3f1f67ffeb2`.
This observed protocol agrees with the pinned [Docker CLI source](https://github.com/docker/cli/blob/v29.1.3/cli/command/system/inspect.go)
and [Moby daemon error source](https://github.com/moby/moby/blob/docker-v29.1.3/daemon/errors.go).

The parser now requires the exact full container ID in a single error line,
optionally preceded by one empty-array line. It rejects generic object errors,
wrong or embedded IDs, extra payload, repeated or reversed lines, interior blanks
and carriage returns. Timeout, truncation, permission, collector-error, exit-code,
identity and stop/remove checks remain independent requirements. The original
retained bytes are never normalized or rewritten.

The paid Fabric return was consumed by its actual assigning Sol parent. Review
found its initial allowed-line-set implementation accepted duplicate and reordered
lines. The parent preserved that return unaccepted and derived this strict ordered
sequence repair. Root independently reviewed the resulting patch and applied the
tests before the source change: the existing full lifecycle discriminator failed
with CLEANUP_UNCERTAIN rather than CLEANED_SUCCESS. Applying the source correction
then produced **167 passing transport tests**. `git diff --check` passed. No helper
that reimplements the old predicate is counted as the red proof.

The repaired source SHA256 is
`b6d36717ad3630d127b16fe9e117d9401bea1136880e28d19f0d18061933c633`;
the transport test file SHA256 is
`7f9c7fccffc1034baef3ea8ea184da2a869605d66c11f3dd01d469a4c4c71f53`.
The existing Research Factory CI job already runs that test file.

This is source and client-protocol qualification only. The sentinel read created,
started and removed no container. The real Docker engine remains dormant and
refuses before a subprocess is created. Real cleanup, hostile-code containment,
resource controls and candidate admission require their separate physical proof.
