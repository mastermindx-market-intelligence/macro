# Main-drift evidence retention

The canonical directory retains the independent review, both drift inventories, both merge
reviews, the preserved Theme Graph diff, the raw tool receipt and the original package inventory.

The original `REVIEW_PACKAGE_FILES.json` also inventories four `.json.gz.b64` scratch transport
encodings. Those encodings are intentionally not copied here: the complete decoded JSON files
are retained byte-for-byte under their original names and hashes. The encodings contain no
additional source or evidence. The package inventory itself remains unchanged.

The separate documentation/generator audit is retained in
`../final_document_audit/DOCUMENTATION_GENERATOR_AUDIT.json`.
