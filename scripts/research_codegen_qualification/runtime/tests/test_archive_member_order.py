"""Pinned publisher member-order regression; fictional bytes, no host effects."""
import io
import tarfile

import pytest
import test_runsc_install as fixtures

mod = fixtures.mod


def archive(entries):
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:bz2") as tf:
        for name, data in entries:
            item = tarfile.TarInfo(name)
            item.mode = 0o755
            if data is None:
                item.type = tarfile.DIRTYPE
                tf.addfile(item)
            else:
                item.size = len(data)
                tf.addfile(item, io.BytesIO(data))
    return out.getvalue()


def regulars():
    return [(mod.OPTIONAL_SHIM_MEMBER, fixtures.SHIM_PAYLOAD),
            ("runsc", fixtures.MEMBER_PAYLOADS["runsc"])] + [
        (name, fixtures.MEMBER_PAYLOADS[name]) for name in fixtures.SIDE_SIZES]


@pytest.fixture
def scan():
    fx = fixtures.Fixture()
    engine = fx.engine()
    engine.binding = mod.Binding(dict(fx.binding_dict), fixtures.TEST_CONTRACT)
    def call(entries):
        fx.overwrite(fx.archive_path, archive(entries), 0o644)
        result = engine._scan_archive(staging_dir=None)
        assert fx.runner.calls == []
        assert fx.config_now() == fixtures.CONFIG_BYTES
        return result
    try:
        yield call
    finally:
        fx.close()


@pytest.mark.parametrize("position", [0, 1, 2, 7])
@pytest.mark.parametrize("directory", ["gvisor-bin", "gvisor-bin/"])
def test_optional_directory_is_independent_of_member_order(scan, position, directory):
    # Publisher receipt: shim, runsc, directory, then five sidecars (position2).
    entries = regulars()
    entries.insert(position, (directory, None))
    facts = scan(entries)
    assert set(facts["members_installed"]) == set(fixtures.TEST_MEMBER_SIZES)
    assert facts["shim_installed"] is False


@pytest.mark.parametrize("first,second", [
    ("gvisor-bin", "gvisor-bin"), ("gvisor-bin/", "gvisor-bin/"),
    ("gvisor-bin", "gvisor-bin/"), ("gvisor-bin/", "gvisor-bin")])
def test_duplicate_directory_stays_refused_across_aliases(scan, first, second):
    entries = regulars()
    entries.insert(2, (first, None))
    entries.append((second, None))
    with pytest.raises(mod.InstallError) as exc:
        scan(entries)
    assert exc.value.category == "ARCHIVE_MEMBER_DUPLICATE"


@pytest.mark.parametrize("name", ["other", "gvisor-bin/nested", "./gvisor-bin", "/gvisor-bin", "../gvisor-bin"])
def test_unexpected_directory_stays_refused_after_regular_files(scan, name):
    entries = regulars()
    entries.insert(2, (name, None))
    with pytest.raises(mod.InstallError) as exc:
        scan(entries)
    assert exc.value.category in ("ARCHIVE_MEMBER_UNEXPECTED", "ARCHIVE_MEMBER_UNSAFE")
