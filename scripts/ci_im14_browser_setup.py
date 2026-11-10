"""Prepare the pinned IM14 Node browser on a GitHub-hosted Noble runner."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import time

APT = Path("/etc/apt")
MIRROR = "mirror+file:/etc/apt/apt-mirrors.txt"
HTTPS_ARCHIVE = "https://archive.ubuntu.com/ubuntu/"
UBUNTU_KEYRING = "/usr/share/keyrings/ubuntu-archive-keyring.gpg"
PLAYWRIGHT_VERSION = "1.63.0"
# Exact Playwright 1.63.0 coreBundle Linux x64 dependency inventory. The
# runtime package and bundle must match before any privileged operation.
DRIVER_SHA256 = "549070af3acabb3efcc4f55bfe6210f9f7c2fcf633cf7eaa59bfe60719969171"
PLAYWRIGHT_CLI_SHA256 = "5e79302a6aad7d835d92d5ae6b4244c91cf61b28e94d7917279090e6c231f7a1"
BROWSER_REGISTRY_SHA256 = "545d52f8382c391e605562c330e9c1c534a16045898203037a49bb8bd769a946"
# The apt image's standard cache-only hook is the only allowed removal.
CACHE_CLEANUP = (
    "rm -f /var/cache/apt/archives/*.deb /var/cache/apt/archives/partial/*.deb "
    "/var/cache/apt/*.bin || true"
)
CACHE_HOOK_KEYS = ("APT::Update::Post-Invoke", "APT::Update::Post-Invoke-Success", "DPkg::Post-Invoke")
ROOT_TIMEOUT_STATUS = 124
PACKAGES = (
    "libasound2t64", "libatk-bridge2.0-0t64", "libatk1.0-0t64", "libatspi2.0-0t64",
    "libcairo2", "libcups2t64", "libdbus-1-3", "libdrm2", "libgbm1",
    "libglib2.0-0t64", "libnspr4", "libnss3", "libpango-1.0-0", "libx11-6",
    "libxcb1", "libxcomposite1", "libxdamage1", "libxext6", "libxfixes3",
    "libxkbcommon0", "libxrandr2", "xvfb", "fonts-noto-color-emoji",
    "fonts-unifont", "libfontconfig1", "libfreetype6", "xfonts-cyrillic",
    "xfonts-scalable", "fonts-liberation", "fonts-ipafont-gothic",
    "fonts-wqy-zenhei", "fonts-tlwg-loma-otf", "fonts-freefont-ttf",
)


def _read_system_file(path: Path) -> bytes:
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as f:
        entry = os.fstat(f.fileno())
        if (not stat.S_ISREG(entry.st_mode) or entry.st_uid != 0
                or entry.st_mode & 0o022 or not entry.st_mode & stat.S_IROTH
                or entry.st_size > 256 * 1024):
            raise ValueError("unqualified APT input file")
        content = f.read(256 * 1024 + 1)
        if len(content) > 256 * 1024:
            raise ValueError("unqualified APT input size")
        return content


def project_sources(original: bytes, mirror_list: bytes) -> bytes:
    """Replace only the runner's known Ubuntu mirror, with unchanged signed suites."""
    mirrors = [line.split() for line in mirror_list.decode("ascii").splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    if mirrors != [
        ["http://azure.archive.ubuntu.com/ubuntu/", "priority:1"],
        [HTTPS_ARCHIVE, "priority:2"],
        ["https://security.ubuntu.com/ubuntu/", "priority:3"],
    ]:
        raise ValueError("unqualified runner mirror inventory")
    text = original.decode("ascii")
    suites = set()
    stanzas = 0
    for stanza in re.split(r"\n[ \t]*\n", text.strip()):
        fields = {}
        for line in stanza.splitlines():
            if line.startswith("#"):
                continue
            match = re.fullmatch(r"([A-Za-z-]+):[ \t]+([^\r\n]+)", line)
            if not match or match[1] in fields:
                raise ValueError("unqualified Ubuntu source syntax")
            fields[match[1]] = match[2].strip()
        if (fields.keys() - {"Types", "URIs", "Suites", "Components", "Signed-By", "Architectures"}
                or fields.get("Types") != "deb" or fields.get("URIs") != MIRROR
                or fields.get("Signed-By") != UBUNTU_KEYRING
                or fields.get("Architectures", "amd64") != "amd64"
                or set(fields.get("Components", "").split()) != {"main", "universe", "restricted", "multiverse"}):
            raise ValueError("unqualified Ubuntu source fields")
        current = fields.get("Suites", "").split()
        if not current or suites.intersection(current) or len(current) != len(set(current)):
            raise ValueError("unqualified Ubuntu suites")
        suites.update(current)
        stanzas += 1
    if suites != {"noble", "noble-updates", "noble-backports", "noble-security"}:
        raise ValueError("unqualified Ubuntu suite inventory")
    projected, changed = re.subn(
        rb"(?m)^(URIs:[ \t]+)mirror\+file:/etc/apt/apt-mirrors\.txt(?=[ \t]*$)",
        rb"\g<1>" + HTTPS_ARCHIVE.encode("ascii"), original
    )
    if changed != stanzas:
        raise ValueError("unqualified Ubuntu URI projection")
    return projected


def _source_profile() -> dict[str, bytes]:
    source_parts = APT / "sources.list.d"
    files = {}
    for path in sorted(source_parts.iterdir()):
        if re.fullmatch(r"[A-Za-z0-9_.-]+\.(list|sources)", path.name):
            files[path.name] = _read_system_file(path)
    files["ubuntu.sources"] = project_sources(files["ubuntu.sources"], _read_system_file(APT / "apt-mirrors.txt"))
    source_list = APT / "sources.list"
    try:
        files[""] = _read_system_file(source_list)
    except FileNotFoundError:
        files[""] = b""
    if any(MIRROR.encode("ascii") in content or b"http://azure.archive.ubuntu.com/" in content
           for content in files.values()):
        raise ValueError("unqualified additional Ubuntu mirror source")
    if not _read_system_file(Path(UBUNTU_KEYRING)):
        raise ValueError("Ubuntu signing keyring unavailable")
    return files


class DeadlineExpired(RuntimeError):
    """The original deadline expired or a root stage did not settle."""


def _run(deadline: float, *args, privileged: bool = False, **kwargs):
    remaining = deadline - time.monotonic()
    if remaining <= (3 if privileged else 0):
        raise DeadlineExpired("original IM14 deadline reached before stage launch")
    if privileged:
        # A root supervisor owns the child group. Reserve time inside the
        # original absolute deadline for TERM/KILL and the outer pack fence.
        args = ("sudo", "-n", "--", "/usr/bin/timeout", "--signal=TERM", "--kill-after=1s",
                f"{remaining - 3:.6f}s", *args)
    result = subprocess.run(args, timeout=remaining, **kwargs)
    if privileged and result.returncode in {124, 137, -9, -15}:
        raise DeadlineExpired("privileged IM14 stage did not settle before its deadline")
    result.check_returncode()
    return result


def private_apt_config(current: str) -> bytes:
    """Refuse unknown post-invoke effects and suppress only exact cache cleanup."""
    clear = []
    for line in current.splitlines():
        key, _, value = line.partition(" ")
        canonical = next((item for item in CACHE_HOOK_KEYS
                          if key.lower() == item.lower() or key.lower().startswith(item.lower() + "::")), None)
        if canonical is None:
            continue
        if key.lower() == canonical.lower() and value == '"";':
            continue
        if key.lower() != canonical.lower() + "::" or value != f'"{CACHE_CLEANUP}";' or canonical in clear:
            raise ValueError("unqualified APT post-invoke policy")
        clear.append(canonical)
    return "".join(f"#clear {key};\n" for key in clear).encode("ascii")


def _apt_install(deadline: float, sources: dict[str, bytes], config: bytes) -> None:
    def root(*args, **kwargs):
        return _run(deadline, *args, privileged=True, **kwargs)

    state = root("/usr/bin/mktemp", "-d", "/var/tmp/mm-im14-apt.XXXXXXXXXX",
                 text=True, stdout=subprocess.PIPE).stdout.rstrip("\n")
    if not re.fullmatch(r"/var/tmp/mm-im14-apt\.[A-Za-z0-9]{10}", state):
        raise ValueError("unqualified private APT state path")
    root("/usr/bin/chmod", "0755", state)
    root("/usr/bin/install", "-d", "-m", "0755", f"{state}/parts",
         f"{state}/lists", f"{state}/archives")
    for name, content in sources.items():
        destination = f"{state}/parts/{name}" if name else f"{state}/sources.list"
        root("/usr/bin/tee", "--", destination, input=content, stdout=subprocess.DEVNULL)
        root("/usr/bin/chmod", "0644", destination)
    root("/usr/bin/tee", "--", f"{state}/private.conf", input=config, stdout=subprocess.DEVNULL)
    apt = ("/usr/bin/apt-get", "-c", f"{state}/private.conf",
           "-o", f"Dir::Etc::sourcelist={state}/sources.list",
           "-o", f"Dir::Etc::sourceparts={state}/parts",
           "-o", f"Dir::State::lists={state}/lists",
           "-o", f"Dir::Cache::archives={state}/archives",
           "-o", "Dir::Cache::pkgcache=", "-o", "Dir::Cache::srcpkgcache=",
           "-o", "APT::Update::Error-Mode=any", "-o", "Acquire::Retries=1",
           "-o", "Acquire::http::Timeout=15", "-o", "Acquire::https::Timeout=15",
           "-o", "Acquire::https::Verify-Peer=true", "-o", "Acquire::https::Verify-Host=true",
           "-o", "Acquire::Check-Valid-Until=true", "-o", "Acquire::AllowInsecureRepositories=false",
           "-o", "Acquire::AllowDowngradeToInsecureRepositories=false",
           "-o", "APT::Get::AllowUnauthenticated=false")
    root(*apt, "update")
    root(*apt, "install", "-y", "--no-install-recommends", *PACKAGES)
    root("/usr/bin/rm", "-rf", "--", state)


def main(deadline: float) -> None:
    remaining = deadline - time.monotonic()
    if not math.isfinite(remaining) or not 0 < remaining <= 20 * 60:
        raise ValueError("IM14 setup requires its original live deadline")
    host = platform.freedesktop_os_release()
    if (host.get("ID") != "ubuntu" or host.get("VERSION_ID") != "24.04"
            or platform.machine() != "x86_64"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or "PLAYWRIGHT_HOST_PLATFORM_OVERRIDE" in os.environ
            or "APT_CONFIG" in os.environ):
        raise ValueError("IM14 setup requires its qualified hosted Noble runner")
    sources = _source_profile()
    config = private_apt_config(
        _run(deadline, "/usr/bin/apt-config", "dump", privileged=True,
             text=True, stdout=subprocess.PIPE).stdout
    )
    _run(deadline, "npm", "install", "--no-save", "--package-lock=false", f"playwright@{PLAYWRIGHT_VERSION}")
    for name in ("playwright", "playwright-core"):
        package = json.loads(Path("node_modules", name, "package.json").read_text())
        if (package.get("name"), package.get("version")) != (name, PLAYWRIGHT_VERSION):
            raise ValueError("IM14 Playwright pin mismatch")
    driver = Path("node_modules/playwright-core/lib/coreBundle.js")
    if hashlib.sha256(driver.read_bytes()).hexdigest() != DRIVER_SHA256:
        raise ValueError("IM14 Playwright driver mismatch")
    cli = Path("node_modules/playwright/cli.js")
    if hashlib.sha256(cli.read_bytes()).hexdigest() != PLAYWRIGHT_CLI_SHA256:
        raise ValueError("IM14 Playwright entry mismatch")
    registry = Path("node_modules/playwright-core/browsers.json")
    if hashlib.sha256(registry.read_bytes()).hexdigest() != BROWSER_REGISTRY_SHA256:
        raise ValueError("IM14 Playwright browser registry mismatch")
    _apt_install(deadline, sources, config)
    _run(deadline, "node", str(cli), "install", "chromium")


if __name__ == "__main__":
    try:
        main(float(sys.argv[1]))
    except (DeadlineExpired, subprocess.TimeoutExpired):
        print("IM14 setup deadline or privileged settlement is uncertain", file=sys.stderr)
        raise SystemExit(ROOT_TIMEOUT_STATUS)
