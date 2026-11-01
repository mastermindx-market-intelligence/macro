"""Explicit bounded private worker; no service/cron/default reader installation."""
from pathlib import Path
import sys
import json
import signal

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
from lib.frozen_options_account import frozen_options_account  # noqa: E402


def main():
    result = None
    # The parent also bounds/terminates its own one-shot child. This local
    # deadline prevents a direct invocation from waiting on an unclosed pipe.
    def expired(_signum, _frame):
        raise TimeoutError('local account input unavailable')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(10)
    try:
        if len(sys.argv) == 1:
            raw = sys.stdin.buffer.read(4097)
            if len(raw) <= 4096:
                value = json.loads(raw.decode('utf-8', 'strict'))
                if isinstance(value, dict) and set(value) == {'principal', 'evaluationAt'}:
                    signal.alarm(15)  # Bound canonical owner work separately from stdin.
                    result = frozen_options_account(value['principal'], value['evaluationAt'])
    except Exception:
        pass
    finally:
        signal.alarm(0)
    if result is None:
        result = {'kind': 'unavailable', 'reason': 'canonical_account_unavailable'}
    text = json.dumps(result, allow_nan=False)
    if len(text.encode('utf-8')) + 1 > 256 * 1024:
        result = {'kind': 'unavailable', 'reason': 'canonical_account_unavailable'}
        text = json.dumps(result)
    sys.stdout.write(text + '\n')
    return 0 if result['kind'] == 'observed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
