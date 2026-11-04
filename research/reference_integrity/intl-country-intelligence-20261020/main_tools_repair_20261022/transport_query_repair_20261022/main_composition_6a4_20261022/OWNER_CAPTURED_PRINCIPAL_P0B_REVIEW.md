# Independent main-6a4 P0B capture review — ACCEPT

Faithful owner-captured summary of /root/intl_release_gate_review. Actual capture source: 51b217b3eb1ee211d54706d2673ab183de9452b3. Paired theme SHA256: d7be48a71598c3c806deb271f346c996dc5136e1030f17546407092b6938e419.

The reviewer read the complete execution receipt, driver, binder and validation. It independently reconstructed, parsed and hashed the four current canonical JSON files and both archived parent manifests. It did not run commands or inspect screenshot pixels.

## Actual execution

Rendering ran 08:55:51–08:55:57 UTC; Chromium 155.0.8059.85 verification completed 08:58:57 UTC. All three commands exited 0. The driver SHA256 independently matches 8c6ca2e6516edfb0611e25afca516790c018e89990f8bcf72a3f477e087a4794.

Hong Kong and Canada each pass all 64 unique case combinations: 48 primary and 16 degraded controls, with eight screenshots each. Ordinary state, expansion, fragment-navigation and desktop groups pass. Every case's HTML hash equals its fixture owner case; all 16 distinct screenshot paths match the manifest.

## Parent preservation

The exact full-object union of incoming 13 history objects, local 18 history objects and both current extensions contains 21 distinct objects, with zero missing or extra entries. The incoming manifest hash is 3e7521ad38a937c8c1bc23f2f0cff8e1c1dc7ab0e5a81194fd550a9772e36071; the local manifest hash is 503024d1d23ce23e4d204e92e4af9e5eb87ecbfc2354fb838b2d8578d2c7a1d8.

The #9969 provenance wrapper, including source_head f7e8076c3854bd262db4c73b68fca2410e3e402d, is intact. All other manifest fields equal incoming main. Historical baseline 3fb76ea810a8e9ef6a05fe808bb6eaee87eb1f86 / tree b4dd8fd9b29b4eb769239d35df2a7911e793c7ec remains historical.

## Dependency closure and hashes

The complete closure contains 54 paths for Hong Kong, 57 for Canada and 59 distinct paths overall, including 23 fixture inputs. Construction maps exactly match the market fixture maps. Only site/theme.css changed versus the prior accepted capture; no paths were added or removed. Bridge/workspace sources do not intersect this closure. Later applicability requires all 59 bindings and receipt/screenshot identities to remain unchanged. The actual capture source must remain 51b217b3.

Independently matched SHA256 values:

- Execution: 9b19e0d2a016024b5636ff1599a62af12a50f76c5f07326fdbb2a1ec773fb172
- Fixture: c2988f6e67654f92d2e125d5f2bf92cdb76ac8a3aec75b12b76b920bc00ef33d
- Hong Kong: 1cfcbe0a08c8f8adca60d40735bbdc107de596066cb92837756828fe35288e3d
- Canada: 68943e2590694c0406ec16732f8c302cfddf9bdaa34ffc44d2fe6896c3bfa9e6
- Manifest: ba006303b4701dcd21a4cae7dc8e194ba125bd32ee67738ae34a5b5ff0d406ac

## Validation and limits

Receipt closure exited 0. The explicit command in validation.json runs tests/test_stock_dashboard_first_frame.py and tests/test_check_p0b_receipt_closure.py: 136 passed in 101.94 seconds, with no warnings, completed 09:03:30 UTC. The complete log hash independently matches 525fa4e64d7b11ed496d6b1958bd24db71c2d9087f4f3110bbe9d65aa9d86ced.

No additional capture or source repair is indicated. Accepted scope remains a reproducible browser fixture; canonical build is unavailable and production claims are none. Query/focus, hosted CI, FX custody and served-adoption obligations remain separate.
