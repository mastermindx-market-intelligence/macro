"""Pinned publisher member-order regression; fictional bytes, no host effects."""
import io
from pathlib import Path
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


def test_directory_spelling_as_regular_file_stays_refused(scan):
    # DIRTYPE names normalize on tarfile read; REGTYPE keeps this spelling.
    with pytest.raises(mod.InstallError) as exc:
        scan(regulars() + [("gvisor-bin/", b"not a directory")])
    assert exc.value.category == "ARCHIVE_MEMBER_UNEXPECTED"


def test_order_tolerance_stages_only_the_six_bound_members():
    fx = fixtures.Fixture()
    try:
        engine = fx.engine()
        engine.binding = mod.Binding(dict(fx.binding_dict), fixtures.TEST_CONTRACT)
        entries = regulars()
        entries.insert(2, ("gvisor-bin/", None))
        fx.overwrite(fx.archive_path, archive(entries), 0o644)
        stage = Path(fx.version_dir() + ".review-stage")
        (stage / mod.GVISOR_BIN_DIR).mkdir(parents=True)
        engine._scan_archive(staging_dir=str(stage))
        files = {str(p.relative_to(stage)) for p in stage.rglob("*") if p.is_file()}
        assert files == set(fixtures.TEST_MEMBER_SIZES)
        assert not (stage / mod.OPTIONAL_SHIM_MEMBER).exists()
        assert not fx.runner.calls
        assert fx.config_now() == fixtures.CONFIG_BYTES
    finally:
        fx.close()
