#!/bin/bash
# Run only the checked-in, fictional PB-D example. Compatible with Bash 3.2.
set -u

if ! CHECKOUT_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"; then
    printf 'PB-D could not locate the checkout containing this launcher.\n' >&2
    exit 2
fi
QUICKSTART="$CHECKOUT_ROOT/research/policy_behavior/pro_returns/PB-D/PB_D_OPERATOR_QUICKSTART.md"
PYTHON_BIN="$CHECKOUT_ROOT/.venv/bin/python"
OUTPUT_PARENT="${TMPDIR:-/tmp}"
CLI="$CHECKOUT_ROOT/scripts/query_pb_d_event_quality.py"
FIXTURE="$CHECKOUT_ROOT/tests/fixtures/pb_d/research_packet.json"

usage() {
    cat <<EOF
Usage: $CHECKOUT_ROOT/scripts/run_pb_d_example.sh [--python ABSOLUTE_EXECUTABLE] [--output-dir EXISTING_DIRECTORY]
       $CHECKOUT_ROOT/scripts/run_pb_d_example.sh --help

Run the synthetic PB-D example; its result is not market evidence.
Default Python: $CHECKOUT_ROOT/.venv/bin/python (Python 3.12 required)
Default output parent: ${TMPDIR:-/tmp}
Each invocation creates a fresh child directory and preserves its report.
Setup instructions: $QUICKSTART
EOF
}

argument_error() {
    printf 'PB-D: %s\n' "$1" >&2
    usage >&2
    exit 2
}

setup_error() {
    printf 'PB-D: %s\nSetup instructions: %s\n' "$1" "$QUICKSTART" >&2
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --help)
            usage
            exit 0
            ;;
        --python|--output-dir)
            if [ "$#" -lt 2 ] || [[ "$2" == --* ]]; then
                argument_error "$1 requires a value."
            fi
            if [ "$1" = --python ]; then
                [[ "$2" == /* ]] || argument_error "--python requires an absolute executable path; received: $2"
                PYTHON_BIN="$2"
            else
                [ -n "$2" ] || argument_error "--output-dir requires an existing directory."
                OUTPUT_PARENT="$2"
            fi
            shift 2
            ;;
        *) argument_error "Unknown argument: $1" ;;
    esac
done

[[ -f "$PYTHON_BIN" && -x "$PYTHON_BIN" ]] || setup_error "Python executable is unavailable: $PYTHON_BIN"
[[ -f "$CLI" && -r "$CLI" ]] || setup_error "Research entry script is unavailable: $CLI"
[[ -f "$FIXTURE" && -r "$FIXTURE" ]] || setup_error "Synthetic input is unavailable: $FIXTURE"
[ -d "$OUTPUT_PARENT" ] || argument_error "Output directory does not exist: $OUTPUT_PARENT"
if ! RESOLVED_OUTPUT_PARENT="$(CDPATH= cd -- "$OUTPUT_PARENT" && pwd -P)"; then
    setup_error "Cannot access output directory: $OUTPUT_PARENT"
fi
OUTPUT_PARENT="$RESOLVED_OUTPUT_PARENT"

# Keep this probe parseable by Python 2 so a mistaken override gets a clear error.
# Ignore Python environment settings and skip site imports while checking sys.
"$PYTHON_BIN" -E -S -B - <<'PY'
import sys
if sys.version_info[:2] != (3, 12):
    sys.stderr.write("PB-D requires Python 3.12; this interpreter reports %s.\n" % sys.version.split()[0])
    sys.exit(2)
PY
if [ "$?" -ne 0 ]; then
    setup_error "Python version check failed for: $PYTHON_BIN"
fi

# Isolated mode excludes the caller's directory and PYTHONPATH from imports.
# Check dependencies before any repository imports or output writes.
"$PYTHON_BIN" -I -B - <<'PY'
import sys
failures = []
for name in ("numpy", "jsonschema", "yaml"):
    try:
        __import__(name)
    except Exception as exc:
        failures.append("%s: %s" % (name, exc))
if failures:
    sys.stderr.write("PB-D required dependencies are unavailable:\n%s\n" % "\n".join(failures))
    sys.exit(2)
PY
if [ "$?" -ne 0 ]; then
    setup_error "Environment check failed for: $PYTHON_BIN"
fi

if ! RUN_DIR="$(mktemp -d "${OUTPUT_PARENT%/}/pb-d-example.XXXXXX")"; then
    setup_error "Cannot create a fresh example directory in: $OUTPUT_PARENT"
fi
REPORT_PATH="$RUN_DIR/report.json"
printf 'Running the PB-D SYNTHETIC EXAMPLE: fictional inputs, not market evidence.\n'
"$PYTHON_BIN" -I -B "$CLI" run --input "$FIXTURE" --output "$REPORT_PATH"
RUN_STATUS=$?
if [ "$RUN_STATUS" -ne 0 ]; then
    printf 'PB-D example did not complete (exit %s). Files are preserved in: %s\n' "$RUN_STATUS" "$RUN_DIR" >&2
    exit "$RUN_STATUS"
fi

# Summarize the saved report without changing the research CLI's JSON contract.
"$PYTHON_BIN" -I -B - "$REPORT_PATH" <<'PY'
import json
import math
import sys

path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as handle:
        report = json.load(handle)
    if report["dataset_kind"] != "SYNTHETIC_DRY_RUN":
        raise ValueError("the report does not identify a synthetic example")
    state = report["state"]
    if state != "FROZEN_DESIGN_NOT_ENROLLED":
        raise ValueError("unexpected study state: %s" % state)
    flags = report["authority_flags"]
    if not isinstance(flags, dict) or not flags or any(value is not False for value in flags.values()):
        raise ValueError("the report does not confirm that all authority flags are disabled")
    primary = report["evaluation"]["primary"]
    count = primary["complete_pair_count"]
    if type(count) is not int or count < 0:
        raise ValueError("invalid complete-pair count")
    effect = primary["equal_date_mean_increment_pp"]
    if effect is not None and (type(effect) not in (int, float) or not math.isfinite(effect)):
        raise ValueError("invalid H5 difference")
    effect_text = "unknown" if effect is None else "{:+g} percentage points".format(effect)
    lines = [
        "PB-D SYNTHETIC EXAMPLE completed. This is not market evidence.",
        "Study state: " + state.replace("_", " ").lower(),
        "Complete synthetic pairs: %d" % count,
        "H5 SPY-excess difference: " + effect_text,
        "Authority flags: all disabled (" + ", ".join(sorted(flags)) + ")",
        "Report saved to: " + path,
    ]
except Exception as exc:
    sys.stderr.write("PB-D could not confirm the saved report: %s\nReport preserved at: %s\n" % (exc, path))
    sys.exit(2)
print("\n".join(lines))
PY
