"""Independent arithmetic for a synthetic design fixture; no product proof."""
from decimal import Decimal as D
from pathlib import Path
import json

fixture = json.loads((Path(__file__).parent / "fixtures/expiry_payoff.json").read_text())
multiplier = D(fixture["multiplier"])
legs = fixture["legs"]
checks = 0


def check(actual, expected, label):
    global checks
    assert actual == expected, f"{label}: {actual!r} != {expected!r}"
    checks += 1


def pnl(spot, long_entry="5.20", short_entry="2.00", size="1"):
    spot = D(str(spot))
    return D(size) * multiplier * (
        max(spot - D("600"), D(0)) - max(spot - D("610"), D(0))
        - D(long_entry) + D(short_entry)
    )


cost = sum(D(x["signed_quantity"]) * multiplier * D(x["entry_per_unit"]) for x in legs)
check(cost, D(fixture["expected"]["signed_cost"]), "signed cost")
for spot, expected in fixture["expected"]["samples"]:
    check(pnl(spot), D(expected), f"P/L at {spot}")
check(min(pnl(0), pnl(600), pnl(610)), D("-320"), "signed worst P/L")
check(max(pnl(0), pnl(600), pnl(610)), D("680"), "signed best P/L")
check(sum(D(x["signed_quantity"]) * multiplier for x in legs), D(0), "flat high-price tail")

lo, hi = D("480"), D("732")
grid = sorted({(lo + (hi - lo) * D(i) / D(100)).quantize(D("0.001")) for i in range(101)} | {D("600"), D("610")})
check(len(grid), fixture["expected"]["grid_count"], "grid count")
check((grid[0], grid[-1]), (lo, hi), "grid endpoints")
check(D("606") in grid, True, "606 is a real consumer sample")
check(D("605") in grid, False, "605 is analytical only")
check(D("603.20") in grid, False, "break-even is not an inserted sample")

for alt in fixture["alternatives"]:
    a, b = alt["long_entry"], alt["short_entry"]
    check(multiplier * (D(a) - D(b)), D(alt["signed_cost"]), alt["name"] + " cost")
    check(pnl(0, a, b), D(alt["worst_pnl"]), alt["name"] + " worst")
    check(pnl(732, a, b), D(alt["best_pnl"]), alt["name"] + " best")
    check(pnl(alt["break_even"], a, b), D(0), alt["name"] + " break-even")
    check(pnl(606, a, b), D(alt["pnl_at_606"]), alt["name"] + " sampled P/L")
    delta = D("320") - D(alt["signed_cost"])
    for spot in grid:
        check(pnl(spot, a, b) - pnl(spot), delta, alt["name"] + " constant shift")

for spot in [D("0"), D("600"), D("606"), D("732")]:
    check(pnl(spot, size="3"), D(3) * pnl(spot), "quantity scaling")
check(pnl(600, "0", "0"), D(0), "zero premium is not missing")

print(json.dumps({"result": "PASS", "checks": checks, "grid_points": len(grid),
                  "scope": "independent synthetic arithmetic only; no API, contract qualification, Save, watch or browser proof"}, indent=2))
