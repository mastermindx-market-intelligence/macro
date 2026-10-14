# Reviewed validator, writer and DOJ source release acceptance

Prepared only; no production acceptance claimed. The active manifest binds24
sources. Relative to the earlier558ca bundle,22 hashes remain unchanged and the
official planner/staging entrypoint are rebound to exact bytes independently
accepted at70d9b7e08337. All four reviewed source/test hashes match the retained
review binding. See `../../doj_source_phase/release_scope_binding.json`.
The same three reviewed page hashes remain byte-identical.

The optional historical issuer-context implementation is deferred, retained at
1989dd890273 and in a hash-bound patch with its original unaccepted review run.
It contributes no active code or tests to this release. Its candidate28-source
manifest and portable issuer probe are historical and must not be used here.
The only source/CI change beyond reviewed70d9 is beautifulsoup4 added to the
existing Press job's minimal dependency install, matching the runtime requirement.

After the follow-on protected PR actually lands, supply its verified merge SHA
and stable observed installed HEAD to prepare-ancestry.py using full canonical
Git objects. Run mmx-current-install-check.py against that actual merge, never a
candidate. Require all24 source hashes, source/site/site.served page checks,
stable HEAD/ancestry and cutover=false. Use the normal VPS updater, no production
Git mutation or unrelated service restart.

Run ../installed_integrity_probe.py (10groups) and
../../doj_source_phase/installed_doj_source_probe.py (5groups) through the existing
SSH transport with `/opt/macro/.venv/bin/python -B`, `/opt/macro` and this manifest.
Both use isolated historical fixtures; zero real provider/producer/public effects.
Do not install pytest. They passed locally with exact current reviewed hashes;
a separate wrong-hash control refuses before imports. Run read-only staging
inspection and HTTP checks afterward. Matching pages permit reuse of prior
scoped browser proof, never a new article, signup/follow write or D14 credit.

Current local validation:335 affected tests passed,1 existing sparse-site skip;
305-job manifest valid, packing totals5435/5435; trigger closure0gaps. Those local
checks do not replace fresh protected-PR CI or installed verification.
