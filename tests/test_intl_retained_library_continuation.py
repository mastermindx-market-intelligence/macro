"""Discriminate the actual normal-publisher retained Library continuation seam."""
import ast
import sys
import types
from pathlib import Path
from unittest.mock import Mock

import pytest
from scripts import build_intl as builder


def test_normal_build_does_not_read_retained_library(monkeypatch):
    monkeypatch.delitem(sys.modules, 'lib.intl_library_retained', raising=False)
    assert builder._retained_library_for_render(None) is None


@pytest.mark.parametrize('lane', ['', 'nightly', 'collect', 'intraday', 'unknown'])
def test_reuse_requires_explicit_render_lane(monkeypatch, lane):
    monkeypatch.setenv('COLLECT_LANE', lane)
    monkeypatch.delenv('US_LANE', raising=False)
    with pytest.raises(ValueError, match='explicit render lane'):
        builder._retained_library_for_render({'receipt': 'not read'})


@pytest.mark.parametrize(('lane', 'legacy'), [('render', ''), ('engine-render', ''), ('', 'render')])
def test_render_receipt_reaches_native_byte_reader(monkeypatch, tmp_path, lane, legacy):
    monkeypatch.setenv('COLLECT_LANE', lane)
    monkeypatch.setenv('US_LANE', legacy)
    receipt = {'caller': 'original completed normal build'}
    native = {'buy': [{'ticker': 'native-output'}]}
    reader = Mock(return_value=native)
    monkeypatch.setitem(sys.modules, 'lib.intl_library_retained', types.SimpleNamespace(load_retained_library=reader))
    monkeypatch.setattr(builder.config, 'data_dir', lambda: tmp_path/'data')
    monkeypatch.setattr(builder.config, 'load', lambda: {'storage': {'site_dir': str(tmp_path/'site')}})
    assert builder._retained_library_for_render(receipt) is native
    reader.assert_called_once_with(data_root=tmp_path/'data', site_root=tmp_path/'site', receipt=receipt)


def test_rejected_receipt_returns_before_any_normal_builder_write(monkeypatch):
    def reject(_receipt):
        raise ValueError('changed committed bytes')
    monkeypatch.setattr(builder, '_retained_library_for_render', reject)
    invalidate = Mock(side_effect=AssertionError('must not write before receipt acceptance'))
    run = Mock(side_effect=AssertionError('must not run engines after receipt rejection'))
    monkeypatch.setitem(sys.modules, 'lib.intl_generation_publication',
                        types.SimpleNamespace(publish_unavailable_generation=invalidate))
    monkeypatch.setitem(sys.modules, 'engine.intl_run', types.SimpleNamespace(run=run))
    # The real main rejects before invalidation/engine execution and never falls
    # through to a second analysis. No synthetic VM or substituted engine result.
    assert builder.main(retained_library_receipt={'invalid': True}) == 1
    invalidate.assert_not_called()
    run.assert_not_called()


def _actual_library_phase():
    tree = ast.parse(Path(builder.__file__).read_text())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    phase = next(n for n in ast.walk(main) if isinstance(n, ast.Try) and
                 any(isinstance(s, ast.If) and isinstance(s.test, ast.Compare) and
                     isinstance(s.test.left, ast.Name) and s.test.left.id == 'retained_library_receipt'
                     for s in n.body))
    return compile(ast.fix_missing_locations(ast.Module(body=[phase], type_ignores=[])), builder.__file__, 'exec')


def test_actual_library_phase_reuses_verified_result_without_analysis(monkeypatch):
    analyze = Mock(side_effect=AssertionError('must not analyze completed library again'))
    monkeypatch.setitem(sys.modules, 'scripts.build_intl_library', types.SimpleNamespace(main=analyze))
    native = {'buy': [{'ticker': 'original-native-result'}]}
    ns = {'retained_library_receipt': {'verified': True}, 'retained_setups': native,
          'alpha': None, 'log': Mock()}
    exec(_actual_library_phase(), ns)
    assert ns['setups'] is native
    analyze.assert_not_called()


def test_actual_normal_phase_still_uses_incumbent_library(monkeypatch):
    native = {'buy': []}
    analyze = Mock(return_value=native)
    # from scripts import binds the package attribute if already imported.
    import scripts
    module = types.SimpleNamespace(main=analyze)
    monkeypatch.setitem(sys.modules, 'scripts.build_intl_library', module)
    monkeypatch.setattr(scripts, 'build_intl_library', module, raising=False)
    alpha = {'native': 'alpha'}
    ns = {'retained_library_receipt': None, 'retained_setups': None, 'alpha': alpha, 'log': Mock()}
    exec(_actual_library_phase(), ns)
    assert ns['setups'] is native
    analyze.assert_called_once_with(alpha=alpha)
