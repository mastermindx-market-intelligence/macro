"""Refresh helper for tools/xguerrilla/tlds.txt (one-shot generator).

Reads the IANA tlds-alpha-by-domain.txt artifact, emits the xguerrilla data
file with provenance header + sha256 contract. Run from anywhere:

    python3 tools/xguerrilla/refresh_tlds.py <tlds-alpha-by-domain.txt> <tlds.txt>

Not part of the test suite; run only when refreshing the snapshot.
"""
import hashlib
import sys
from pathlib import Path

RESERVED = ["EXAMPLE", "INVALID", "LOCALHOST", "ONION", "TEST"]

HEADER = """\
# xguerrilla link-gate TLD set — real-TLD membership, not label shape.
#
# Consumer: tools/xguerrilla/tlds.py (parsed + sha256-verified at import).
# Why: the general scheme-less-host alternative of validators._LINK_TOKEN
# used to fire on any dotted word with an alphabetic 2+ label tail, so
# filename-shaped prose ("Node.js", "notes.txt", "setup.exe") was refused
# by the zero-URL post gate. The tail label must now be a member of this
# set (tlds.is_tld) for the token to count as a link.
#
# source: https://data.iana.org/TLD/tlds-alpha-by-domain.txt
# iana-version: {version}
# fetched: 2026-11-12
# iana-labels-sha256: {sha}
#   The hash covers EXACTLY the label lines between 'begin-iana' and
#   'end-iana' below (one label per line, IANA order, each LF-terminated).
#   tools/xguerrilla/tlds.py recomputes it at import and refuses to load a
#   file that does not match its own claim, so the set cannot drift
#   silently; regenerate the file (never hand-edit the label lines) with:
#     curl -fsSL https://data.iana.org/TLD/tlds-alpha-by-domain.txt \\
#       -o /tmp/tlds-alpha.txt && \\
#     python3 tools/xguerrilla/refresh_tlds.py /tmp/tlds-alpha.txt \\
#       tools/xguerrilla/tlds.txt
#   then update the pinned sentinel rows in test_validators.py if IANA
#   added/removed any of them.
#
# reserved-additions (after 'begin-reserved'): names IANA's registry
# deliberately omits but that still resolve as hosts in prose, so the gate
# refuses them fail-closed instead of passing a reserved name:
#   EXAMPLE INVALID LOCALHOST TEST — RFC 2606 §1 / RFC 6761 §6.2
#     (test/invalid/localhost are also §6.2-special-use)
#   ONION — RFC 7686 pseudo-TLD
#
# Collision policy (documented decision, pinned by tests): labels that are
# BOTH registered TLDs and file extensions (ZIP MOV APP DEV AI PY MD SH SO
# PL PM …) are treated as TLDs — "archive.zip"/"movie.mov" FIRE. The gate
# is fail-closed by law (BL-9 absolute) and the fire direction must not
# weaken; extensions that are NOT TLDs (js txt exe html json …) do not
# fire. Both halves are pinned rows in test_validators.py.
"""


def main() -> None:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    lines = src.read_text(encoding="utf-8").splitlines()
    version = lines[0].lstrip("# ").strip()
    labels = [ln.strip().upper() for ln in lines[1:] if ln.strip() and not ln.startswith("#")]
    assert len(labels) > 1000, f"implausibly small IANA artifact: {len(labels)}"
    assert len(set(labels)) == len(labels), "duplicate labels in IANA artifact"
    sha = hashlib.sha256(("".join(ln + "\n" for ln in labels)).encode("utf-8")).hexdigest()
    body = HEADER.format(version=version, sha=sha)
    body += "#\n# begin-iana\n" + "".join(ln + "\n" for ln in labels)
    body += "# end-iana\n#\n# begin-reserved\n" + "".join(ln + "\n" for ln in RESERVED)
    body += "# end-reserved\n"
    dst.write_text(body, encoding="utf-8", newline="\n")
    print(f"wrote {dst}: {len(labels)} iana labels + {len(RESERVED)} reserved, sha256={sha}")


if __name__ == "__main__":
    main()
