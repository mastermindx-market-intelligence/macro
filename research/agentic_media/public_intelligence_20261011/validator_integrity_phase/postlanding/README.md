> Current-source warning (October 14): this accepted 558ca manifest is stale for the later DOJ and issuer-context additions. Do not use it to claim their installed acceptance. Candidate preparation is in `../../doj_source_phase/issuer_context/`; independent review and explicit manifest acceptance remain required.

# Validator and writer follow-on acceptance bundle

Prepared only; never executed against production. This directory keeps the prior accepted three-page binding and a distinct 24-source manifest for the follow-on. The four changed source hashes are validators.py, writer.py, run_press.py and stage_official_feed_press.py; the original PR 9209 manifest is unchanged.

After the follow-on actually lands through its protected PR, supply its verified merge SHA (never a candidate SHA) and the observed stable installed HEAD to prepare-ancestry.py. Use the full canonical local repository to verify the raw commit-object chain needed by the shallow VPS. Then run mmx-current-install-check.py with that actual merge SHA. It takes its complete source inventory from the manifest. All source, site and site.served checks, stable HEAD, ancestry and cutover=false are required. Preserve the normal VPS updater; no production Git mutation or unrelated service restart.

Run ../installed_integrity_probe.py in /opt/macro/.venv/bin/python -B with /opt/macro and the bound manifest through the existing SSH transport. Its ten controls use isolated historical fixtures, one mocked writer, pure prompt assembly, and no real provider. It must leave runtime inputs, staging, public content and HEAD unchanged. Run mmx-current-runtime-inspect.py and mmx-current-http-check.py afterward. Matching pages permit reuse of the prior scoped browser evidence; they do not admit a new article, prove new signup/follow writes, or earn D14 acceptance credit.

Any drift must be reviewed before manifest replacement. Pytest is not required or installed on production. The other probes from the original release have their own expected hashes; do not run them with stale digest arguments after this follow-on changes their source.
