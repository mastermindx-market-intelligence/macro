"""D07 candidate arithmetic only. No browser, production code or Paper mutation.

Manually transcribed immutable specification inputs
F01 245a7d2cd62d88fb6d2ee3863f9d26c63052d8e7
  f01/JOINT_SHELL_SYSTEM_CONTRACT.md
F02 f7c25c4b9870cff260c2a4b998be18d6c04d36d0
  f02/F01_HANDSHAKE_CANDIDATE.md
Repository mastermindx-market-intelligence/macro

F01 candidate 2 accepts F02's continuous cutoffs. Both pinned source labels
use the agreed candidate rule. Native and release qualification remain open.
"""

from fractions import Fraction


def geometry(width, specification, compact=False, local_reserved=0):
    width = Fraction(str(width))
    if width <= 860:
        rail = 0
    elif width >= 1200:
        rail = 72 if compact else 224
    else:
        rail = 72 if compact else 196

    assert specification in ("F01", "F02")
    gutter = 16 if width <= 600 else 20 if width < 1200 else 24

    content = width - rail - 2 * gutter - local_reserved
    docked = content >= 984
    primary = content - 344 if docked else content
    return (content, primary, "dock" if docked else "overlay")


checks = 0


def check(label, actual, expected):
    global checks
    assert actual == expected, (label, actual, expected)
    checks += 1
    print(f"PASS {checks:02d} | {label} | {actual}")


print("D07 foundation candidate arithmetic")
print("F01 245a7d2cd62d88fb6d2ee3863f9d26c63052d8e7")
print("F02 f7c25c4b9870cff260c2a4b998be18d6c04d36d0")

shared = [
    (320, (288, 288, "overlay")),
    (390, (358, 358, "overlay")),
    (768, (728, 728, "overlay")),
    (1024, (788, 788, "overlay")),
    (1280, (1008, 664, "dock")),
    (1440, (1168, 824, "dock")),
    (1600, (1328, 984, "dock")),
]
for specification in ("F01", "F02"):
    for width, expected in shared:
        check(f"{specification} expanded {width}", geometry(width, specification), expected)
    check(f"{specification} expanded 1255", geometry(1255, specification), (983, 983, "overlay"))
    check(f"{specification} expanded 1256", geometry(1256, specification), (984, 640, "dock"))
    check(f"{specification} compact 1095", geometry(1095, specification, compact=True), (983, 983, "overlay"))
    check(f"{specification} compact 1096", geometry(1096, specification, compact=True), (984, 640, "dock"))
    check(f"{specification} 1280 with local32", geometry(1280, specification, local_reserved=32), (976, 976, "overlay"))

check("F01 gutter at 600", geometry(600, "F01"), (568, 568, "overlay"))
check("F02 gutter at 600", geometry(600, "F02"), (568, 568, "overlay"))
check("F01 gutter at 601", geometry(601, "F01"), (561, 561, "overlay"))
check("F02 gutter at 601", geometry(601, "F02"), (561, 561, "overlay"))
check("F01 gutter at 767", geometry(767, "F01"), (727, 727, "overlay"))
check("F02 gutter at 767", geometry(767, "F02"), (727, 727, "overlay"))
check("current candidates at 860", geometry(860, "F01"), (820, 820, "overlay"))
check("current candidates at 861", geometry(861, "F02"), (625, 625, "overlay"))
check("current candidates at 1199", geometry(1199, "F01"), (963, 963, "overlay"))
check("current candidates at 1200", geometry(1200, "F02"), (928, 928, "overlay"))
check("F01 fractional navigation at 860.5", geometry(860.5, "F01"), (Fraction("624.5"), Fraction("624.5"), "overlay"))
check("F02 fractional navigation at 860.5", geometry(860.5, "F02"), (Fraction("624.5"), Fraction("624.5"), "overlay"))
check("F01 fractional navigation at 1199.5", geometry(1199.5, "F01"), (Fraction("963.5"), Fraction("963.5"), "overlay"))
check("F02 fractional navigation at 1199.5", geometry(1199.5, "F02"), (Fraction("963.5"), Fraction("963.5"), "overlay"))
check("two 320px control cells with 8px gap", (288 - 8) / 2, 140)
check("two 390px control cells with 8px gap", (358 - 8) / 2, 175)
check("664px table, 196 label + 3 x 156 periods", 196 + 3 * 156, 664)
check("600 to 768 candidate agreement", geometry(767, "F01")[0] - geometry(767, "F02")[0], 0)
print(f"PASS {checks}/{checks} specification arithmetic assertions")
print("No served viewport, font metric, control fit, focus, browser or RIG qualification is asserted.")
