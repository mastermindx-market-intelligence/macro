# Owner-captured independent fresh-main conflict ruling

Reviewer:/root/intl_release_gate_review. Owner-captured précis of delivered final ruling; reviewer made no mutations/tests/publication.

Base25051144947f027c698cd1ce10e3c8824ee6ade9; International14ed4f12f31b71c63bbabd969aebbf9c4305ccaa; protectedmain64ef5131a5f50fb65f0ad25a049a457e18258495.
Reviewed PREIMAGES.json and all eight branch/main diffs completely.

**Accept exact protected-main versions as a historical staging point for these four conflicts**, preserving branch receipts/history in retained preimages and immutable14ed. No International implementation, case coverage, assertions or navigation changes occur in these four conflicts.
- manifest.json main blob51423a5460dca19531fbbe77fe9aae6e037af037.
- mobile-layout-canada.json main blob66e1c88fe87c745632f4a4107326917f2c82806e.
- mobile-layout.json main blob2b359cd7c18aba0d1c376dfef8b5569180599ac5.
- site/research_screener.html main blobad3b81480920861e8acf6da2ea6c0f4b626a7ce6.

Branch manifest has meaningful updated timestamp/browser hashes and four additional historical repair extensions. Branch browser receipts change Chromium151→155, favicon hash and theme hash, without changing case results. Main changes receipt theme hashes and matching manifest hashes only. Main Canada receiptSHA256bbc6f54d26f36acdbb8daa84ba67095e54c292b5b81b03d6a52851e098e9b7ce; HK b8349824849fa8aeda2ed35e483df1a0e6e55a08ad86784b8da6ff540f512e51. Do not mix main manifest with branch receipts.

Screener only differs in theme.css cache token: base2e861147,branch61428c7d,maina922b22c. Bind eventual token through normal build/stamping to actual composed bytes.

Receipts are prophet-cockpit-p0b-zero-fouc-20260904-sol-001 browser_fixture/reproducible, canonical_build unavailable, production none. Main's newer commit is not a newer observation. Neither parent receipt validates a composed theme differing from the recorded hash. Current-source proof requires an actual capture; changing receipt hashes alone is insufficient. No new human owner hold established.
