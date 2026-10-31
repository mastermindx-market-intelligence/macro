"""The isolated outside-checkout bootstrap refuses mutable import paths."""
from tests.test_qledger_runner_bootstrap import bootstrap  # noqa: F401
from tests.test_qledger_conversion_candidate import fixture, conversion_invocation  # noqa: F401


def test_checkout_path_insertion_refuses_before_qualified_owner_import(bootstrap):
    run,_,owner,repo=bootstrap
    driver=owner.parent/'driver.py'
    driver.write_text(driver.read_text().replace('operational=False',
        'sys.path.insert(0,str(repo))\noperational=False',1))
    run('reader','mutable checkout import path is active')
    assert not (owner/'bundle/IMPORT_OCCURRED').exists()
