# Native TOI accounting contract verification

This is offline verification of the existing `engine/trial_ledger.py` and the already proposed 22-slot Daily subset, not a new ledger, admission checker, harness, experiment registration or CI integration.

Source: Macro `dc59164faa9c7126115dc5f3aaba6984560b421a`, native blob `eb364fe9fa53f46d0455e194d3e3ccdbb5732778`, SHA256 `7b99683c9aee822df138d35b8294318e3316c3b6a8b5a80934614141a15413f7`. Inventory: #8332 `c9c1e7eea12868bda9d396c654b55bd1d0ab1aea`, SHA256 `2e41f2ce632da6d5a55343fd1ef8e22b03219d0a504873bc435d29e43ec88e2f`.

Seventeen unittest cases passed. Three mutations to disposable copies were killed by 3, 4 and 3 assertion failures, respectively. The canonical source and draft inventory remained unchanged. No real configuration, production ledger, market data or outcome was read or written.

`native_accounting_contract.py.txt` preserves the executed source byte-for-byte as an explicitly inert review artifact; it is not installed in repository CI. To reproduce against an exact read-only export containing `engine/trial_ledger.py`, set `SUBJECT_ROOT` to that export and `INVENTORY_PATH` to the original draft JSON, then run Python on this file. The script itself supplies temporary synthetic ledger paths and checks that the default ledger was never created. No production path should be supplied as a fixture ledger.

The proof intentionally verifies native behavior rather than replacing it. In particular, metadata-only source/cutoff changes do not change config identity, and an empty ledger's effective count is one. Read the steering document for the resulting manifest requirements; these observations are not a W3 admission.
