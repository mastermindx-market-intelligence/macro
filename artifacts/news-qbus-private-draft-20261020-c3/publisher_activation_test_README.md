# Portable publisher activation operation tests

Keep these files beside each other:

- `publisher_activation_operation.py`
- `test_publisher_activation_operation.py`
- `publisher_activation_fixture_receipts.json`

The operation artifact qualified here has SHA-256
`4f6b515ad32295b3b2ba6a896801cb32afbac5904ed8de9d30585720cda84428`.
The test and fixture resolve from the test file's own directory; the checkout
location does not matter.

Run from that directory with Python 3.12 in an isolated POSIX runtime as UID 0:

```sh
python3 -m unittest -v test_publisher_activation_operation.py
```

Or invoke the test file directly from any working directory:

```sh
python3 /path/to/artifacts/test_publisher_activation_operation.py -v
```

This command runs the thirteen isolated tests. The tests mock systemctl, Git,
and provider commands and use temporary local state and synthetic unit bytes.
They do not execute the production activation. The original operation root and
file-ownership checks remain intact, so the temporary test files must be owned by
UID 0; use an isolated root container/runtime. No live service, credential, network
connection, or production database is required. The current environment ran the
tests as UID 0 in a fresh unrelated temporary directory.

`publisher_activation_portable_test_receipt.json` records the command, exact
script/test/fixture hashes, unchanged test assertions, and complete test result.
Runtime activation still belongs to the parent operation and its reviewed
expected-merge preview/apply procedure.
