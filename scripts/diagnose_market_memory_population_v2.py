"""Read-only installed-operator entry point for the native W2C v2 census.

Never mount this operator command on a customer/API route. Its narrow scope is
the commissioned internal metadata census, not a website entitlement or a new
permission issuer. No writer, install-marker writer, service or study is called.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from scripts import accrue_market_memory_spy_experience as installed  # noqa: E402

_ROOTS = (Path("/opt/macro"),
          Path("/var/lib/macro-market-memory/state/experience-v2"),
          Path("/var/lib/macro-market-memory/state/sources-spy-rest-v1"),
          Path("/var/lib/macro-market-memory/state/technicals-v2"))
_REGISTRATION = "mmspyexpreg_ff4151e717d87d4ac32b59c515d677b01bf889feb494245c1ce655918fa875f4"
_CLOSURE = (
    "scripts/diagnose_market_memory_population_v2.py",
    "scripts/accrue_market_memory_spy_experience_v2.py",
    "scripts/capture_market_memory_technicals_v2.py",
    "engine/neuralweb/market_memory_population.py",
    "engine/neuralweb/market_memory_population_v2.py",
    "engine/neuralweb/market_memory_source_kernel.py",
    "engine/neuralweb/market_memory_sources.py",
    "engine/neuralweb/market_memory_sources_spy.py",
    "config/market_memory_spy_experience_registration.v2.json",
)


def _check_imports(repository):
    from engine.neuralweb import market_memory_population as policy
    from engine.neuralweb import market_memory_population_v2 as census
    modules = {installed: "scripts/accrue_market_memory_spy_experience.py",
               policy: "engine/neuralweb/market_memory_population.py",
               census: "engine/neuralweb/market_memory_population_v2.py",
               census.owner: "scripts/accrue_market_memory_spy_experience_v2.py",
               census.technical: "scripts/capture_market_memory_technicals_v2.py",
               census.sources: "engine/neuralweb/market_memory_sources_spy.py",
               census.kernel: "engine/neuralweb/market_memory_source_kernel.py",
               census.accrual: "engine/neuralweb/market_memory_experience_accrual.py",
               census.nyse_calendar: "lib/nyse_calendar.py"}
    if any(Path(module.__file__).resolve() != repository / relative
           for module, relative in modules.items()):
        raise installed.MarketMemoryExperienceCliError("v2 diagnostic imports differ from installed checkout")


def diagnose_population_v2(repository_root, *, experience_root, source_root,
                           technicals_v2_root, through_session):
    supplied = tuple(Path(path) for path in
                     (repository_root, experience_root, source_root, technicals_v2_root))
    if supplied != _ROOTS or any(path.resolve() != path for path in supplied):
        raise installed.MarketMemoryExperienceCliError("v2 diagnostic requires exact installed roots")
    repository = supplied[0]
    if _ROOT != repository:
        raise installed.MarketMemoryExperienceCliError("v2 diagnostic must execute the installed CLI")
    _check_imports(repository)
    verify = lambda: installed._verified_repository_commit(repository, extra_inputs=_CLOSURE)
    commit = verify()
    from engine.neuralweb import market_memory_population as policy
    from engine.neuralweb import market_memory_population_v2 as census
    census._session(through_session)

    class OperatorPolicy:
        def authorize_population_manifest(self, *, repository_root, experience_root,
                                          through_session: str, registration_id, store_id):
            if (repository_root != str(repository) or experience_root != str(supplied[1])
                    or through_session != requested_session or store_id is not None):
                raise policy.MarketMemoryPopulationAccessError("v2 operator scope mismatch")
            # Scope-only unbound grant performs no private owner I/O. The
            # native reader validates actual registration/marker/records next.
            if registration_id is not None:
                if registration_id != _REGISTRATION or verify() != commit:
                    raise policy.MarketMemoryPopulationAccessError("installed v2 registration/source changed")
                _check_imports(repository)
            return policy.PopulationAccessGrant(
                policy.POPULATION_ACCESS_POLICY_VERSION,
                "operator.readonly_w2c_v2_census", True,
                registration_id=registration_id, store_id=None,
                limitations=("internal_operator_metadata_only", "no_study_or_label_admission",
                             "no_fit_or_customer_redistribution", "v2_has_no_native_experience_store_id"))

    requested_session = through_session
    manifest = census.read_population_v2(
        repository, experience_root=supplied[1], source_root=supplied[2],
        technicals_v2_root=supplied[3], through_session=through_session, policy=OperatorPolicy())
    return {"schema": "market_memory.operator_v2_population_diagnostic.v1",
            "deployed_commit": commit, "scope": "internal_operator_outcome_blind_v2_census",
            "operational_study_admission": False, "manifest": manifest}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=_ROOTS[0])
    parser.add_argument("--experience-root", type=Path, default=_ROOTS[1])
    parser.add_argument("--source-root", type=Path, default=_ROOTS[2])
    parser.add_argument("--technicals-v2-root", type=Path, default=_ROOTS[3])
    parser.add_argument("--through-session", required=True)
    args = parser.parse_args(argv)
    result = diagnose_population_v2(**vars(args))
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
