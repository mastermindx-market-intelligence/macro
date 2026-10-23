# R1 requested-viewport acceptance

The mobile browser can expand its layout viewport when page content overflows.
A scrollWidth <= innerWidth check alone can falsely pass that zoomed-out page.
The capture producer now binds job.width before validating document geometry.

150 tests passed. The new 13 cases produced 10 failures / 3 controls before the
correction. An actual R2-only archived full page expanded the requested 390px
viewport to 518px EN / 425px ZH. The corrected check rejects all four affected
mobile observations while preserving four desktop controls. That R2-only page
still lacks its R1 layout prerequisite; no new R2 layout defect is inferred.

The existing R1 synthetic fixture corpus was recaptured: 32/32 states pass the
requested-width gate in both themes/locales at 1440/390. Product template and
model bytes did not change. Images and metadata are synthetic browser proof,
not a production release or market update. External network access was refused.
