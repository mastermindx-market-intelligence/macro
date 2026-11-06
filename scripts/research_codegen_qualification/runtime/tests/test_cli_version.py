"""Pure version parser: no CLI, socket, install or canary replay."""
import hashlib

import pytest
import cli29_anonymous_config as source


def test_current_version_digest_identifies_packaging_tilde_not_version_drift():
    # Digest-correlated reconstruction of the current read's 53-byte command
    # capture. The original helper did not retain the version text itself.
    raw = b"Docker version 29.1.3, build 29.1.3-0ubuntu3~24.04.2\n"
    assert len(raw) == 53
    assert hashlib.sha256(raw).hexdigest() == (
        "3548432b70959bfb691169dfd9f9adbc829c1ce0493dc817e69a364821caca2f")
    assert source.expected_client_version(raw) == raw.decode().removesuffix("\n")


def test_original_short_git_build_remains_accepted():
    assert source.expected_client_version(b"Docker version 29.1.3, build abc1234\n") == (
        "Docker version 29.1.3, build abc1234")


@pytest.mark.parametrize("raw", [
    b"Docker version 29.1.30, build abc1234\n",
    b"Docker version 29.1.4, build abc1234\n",
    b"Docker version 28.1.3, build abc1234\n",
    b"Docker version 29.1.3-rc1, build abc1234\n",
    b"Docker version 29.1.3, build \n",
    b"Docker version 29.1.3, build abc\nextra\n",
    b" Docker version 29.1.3, build abc\n",
    b"Docker version 29.1.3, build abc;echo\n",
    b"Docker version 29.1.3, build \xff\n",
    b"Docker version 29.1.3, build " + b"a" * 129,
    b"a" * 257,
    "Docker version 29.1.3, build abc1234\n",
    True,
])
def test_other_versions_or_nonversion_output_still_refuse(raw):
    with pytest.raises(RuntimeError, match="^actual_client_not_29_1_3$"):
        source.expected_client_version(raw)
