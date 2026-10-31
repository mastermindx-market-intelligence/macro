"""Contract tests for ci_apt_transaction_contract (pure, stdlib + pytest)."""

import json

import pytest

from scripts import ci_apt_transaction_contract as contract
from scripts.ci_apt_transaction_contract import (
    ERR_BAD_COMMAND,
    ERR_BAD_ENVELOPE,
    ERR_BAD_JSON,
    ERR_BAD_ORIGIN,
    ERR_BAD_ROW,
    ERR_BAD_PACKAGES,
    ERR_BAD_PARAMS,
    ERR_BAD_SEARCH_TERMS,
    ERR_BAD_UNKNOWN_PACKAGES,
    ERR_BAD_VERSION_BLOCK,
    ERR_DUPLICATE_KEY,
    ERR_DUPLICATE_ROW,
    ERR_HUGE_INT,
    ERR_MISSING_VERSION,
    ERR_NONFINITE,
    ERR_NOT_UTF8,
    ERR_PREINSTALL_BAD_FIELD,
    ERR_PREINSTALL_BAD_VERSION,
    ERR_PREINSTALL_DUPLICATE_ROW,
    ERR_PREINSTALL_ERROR_ACTION,
    ERR_PREINSTALL_MALFORMED,
    ERR_PREINSTALL_TOO_LARGE,
    ERR_TOO_DEEP,
    ERR_TOO_LARGE,
    ERR_CHANGED,
    assert_same_transaction,
    normalize_transaction,
    parse_preinstall_v3,
)

SECRET_MARKER = "S3CRET-TOKEN-XYZ"


def origin(**overrides):
    base = {
        "archive": "noble",
        "codename": "noble",
        "version": "24.04",
        "origin": "Ubuntu",
        "label": "Ubuntu",
        "site": "archive.ubuntu.com",
    }
    base.update(overrides)
    return base


def version_entry(id=11, **overrides):
    base = {
        "id": id,
        "version": "1:1.0-1",
        "architecture": "amd64",
        "pin": 500,
        "origins": [origin()],
    }
    base.update(overrides)
    return base


def package_row(name="vim", mode="install", automatic=False, id=7,
                architecture="amd64", versions=None):
    if versions is None:
        versions = {"candidate": version_entry(id=21),
                    "install": version_entry(id=22)}
    return {
        "id": id,
        "name": name,
        "architecture": architecture,
        "mode": mode,
        "automatic": automatic,
        "versions": versions,
    }


def envelope(packages=None, search_terms=("vim",), rpc_id=1,
             method="org.debian.apt.hooks.install.pre-prompt",
             command="install", unknown_packages=None):
    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "method": method,
        "params": {
            "command": command,
            "search-terms": list(search_terms),
            "unknown-packages": list(unknown_packages or []),
            "packages": list(
                [package_row()] if packages is None else packages),
        },
    }


def raw_txn(**overrides):
    return json.dumps(envelope(**overrides)).encode("utf-8")


def reason_of(function, *args):
    with pytest.raises(ValueError) as excinfo:
        function(*args)
    return str(excinfo.value)


def assert_no_echo(function, *args, secret=SECRET_MARKER):
    try:
        function(*args)
    except ValueError as exc:
        assert str(exc) in contract._REASONS
        assert secret not in str(exc)
        assert secret not in repr(exc)
    else:
        raise AssertionError("expected ValueError")


# --- normalize_transaction: acceptance -------------------------------------


def test_normalize_returns_canonical_shape():
    frozen = normalize_transaction(raw_txn())
    assert frozen["command"] == "install"
    assert frozen["search-terms"] == ["vim"]
    assert set(frozen) == {"command", "search-terms", "packages"}


def test_internal_ids_dropped_and_fields_kept():
    frozen = normalize_transaction(raw_txn())
    row = frozen["packages"][0]
    assert set(row) == {"name", "architecture", "mode", "automatic", "versions"}
    assert row["automatic"] is False
    entry = row["versions"]["install"]
    assert set(entry) == {"version", "architecture", "pin", "origins"}


def test_rows_sorted_by_name_and_architecture():
    rows = [
        package_row(name="zbar"),
        package_row(name="0ad", architecture="amd64"),
        package_row(name="vim", architecture="i386"),
        package_row(name="vim", architecture="amd64"),
    ]
    frozen = normalize_transaction(raw_txn(packages=rows))
    order = [(row["name"], row["architecture"])
             for row in frozen["packages"]]
    assert order == [("0ad", "amd64"), ("vim", "amd64"),
                     ("vim", "i386"), ("zbar", "amd64")]


def test_fonts_all_archive_arch_preserved_against_row_arch():
    fonts = package_row(
        name="fonts-noto-color-emoji",
        architecture="amd64",
        versions={
            "candidate": version_entry(id=31, version="2.047",
                                       architecture="all"),
            "install": version_entry(id=32, version="2.047",
                                     architecture="all"),
        },
    )
    frozen = normalize_transaction(raw_txn(packages=[fonts]))
    entry = frozen["packages"][0]["versions"]["install"]
    assert entry["architecture"] == "all"
    assert frozen["packages"][0]["architecture"] == "amd64"


def test_upgrade_downgrade_reinstall_modes_accepted():
    for mode in ("upgrade", "downgrade", "reinstall"):
        frozen = normalize_transaction(
            raw_txn(packages=[package_row(mode=mode)]))
        assert frozen["packages"][0]["mode"] == mode


def test_purge_and_deinstall_kept_with_current():
    for mode in ("deinstall", "purge"):
        row = package_row(mode=mode,
                          versions={"current": version_entry(id=41)})
        frozen = normalize_transaction(raw_txn(packages=[row]))
        assert frozen["packages"][0]["versions"]["current"]["version"] == "1:1.0-1"


def test_origins_preserved_verbatim_not_reduced_to_boolean():
    origins = [origin(site="archive.ubuntu.com", archive="noble"),
               origin(site="security.ubuntu.com", archive="noble-security",
                      label="Ubuntu-Security")]
    row = package_row(versions={"install": version_entry(origins=origins)})
    frozen = normalize_transaction(raw_txn(packages=[row]))
    assert frozen["packages"][0]["versions"]["install"]["origins"] == origins
    assert not any("authenticated" in key
                   for key in frozen["packages"][0])


# --- normalize_transaction: rejection --------------------------------------


def test_rejects_oversize_raw():
    assert (reason_of(normalize_transaction, b"x" * (1024 * 1024 + 1))
            == ERR_TOO_LARGE)


def test_rejects_non_bytes():
    assert reason_of(normalize_transaction, "{\"jsonrpc\": \"2.0\"}") == ERR_NOT_UTF8
    assert reason_of(normalize_transaction, None) == ERR_NOT_UTF8


def test_rejects_invalid_json_and_bad_envelope():
    assert reason_of(normalize_transaction, b"{not json") == ERR_BAD_JSON
    assert reason_of(normalize_transaction, b"[1, 2]") == ERR_BAD_ENVELOPE
    body = envelope()
    body["jsonrpc"] = "1.0"
    assert (reason_of(normalize_transaction, json.dumps(body).encode())
            == ERR_BAD_ENVELOPE)
    body = envelope(method="org.debian.apt.hooks.install.unknown")
    assert (reason_of(normalize_transaction, json.dumps(body).encode())
            == ERR_BAD_ENVELOPE)
    raw = json.dumps(envelope()).encode()[:-1] + b',"extra":1}'
    assert reason_of(normalize_transaction, raw) == ERR_BAD_ENVELOPE


def test_rejects_duplicate_json_keys():
    raw = (b'{"jsonrpc":"2.0","id":1,'
           b'"method":"org.debian.apt.hooks.install.pre-prompt",'
           b'"params":{"command":"install","command":"install",'
           b'"search-terms":["vim"],"unknown-packages":[],'
           b'"packages":[]}}')
    assert reason_of(normalize_transaction, raw) == ERR_DUPLICATE_KEY


def test_rejects_nonfinite_numbers_without_echo():
    body = envelope(packages=[package_row(
        versions={"install": version_entry(pin=float("nan"))})])
    raw = json.dumps(body).encode()
    assert reason_of(normalize_transaction, raw) == ERR_NONFINITE
    assert_no_echo(normalize_transaction, raw)


def test_rejects_huge_integers():
    raw = raw_txn(rpc_id=2 ** 70)
    assert reason_of(normalize_transaction, raw) == ERR_HUGE_INT
    raw = raw_txn(packages=[package_row(
        versions={"install": version_entry(pin=2 ** 70)})])
    assert reason_of(normalize_transaction, raw) == ERR_HUGE_INT


def test_rejects_deeply_nested_json():
    raw = b"[" * 100000 + b"]" * 100000
    assert reason_of(normalize_transaction, raw) == ERR_TOO_DEEP


def test_rejects_bad_command_and_params_shape():
    raw = raw_txn(command="remove")
    assert reason_of(normalize_transaction, raw) == ERR_BAD_COMMAND
    body = envelope()
    body["params"]["local-repositories"] = []
    assert (reason_of(normalize_transaction, json.dumps(body).encode())
            == ERR_BAD_PARAMS)
    assert reason_of(normalize_transaction,
                     raw_txn(unknown_packages=["vim"])) == ERR_BAD_UNKNOWN_PACKAGES


@pytest.mark.parametrize("term", [
    "-y", "--force-yes", "a b", "a;b", "a'b", 'a"b', "a$b", "a*b", "a`b",
    "~/x", "a\\b", "", "a\tb", "vim\n", "$(x)", "a|b",
])
def test_rejects_unsafe_search_terms(term):
    assert (reason_of(normalize_transaction, raw_txn(search_terms=(term,)))
            == ERR_BAD_SEARCH_TERMS)


def test_rejects_search_term_count_out_of_bounds():
    assert (reason_of(normalize_transaction, raw_txn(search_terms=()))
            == ERR_BAD_SEARCH_TERMS)
    many = tuple("pkg%02d" % index for index in range(65))
    assert (reason_of(normalize_transaction, raw_txn(search_terms=many))
            == ERR_BAD_SEARCH_TERMS)


def test_rejects_package_count_over_128():
    rows = [package_row(name="pkg%03d" % index) for index in range(129)]
    assert reason_of(normalize_transaction, raw_txn(packages=rows)) == ERR_BAD_PACKAGES


def test_rejects_bad_package_rows():
    bad_rows = [
        package_row(name="Vim"),
        package_row(name="-vim"),
        package_row(name="a"),
        package_row(name="vi m"),
        package_row(mode="hold"),
        package_row(automatic=1),
        {key: value for key, value in package_row().items() if key != "id"},
        dict(package_row(), extra=1),
        {"id": 1, "name": "vim", "architecture": "amd64", "mode": "install",
         "automatic": False},
    ]
    for row in bad_rows:
        assert reason_of(normalize_transaction,
                         raw_txn(packages=[row])) == ERR_BAD_ROW


def test_rejects_bad_version_blocks_and_missing_mode_versions():
    bad_versions = [
        {"candidate": version_entry(), "install": version_entry(),
         "current": version_entry(), "unknown": version_entry()},
        {"install": dict(version_entry(), extra=1)},
        {"install": version_entry(version="1.0_2")},
        {"install": version_entry(architecture="amd64;")},
        {"install": version_entry(pin="500")},
        {"install": version_entry(pin=True)},
    ]
    for versions in bad_versions:
        assert reason_of(normalize_transaction, raw_txn(
            packages=[package_row(versions=versions)])) == ERR_BAD_VERSION_BLOCK
    assert reason_of(normalize_transaction, raw_txn(
        packages=[package_row(mode="upgrade",
                              versions={"current": version_entry()})])
        ) == ERR_MISSING_VERSION
    assert reason_of(normalize_transaction, raw_txn(
        packages=[package_row(mode="purge",
                              versions={"install": version_entry()})])
        ) == ERR_MISSING_VERSION
    assert reason_of(normalize_transaction, raw_txn(
        packages=[package_row(versions={
            "install": dict(version_entry(), origins="x")})])
        ) == ERR_BAD_VERSION_BLOCK
    assert reason_of(normalize_transaction, raw_txn(
        packages=[package_row(versions={
            "install": dict(version_entry(), origins=[
                {"archive": "noble", "codename": "noble", "version": "24.04",
                 "origin": "Ubuntu", "label": "Ubuntu"}])})])
        ) == ERR_BAD_ORIGIN
    assert reason_of(normalize_transaction, raw_txn(
        packages=[package_row(versions={
            "install": version_entry(
                origins=[dict(origin(), extra=1)])})])
        ) == ERR_BAD_ORIGIN
    assert reason_of(normalize_transaction, raw_txn(
        packages=[package_row(versions={
            "install": version_entry(
                origins=[origin(site="a b\x01")])})])
        ) == ERR_BAD_ORIGIN


def test_rejects_duplicate_row_identity():
    rows = [package_row(name="vim", architecture="amd64", mode="install"),
            package_row(name="vim", architecture="amd64", mode="purge",
                        versions={"current": version_entry(id=99)})]
    assert (reason_of(normalize_transaction, raw_txn(packages=rows))
            == ERR_DUPLICATE_ROW)


# --- assert_same_transaction ------------------------------------------------


def test_ids_and_method_may_differ_only():
    left = normalize_transaction(raw_txn(rpc_id=1))
    right = normalize_transaction(raw_txn(
        rpc_id="client-2",
        method="org.debian.apt.hooks.install.package-list"))
    assert left == right
    assert_same_transaction(left, right)


def _mutants(base):
    def with_packages(packages):
        return {"command": base["command"],
                "search-terms": base["search-terms"],
                "packages": packages}
    row = base["packages"][0]
    entry = row["versions"]["install"]
    changed_entry = dict(entry, version="9:9.9-1")
    changed_row = dict(row, versions=dict(row["versions"], install=changed_entry))
    origin_row = dict(row, versions=dict(row["versions"], install=dict(
        entry, origins=[dict(entry["origins"][0], site="evil.example")])))
    return [
        ("version", with_packages([changed_row])),
        ("version-arch", with_packages([dict(row, versions=dict(
            row["versions"], install=dict(entry, architecture="all")))])),
        ("mode", with_packages([dict(row, mode="upgrade")])),
        ("automatic", with_packages([dict(row, automatic=True)])),
        ("origin-site", with_packages([origin_row])),
        ("origin-label", with_packages([dict(row, versions=dict(
            row["versions"], install=dict(
                entry, origins=[dict(entry["origins"][0], label="Other")])))])),
        ("dropped-version", with_packages([dict(
            row, versions={"candidate": row["versions"]["candidate"]})])),
        ("pin", with_packages([dict(row, versions=dict(
            row["versions"], install=dict(entry, pin=501)))])),
        ("row-order", with_packages(list(reversed(base["packages"])))),
        ("extra-row", with_packages(base["packages"] + [row])),
        ("search-terms", {"command": base["command"],
                          "search-terms": ["vim", "emacs"],
                          "packages": base["packages"]}),
        ("command", {"command": "reinstall",
                     "search-terms": base["search-terms"],
                     "packages": base["packages"]}),
        ("bool-vs-int", {"command": base["command"],
                         "search-terms": base["search-terms"],
                         "packages": [dict(row, automatic=1)]}),
        ("int-vs-float", with_packages([dict(row, versions=dict(
            row["versions"], install=dict(entry, pin=500.0)))])),
    ]


def test_changed_transactions_rejected():
    base = normalize_transaction(raw_txn(packages=[
        package_row(name="vim"),
        package_row(name="zbar", mode="deinstall",
                    versions={"current": version_entry(id=51)}),
    ]))
    for label, observed in _mutants(base):
        reason = reason_of(assert_same_transaction, base, observed)
        assert reason == ERR_CHANGED, label
        assert_no_echo(assert_same_transaction, base, observed)


def test_equal_transactions_accepted_after_key_reordering():
    base = normalize_transaction(raw_txn())
    reordered = json.loads(json.dumps(base))
    assert_same_transaction(base, reordered)
    assert_same_transaction({}, {})
    assert reason_of(assert_same_transaction, None, {}) == ERR_CHANGED
    assert reason_of(assert_same_transaction, [], {}) == ERR_CHANGED


# --- parse_preinstall_v3 ----------------------------------------------------


def preinstall_text(actions, config=("APT::Architecture: amd64",
                                     "Acquire::Retries: 3",
                                     "Dir::Cache::Archives: " + SECRET_MARKER),
                   header="VERSION 3", blank=True):
    lines = [header] + list(config)
    if blank:
        lines.append("")
    lines.extend(actions)
    return ("\n".join(lines) + "\n").encode("utf-8")


UPGRADE = "libc6 2.39-0ubuntu8.4 amd64 same < 2.39-0ubuntu8.6 amd64 same **CONFIGURE**"
NEW_FONTS = "fonts-noto-color-emoji - - none > 2.047-0ubuntu1 all no **CONFIGURE**"
REMOVE = "apache2 2.4.58-1ubuntu8 amd64 same > - - no **REMOVE**"
DEB_PATH = ("libqt6core6 6.4.2+dfsg-3 amd64 same < 6.4.2+dfsg-4 amd64 same "
            "/var/cache/apt/archives/libqt6core6_6.4.2+dfsg-4_amd64.deb")
DOWNGRADE = "curl 8.5.0-2ubuntu10 amd64 same = 8.5.0-2ubuntu9 amd64 same **CONFIGURE**"


def test_preinstall_parses_complete_action_set_in_order():
    rows = parse_preinstall_v3(
        preinstall_text([UPGRADE, NEW_FONTS, REMOVE, DEB_PATH, DOWNGRADE]))
    assert isinstance(rows, tuple)
    assert [row["name"] for row in rows] == [
        "libc6", "fonts-noto-color-emoji", "apache2", "libqt6core6", "curl"]
    fonts = rows[1]
    assert fonts == {
        "name": "fonts-noto-color-emoji",
        "oldversion": "-", "oldarch": "-", "oldmulti": "none",
        "direction": ">",
        "newversion": "2.047-0ubuntu1", "newarch": "all", "newmulti": "no",
        "action": "**CONFIGURE**",
    }
    removal = rows[2]
    assert removal["action"] == "**REMOVE**"
    assert removal["newversion"] == "-" and removal["newarch"] == "-"
    assert rows[3]["action"].endswith(".deb")
    assert rows[3]["direction"] == "<"
    assert rows[4]["direction"] == "="
    for row in rows:
        assert set(row) == {"name", "oldversion", "oldarch", "oldmulti",
                            "direction", "newversion", "newarch", "newmulti",
                            "action"}


def test_preinstall_never_returns_or_echoes_config():
    rows = parse_preinstall_v3(preinstall_text([UPGRADE]))
    flat = repr(rows)
    assert SECRET_MARKER not in flat
    assert "APT::Architecture" not in flat
    assert "amd64: amd64" not in flat
    for row in rows:
        assert "config" not in row


def test_preinstall_allows_empty_config_and_empty_actions():
    assert parse_preinstall_v3(b"VERSION 3\n\n") == ()
    assert parse_preinstall_v3(
        preinstall_text([UPGRADE], config=())) == (
            {"name": "libc6", "oldversion": "2.39-0ubuntu8.4",
             "oldarch": "amd64", "oldmulti": "same", "direction": "<",
             "newversion": "2.39-0ubuntu8.6", "newarch": "amd64",
             "newmulti": "same", "action": "**CONFIGURE**"},)


def test_preinstall_rejects_error_action_and_bad_versions():
    error_line = ("libbad 1.0-1 amd64 same < 1.1-1 amd64 same **ERROR**")
    assert (reason_of(parse_preinstall_v3, preinstall_text([error_line]))
            == ERR_PREINSTALL_ERROR_ACTION)
    assert (reason_of(parse_preinstall_v3,
                      preinstall_text([UPGRADE], header="VERSION 2"))
            == ERR_PREINSTALL_BAD_VERSION)
    assert (reason_of(parse_preinstall_v3,
                      preinstall_text([UPGRADE], header="VERSION 4"))
            == ERR_PREINSTALL_BAD_VERSION)
    assert (reason_of(parse_preinstall_v3,
                      preinstall_text([UPGRADE], header="version 3"))
            == ERR_PREINSTALL_BAD_VERSION)
    assert (reason_of(parse_preinstall_v3,
                      preinstall_text([UPGRADE], header="VERSION 3 "))
            == ERR_PREINSTALL_BAD_VERSION)


def test_preinstall_rejects_missing_blank_and_malformed_rows():
    no_blank = b"VERSION 3\nAPT::Architecture: amd64\n" + UPGRADE.encode() + b"\n"
    assert reason_of(parse_preinstall_v3, no_blank) == ERR_PREINSTALL_MALFORMED
    short = "libc6 2.39 amd64 same < 2.39 amd64 same"
    assert (reason_of(parse_preinstall_v3, preinstall_text([short]))
            == ERR_PREINSTALL_MALFORMED)
    long = UPGRADE + " extra"
    assert (reason_of(parse_preinstall_v3, preinstall_text([long]))
            == ERR_PREINSTALL_MALFORMED)
    assert (reason_of(parse_preinstall_v3,
                      preinstall_text([UPGRADE, "", REMOVE]))
            == ERR_PREINSTALL_MALFORMED)
    assert (reason_of(parse_preinstall_v3, b"VERSION 3\n\n\x80 bad\n")
            == ERR_PREINSTALL_MALFORMED)
    assert (reason_of(parse_preinstall_v3, b"VERSION 3\r\n\n" + UPGRADE.encode())
            == ERR_PREINSTALL_MALFORMED)
    assert reason_of(parse_preinstall_v3, b"") == ERR_PREINSTALL_BAD_VERSION
    assert reason_of(parse_preinstall_v3, None) == ERR_PREINSTALL_MALFORMED


def test_preinstall_rejects_duplicate_exact_rows():
    assert (reason_of(parse_preinstall_v3, preinstall_text([UPGRADE, UPGRADE]))
            == ERR_PREINSTALL_DUPLICATE_ROW)


@pytest.mark.parametrize("line", [
    "vim - amd64 same < 2:9.1 amd64 same **CONFIGURE**",
    "vim - - same < 2:9.1 amd64 same **CONFIGURE**",
    "vim 2:9.0 amd64+bad same < 2:9.1 amd64 same **CONFIGURE**",
    "vim 2:9.0 amd64 same < - amd64 no **CONFIGURE**",
    "vim 2:9.0 amd64 same < 2:9.1 amd64 both **CONFIGURE**",
    "vim 2:9.0 amd64 same <> 2:9.1 amd64 same **CONFIGURE**",
    "vim 2:9.0 amd64 same == 2:9.1 amd64 same **CONFIGURE**",
    "vim 2:9.0 amd64 same < 2:9.1 amd64 same CONFIGURE",
    "vim 2:9.0 amd64 same < 2:9.1 amd64 same **PURGE**",
    "vim 2:9.0 amd64 same < archives/vim.deb amd64 same **CONFIGURE**",
    "Vim 2:9.0 amd64 same < 2:9.1 amd64 same **CONFIGURE**",
])
def test_preinstall_rejects_bad_action_fields(line):
    assert (reason_of(parse_preinstall_v3, preinstall_text([line]))
            == ERR_PREINSTALL_BAD_FIELD)


def test_preinstall_rejects_oversize_without_echo():
    big = b"VERSION 3\n\n" + b"x" * (1024 * 1024)
    assert reason_of(parse_preinstall_v3, big) == ERR_PREINSTALL_TOO_LARGE
    assert_no_echo(parse_preinstall_v3, big)


def test_error_messages_are_fixed_codes_without_body_or_secret_echo():
    assert_no_echo(parse_preinstall_v3, preinstall_text([UPGRADE, UPGRADE]))
    raw = raw_txn(packages=[package_row(name="vim " + SECRET_MARKER)])
    assert_no_echo(normalize_transaction, raw)
    raw = raw_txn(search_terms=("vim; " + SECRET_MARKER,))
    assert_no_echo(normalize_transaction, raw)
    body = envelope(packages=[package_row(
        versions={"install": version_entry(
            origins=[origin(site=SECRET_MARKER)])})])
    frozen = normalize_transaction(json.dumps(body).encode())
    assert SECRET_MARKER in json.dumps(frozen)


def test_depth_limit_is_explicit_across_decoder_versions_and_ignores_quoted_brackets():
    assert reason_of(normalize_transaction, b'[' * 65 + b']' * 65) == ERR_TOO_DEEP
    assert reason_of(normalize_transaction, json.dumps("[" * 100).encode()) == ERR_BAD_ENVELOPE
