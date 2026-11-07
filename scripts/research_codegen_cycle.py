"""Public cycle entrypoint; no qualified runtime issuer is installed.

Source tests exercise adapter_codegen with explicit invented input/transport.
No CLI argument, JSON claim or caller boolean can activate that private seam.
"""
import argparse
import json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    print(json.dumps({"status": "REFUSED", "reason": "RUNTIME_QUALIFICATION_UNAVAILABLE",
                      "execution_enabled": False, "authority_granted": False}))
    return 78


if __name__ == "__main__":
    raise SystemExit(main())
