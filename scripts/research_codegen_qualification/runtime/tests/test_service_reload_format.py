"""Official systemd rendered-format fixtures; no systemctl or service effects."""
import pytest
import test_runsc_install as fixtures

mod = fixtures.mod


@pytest.mark.parametrize('value,expected', [
    ('{ path=/bin/kill ; argv[]=/bin/kill -s HUP $MAINPID ; ignore_errors=no ; '
     'start_time=[n/a] ; stop_time=[n/a] ; pid=0 ; code=(null) ; status=0/0 }', True),
    ('{ path=/usr/bin/kill ; argv[]=/usr/bin/kill -s HUP $MAINPID ; ignore_errors=no }', True),
    ('{ path=/bin/kill ; argv[]=/bin/kill -s HUP 1 ; ignore_errors=no }', False),
    ('{ path=/bin/kill ; argv[]=/bin/kill -s HUP $MAINPID 1 ; ignore_errors=no }', False),
    ('{ path=/bin/kill ; argv[]=/bin/kill -s HUP $MAINPID ; ignore_errors=yes }', False),
    ('{ path=/bin/echo ; argv=["/bin/echo" "HUP"] ; ignore_errors=no }', False),
    ('{ path=/bin/kill ; argv=["/bin/kill" "-s" "HUP" "$MAINPID"] ; ignore_errors=no }', False),
    ('{ path=/bin/kill ; argv[]=/bin/kill -s HUP $MAINPID ; ignore_errors=no } '
     '{ path=/bin/false ; argv[]=/bin/false ; ignore_errors=no }', False),
])
def test_service_check_uses_single_qualified_rendered_reload(value, expected):
    engine = mod.InstallEngine.__new__(mod.InstallEngine)
    data = ('ActiveState=active\nCanReload=yes\nExecReload=' + value + '\n').encode()
    engine._run = lambda argv, role: {'out': data}
    engine._service_facts()
    assert engine.exec_reload_hup is expected


@pytest.mark.parametrize('key', mod.SYSTEMD_ALLOWED_KEYS)
def test_duplicate_service_properties_refuse_instead_of_overwriting(key):
    engine = mod.InstallEngine.__new__(mod.InstallEngine)
    with pytest.raises(mod.InstallError, match='SERVICE_FACT_DUPLICATE'):
        engine._parse_show((key + '=first\n' + key + '=second\n').encode())
