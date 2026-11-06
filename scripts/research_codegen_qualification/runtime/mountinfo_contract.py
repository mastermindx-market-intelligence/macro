"""Pure Python3 mountinfo contract parser for Research Factory host-resource
observation preparation.

Parses kernel mountinfo data per the documented format
(https://docs.kernel.org/filesystems/proc.html section 3.5) and returns a
closed, redacted declaration describing the cgroup2 mount under
/sys/fs/cgroup. No I/O on import; no host observation.

API:
    parse_mountinfo(raw: bytes, *, expected_mount_id: int,
                    expected_device: tuple[int, int]) -> dict

Raises:
    MountInfoRefused with one of a fixed set of reason strings. Reason
    strings never echo the supplied bytes, paths, or identifiers.
"""

import hashlib

SCHEMA_VERSION = "rf.mountinfo_declaration.v1"
STATE_MATCHED = "MATCHED_DECLARATIONS_ONLY"
FIXED_TARGET_MOUNTPOINT = "/sys/fs/cgroup"
TARGET_FS_TYPE = "cgroup2"
REQUIRED_FS_ROOT = "/"

MAX_BYTES = 262144
MAX_LINES = 2048
MAX_LINE_LEN = 4096

MOUNT_ID_MIN = 1
MOUNT_ID_MAX = (1 << 31) - 1
DEVICE_INT_MIN = 0
DEVICE_INT_MAX = (1 << 32) - 1

_PARENT_ID_MIN = 0
_PARENT_ID_MAX = (1 << 31) - 1

_STANDARD_ESCAPES = ("\\040", "\\011", "\\012", "\\134")


class MountInfoRefused(Exception):
    """Raised when mountinfo parsing or validation fails.

    The reason string is one of a fixed set of literals; no raw data is
    echoed in the message. Construction with an unknown reason is a
    programming error and raises AssertionError.
    """

    _ALLOWED_REASONS = frozenset({
        "type:bytes_required",
        "type:bytes_subclass_rejected",
        "type:bytearray_rejected",
        "size:bytes_exceeded",
        "lines:count_exceeded",
        "line:length_exceeded",
        "line:non_ascii_printable",
        "line:missing_final_lf",
        "line:blank",
        "id:mount_not_positive_int",
        "id:parent_out_of_range",
        "device:major_minor_shape",
        "device:major_out_of_range",
        "device:minor_out_of_range",
        "separator:missing",
        "separator:multiple",
        "fields:prefix_count",
        "fields:optional_invalid",
        "fields:trailing_count",
        "numeric:not_decimal",
        "root:not_absolute",
        "mountpoint:not_absolute",
        "escape:unknown",
        "escape:trailing_backslash",
        "target:missing",
        "target:duplicate",
        "target:nested",
        "id:duplicate",
        "filesystem:not_cgroup2",
        "root:not_slash",
        "id:mount_mismatch",
        "device:mismatch",
        "expected:mount_id_type",
        "expected:mount_id_range",
        "expected:device_type",
        "expected:device_shape",
        "expected:device_range",
    })

    def __init__(self, reason):
        if reason not in self._ALLOWED_REASONS:
            raise AssertionError("unknown reason: " + repr(reason))
        super().__init__(reason)
        self.reason = reason


def _check_raw_bytes(raw):
    """Validate the raw bytes container. Returns the bytes unchanged."""
    if type(raw) is bytearray:
        raise MountInfoRefused("type:bytearray_rejected")
    if type(raw) is not bytes and not issubclass(type(raw), bytes):
        raise MountInfoRefused("type:bytes_required")
    if type(raw) is not bytes:
        raise MountInfoRefused("type:bytes_subclass_rejected")
    if len(raw) == 0:
        raise MountInfoRefused("line:missing_final_lf")
    if len(raw) > MAX_BYTES:
        raise MountInfoRefused("size:bytes_exceeded")
    if raw[-1:] != b"\n":
        raise MountInfoRefused("line:missing_final_lf")
    return raw


def _check_expected_mount_id(value):
    """Validate the expected_mount_id parameter."""
    if type(value) is not int:
        raise MountInfoRefused("expected:mount_id_type")
    if not (MOUNT_ID_MIN <= value <= MOUNT_ID_MAX):
        raise MountInfoRefused("expected:mount_id_range")
    return value


def _check_expected_device(value):
    """Validate the expected_device parameter."""
    if type(value) is not tuple:
        raise MountInfoRefused("expected:device_type")
    if len(value) != 2:
        raise MountInfoRefused("expected:device_shape")
    major, minor = value
    if type(major) is not int:
        raise MountInfoRefused("expected:device_type")
    if type(minor) is not int:
        raise MountInfoRefused("expected:device_type")
    if not (DEVICE_INT_MIN <= major <= DEVICE_INT_MAX):
        raise MountInfoRefused("expected:device_range")
    if not (DEVICE_INT_MIN <= minor <= DEVICE_INT_MAX):
        raise MountInfoRefused("expected:device_range")
    return (major, minor)


def _decode_path_escapes(s):
    """Decode kernel mountinfo standard escape sequences in a path field.

    Recognizes only the four standard escapes \\040, \\011, \\012, \\134.
    Any other escape sequence is rejected as malformed so it cannot hide
    the target mountpoint or a nested mount.
    """
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        if i + 4 > n:
            raise MountInfoRefused("escape:trailing_backslash")
        esc = s[i:i + 4]
        if esc == "\\040":
            out.append(" ")
        elif esc == "\\011":
            out.append("\t")
        elif esc == "\\012":
            out.append("\n")
        elif esc == "\\134":
            out.append("\\")
        else:
            raise MountInfoRefused("escape:unknown")
        i += 4
    return "".join(out)


def _parse_uint_digits(s):
    """Parse a non-empty decimal digit string into a non-negative int."""
    if not s or len(s) > 10 or (len(s) > 1 and s[0] == "0"):
        raise MountInfoRefused("numeric:not_decimal")
    for ch in s:
        if not ("0" <= ch <= "9"):
            raise MountInfoRefused("numeric:not_decimal")
    return int(s)


def _split_on_separator(line):
    """Split a mountinfo line into (prefix_fields, trailing_fields).

    The single '-' separator divides the prefix (6 fixed fields plus zero+)
    optional fields) from the trailing fields (exactly 3: filesystem,
    source, superoptions).
    """
    parts = line.split(" ")
    sep_indices = [i for i, p in enumerate(parts) if p == "-"]
    if not sep_indices:
        raise MountInfoRefused("separator:missing")
    if len(sep_indices) > 1:
        raise MountInfoRefused("separator:multiple")
    sep_idx = sep_indices[0]
    if sep_idx < 6:
        raise MountInfoRefused("fields:prefix_count")
    prefix = parts[:sep_idx]
    trailing = parts[sep_idx + 1:]
    if len(trailing) != 3:
        raise MountInfoRefused("fields:trailing_count")
    return prefix, trailing


def parse_mountinfo(raw, *, expected_mount_id, expected_device):
    """Parse mountinfo bytes and validate the cgroup2 mount.

    Returns a closed, redacted dict describing the matched target. The
    fixed consumer mountpoint is /sys/fs/cgroup; the caller does not
    supply a path. Returns a dict shaped by rf.mountinfo_declaration.v1.

    On any structural, type, bounds, escape, or mismatch problem, raises
    MountInfoRefused with a fixed reason string.
    """
    raw_b = _check_raw_bytes(raw)
    exp_mid = _check_expected_mount_id(expected_mount_id)
    exp_dev = _check_expected_device(expected_device)

    # Split into per-line byte chunks. The trailing LF is required.
    lines_bytes = raw_b.split(b"\n")
    # The final element must be empty (because of the required trailing LF).
    if lines_bytes[-1] != b"":
        raise MountInfoRefused("line:missing_final_lf")
    lines_bytes = lines_bytes[:-1]

    if len(lines_bytes) > MAX_LINES:
        raise MountInfoRefused("lines:count_exceeded")

    records = []
    seen_ids = set()
    for lb in lines_bytes:
        # Reject blank lines (truly empty or whitespace-only).
        if len(lb) == 0:
            raise MountInfoRefused("line:blank")
        if len(lb) > MAX_LINE_LEN:
            raise MountInfoRefused("line:length_exceeded")
        # ASCII printable only (0x20..0x7E); LF was split away.
        for b in lb:
            if not (0x20 <= b <= 0x7E):
                raise MountInfoRefused("line:non_ascii_printable")
        # Whitespace-only line is also blank.
        all_space = True
        for b in lb:
            if b != 0x20:
                all_space = False
                break
        if all_space:
            raise MountInfoRefused("line:blank")

        line = lb.decode("ascii")
        prefix, trailing = _split_on_separator(line)

        # Optional fields are anything between the 6 fixed prefix and '-'.
        optional = prefix[6:]
        for opt in optional:
            if not opt:
                raise MountInfoRefused("fields:optional_invalid")

        # Fixed prefix: mount_id, parent_id, major:minor, root, mountpoint, options
        mount_id_s = prefix[0]
        parent_id_s = prefix[1]
        majmin_s = prefix[2]
        root_s = prefix[3]
        mountpoint_s = prefix[4]
        options_s = prefix[5]
        if not options_s:
            raise MountInfoRefused("fields:prefix_count")

        # mount_id: strict decimal, bounded, unique within payload.
        mount_id = _parse_uint_digits(mount_id_s)
        if not (MOUNT_ID_MIN <= mount_id <= MOUNT_ID_MAX):
            raise MountInfoRefused("id:mount_not_positive_int")
        if mount_id in seen_ids:
            raise MountInfoRefused("id:duplicate")
        seen_ids.add(mount_id)

        # parent_id: strict decimal, bounded non-negative.
        parent_id = _parse_uint_digits(parent_id_s)
        if not (_PARENT_ID_MIN <= parent_id <= _PARENT_ID_MAX):
            raise MountInfoRefused("id:parent_out_of_range")

        # major:minor must be exactly "<digits>:<digits>".
        if majmin_s.count(":") != 1:
            raise MountInfoRefused("device:major_minor_shape")
        m_s, n_s = majmin_s.split(":")
        if not m_s or not n_s:
            raise MountInfoRefused("device:major_minor_shape")
        major = _parse_uint_digits(m_s)
        if not (DEVICE_INT_MIN <= major <= DEVICE_INT_MAX):
            raise MountInfoRefused("device:major_out_of_range")
        minor = _parse_uint_digits(n_s)
        if not (DEVICE_INT_MIN <= minor <= DEVICE_INT_MAX):
            raise MountInfoRefused("device:minor_out_of_range")

        # root and mountpoint: decode only the 4 standard escapes.
        root = _decode_path_escapes(root_s)
        if not root.startswith("/"):
            raise MountInfoRefused("root:not_absolute")
        mountpoint = _decode_path_escapes(mountpoint_s)
        if not mountpoint.startswith("/"):
            raise MountInfoRefused("mountpoint:not_absolute")

        # Trailing fields: filesystem, source, superoptions.
        fs_type = trailing[0]
        source = trailing[1]
        superoptions = trailing[2]
        if not fs_type or not source or not superoptions:
            raise MountInfoRefused("fields:trailing_count")

        records.append({
            "mount_id": mount_id,
            "parent_id": parent_id,
            "major": major,
            "minor": minor,
            "root": root,
            "mountpoint": mountpoint,
            "options": options_s,
            "fs_type": fs_type,
            "source": source,
            "superoptions": superoptions,
        })

    # Find target records whose mountpoint equals the fixed consumer path.
    target_records = [r for r in records if r["mountpoint"] == FIXED_TARGET_MOUNTPOINT]
    if not target_records:
        raise MountInfoRefused("target:missing")
    if len(target_records) > 1:
        raise MountInfoRefused("target:duplicate")
    target = target_records[0]

    # Reject any nested mountpoint under /sys/fs/cgroup/ (overmounted
    # subtrees are unsupported in this contract).
    nested_prefix = FIXED_TARGET_MOUNTPOINT + "/"
    for r in records:
        if r["mountpoint"].startswith(nested_prefix):
            raise MountInfoRefused("target:nested")

    # Validate the matched target.
    if target["fs_type"] != TARGET_FS_TYPE:
        raise MountInfoRefused("filesystem:not_cgroup2")
    if target["root"] != REQUIRED_FS_ROOT:
        raise MountInfoRefused("root:not_slash")
    if target["mount_id"] != exp_mid:
        raise MountInfoRefused("id:mount_mismatch")
    if (target["major"], target["minor"]) != exp_dev:
        raise MountInfoRefused("device:mismatch")

    raw_sha = hashlib.sha256(raw_b).hexdigest()

    return {
        "schema": SCHEMA_VERSION,
        "state": STATE_MATCHED,
        "raw_sha256": raw_sha,
        "mount_id": target["mount_id"],
        "device": [target["major"], target["minor"]],
        "fs_root_is_slash": True,
        "host_namespace_verified": False,
        "full_host_hierarchy_verified": False,
        "enforcement_proven": False,
        "candidate_admission": False,
    }
