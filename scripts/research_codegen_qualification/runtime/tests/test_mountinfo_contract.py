"""Pytest tests for mountinfo_contract. Literal inert records; no host reads."""

import hashlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mountinfo_contract import (
    FIXED_TARGET_MOUNTPOINT,
    SCHEMA_VERSION,
    STATE_MATCHED,
    MountInfoRefused,
    parse_mountinfo,
)


def _make_line(
    mount_id=99, parent_id=1, major=0, minor=50, root="/",
    mountpoint="/sys/fs/cgroup",
    options="rw,nosuid,nodev,noexec,relatime",
    optional_fields="", fs_type="cgroup2", source="cgroup2",
    superoptions="rw,nosuid,nodev,noexec,relatime",
):
    opt = (" " + optional_fields) if optional_fields else ""
    return (f"{mount_id} {parent_id} {major}:{minor} {root} {mountpoint} "
            f"{options}{opt} - {fs_type} {source} {superoptions}\n")


def _expected_dict(raw_bytes, mount_id=99, device=(0, 50)):
    return {
        "schema": SCHEMA_VERSION,
        "state": STATE_MATCHED,
        "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "mount_id": mount_id,
        "device": [device[0], device[1]],
        "fs_root_is_slash": True,
        "host_namespace_verified": False,
        "full_host_hierarchy_verified": False,
        "enforcement_proven": False,
        "candidate_admission": False,
    }


# --- Success ---

def test_ok_basic():
    raw = _make_line().encode("ascii")
    assert parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50)) == _expected_dict(raw)


def test_ok_keys_in_order():
    raw = _make_line().encode("ascii")
    r = parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert list(r.keys()) == [
        "schema", "state", "raw_sha256", "mount_id", "device",
        "fs_root_is_slash", "host_namespace_verified",
        "full_host_hierarchy_verified", "enforcement_proven", "candidate_admission",
    ]


def test_ok_schema_strings():
    raw = _make_line().encode("ascii")
    r = parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert r["schema"] == "rf.mountinfo_declaration.v1"
    assert r["state"] == "MATCHED_DECLARATIONS_ONLY"


def test_ok_unknown_optional_tags():
    raw = _make_line(optional_fields="shared:1 master:5 weird:foo").encode("ascii")
    assert parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50)) == _expected_dict(raw)


def test_ok_unrelated_escaped_path():
    other = _make_line(mount_id=10, parent_id=1, major=1, minor=1,
                       mountpoint="/mnt/My\\040Disk\\011sub")
    target = _make_line(mount_id=99, parent_id=1, major=0, minor=50)
    raw = (other + target).encode("ascii")
    assert parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50)) == _expected_dict(raw)


def test_ok_root_escape_in_non_target():
    other = _make_line(mount_id=10, parent_id=1, major=1, minor=1,
                       root="/foo\\040bar", mountpoint="/mnt/something")
    target = _make_line(mount_id=99, parent_id=1, major=0, minor=50)
    raw = (other + target).encode("ascii")
    assert parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50)) == _expected_dict(raw)


def test_ok_mount_id_boundary_max():
    m = (1 << 31) - 1
    raw = _make_line(mount_id=m, parent_id=1, major=0, minor=50).encode("ascii")
    assert parse_mountinfo(raw, expected_mount_id=m, expected_device=(0, 50))["mount_id"] == m


def test_ok_device_boundary_max():
    d = (1 << 32) - 1
    raw = _make_line(mount_id=99, parent_id=1, major=d, minor=d).encode("ascii")
    assert parse_mountinfo(raw, expected_mount_id=99, expected_device=(d, d))["device"] == [d, d]


def test_ok_self_parent():
    raw = _make_line(mount_id=99, parent_id=99, major=0, minor=50).encode("ascii")
    assert parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50)) == _expected_dict(raw)


# --- Target/field mismatch ---

def test_bad_fs():
    raw = _make_line(fs_type="cgroup", source="tmpfs").encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "filesystem:not_cgroup2"


def test_bad_root():
    raw = _make_line(root="/subpath").encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "root:not_slash"


def test_bad_mid():
    raw = _make_line(mount_id=99).encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=100, expected_device=(0, 50))
    assert exc.value.reason == "id:mount_mismatch"


def test_bad_dev_major():
    raw = _make_line(major=0, minor=50).encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(1, 50))
    assert exc.value.reason == "device:mismatch"


def test_bad_dev_minor():
    raw = _make_line(major=0, minor=50).encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 51))
    assert exc.value.reason == "device:mismatch"


# --- Ambiguous / nested ---

def test_dup_target():
    raw = (_make_line(mount_id=10, parent_id=1, major=1, minor=1, mountpoint="/")
           + _make_line(mount_id=20, parent_id=1, major=0, minor=50)
           + _make_line(mount_id=30, parent_id=20, major=0, minor=51)).encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=20, expected_device=(0, 50))
    assert exc.value.reason == "target:duplicate"


def test_dup_id():
    raw = (_make_line(mount_id=10, parent_id=1, major=1, minor=1, mountpoint="/")
           + _make_line(mount_id=10, parent_id=10, major=0, minor=50)).encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=10, expected_device=(0, 50))
    assert exc.value.reason == "id:duplicate"


def test_nested():
    raw = (_make_line(mount_id=99, parent_id=1, major=0, minor=50)
           + _make_line(mount_id=100, parent_id=99, major=0, minor=51,
                        mountpoint="/sys/fs/cgroup/subtree")).encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "target:nested"


def test_missing_target():
    raw = _make_line(mountpoint="/mnt/elsewhere").encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "target:missing"


# --- Escape traps ---

def test_octal_slash_target():
    raw = _make_line(mountpoint="\\057sys\\057fs\\057cgroup").encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "escape:unknown"


def test_octal_slash_nested():
    raw = (_make_line(mount_id=99, parent_id=1, major=0, minor=50)
           + _make_line(mount_id=100, parent_id=99, major=0, minor=51,
                        mountpoint="/sys\\057fs\\057cgroup/sub")).encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "escape:unknown"


def test_unk_escape_mountpoint():
    raw = _make_line(mountpoint="/sys/fs/cgroup\\999").encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "escape:unknown"


def test_unk_escape_root():
    raw = _make_line(root="/\\999").encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "escape:unknown"


def test_trail_bs_mountpoint():
    raw = _make_line(mountpoint="/sys/fs/cgroup\\").encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "escape:trailing_backslash"


def test_trail_bs_root():
    raw = _make_line(root="/\\").encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "escape:trailing_backslash"


def test_oversized_escape():
    raw = _make_line(mountpoint="/sys/fs/cgroup\\12345").encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "escape:unknown"


# --- Structural traps ---

def test_no_sep():
    bad = ("99 1 0:50 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime "
           "cgroup2 cgroup2 rw,nosuid,nodev,noexec,relatime\n")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(bad.encode("ascii"), expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "separator:missing"


def test_multi_sep():
    bad = ("99 1 0:50 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime "
           "- cgroup2 - rw,nosuid,nodev,noexec,relatime\n")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(bad.encode("ascii"), expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "separator:multiple"


def test_few_trailing():
    bad = ("99 1 0:50 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime "
           "- cgroup2 cgroup2\n")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(bad.encode("ascii"), expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "fields:trailing_count"


def test_few_prefix():
    bad = ("99 1 0:50 / /sys/fs/cgroup "
           "- cgroup2 cgroup2 rw,nosuid,nodev,noexec,relatime\n")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(bad.encode("ascii"), expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "fields:prefix_count"


def test_hex_mid():
    bad = ("0x63 1 0:50 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime "
           "- cgroup2 cgroup2 rw,nosuid,nodev,noexec,relatime\n")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(bad.encode("ascii"), expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "numeric:not_decimal"


def test_signed_mid():
    bad = ("-99 1 0:50 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime "
           "- cgroup2 cgroup2 rw,nosuid,nodev,noexec,relatime\n")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(bad.encode("ascii"), expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "numeric:not_decimal"


def test_zero_mid():
    bad = ("0 1 0:50 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime "
           "- cgroup2 cgroup2 rw,nosuid,nodev,noexec,relatime\n")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(bad.encode("ascii"), expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "id:mount_not_positive_int"


def test_dev_no_colon():
    bad = ("99 1 0/50 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime "
           "- cgroup2 cgroup2 rw,nosuid,nodev,noexec,relatime\n")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(bad.encode("ascii"), expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "device:major_minor_shape"


def test_dev_multi_colon():
    bad = ("99 1 0:50:0 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime "
           "- cgroup2 cgroup2 rw,nosuid,nodev,noexec,relatime\n")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(bad.encode("ascii"), expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "device:major_minor_shape"


def test_dev_empty_major():
    bad = ("99 1 :50 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime "
           "- cgroup2 cgroup2 rw,nosuid,nodev,noexec,relatime\n")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(bad.encode("ascii"), expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "device:major_minor_shape"


def test_dev_empty_minor():
    bad = ("99 1 0: / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime "
           "- cgroup2 cgroup2 rw,nosuid,nodev,noexec,relatime\n")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(bad.encode("ascii"), expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "device:major_minor_shape"


def test_non_abs_root():
    raw = _make_line(root="\\040").encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "root:not_absolute"


def test_non_abs_mp():
    raw = _make_line(mountpoint="\\040").encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "mountpoint:not_absolute"


# --- Input container types ---

def test_bytearray():
    raw = bytearray(_make_line().encode("ascii"))
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "type:bytearray_rejected"


def test_bytes_subclass():
    class MyBytes(bytes):
        pass
    raw = MyBytes(_make_line().encode("ascii"))
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "type:bytes_subclass_rejected"


def test_memoryview():
    raw = memoryview(_make_line().encode("ascii"))
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "type:bytes_required"


def test_str_input():
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo("not bytes", expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "type:bytes_required"


def test_none_input():
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(None, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "type:bytes_required"


# --- Input bounds ---

def test_size_exceeded():
    lines = [_make_line(mount_id=1000 + i, parent_id=1, major=1, minor=1,
                        mountpoint="/" + "x" * 1000) for i in range(300)]
    raw = "".join(lines).encode("ascii")
    assert len(raw) > 262144
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "size:bytes_exceeded"


def test_lines_exceeded():
    lines = [_make_line(mount_id=1000 + i, parent_id=1, major=1, minor=1,
                        mountpoint="/some/mount") for i in range(2049)]
    raw = "".join(lines).encode("ascii")
    assert len(raw) <= 262144
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "lines:count_exceeded"


def test_line_too_long():
    line = _make_line(mountpoint="/" + "x" * 4080)
    assert len(line) > 4096
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(line.encode("ascii"), expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "line:length_exceeded"


def test_non_ascii():
    bad = (b"99 1 0:50 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime "
           b"- cgroup2 cgroup2 rw,nosuid,nodev,noexec,relatime\xc0\n")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(bad, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "line:non_ascii_printable"


def test_tab_byte():
    bad = (b"99 1 0:50 / /sys/fs/cgroup\trw,nosuid,nodev,noexec,relatime "
           b"- cgroup2 cgroup2 rw,nosuid,nodev,noexec,relatime\n")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(bad, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "line:non_ascii_printable"


def test_no_final_lf():
    raw = _make_line().encode("ascii").rstrip(b"\n")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "line:missing_final_lf"


def test_empty():
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(b"", expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "line:missing_final_lf"


def test_blank_line():
    raw = (_make_line(mount_id=99, parent_id=1, major=0, minor=50) + "\n").encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "line:blank"


def test_ws_line():
    raw = (_make_line(mount_id=99, parent_id=1, major=0, minor=50) + "   \n").encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50))
    assert exc.value.reason == "line:blank"


# --- Expected-arg validation ---

def test_mid_bool_true():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=True, expected_device=(0, 50))
    assert exc.value.reason == "expected:mount_id_type"


def test_mid_bool_false():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=False, expected_device=(0, 50))
    assert exc.value.reason == "expected:mount_id_type"


def test_mid_zero():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=0, expected_device=(0, 50))
    assert exc.value.reason == "expected:mount_id_range"


def test_mid_neg():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=-1, expected_device=(0, 50))
    assert exc.value.reason == "expected:mount_id_range"


def test_mid_overflow():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=1 << 31, expected_device=(0, 50))
    assert exc.value.reason == "expected:mount_id_range"


def test_mid_str():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id="99", expected_device=(0, 50))
    assert exc.value.reason == "expected:mount_id_type"


def test_mid_none():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=None, expected_device=(0, 50))
    assert exc.value.reason == "expected:mount_id_type"


def test_dev_list():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=[0, 50])
    assert exc.value.reason == "expected:device_type"


def test_dev_len1():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0,))
    assert exc.value.reason == "expected:device_shape"


def test_dev_len3():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 50, 100))
    assert exc.value.reason == "expected:device_shape"


def test_dev_bool_major():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(True, 50))
    assert exc.value.reason == "expected:device_type"


def test_dev_bool_minor():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, True))
    assert exc.value.reason == "expected:device_type"


def test_dev_neg_major():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(-1, 50))
    assert exc.value.reason == "expected:device_range"


def test_dev_overflow_major():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(1 << 32, 50))
    assert exc.value.reason == "expected:device_range"


def test_dev_overflow_minor():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=(0, 1 << 32))
    assert exc.value.reason == "expected:device_range"


def test_dev_str_elems():
    raw = _make_line().encode("ascii")
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(raw, expected_mount_id=99, expected_device=("0", "50"))
    assert exc.value.reason == "expected:device_type"


# --- Secrecy / redaction ---

def test_no_leak_secret():
    secret_mp = "/DO_NOT_LEAK_SECRET_PATH_XYZZY_Q"
    secret_root = "/SECRET_ROOT_MARKER_QQ"
    line = _make_line(mountpoint=secret_mp, root=secret_root)
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(line.encode("ascii"), expected_mount_id=99, expected_device=(0, 50))
    msg = str(exc.value)
    assert "DO_NOT_LEAK" not in msg
    assert "XYZZY" not in msg
    assert secret_mp not in msg
    assert "SECRET_ROOT" not in msg
    assert secret_root not in msg
    assert exc.value.reason not in (secret_mp, secret_root, "secret", "SECRET")


def test_no_leak_decoy():
    decoy = "/PRIVATE_KEY_DO_NOT_LEAK\\057abc"
    line = _make_line(mountpoint=decoy)
    with pytest.raises(MountInfoRefused) as exc:
        parse_mountinfo(line.encode("ascii"), expected_mount_id=99, expected_device=(0, 50))
    msg = str(exc.value)
    assert "PRIVATE_KEY" not in msg
    assert "DO_NOT_LEAK" not in msg
    assert decoy not in msg


# --- Reason catalogue ---

def test_reason_closed():
    with pytest.raises(AssertionError):
        MountInfoRefused("not-a-real-reason")


def test_fixed_mp_const():
    assert FIXED_TARGET_MOUNTPOINT == "/sys/fs/cgroup"