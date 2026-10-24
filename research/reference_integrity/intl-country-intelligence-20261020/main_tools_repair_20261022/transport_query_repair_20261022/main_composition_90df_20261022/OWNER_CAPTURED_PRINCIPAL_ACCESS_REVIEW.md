# Independent inherited-access review — ACCEPT

Reviewer /root/intl_release_scope_adjudication read the complete four access diffs,24-file applicability diagnostic,current Caddy serving blocks,site_access policy and relevant test bodies.

The only Caddy change since reviewed14ed is the exact /baskets_china.html redirect exception for mmx_shell=1 and the beta-parent Referer. It lets the existing moved-page stub navigate through the parent; it neither grants identity/entitlement nor exposes protected payloads. The current Caddyfile equals protected main90df. The access-test delta since14ed adds only the exact Baskets redirect assertion; the original International assertion and fnmatchcase import remain intact.

All nine presentation filenames remain explicit in policy and all four serving matchers. No broad /intl* exemption is introduced. Template/site equality and negative controls for raw country/provenance/Parquet inputs,data/run_status,neighboring data scripts,JSON,maps,private CSS and suffix paths remain. API authorization and both regwall/paywall subrequests remain; asset errors stay private/noncacheable503. /macrodata/ remains registered-only and site_full remains the premium feature. This is source acceptance, not deployed entitlement proof.

The24-file diagnostic contains21 exact reviewed-byte matches in local48b5 and prospective5e1, including the four findings' implementation/regressions and access policy. Three exceptions now have bounded dispositions: CI enrollment/composition separately accepted; Caddy and added access guard accepted here. Caddy SHA256f72c04b943e49c79352fee7bb91f44f7f34898e9f40c37fa12a651e92290a3b7 and test SHA256b09d72367b545b93f1c7154b7d4ba38f4ab0e4d9954de1cea76827f733a30e53 match local and prospective inputs.

Retain initial process52807 exit1 as an applicability-guard diagnostic, not a product-test failure. One run of the existing test_site_access_boundary.py owner is sufficient for this concrete change; no further data-suite repetition or new test is indicated. Execution is recorded separately in ACCESS_REVIEW_VALIDATION.json. No source mutation was requested by this review.
