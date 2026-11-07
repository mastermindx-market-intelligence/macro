"""Generate an OFFLINE, editable Paper import blueprint from the options source.

This writes only paper_blueprint.json beside this file. It performs no Paper,
network, runtime, git, or host operations. Import and visual review remain separate.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


OUT = Path(__file__).with_name("paper_blueprint.json")
ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "templates/options.html.j2"
BUILDER = ROOT / "scripts/build_options_command.py"
ACTUAL_SAMPLES = OUT.with_name("paper_actual_samples.json")
MOBILE_STATUS_BAR = OUT.with_name("paper_mobile_status_bar.html")
DESIGN_TOKENS_FILE = OUT.with_name("paper_design_tokens.json")
BRAND_GLYPH_FILE = OUT.with_name("paper_brand_glyph.svg")
DESIGN_TOKENS = json.loads(DESIGN_TOKENS_FILE.read_text())
TOKEN_VALUES = {token["name"]: token["value"] for token in DESIGN_TOKENS}
BRAND_GLYPH = BRAND_GLYPH_FILE.read_text()
OBSERVED = json.loads(ACTUAL_SAMPLES.read_text()) if ACTUAL_SAMPLES.exists() else None
TARGET = "2026-10-30"
UI = "Inter, sans-serif"
MONO = "Menlo, monospace"
TOKENS = {
    "dark": dict(bg="#0F1115", panel="#181B21", panel2="#1E222A", text="#D7DCE3", muted="#8B93A1", line="#3A4150", info="#5B9BF0", link="#7AA7E0", up="#45B873", down="#E06464", warn="#E0A030", ok="#3DA564", ink_up="#45B873", ink_down="#E06464", ink_warn="#E0A030", ink_link="#7AA7E0"),
    "light": dict(bg="#F7F8FA", panel="#FFFFFF", panel2="#EEF1F6", text="#1C2430", muted="#5D6B7E", line="#C9CCD1", info="#285FFF", link="#285FFF", up="#1F9A55", down="#CF4040", warn="#B9791A", ok="#2F8A52", ink_up="#1E6D47", ink_down="#B23C3D", ink_warn="#7D5922", ink_link="#2758E6"),
}
TOKEN_REFERENCES = {}
for theme, palette in TOKENS.items():
    TOKEN_REFERENCES[theme] = {}
    for semantic, value in palette.items():
        suffix = semantic.replace("_", "-")
        if theme == "dark" and suffix.startswith("ink-"):
            suffix = suffix[4:]
        name = f"--mx-{theme}-{suffix}"
        assert TOKEN_VALUES.get(name, "").lower() == value.lower(), f"Existing token mismatch: {name}"
        TOKEN_REFERENCES[theme][semantic] = f"var({name})"
SPACING_REFERENCES = {TOKEN_VALUES[f"--sp-{i}"]: f"var(--sp-{i})" for i in range(1, 9)}
RADIUS_REFERENCES = {TOKEN_VALUES[name]: f"var({name})" for name in ("--r-ctl", "--r-btn", "--r-card", "--r-panel", "--r-pill")}
INDEXES = [
    dict(symbol="SPX", name="S&P 500 Index", close=7580.07, floor=7500, flip=7699.43, ceiling=8100),
    dict(symbol="SPY", name="S&P 500 ETF", close=755.72, floor=750, flip=772.93, ceiling=800),
    dict(symbol="QQQ", name="Nasdaq 100 ETF", close=690.49, floor=680, flip=727.45, ceiling=760),
    dict(symbol="IWM", name="Russell 2000 ETF", close=279.33, floor=270, flip=289.73, ceiling=300),
]
# Parent verified these exact fields in the pinned published GEX files on M2.
# The retained Brief text export is blank for the index cards; it is not the
# provenance of these values, and no expected move is inferred from geometry.
INDEX_DAILY_MOVES = {"SPX": 0.97, "SPY": 0.97, "QQQ": 1.54, "IWM": 1.25}
INDEX_DAILY_MOVE_SOURCE_PIN = "e4009c94d75770739844240b22f5fc915668aa9b"
SECTORS = [
    ("Technology", 10900, "$10.9B"), ("Index ETFs", 3900, "$3.9B"),
    ("Consumer Disc.", 1600, "$1.6B"), ("Communication", 1200, "$1.2B"),
    ("Health Care", 424, "$424M"), ("Industrials", 423, "$423M"),
    ("Financials", 347, "$347M"), ("Energy", 115, "$115M"),
    ("Staples", 92, "$92M"), ("Utilities", 51, "$51M"),
    ("Materials", 12, "$12M"), ("Real Estate", 0.5, "$500K"),
]
PRESETS = ["Premium leaders", "Volume surge", "Expensive options", "Same-day heavy", "Downside cover bid", "Near a flip level", "Put-heavy OI"]
RANGES = ["IV 30d", "IV rank", "Expected move", "Put/call OI", "Volume", "Premium", "Same-day share", "Rel vol ×", "Put-skew pp", "IV-spread pp"]
RAW_PANELS = ["Dealer gamma by strike", "Net gamma against price", "The surface — strikes by expiry", "What cover costs by strike", "What cover costs by date", "Every expiry on file", "Positioning greeks"]
EVIDENCE_A = ["Money keeps showing up", "Unusually heavy premium", "New positions opened", "Spread across expirations", "Price is leading", "Near 52-week high", "Volume confirms", "Not a failed breakout"]
EVIDENCE_B = ["Recently washed out", "Oversold", "Turn signal is on", "Money flipped positive", "New positions opened", "Volume confirms", "Not a failed breakout"]
SOURCES = [
    ("Dealer levels", "2026-10-30", "Selected session"),
    ("Volatility", "2026-10-30", "Selected session"),
    ("Index context", "2026-10-20", "Earlier session"),
    ("Daily Brief", "2026-08-19", "Earlier session"),
    ("Flow", "2026-08-13", "Earlier session"),
    ("Scanner", "2026-08-13", "Earlier session"),
    ("Leaders", "2026-08-12", "Earlier session"),
]


def esc(value):
    return html.escape(str(value), quote=True)


def css(**values):
    styles = []
    for key, value in values.items():
        if value is None:
            continue
        if key == "font_family" and value == UI:
            value = "var(--font-ui), sans-serif"
        elif key == "border_radius":
            value = RADIUS_REFERENCES.get(value, value)
        elif key in ("gap", "row_gap", "column_gap", "padding", "padding_top", "padding_right", "padding_bottom", "padding_left"):
            value = " ".join(SPACING_REFERENCES.get(part, part) for part in str(value).split())
        styles.append(f"{key.replace('_', '-')}:{value}")
    return ";".join(styles)


def div(content="", name=None, **style):
    attrs = f' layer-name="{esc(name)}"' if name else ""
    return f'<div{attrs} style="{esc(css(box_sizing="border-box", **style))}">{content}</div>'


class Screen:
    def __init__(self, mode, mobile, theme, variant="workspace"):
        self.mode, self.mobile, self.theme = mode, mobile, theme
        self.c = TOKEN_REFERENCES[theme]
        self.width = 390 if mobile else 1440
        self.inner = 358 if mobile else 1280
        self.pad = 16 if mobile else 80
        self.variant = variant
        self.fragments = []
        self.id = f"{mode}-{'mobile' if mobile else 'desktop'}-{theme}"

    def text(self, value, size=14, color=None, weight=400, mono=False, **style):
        has_cjk=any("\u3400" <= char <= "\u9fff" for char in value)
        if mono:
            assert not has_cjk
            weight=700 if weight>=600 else 400
        elif has_cjk:
            weight=min(weight,600)
        return div(esc(value), font_family=MONO if mono else "PingFang SC, sans-serif" if has_cjk else UI, font_size=f"{size}px", line_height="1.45", font_weight=str(weight), color=color or self.c["text"], **style)

    def label(self, value):
        return self.text(value.upper(), 10, self.c["muted"], 600, letter_spacing="1.1px")

    def row(self, *children, gap=12, **style):
        return div("".join(children), display="flex", flex_direction="row", gap=f"{gap}px", **style)

    def col(self, *children, gap=12, **style):
        return div("".join(children), display="flex", flex_direction="column", gap=f"{gap}px", **style)

    def repeat_row(self, name, *children, **style):
        """Mark semantic repeated items for separate guarded Paper writes."""
        markup = self.row(*children, **style)
        return markup.replace('<div ', f'<div layer-name="{esc(self.id + " · " + name)}" data-paper-repeat="items" ', 1)

    def repeat_col(self, name, *children, **style):
        markup = self.col(*children, **style)
        return markup.replace('<div ', f'<div layer-name="{esc(self.id + " · " + name)}" data-paper-repeat="items" ', 1)

    def rule(self):
        return div(height="1px", width="100%", background=self.c["line"], flex_shrink="0")

    def button(self, label, primary=False, compact=False, muted=False, focused=False, selected=False):
        return div(self.text(label, 12.5 if compact else 14,
                            (self.c["bg"] if self.theme == "dark" else self.c["panel"]) if primary else self.c["text"] if selected else self.c["muted"] if muted else self.c["ink_link"],
                            600), display="flex", align_items="center", justify_content="center",
                   min_height="44px", padding="8px 12px" if compact else "10px 16px",
                   border=f"1px solid {self.c['line']}", border_radius="8px",
                   background=self.c["info"] if primary else f"var(--mx-{self.theme}-info-soft)" if selected else self.c["panel"],
                   outline=f"2px solid {self.c['info']}" if focused else None, outline_offset="2px" if focused else None)

    def settings_button(self):
        icon = (f'<svg width="18" height="18" viewBox="0 0 24 24" role="img" aria-label="Settings" '
                f'fill="none" stroke="{self.c["ink_link"]}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
                '<path d="M9.5 2.5h5l.5 2.4 1.8 1 2.3-.8 2.5 4.3-1.8 1.6v2l1.8 1.6-2.5 4.3-2.3-.8-1.8 1-.5 2.4h-5l-.5-2.4-1.8-1-2.3.8L2.4 14.6 4.2 13v-2L2.4 9.4l2.5-4.3 2.3.8 1.8-1z"></path>'
                '<circle cx="12" cy="12" r="3"></circle></svg>')
        return div(icon, name="Settings control", display="flex", align_items="center", justify_content="center",
                   width="44px", min_height="44px", padding="8px", flex_shrink="0",
                   border=f"1px solid {self.c['line']}", border_radius="8px", background=self.c["panel"])

    def chip(self, label, tone="muted"):
        ink = {"up": "ink_up", "down": "ink_down", "warn": "ink_warn", "link": "ink_link"}.get(tone, "muted")
        return div(self.text(label, 11, self.c[ink], 500), display="flex", align_items="center", width="fit-content", max_width="100%", padding="4px 8px", border=f"1px solid {self.c['line']}", border_radius="999px", background=self.c["panel2"])

    def heading(self, title, subtitle=None, date=None):
        bits = [self.text(title, 17, weight=700)]
        if subtitle:
            bits.append(self.text(subtitle, 12.5, self.c["muted"]))
        if self.mobile:
            return self.col(*bits, self.source(date) if date else "", gap=4)
        return self.row(self.col(*bits, gap=4, flex="1", min_width="0"), self.source(date) if date else "", align_items="center", justify_content="space-between")

    def source(self, date, selected=None):
        selected = date == TARGET if selected is None else selected
        return self.row(self.text(date or "Date unavailable", 11, self.c["muted"], mono=bool(date)), self.text("Selected session" if selected else "Earlier session", 11, self.c["muted"]) if date else "", gap=8, flex_wrap="wrap", align_items="center")

    def panel(self, content, name, padding=20):
        return div(content, name=name, display="flex", flex_direction="column", gap="16px", padding=f"{padding}px", background=self.c["panel"], border=f"1px solid {self.c['line']}", border_radius="14px", width="100%", min_width="0")

    def missing(self, title="Source data unavailable", subtitle="This view will populate when its source data is available.", height=116):
        return self.col(self.text(title, 14, weight=600), self.text(subtitle, 12.5, self.c["muted"]), gap=8, justify_content="center", align_items="flex-start", min_height=f"{height}px", padding="20px", background=self.c["panel2"], border_radius="10px")

    def add(self, name, content, height, selectors, dates=None, state="supplied_source_values", actions=None, full_bleed=False, note=None):
        fragment_id = f"{self.id}/{len(self.fragments)+1:02d}-{name.lower().replace(' ', '-')}"
        wrapped = div(content, name=name, display="flex", flex_direction="column", gap="20px", width=f"{self.width}px", padding=f"{'0' if full_bleed else '20px'} {'0' if full_bleed else str(self.pad)+'px'} 0", background=self.c["bg"], color=self.c["text"], font_family=UI)
        self.fragments.append(dict(id=fragment_id, name=name, html=wrapped, estimated_height=height, source_selectors=selectors, source_dates=dates or [], data_state=state, intended_actions=actions or [], note=note))

    def board(self):
        return dict(id=self.id, name=f"Options / {self.mode.title()} / {'Mobile 390' if self.mobile else 'Desktop 1440'} / {self.theme.title()}", width=self.width,
                    estimated_height=sum(f["estimated_height"] for f in self.fragments)+44, theme=self.theme, locale="en", variant=self.variant,
                    layout=dict(root="vertical flex stack", inner_width=self.inner, viewport_reference_height=844 if self.mobile else 1000, scroll="vertical; board is full research surface, not a claim that all content is above the fold"),
                    fragments=self.fragments)

    def shell(self):
        logo = self.row(div(BRAND_GLYPH, name="Canonical Mastermind brand glyph", display="flex", align_items="center", justify_content="center", width="29px", height="29px", flex_shrink="0"), self.text("MASTERMINDX", 12.5, weight=800, letter_spacing="1.2px"), gap=8, align_items="center")
        if self.mobile:
            content = self.col(self.row(logo, self.row(self.button("☰", compact=True), self.settings_button(), gap=8), justify_content="space-between", align_items="center"),
                               self.row(div(self.text("Search markets", 12.5, self.c["muted"]), padding="10px 12px", background=self.c["panel"], border=f"1px solid {self.c['line']}", border_radius="10px", flex="1"), self.button("Terminal ↗", compact=True), gap=8), gap=8, padding="12px 16px", border_bottom=f"1px solid {self.c['line']}")
        else:
            menus = self.repeat_row("Shared navigation links", *(self.text(x, 11, self.c["muted"], 500) for x in ["United States⌄", "China⌄", "Hong Kong⌄", "Canada⌄", "International⌄", "Other Assets⌄", "Research⌄"]), gap=16, align_items="center", flex="1", justify_content="center")
            content = self.row(logo, menus, div(self.text("Search markets", 12.5, self.c["muted"]), padding="10px 12px", width="150px", background=self.c["panel"], border=f"1px solid {self.c['line']}", border_radius="10px"), self.button("Terminal ↗", compact=True), self.settings_button(), gap=16, align_items="center", padding="16px 40px", border_bottom=f"1px solid {self.c['line']}")
        self.add("Shared navigation", content, 116 if self.mobile else 78, ["_site_nav.html.j2"], state="shared_shell_reference", actions=["existing navigation", "global search", "Terminal", "existing settings/menu"], full_bleed=True, note="Reconstruction of the inspected shared shell; retain the real shared component in production. No new global behavior is specified.")

    def chrome(self):
        title = self.col(self.label("Research desk / US markets"), self.text("Options", 28 if self.mobile else 38, weight=800, letter_spacing="-0.8px"), self.text("The settled close, in perspective.", 12.5 if self.mobile else 14, self.c["muted"]), gap=4)
        session = self.col(self.label("Latest completed session"), self.text(TARGET, 17, weight=600, mono=True), gap=4)
        self.add("Workspace header", self.col(title, session, gap=16) if self.mobile else self.row(title, session, justify_content="space-between", align_items="center"), 162 if self.mobile else 132, [".oew-idrow", ".oew-session"], [TARGET])
        context = self.row(self.col(self.label("Market context"), self.text("Sources have different dates", 12.5 if self.mobile else 14, weight=500), gap=4), self.text("View sources ›", 11 if self.mobile else 12.5, self.c["ink_link"], 600), align_items="center", justify_content="space-between", padding="12px 16px", border=f"1px solid {self.c['line']}", border_radius="12px", background=self.c["panel"])
        names = [("brief", "Daily Brief"), ("flow", "Flow"), ("scanner", "Scanner"), ("ticker", "Ticker"), ("leaders", "Leaders")]
        tabs = []
        for key, label in names:
            selected = key == self.mode
            txt = self.text(label, 12 if self.mobile else 14, self.c["ink_link"] if selected else self.c["muted"], 600 if selected else 500, white_space="nowrap" if self.mobile else None, text_align="center" if self.mobile else None)
            if key == "ticker" and not self.mobile:
                txt = self.row(txt, self.text("SPY", 10, self.c["muted"], mono=True), gap=8, align_items="center")
            tabs.append(div(txt, display="flex", align_items="center", justify_content="center", min_height="44px", flex="1", min_width="0", padding="8px 3px" if self.mobile else "8px 4px", background=self.c["panel"] if selected else self.c["panel2"], border=f"1px solid {self.c['line']}" if selected else "1px solid transparent", border_radius="8px"))
        self.add("Sources and five research tasks", self.col(context, self.repeat_row("Research task tabs", *tabs, gap=4, padding="4px", background=self.c["panel2"], border_radius="12px"), gap=16), 144 if self.mobile else 136, ["#oew-sources", ".oew-tabs", "#tab-brief", "#tab-flow", "#tab-scanner", "#tab-ticker", "#tab-leaders"], [s[1] for s in SOURCES], actions=["expand source details", "five-tab navigation with ArrowLeft/Right, Home/End and roving focus"], state="actual_mixed_source_dates")

    def intro(self, title, description, date):
        self.add("Mode introduction", self.heading(title, description, date), 110 if self.mobile else 92, [f"#mode-{self.mode}"], [date] if date else [], state="dated_mode_context")

    def terminal(self):
        text = self.col(self.text("Continue in the live Terminal", 15, weight=700), self.text("Live tape, replay, and alerts.", 12.5, self.c["muted"]), gap=4)
        content = self.col(text, self.button("Open the Terminal ↗"), gap=12) if self.mobile else self.row(text, self.button("Open the Terminal ↗"), align_items="center", justify_content="space-between")
        self.add("Terminal continuation", self.panel(content, "Terminal continuation", 16), 160 if self.mobile else 108, [".oew-handoff", "#oew-brief-cta", "terminalUrl"], state="retained_shared_navigation", actions=["open existing Terminal"], note="The production template has native Brief and Ticker handoffs. On other workspace review boards this is a shared Terminal navigation specimen, not a proposed new product CTA.")


def level_track(s, ix, width, pad_ratio=0.08):
    values = [ix[k] for k in ("floor", "flip", "close", "ceiling")]
    low, high = min(values), max(values)
    pad = (high-low)*pad_ratio
    low, high = low-pad, high+pad
    positions = {k: round((ix[k]-low)/(high-low)*100, 5) for k in ("floor", "flip", "close", "ceiling")}
    shapes = [div(position="absolute", left="0", right="0", top="13px", height="2px", background=s.c["line"])]
    for key in ["floor", "ceiling", "flip", "close"]:
        dot = key == "close"
        shapes.append(div(name=f"{ix['symbol']} {key}", position="absolute", left=f"calc({positions[key]}% - {4 if dot else 1}px)", top="10px" if dot else "6px", width="8px" if dot else "2px", height="8px" if dot else "16px", border_radius="999px" if dot else "0", background=s.c["info"] if dot else s.c["warn"] if key == "flip" else s.c["muted"]))
    return div("".join(shapes), name=f"{ix['symbol']} scaled dealer levels", position="relative", height="28px", width="100%", flex_shrink="0"), positions


def index_card(s, ix, detailed=False, expanded_payoff=False):
    compact = s.mobile and not detailed
    size = 22
    width = (s.inner-12)/2 if compact else (s.inner-3*16)/4
    track, _ = level_track(s, ix, width)
    number = lambda v: f"{v:,.2f}".rstrip("0").rstrip(".") if v % 1 else f"{int(v):,}"
    symbol = s.text(ix["symbol"]+" ↗", 14 if compact else 15, s.c["ink_link"], 700, mono=True)
    price = s.text(f"{ix['close']:,.2f}", size, weight=700, mono=True)
    top = s.col(symbol,price,gap=8) if compact else s.row(symbol,price,gap=8,align_items="center",justify_content="space-between")
    levels = s.col(*(s.row(s.text(key.title(),12.5,s.c["muted"]),s.text(number(ix[key]),12.5,weight=600,mono=True),gap=4,justify_content="space-between",align_items="baseline") for key in ["floor","flip","ceiling"]),gap=8) if s.mobile else s.row(*(s.col(s.text(key.title(), 10, s.c["muted"]), s.text(number(ix[key]), 14, weight=600, mono=True), gap=4, flex="1", min_width="0") for key in ["floor", "flip", "ceiling"]), gap=8)
    source = s.col(s.text(TARGET, 11, s.c["muted"], mono=True), s.text("Selected session", 11, s.c["muted"]), gap=2) if compact else s.source(TARGET, True)
    daily_move=f"±{INDEX_DAILY_MOVES[ix['symbol']]:.2f}%"
    body = [top, s.text(ix["name"], 11 if compact else 12.5, s.c["muted"]), source,
            s.text("Jumpy — moves get amplified", 12.5 if compact else 14, weight=600),
            s.text("Below the flip. Swings run larger than usual.", 12.5, s.c["muted"]), track, levels, s.rule(),
            s.col(s.chip("Protect gains", "warn"), s.text("1-day move  "+daily_move, 12.5, s.c["muted"]), gap=8) if s.mobile else s.row(s.chip("Protect gains", "warn"), s.text("1-day move  "+daily_move, 11, s.c["muted"]), gap=8, flex_wrap="wrap")]
    if ix["symbol"] != "SPX":
        body += [s.rule(), s.text("What a structure pays ↓" if expanded_payoff else "What a structure pays ›", 12.5, s.c["ink_link"], 500)]
        if expanded_payoff:
            body += [s.text("Structure prices: date unavailable · Dealer levels: 2026-10-30",12 if s.mobile else 12.5,s.c["muted"]),payoff_rows(s),s.text("End-of-day mid prices. Pricing and expiry appear when the source is available.",12 if s.mobile else 11,s.c["muted"])]
    return div("".join(body), name=f"{ix['symbol']} dealer-level card", display="flex", flex_direction="column", gap="10px" if compact else "12px", padding="12px" if compact else "16px", background=s.c["panel"], border=f"1px solid {s.c['line']}", border_radius="12px", width=f"{width}px" if not detailed else "100%", min_width="0", flex_shrink="0")


def brief(s):
    notice = s.col(s.text("Brief unavailable for the latest session", 15, weight=700), s.text("Latest brief 2026-08-19. Dealer levels are below. Earlier research is available.", 12.5, s.c["muted"]), gap=8)
    actions = s.row(s.button("View earlier research", compact=True), s.text("Source details", 12.5, s.c["ink_link"], 600), gap=16, flex_wrap="wrap", align_items="center")
    s.add("Compact Brief availability", s.panel(s.col(notice, actions, gap=12) if s.mobile else s.row(notice, actions, justify_content="space-between", align_items="center", gap=24), "Brief availability", 16), 194 if s.mobile else 132, [".oew-availability", "[data-open-details='oew-history']", "[data-open-details='oew-sources']"], ["2026-08-19", TARGET], state="actual_brief_unavailable_for_target", actions=["open Earlier-session research", "open Source details"])
    cards = [index_card(s, ix) for ix in INDEXES]
    card_rows = s.repeat_row("Dealer index cards",*cards,gap=12 if s.mobile else 16,flex_wrap="wrap")
    legend = s.col(s.row(div(width="8px", height="8px", border_radius="999px", background=s.c["info"]), s.text("Last close", 11, s.c["muted"]), div(width="2px", height="14px", background=s.c["warn"]), s.text("Gamma flip", 11, s.c["muted"]), gap=8, align_items="center"), s.text("Model estimates from each dated close. Intraday moves do not confirm a level.", 11, s.c["muted"]), gap=8)
    s.add("Four index dealer-level cards", s.col(s.heading("Dealer levels at the close", "Four index products · source dates shown on each card"), card_rows, legend, gap=16), 1260 if s.mobile else 510, ["#oew-index-structure", ".oew-idx", ".oew-index-track", ".oew-index-legend", ".oew-lab"], [TARGET], actions=["open an index in Ticker", "expand available payoff lab", "read model-estimate explanation"], note="Track coordinates use 8% domain padding. All four 1-day moves use parent-verified expected_move.daily_pct values from the pinned published GEX JSON, dated Oct30; see data_provenance.index_daily_moves. They are not inferred from the blank Brief text export. Structure pricing remains absent from the supplied evidence. Current short-regime GEX is distinct from Oct20 market_structure. At <=760px, money and level values are >=12.5px, level rows stack vertically, and an expanded payoff card spans the full index-grid row; mobile payoff rows use 13px and notes 12px.")
    history = s.row(s.col(s.text("Earlier-session research", 17, weight=700), s.text("Intelligence, changes, sector flows, and names to investigate. Each module keeps its source date.", 12.5, s.c["muted"]), gap=4, flex="1"), s.text("›", 22, s.c["muted"]), align_items="center", gap=16)
    s.add("Earlier research disclosure", s.panel(history, "Earlier-session research", 20), 156 if s.mobile else 116, ["#oew-history", ".oew-history-body"], ["2026-08-19", "2026-08-13", "2026-08-12", "2026-10-20"], state="collapsed_history_with_individual_source_dates", actions=["expand original intelligence brief, What changed, sector flows, biggest bets and research names"], note="Collapsed by default for mixed source dates. No prior-session value is promoted to the target-session summary.")


def flow_tide_charts(s, history_date=None):
    historical_source = s.row(s.text("History through:",12.5,s.c["muted"]),s.text(history_date or "Date unavailable",12.5,s.c["muted"],mono=bool(history_date)),gap=4,flex_wrap="wrap")
    return [
        s.col(s.label("Thirty sessions"),historical_source,s.missing("Chart values unavailable",subtitle="",height=128),gap=12,flex="1",min_width="0"),
        s.col(s.label("Intraday record"),s.text("Requested session: Date unavailable",12.5,s.c["muted"]),s.missing("Intraday record unavailable.",subtitle="",height=128),gap=12,flex="1",min_width="0"),
    ]


def flow(s):
    s.intro("Flow", "Follow the options money through its own source session.", "2026-08-13")
    rows = []
    for name, value, formatted in SECTORS:
        bar = div(div(width=f"{value/10900*100:.6f}%", height="8px", background=s.c["info"], border_radius="999px"), height="8px", width="100%", background=s.c["panel2"], border_radius="999px")
        if s.mobile:
            rows.append(s.col(s.row(s.text(name, 12.5), s.text(formatted, 12.5, weight=600, mono=True), justify_content="space-between", gap=8), bar, gap=8))
        else:
            rows.append(s.row(s.text(name, 12.5, width="150px", flex_shrink="0"), div(bar, flex="1"), s.text(formatted, 12.5, weight=600, mono=True, width="90px", text_align="right", flex_shrink="0"), gap=16, align_items="center"))
    title = s.heading("Premium by sector — the full desk", "Gross premium · relative size across sectors", "2026-08-13")
    s.add("Dated sector-premium bars", s.panel(s.col(title, s.repeat_col("Sector premium rows",*rows, gap=16), s.rule(), s.text("This is where money went in that session. Bar length shows premium; it does not encode direction.", 11, s.c["muted"]), gap=20), "Sector premium"), 820 if s.mobile else 600, ["renderFlow", "flSectorPanel"], ["2026-08-13"], note="All twelve supplied sector values are retained. Exact proportional widths use a $10.9B maximum, no minimum bar width, and a single information color. Directional tone is intentionally absent because no source tone fields were supplied.")
    for title, subtitle, selector in [("Theme groups", "A second view of options premium, grouped by theme.", "flThemePanel"), ("Sector ETF money", "Share-count estimates · 1D, 5D and 21D", "flEtfPanel")]:
        s.add(title, s.panel(s.col(s.heading(title, subtitle), s.missing(subtitle="The source values for this module are unavailable."), gap=16), title), 280 if s.mobile else 245, [selector], state="source_values_not_supplied", note="Unavailable design state, not a claim that the production producer failed. Theme/ETF values and their individual asof dates were not supplied.")
    charts = flow_tide_charts(s)
    s.add("The tide and intraday record", s.panel(s.col(s.heading("The tide", "Historical net premium and a separately dated intraday record"), s.repeat_col("Tide chart frames",*charts, gap=20) if s.mobile else s.repeat_row("Tide chart frames",*charts, gap=20), s.text("Shape only. Direction is approximate and is never a buy or sell signal.", 11, s.c["muted"]), gap=20), "The tide"), 580 if s.mobile else 350, ["flTidePanel", "#oew-fl-spark", "#oew-fl-unfold", "#oew-fl-history-source", "#oew-fl-intraday-source"], state="source_observations_not_supplied")


def filter_field(s, label, single=False):
    field = lambda value: div(s.text(value, 12.5, s.c["muted"]), min_height="44px", display="flex", align_items="center", padding="8px 12px", background=s.c["panel"], border=f"1px solid {s.c['line']}", border_radius="8px", flex="1", min_width="0")
    return s.col(s.text(label, 11, s.c["muted"], 600), field("Maximum") if single else s.row(field("Min"), s.text("–", 12.5, s.c["muted"]), field("Max"), gap=8, align_items="center"), gap=8, width="100%" if s.mobile else "calc((100% - 40px) / 3)")


def scanner(s):
    s.intro("Scanner", "Explore the full screened universe with presets, views, and ranges.", "2026-08-13")
    presets = s.repeat_row("Scanner presets",*(s.button(p, compact=True) for p in PRESETS), gap=8, flex_wrap="wrap")
    views = s.repeat_row("Scanner views",*(s.button(v, compact=True, selected=v == "Overview") for v in ["Overview", "Flow", "Positioning"]), gap=8, flex_wrap="wrap")
    coverage = s.col(s.text("372 / 408 names covered", 22 if not s.mobile else 17, weight=700, mono=True), s.text("Scanner snapshot 2026-08-13 · coverage belongs to this snapshot.", 12.5, s.c["muted"]), gap=4)
    content = s.col(coverage, presets, s.rule(), s.col(views, s.button("Export CSV", compact=True), gap=12) if s.mobile else s.row(views, s.button("Export CSV", compact=True), justify_content="space-between", align_items="center"), gap=20)
    s.add("Scanner presets and views", s.panel(content, "Scanner controls"), 490 if s.mobile else 290, ["SC_PRESETS", ".oew-sc-bar", ".oew-seg [data-view]", "#oew-sc-csv"], ["2026-08-13"], actions=["seven source-defined presets", "Overview/Flow/Positioning", "export filtered and sorted CSV"], note="Coverage is separate from the result-row count. The result fragment records whether exact rows are available in the supplied fixture.")
    field = lambda label, placeholder: s.col(s.text(label, 11, s.c["muted"], 600), div(s.text(placeholder, 12.5, s.c["muted"]), min_height="44px", display="flex", align_items="center", padding="8px 12px", border=f"1px solid {s.c['line']}", border_radius="8px", background=s.c["panel"]), gap=8, width="100%" if s.mobile else "calc((100% - 20px) / 2)")
    fields = [field("Name or sector", "Filter ticker or sector…"), field("Sector", "All sectors ⌄")]
    ranges = [filter_field(s, label) for label in RANGES] + [filter_field(s, "From flip", True)]
    s.add("Expanded scanner filters", s.panel(s.col(s.heading("More filters — ranges, sector, text", "Use any combination. Clear all restores the full snapshot."), s.repeat_row("Scanner text and sector filters",*fields, gap=20, flex_wrap="wrap"), s.repeat_row("Scanner range controls",*ranges, gap=20, flex_wrap="wrap"), s.row(s.button("Clear all", compact=True), justify_content="flex-start"), gap=20), "Expanded scanner filters"), 1570 if s.mobile else 660, ["#oew-sc-more", "#oew-f-q", "#oew-f-sector", "SC_RANGES", "#oew-f-flip-max", "#oew-f-clear"], ["2026-08-13"], state="expanded_control_state", actions=["text/sector filters", "ten min/max range pairs", "maximum distance from flip", "Clear all"], note="This review board deliberately opens the default-collapsed advanced filter disclosure to make feature retention inspectable. Runtime defaults remain the source defaults.")
    columns = ["Name ↕", "Spot ↕", "IV 30d ↕", "IV rank ↕", "Expected move ↕", "Put/call OI ↕", "Volume ↕", "Premium ↓", "Tone ↕", "Row lag ↕"] if not s.mobile else ["Name ↕", "Spot ↕", "IV 30d ↕"]
    head = s.row(*(s.text(c, 11, s.c["muted"], 600, flex="1", min_width="0") for c in columns), gap=12, padding="12px", background=s.c["panel2"], border_radius="8px")
    s.add("Scanner results structure", s.panel(s.col(s.heading("Screened names", "Sort any visible column; choose a view for related measures."), head, s.missing("Scanner rows unavailable", "Individual scanner values are unavailable for this snapshot.", 136), s.text("Row lag is measured against this scanner snapshot. It does not describe freshness against the selected session.",12.5,s.c["muted"]),s.text("A screen is a starting list. Nothing here is scored or ordered by expected return.", 11, s.c["muted"]), gap=16), "Scanner result structure"), 410 if s.mobile else 330, ["scHead", "scBody", "scVisibleRows", ".oew-tbl", "#oew-sc-head", "#oew-sc-body", "ageCell"], ["2026-08-13"], state="scanner_row_values_not_supplied", actions=["sort columns", "open a result in Ticker", "switch metric view"], note="An unavailable specimen, distinct from a genuine zero-match state. Row lag / 行数据滞后 is relative to the snapshot, as in the existing tooltip; it is not global data freshness. No Oct30 index data is relabeled as Aug13 scanner data.")


def ticker(s):
    s.intro("Ticker", "Read one name across price, positioning, and measured flow.", TARGET)
    search = div(s.text("SPY", 15, weight=600, mono=True), padding="10px 16px", min_height="44px", border=f"1px solid {s.c['line']}", border_radius="8px", background=s.c["panel"], flex="1")
    s.add("Ticker search and return", s.col(s.text("← Back to research", 12.5, s.c["ink_link"], 600), search, s.text("Press / to search a ticker", 11, s.c["muted"]), gap=12), 152 if s.mobile else 140, ["setupTickerSearch", "#oew-tk-q", "#oew-tk-sugg", "#oew-tk-back"], [TARGET], state="SPY_selected", actions=["ticker autocomplete", "keyboard search", "return to originating mode"])
    ix = INDEXES[1]
    header = s.col(s.row(s.col(s.text("SPY",28,weight=800,mono=True),s.text("S&P 500 ETF",12.5,s.c["muted"]),gap=4),s.col(s.label("Last close"),s.text("755.72",28,weight=700,mono=True),gap=4),justify_content="space-between",align_items="center"),s.source(TARGET),s.text("Jumpy — moves get amplified",17,weight=700),s.text("Dealer hedging adds to moves — swings and air-pockets run bigger than usual.",12.5,s.c["muted"]),s.row(s.chip("Protect gains","warn"),s.text("1-day implied range —",11,s.c["muted"]),gap=12,flex_wrap="wrap",align_items="center"),gap=16)
    s.add("SPY dated close and regime",s.panel(header,"SPY dated close and regime"),360 if s.mobile else 310,["renderTicker", "sourceContext", ".oew-tk-head", ".oew-tk-regime", "[data-verdict-surface]"],[TARGET],state="supplied_SPY_GEX",note="Current spot and short regime are Oct30 GEX. Expected move is not supplied. Other Ticker datasets retain separate dates.")
    s.add("How the day traded",s.panel(s.col(s.heading("How the day traded","Intraday film from the completed source session"),s.missing(subtitle="The observations for this module are unavailable."),gap=16),"How the day traded"),280 if s.mobile else 245,["filmstripPanelHTML", "filmstripSentence"],state="intraday_observations_not_supplied")
    track, _ = level_track(s,ix,s.inner,pad_ratio=0.12)
    levelrows=s.repeat_col("Ticker dealer level rows",*(s.row(s.col(s.text(label,14,weight=600),s.text(description,12.5,s.c["muted"]),gap=4,flex="1"),s.text(value,15,weight=600,mono=True),gap=16,padding="12px 0",border_bottom=f"1px solid {s.c['line']}",align_items="center") for label,value,description in [
        ("Ceiling — call wall","800","The upper dealer-hedging wall."),
        ("Flip — the regime line","772.93","Calm above this line, jumpy below."),
        ("Magnet — max pain","—","Source value unavailable."),
        ("Floor — put wall","750","The lower dealer-hedging wall."),
    ]),gap=0)
    s.add("SPY dealer map and level detail",s.panel(s.col(s.heading("The map — where dealer hedging sits",date=TARGET),track,levelrows,s.text("Model estimates from the source close shown here. Intraday moves do not confirm a level.",11,s.c["muted"]),gap=16),"SPY dealer map"),610 if s.mobile else 490,["renderTicker", ".oew-lad", "lvRow", "wcheckChip", ".oew-lvl"],[TARGET],state="supplied_map_with_unavailable_magnet",note="The blueprint uses the four supplied levels, with the production Ticker 12% domain padding. Exact magnet, level strengths, cross-source wall checks and missing values remain absent; the blueprint does not invent those markers or strengths.")
    for title, subtitle, selector in [("Rich or cheap?", "Implied volatility, rank, and relative pricing", "richOrCheapHTML"), ("Where positions built", "Position changes across the source snapshot", "wherePositionsBuiltHTML")]:
        s.add(title, s.panel(s.col(s.heading(title, subtitle), s.missing(subtitle="The observations for this module are unavailable."), gap=16), title), 280 if s.mobile else 245, [selector], state="module_observations_not_supplied", note="Preserved module and honest source-data state. These unavailable specimens do not assert a live-source failure.")
    reads=[s.panel(s.col(s.label(label),s.text(value,17,weight=700),s.text(description,12.5,s.c["muted"]),gap=12),label,16) for label,value,description in [
        ("The tape — calm or jumpy?","Jumpy","Dealer hedging adds to moves."),
        ("The mood — what options cost","Unavailable","What the options market charges for 30-day cover."),
        ("The lean — direction by time window","Unavailable","Context from put/call positions; not a separate signal."),
    ]]
    s.add("Three independent ticker readings",s.repeat_col("Ticker independent readings",*reads,gap=12) if s.mobile else s.repeat_row("Ticker independent readings",*reads,gap=20),530 if s.mobile else 210,[".oew-reads", "rdCard"],[TARGET],state="regime_supplied_other_readings_unavailable",note="Unknown put/call ratio is not changed into a claimed Two-sided value. This is an explicit absent-value design specimen.")
    placeholders = [s.panel(s.col(s.heading(title), s.missing("Not available yet", subtitle, 88), gap=12), title, 16) for title, subtitle in [("What the move is worth", "Structure prices are needed to compare the cost and payoff."), ("Expiration pressure", "Expiry-level source data is needed to explain the pressure.")]]
    s.add("Move value and expiration pressure", s.repeat_col("Ticker unavailable capability cards",*placeholders, gap=16) if s.mobile else s.repeat_row("Ticker unavailable capability cards",*placeholders, gap=20), 490 if s.mobile else 260, ["whatMoveWorthHTML", "expirationPressureHTML"], state="existing_unavailable_modules", note="Existing unavailable capabilities are retained; no new pricing engine or expiration calculations are implied.")
    flowmetrics=s.repeat_row("Ticker measured flow metrics",*(s.col(s.label(label),s.text("—",22,weight=600,mono=True),gap=8,width="calc((100% - 12px) / 2)" if s.mobile else "calc((100% - 48px) / 4)") for label in ["Premium","Same-day","Put/call","Net premium"]),gap=12 if s.mobile else 16,flex_wrap="wrap")
    s.add("Measured options flow", s.panel(s.col(s.heading("Measured options flow", "Options money from its own source snapshot", "2026-08-13"),flowmetrics,s.text("Ticker flow values unavailable. This source session is earlier than the dealer-level session.",12.5,s.c["muted"]),gap=16), "Measured options flow"), 340 if s.mobile else 260, ["renderTicker", ".oew-metrics", "mt"], ["2026-08-13", TARGET], state="ticker_specific_values_not_supplied")
    rawmetrics=s.repeat_row("Ticker raw structure metrics",*(s.col(s.label(label),s.text("—",22,weight=600,mono=True),gap=8,width="calc((100% - 12px) / 2)" if s.mobile else "calc((100% - 64px) / 5)") for label in ["Net gamma","Strikes","Put/call OI","Max pain","Chain depth"]),gap=12 if s.mobile else 16,flex_wrap="wrap")
    s.add("Advanced research entry", s.panel(s.col(s.heading("Under the hood — the raw options structure", "Charts and the full strike record ↓"),rawmetrics,s.text("Reference figures are reconstructed from the options chain. Real dealer books are unobservable.",11,s.c["muted"]),gap=20), "Advanced research entry", 16), 410 if s.mobile else 250, ["#oew-shelf", "#oew-raw-slot", ".oew-metrics"], state="expanded_advanced_disclosure", actions=["expand all retained raw structure panels"], note="The blueprint opens the advanced disclosure for inspectability; it does not change the production default.")
    for title in RAW_PANELS:
        body = s.missing("Source observations unavailable", "Values and source date appear with this module when available.", 96)
        if title == "Every expiry on file":
            body = s.col(s.row(*(s.text(t, 11, s.c["muted"], 600, flex="1") for t in ["Expiry", "IV", "Straddle", "Magnet"]), gap=8, padding="12px", background=s.c["panel2"], border_radius="8px"), body, gap=12)
        s.add(title, s.panel(s.col(s.heading(title), body, gap=16), title, 16), 250 if s.mobile else 220, ["rawShelfBody", "rawItem", "#oew-raw-slot", title], state="advanced_source_observations_not_supplied", note="No fabricated strike series, gamma profile, heatmap, skew curve, term curve, expiry values, Greeks or inferred scores. Editable structure only.")
    s.add("Options primer", s.panel(s.row(s.text("New to options? Read this first.", 14, weight=600), s.text("›", 22, s.c["muted"]), justify_content="space-between", align_items="center"), "Options primer", 16), 100, [".oew-primer"], state="retained_disclosure", actions=["open original options primer"])


def leaders(s):
    s.intro("Leaders", "Repeated evidence to investigate, with each board's source session.", "2026-08-12")
    rows = []
    for symbol in ["AAL", "AAPL", "ABNB", "ACLS", "ADBE"]:
        rows.append(s.row(s.text(symbol+" ↗", 15, s.c["ink_link"], 700, mono=True), s.chip("On radar"), s.text("Evidence ›", 11, s.c["ink_link"], 500), gap=12, padding="12px 0", align_items="center", justify_content="space-between", border_bottom=f"1px solid {s.c['line']}"))
    s.add("Recurring-money candidates", s.panel(s.col(s.heading("Money keeps showing up", "Research candidates from the source session", "2026-08-12"), s.repeat_col("Recurring-money candidate rows",*rows, gap=0), s.button("Show all",compact=True),s.text("Names to investigate, with evidence from their own source session.", 11, s.c["muted"]), gap=16), "Recurring-money candidates"), 590 if s.mobile else 530, ["renderLeaders", "ldRows", "ldState", "ladder"], ["2026-08-12"], state="supplied_sample_names_and_on_radar_status", actions=["open name in Ticker", "expand original evidence", "show all when the source board has additional candidates"], note="Five supplied sample names are not represented as a complete count or ranked order. Scores, recurrence totals and active legs were not supplied. Show all is a retained control specimen; real visibility and count follow the source dataset. No fabricated rank numerals or completed evidence bars.")
    legs = s.repeat_col("Leader A evidence rows",*(s.row(s.text(label, 12.5, flex="1"), s.text("Unavailable", 11, s.c["muted"]), align_items="center", gap=12, padding="8px 0", border_bottom=f"1px solid {s.c['line']}") for label in EVIDENCE_A), gap=0)
    s.add("Leader evidence expansion", s.panel(s.col(s.heading("AAL · evidence", "Source 2026-08-12"), legs, s.text("Evidence values unavailable. An empty value is not a failed condition.", 11, s.c["muted"]), gap=16), "AAL evidence"), 600 if s.mobile else 510, ["A_LEGS", "ladder", "ldRows"], ["2026-08-12"], state="evidence_labels_with_unavailable_values", actions=["collapse evidence detail"])
    s.add("Washout-recovery candidates", s.panel(s.col(s.heading("Turned back up after a washout", "A separate board with its own evidence", "2026-08-12"), s.missing("Candidate values unavailable", "Candidate values are unavailable for this source session."), s.text("Evidence includes recent washout, oversold condition, turn signal, positive money, new positions, volume, and failed-breakout check.", 11, s.c["muted"]), gap=16), "Washout-recovery candidates"), 380 if s.mobile else 300, ["renderLeaders", "B_LEGS", "ldRows"], ["2026-08-12"], state="boardB_values_not_supplied", note="All seven exact B_LEGS labels are retained in metadata coverage; no pass/fail flags are invented.")
    s.add("Leader sector ETF context", s.panel(s.col(s.heading("Sector ETF flows", "Share-count estimates retain their individual source date"), s.missing(), gap=16), "Sector ETF flows"), 280 if s.mobile else 245, ["renderLeaders", ".oew-etf"], state="ETF_source_values_and_date_not_supplied")


def source_receipt(s):
    rows=[]
    for name, date, state in SOURCES:
        if s.mobile:
            rows.append(s.col(s.row(s.text(name, 12.5, weight=500), s.text(date, 11, s.c["muted"], mono=True), justify_content="space-between", gap=12), s.text(state, 11, s.c["muted"]), gap=4, padding="8px 0", border_bottom=f"1px solid {s.c['line']}"))
        else:
            rows.append(s.row(s.text(name, 12.5, weight=500, flex="1"), s.text(date, 11, s.c["muted"], mono=True, width="120px"), s.text(state, 11, s.c["muted"], width="140px"), gap=20, padding="10px 0", border_bottom=f"1px solid {s.c['line']}"))
    return s.panel(s.col(s.heading("Source details", "Latest completed session 2026-10-30"), s.repeat_col("Source receipt rows",*rows,gap=0), s.text("Scanner coverage 372/408 · 2026-08-13. Coverage belongs to that scanner snapshot. Each index card retains its own date.", 12.5, s.c["muted"]), s.text("Four independent readings, never averaged into one score. Historical readings describe their own source session.", 11, s.c["muted"]), gap=16), "Source details")


def payoff_rows(s):
    labels=["Straddle","Upside for downside","Downside hedge","Upside play"]
    size=13 if s.mobile else 12.5
    rows=[]
    for label in labels:
        content=[s.text(label,size,weight=500),s.text("Pricing unavailable",size,s.c["muted"])]
        rows.append(s.col(*content,gap=4,padding="12px 0",border_bottom=f"1px solid {s.c['line']}") if s.mobile else s.row(*content,gap=16,padding="12px 0",border_bottom=f"1px solid {s.c['line']}",justify_content="space-between"))
    return s.repeat_col("Payoff detail rows",*rows,gap=0)


def components():
    s=Screen("components",False,"light","component_review")
    s.add("Component review introduction",s.col(s.text("Options workspace components",28,weight=800),s.text("Dates, controls, disclosures, and the retained payoff structure.",14,s.c["muted"]),gap=8),120,[],state="explicit_UI_specimen")
    paired=[]
    for theme in ("light","dark"):
        x=Screen("components",False,theme)
        content=x.col(x.label(theme+" theme"),x.text("Dealer levels at the close",17,weight=700),x.text("2026-10-30",22,weight=700,mono=True),x.row(x.chip("Selected session"),x.chip("Earlier session"),x.chip("Date unavailable"),gap=8,flex_wrap="wrap"),x.row(x.button("View sources",compact=True),x.button("Retry",primary=True,compact=True),x.button("Keyboard focus",compact=True,focused=True),gap=12,flex_wrap="wrap"),x.text("Base canonical tokens. Source meaning never depends on color alone.",12.5,x.c["muted"]),gap=20)
        paired.append(div(content,name=theme+" canonical controls",display="flex",flex_direction="column",gap="20px",padding="24px",background=x.c["bg"],border=f"1px solid {x.c['line']}",border_radius="14px",flex="1",min_width="0"))
    s.add("Light and dark shared controls",s.repeat_row("Light and dark component cards",*paired,gap=24),340,[".oew", ".oew-secondary", ".oew-tab", ".oew-source-state"],state="explicit_UI_specimens")
    s.add("Expanded source receipt",source_receipt(s),490,["#oew-sources", ".oew-source-grid"],[r[1] for r in SOURCES],state="supplied_source_receipt")
    readings=s.repeat_row("Independent context cards",*[s.panel(s.col(s.label(label),s.text(value,17,weight=700),s.source(date,selected),s.text(note,12.5,s.c["muted"]),gap=12),label,16) for label,value,date,selected,note in [
        ("Whole market","Mixed — normalizing","2026-10-30",True,"VIX 19.4"),
        ("Index context","Source values unavailable","2026-10-20",False,"Separate from the current per-index GEX regime."),
        ("Options tape","Source values unavailable","2026-08-13",False,"Do not carry this reading into the selected session."),
        ("Same-day options","Source values unavailable","2026-08-13",False,"Share values are not supplied for this specimen."),
    ]],gap=16)
    s.add("Independent dated context readings",readings,310,[".oew-console-grid", ".oew-read", ".oew-reading-date"],[TARGET,"2026-10-20","2026-08-13"],state="mixed_supplied_and_unavailable_readings",note="No fabricated confidence pips. Actual whole-market state/VIX are supplied. Unknown posture values remain unavailable.")
    s.add("Expanded payoff structure",s.panel(s.col(s.heading("SPY · What a structure pays"),s.text("Structure prices: date unavailable · Dealer levels: 2026-10-30",12.5,s.c["muted"]),payoff_rows(s),s.text("End-of-day mid prices. Source date, expiry, cost, payout and risk appear only when supplied.",11,s.c["muted"]),gap=16),"Payoff structure"),390,[".oew-lab", "_PAYOFF_LAB_ROWS", "lab.source_session", "lab.dealer_session"],[TARGET],state="explicit_payoff_unavailable_specimen",note="Exact four retained row names; no quote, expiry, catalyst, price or breakeven is invented. Responsive behavior <=760px: an expanded index payoff card occupies the full row; level/money values >=12.5px, detail rows 13px, notes 12px. The recovery board includes this full-width mobile state.")
    historical=s.repeat_col("Earlier research inventory rows",*(s.row(s.text(label,14,weight=600,flex="1"),s.text(date,11,s.c["muted"],mono=bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}",date))),s.text("›",22,s.c["muted"]),gap=16,padding="16px 0",border_bottom=f"1px solid {s.c['line']}") for label,date in [("Options Intelligence Brief","2026-08-19"),("What changed","Individual source dates"),("Premium by sector","2026-08-13"),("Biggest single bets","2026-08-13"),("Names to investigate","Dates shown per group/name")]),gap=0)
    s.add("Earlier research content inventory",s.panel(s.col(s.heading("Earlier-session research", "Individual sections keep their original source sessions"),historical,gap=16),"Earlier research"),460,["#oew-history", "intelligence_brief", ".oew-rg"],["2026-08-19","2026-08-13","2026-08-12"],state="expanded_history_inventory",note="Inventory rows represent retained modules, not a change into new nested product disclosures. What changed has per-change dates and no invented aggregate date. Names to investigate retains group/name dates; near-flip context uses its own Scanner snapshot, not an aggregate Leaders date.")
    return s.board()


def recovery():
    s=Screen("recovery",True,"dark","state_review")
    s.add("Recovery specimen introduction",s.col(s.text("Recovery states",28,weight=800),s.text("Explicit interface specimens for loading, retry, empty results, and dates.",14,s.c["muted"]),gap=8),160,[],state="explicit_UI_specimen")
    s.add("Loading",s.panel(s.col(s.heading("Loading Scanner…"),s.text("Retrieving the source snapshot.",12.5,s.c["muted"]),div(height="8px",width="100%",background=s.c["panel2"],border_radius="999px"),gap=16),"Loading"),180,["loadMode", "aria-busy"],state="explicit_loading_specimen",note="Loading is distinct from empty results. A decorative track carries no market value or fabricated completion percentage.")
    s.add("Timeout and retry",s.panel(s.col(s.heading("Scanner could not load"),s.text("The request timed out. Retry to load the source snapshot.",12.5,s.c["muted"]),s.button("Retry",primary=True,focused=True),gap=16),"Timeout and retry"),230,["getJSON", "loadMode", "[data-retry-mode]"],state="explicit_timeout_specimen",actions=["keyboard-accessible retry", "one in-flight request per mode", "retry clears failed state"])
    s.add("No filter matches",s.panel(s.col(s.heading("No names match these filters"),s.text("Choose another preset or clear your filters to see the available snapshot.",12.5,s.c["muted"]),s.button("Clear all"),s.source("2026-08-13"),gap=16),"No filter matches"),260,["scBody", "#oew-f-clear"],["2026-08-13"],state="explicit_zero_match_specimen",note="This is not used for unavailable data. No market conclusion is inferred from a filter result.")
    s.add("Source date states",s.panel(s.col(s.heading("Source dates"),s.col(s.text("2026-10-30 · Selected session",12.5,s.c["muted"]),s.text("2026-08-13 · Earlier session",12.5,s.c["muted"]),s.text("Date unavailable",12.5,s.c["muted"]),s.text("Later source · requires its own date",12.5,s.c["muted"]),gap=16),s.text("A build timestamp does not establish a source session.",11,s.c["muted"]),gap=20),"Source date states"),320,["sourceContext", "sourceDay", ".oew-source-state"],[TARGET,"2026-08-13"],state="explicit_source_status_specimens",note="No hypothetical later market date is invented. Nov2 Leaders build timestamp is metadata, not the Aug12 source date.")
    s.add("Mobile source receipt",source_receipt(s),740,["#oew-sources", ".oew-source-grid"],[r[1] for r in SOURCES],state="expanded_mobile_receipt",actions=["disclosure keyboard open/close", "return focus to source control"])
    s.add("Expanded mobile payoff card",index_card(s,INDEXES[1],detailed=True,expanded_payoff=True),1060,[".oew-ic:has(.oew-lab[open])", ".oew-lab-row", ".oew-lab-foot", ".oew-ic-lv .v"],[TARGET],state="explicit_full_width_mobile_payoff_specimen",actions=["expand and collapse payoff without narrowing prices into a half-width card"],note="At viewport <=760px the expanded card spans the entire index-grid row, represented here as a 358px-wide native card in the 390px board. Money/level values are >=12.5px, payoff rows 13px, notes 12px. Prices remain unavailable until supplied; no quote-specific failure is inferred.")
    return s.board()


class EditableNode:
    def __init__(self,tag,attrs,opening,self_closing=False):
        self.tag,self.attrs,self.opening=tag,list(attrs),opening
        self.self_closing=self_closing
        self.children=[]
        self.changed=False
        match=re.match(r"<\s*([^\s/>]+)",opening)
        self.original_tag=match.group(1) if match else tag

    def get(self,key):
        return dict(self.attrs).get(key)

    def set(self,key,value):
        self.attrs=[(k,v) for k,v in self.attrs if k!=key]
        if value is not None:
            self.attrs.append((key,value))
        self.changed=True

    def render(self):
        if self.changed:
            attrs="".join(f' {k}="{esc(v)}"' if v is not None else f" {k}" for k,v in self.attrs)
            opening=f"<{self.original_tag}{attrs}{' /' if self.self_closing else ''}>"
        else:
            opening=self.opening
        if self.self_closing:
            return opening
        return opening+"".join(c.render() if isinstance(c,EditableNode) else c for c in self.children)+f"</{self.original_tag}>"


class EditableHTML(HTMLParser):
    def __init__(self,markup):
        super().__init__(convert_charrefs=False)
        self.roots=[]
        self.stack=[]
        self.feed(markup)
        assert not self.stack,"Unclosed editable nodes"

    def push(self,item):
        (self.stack[-1].children if self.stack else self.roots).append(item)

    def handle_starttag(self,tag,attrs):
        node=EditableNode(tag,attrs,self.get_starttag_text())
        self.push(node)
        self.stack.append(node)

    def handle_startendtag(self,tag,attrs):
        self.push(EditableNode(tag,attrs,self.get_starttag_text(),True))

    def handle_endtag(self,tag):
        assert self.stack and self.stack[-1].tag==tag,f"Mismatched editable end tag {tag}"
        self.stack.pop()

    def handle_data(self,data):
        self.push(data)

    def handle_entityref(self,name):
        self.push(f"&{name};")

    def handle_charref(self,name):
        self.push(f"&#{name};")


def split_repeated_items(board):
    """Compile repeated semantic items into topologically ordered one-item writes.

    Named slots stay inside the original layout. After the containing write, the
    importer binds each slot's actual native node ID, then appends each child in
    its own write_html call. Logical refs are never sent as native Paper IDs.
    """
    compiled=[]

    def emit(fragment,parent_ref,kind):
        parser=EditableHTML(fragment["html"])
        roots=[n for n in parser.roots if isinstance(n,EditableNode)]
        assert len(roots)==1,"Each write must have exactly one editable root"
        pending=[]
        bindings=[dict(logical_ref=fragment["id"],match="created_root")]

        def visit(node):
            if node.get("data-paper-repeat"):
                name=node.get("layer-name")
                assert name,"Every repeated collection needs a named native slot"
                ref=fragment["id"]+"/container/"+str(len(bindings))
                items=[c for c in node.children if isinstance(c,EditableNode)]
                assert all(isinstance(c,EditableNode) or not c.strip() for c in node.children)
                node.children=[]
                node.set("data-paper-repeat",None)
                bindings.append(dict(logical_ref=ref,match="named_descendant",layer_name=name,within_logical_ref=fragment["id"]))
                for i,item in enumerate(items,1):
                    if not item.get("layer-name"):
                        item.set("layer-name",f"{name} · item {i:02d}")
                    pending.append((ref,name,i,item))
                return
            for child in node.children:
                if isinstance(child,EditableNode):
                    visit(child)

        visit(roots[0])
        own=dict(fragment)
        own["html"]=roots[0].render() if pending else fragment["html"]
        own["logical_parent_ref"]=parent_ref
        own["write_kind"]=kind
        own["provides_nodes"]=bindings
        own["estimated_root_height_contribution"]=fragment["estimated_height"] if kind=="board_group" else 0
        own["import_sequence"]=len(compiled)+1
        compiled.append(own)
        for ref,name,i,item in pending:
            child=dict(fragment)
            child.update(id=ref+f"/item/{i:02d}",name=item.get("layer-name"),html=item.render(),estimated_height=None,
                         repeated_collection=name,repeated_item_index=i,note=(fragment.get("note") or "")+" Imported as one repeated item into its registered parent container.")
            emit(child,ref,"repeated_item")

    for original in board["fragments"]:
        section_start=len(compiled)
        emit(original,"artboard:"+board["id"],"board_group")
        compiled[section_start]["section_complete_after"]=compiled[-1]["id"]
    board["fragments"]=compiled
    board["estimated_height"]=sum(f["estimated_root_height_contribution"] or 0 for f in compiled)+44
    board["import_root_ref"]="artboard:"+board["id"]
    return board


def source_svg(s,markup):
    """Keep measured paths, bars and coordinates; resolve only presentation."""
    svg=ET.fromstring(markup)
    paths_before=[node.get("d") for node in svg.iter("path")]
    original_box=[float(v) for v in svg.get("viewBox").split()]
    w,h=original_box[2:]
    for parent in list(svg.iter()):
        for child in list(parent):
            cls=child.get("class","")
            if "l-zh" in cls.split() or (s.mobile and child.tag=="text" and "l-en" in cls.split()):
                parent.remove(child)
    mapping={"--line":s.c["line"],"--muted":s.c["muted"],"--text":s.c["text"],"--up":s.c["up"],"--down":s.c["down"],"--oew-accent":s.c["info"]}
    for node in svg.iter():
        node.attrib.pop("class",None)
        for key,value in list(node.attrib.items()):
            for token,color in mapping.items():
                value=value.replace("var("+token+")",color)
            node.set(key,value)
        if node.tag=="text":
            node.set("font-family",UI)
            if s.mobile:
                node.set("font-size","23.5")
                if float(node.get("y","0"))>=h-16 and h!=400:
                    node.set("y",str(float(node.get("y"))+32))
    if s.mobile:
        svg.set("viewBox",f"-30 -8 610 {h+52:g}")
        rendered_w=318
        rendered_h=rendered_w*(h+52)/610
    else:
        rendered_w=640
        rendered_h=rendered_w*h/w
    svg.set("width",str(rendered_w))
    svg.set("height",f"{rendered_h:.2f}")
    svg.set("style",f"display:block;width:{rendered_w}px;height:{rendered_h:.2f}px;flex-shrink:0")
    assert paths_before==[node.get("d") for node in svg.iter("path")]
    result=ET.tostring(svg,encoding="unicode",short_empty_elements=False)
    assert all(name in TOKEN_VALUES for name in re.findall(r"var\((--[\w-]+)\)", result))
    assert "<script" not in result and "href=" not in result
    return result,dict(original_sha256=hashlib.sha256(markup.encode()).hexdigest(),rendered_sha256=hashlib.sha256(result.encode()).hexdigest(),path_data_unchanged=True,presentation_changes=["bind existing Paper semantic color tokens","retain English locale only","Inter font"]+(["larger mobile axis type with viewBox padding","move bottom-axis labels for separation","move crowded right-side labels into external legend"] if s.mobile else []))


def enrich_with_actual_samples(boards,samples):
    sample_hash=hashlib.sha256(ACTUAL_SAMPLES.read_bytes()).hexdigest()
    modes=samples["modes"]
    fixture_pin=samples["manifest"]["source_pin"]

    def panel(mode,title):
        return next(p for p in modes[mode]["panels"] if p.get("title")==title)

    def set_fragment(board,s,name,content,dates,proof,height=None,extra=None):
        old=next(f for f in board["fragments"] if f["name"]==name)
        old["html"]=div(content,name=name,display="flex",flex_direction="column",gap="20px",width=f"{s.width}px",padding=f"20px {s.pad}px 0",background=s.c["bg"],color=s.c["text"],font_family=UI)
        old["source_dates"]=dates
        old["data_state"]="verified_rendered_fixture"
        old["provenance"]=dict(file=str(ACTUAL_SAMPLES),sha256=sample_hash,source_pin=fixture_pin,json_path=proof)
        if extra:
            old["provenance"].update(extra)
        if height is not None:
            old["estimated_height"]=height
        old["note"]="Values and text are copied from the verified dated fixture. The design artifact is a bounded view; production retains the full source records. No missing observations are interpolated."
        return old

    def metrics(s,name,items):
        return s.repeat_row(name,*(s.col(s.label(label),s.text(value,22 if not s.mobile else 17,weight=600,mono=True),gap=8,width="calc((100% - 12px) / 2)" if s.mobile else "calc((100% - 60px) / 4)") for label,value in items),gap=12 if s.mobile else 20,flex_wrap="wrap")

    def etf_cards(s,name,records):
        cards=[]
        for symbol,value,detail in records:
            ink=s.c["ink_down"] if "−" in value or value.startswith("-") or value.startswith("~-") else s.c["ink_up"]
            content=s.col(s.text(symbol,14,weight=700,mono=True),s.text(value,22 if not s.mobile else 17,ink,600,mono=True),*(s.text(line,11,s.c["muted"]) for line in detail),gap=8)
            cards.append(div(s.panel(content,symbol+" ETF",12),width="calc((100% - 12px) / 2)" if s.mobile else "calc((100% - 48px) / 4)",flex_shrink="0"))
        return s.repeat_row(name,*cards,gap=12 if s.mobile else 16,flex_wrap="wrap")

    def source_leaders(p):
        lines=[line.strip() for line in p["text"].splitlines() if line.strip()]
        starts=[i for i,line in enumerate(lines) if re.fullmatch(r"\d{2}",line)]
        records=[]
        for n,start in enumerate(starts):
            end=starts[n+1] if n+1<len(starts) else next((i for i in range(start+1,len(lines)) if lines[i].startswith("Show all")),len(lines))
            values=lines[start+1:end]
            state_at=values.index("On the radar")
            records.append(dict(rank=lines[start],symbol=values[0],sector=" · ".join(values[1:state_at]),state=values[state_at],evidence=values[state_at+1],read=values[state_at+2],cautions=values[state_at+3:]))
        return records,next(line for line in lines if line.startswith("Show all"))

    for board in boards:
        mode=board["id"].split("-")[0]
        s=Screen(mode,board["width"]==390,board["theme"],board["variant"])
        if mode=="flow":
            sector=panel("flow","Premium by sector — the full desk")
            tones={}
            lines=sector["text"].splitlines()
            for i,line in enumerate(lines):
                key=line.lstrip("⚑")
                if key in {r[0] for r in SECTORS} and i+2<len(lines):
                    tones[key]=lines[i+2]
            rows=[]
            for name,value,formatted in SECTORS:
                tone=tones[name]
                chip=s.chip(tone,"up" if tone.startswith("buying") else "down" if tone.startswith("selling") else "muted")
                label=("⚑ " if "⚑"+name in sector["text"] else "")+name
                bar=div(div(width=f"{value/10900*100:.6f}%",height="8px",background=s.c["info"],border_radius="999px"),height="8px",width="100%",background=s.c["panel2"],border_radius="999px")
                rows.append(s.col(s.row(s.text(label,12.5),s.text(formatted,12.5,weight=600,mono=True),justify_content="space-between"),bar,s.row(chip,gap=8),gap=8) if s.mobile else s.row(s.text(label,12.5,width="150px",flex_shrink="0"),div(bar,flex="1"),s.text(formatted,12.5,weight=600,mono=True,width="90px",text_align="right"),chip,gap=16,align_items="center"))
            content=s.panel(s.col(s.heading("Premium by sector — the full desk","Every covered sector · shared scale · unusual days flagged","2026-08-13"),s.repeat_col("Sector premium rows",*rows,gap=16),s.text("A record of where options money went in that session, not a forecast of where it goes next. Direction is approximate ~.",11,s.c["muted"]),gap=20),"Sector premium")
            set_fragment(board,s,"Dated sector-premium bars",content,["2026-08-13"],"modes.flow.panels[0]",1080 if s.mobile else 650)
            etf=panel("flow","Sector ETF money")
            records=[]
            lines=etf["text"].splitlines()
            for i,line in enumerate(lines):
                if re.fullmatch(r"XL[A-Z]+",line):
                    records.append((line,lines[i+1],lines[i+2].split(" · ")))
            content=s.panel(s.col(s.heading("Sector ETF money","Share-count estimates · 1D, 5D and 21D","2026-10-19"),etf_cards(s,"Flow ETF cards",records),s.text("Estimates from share-count changes, not reported fund flows. A background check, not a signal.",11,s.c["muted"]),gap=20),"Sector ETF money")
            set_fragment(board,s,"Sector ETF money",content,["2026-10-19"],"modes.flow.panels[2]",1230 if s.mobile else 670)
            theme=panel("flow","Theme groups")
            content=s.panel(s.col(s.heading("Theme groups","How the big themes traded as groups"),s.missing("Theme-group data unavailable","Theme-group data is unavailable for this source session."),gap=16),"Theme groups")
            set_fragment(board,s,"Theme groups",content,[],"modes.flow.panels[1]")
            charts=flow_tide_charts(s,"2026-08-13")
            content=s.panel(s.col(s.heading("The tide","Historical net premium and a separately dated intraday record"),s.repeat_col("Tide chart frames",*charts,gap=20) if s.mobile else s.repeat_row("Tide chart frames",*charts,gap=20),s.text("Shape only. Direction is approximate ~ and is never a buy or sell signal.",11,s.c["muted"]),gap=20),"The tide")
            tide=set_fragment(board,s,"The tide and intraday record",content,["2026-08-13"],"modes.flow.panels[3]")
            tide["data_state"]="historical_canvas_observations_not_exported_actual_intraday_empty"
            tide["note"]="The historical series is dated Aug13. Its canvas observations were not exported, so no curve is invented and no historical producer failure is asserted. The fixture has an empty intraday record but does not record LIVE_SESSION_DATE; its requested session is explicitly unknown and never borrowed from the historical series. The current implementation labels each chart with its own date."

        elif mode=="scanner":
            actual_rows=modes["scanner"]["rows"]
            rendered=[]
            labels=["Spot","IV 30d","IV rank","Expected move","Put/call OI","Volume","Premium","Tone","Row lag"]
            for row in actual_rows:
                name_parts=[v.strip() for v in row[0].splitlines() if v.strip() and v.strip()!="→"]
                symbol,sector=name_parts[0]," · ".join(name_parts[1:])
                if s.mobile:
                    name=s.row(s.text(symbol+" ↗",14,s.c["ink_link"],700,mono=True),s.text(sector,11.5,s.c["muted"]),gap=8,align_items="center",width="200px",flex_shrink="0",white_space="nowrap",position="sticky",left="0",z_index="1",background=s.c["panel"])
                    cells=[name]+[s.text(v,12.5,weight=500,mono=i!=7,flex="1",min_width="0",white_space="nowrap",text_align="right") for i,v in enumerate(row[1:])]
                    rendered.append(s.row(*cells,gap=12,padding="12px 0",border_bottom=f"1px solid {s.c['line']}",align_items="center",width="100%"))
                else:
                    cells=[s.col(s.text(symbol+" ↗",14,s.c["ink_link"],700,mono=True),s.text(sector,10,s.c["muted"]),gap=4,width="160px",flex_shrink="0")]+[s.text(v,12.5,weight=500,mono=i!=7,flex="1",min_width="0") for i,v in enumerate(row[1:])]
                    rendered.append(s.row(*cells,gap=12,padding="12px 0",border_bottom=f"1px solid {s.c['line']}",align_items="center"))
            first=s.text("Name",11.5 if s.mobile else 11,s.c["muted"],600,width="200px" if s.mobile else "160px",flex_shrink="0",position="sticky" if s.mobile else None,left="0" if s.mobile else None,z_index="1" if s.mobile else None,background=s.c["panel"] if s.mobile else None)
            head=s.row(first,*(s.text(v,11.5 if s.mobile else 11,s.c["muted"],600,flex="1",min_width="0",white_space="nowrap" if s.mobile else None,text_align="right" if s.mobile else None) for v in labels),gap=12,padding="12px 0",border_bottom=f"1px solid {s.c['line']}")
            table=s.col(head,s.repeat_col("Verified Scanner rows",*rendered,gap=0),gap=0,width="1200px" if s.mobile else "100%",min_width="850px" if s.mobile else "0")
            viewport=div(table,name=s.id+" · Horizontal Scanner viewport",width="100%",min_width="0",overflow_x="auto",overflow_y="hidden",overscroll_behavior_x="contain") if s.mobile else table
            content=s.panel(s.col(s.heading("Screener","408 screened names · sort any column, filter above.","2026-08-13"),s.text("Scroll horizontally for all 10 columns →",12.5,s.c["ink_link"]) if s.mobile else "",viewport,s.text("Row lag is relative to this scanner snapshot. It does not describe freshness against the selected session.",12.5,s.c["muted"]),gap=16),"Verified Scanner results")
            frag=set_fragment(board,s,"Scanner results structure",content,["2026-08-13"],"modes.scanner.rows + modes.scanner.panels[0]",960)
            frag["provenance"].update(rendered_rows=8,source_total_rows=408,coverage_reported_separately="372/408; never substituted for the actual 408-row export")
            if s.mobile:
                frag["provenance"]["table_layout"]=dict(kind="horizontal_scroll",source_minimum_width_px=850,design_table_width_px=1200,rendered_columns=["Name"]+labels,initial_view="Name and Spot, with remaining columns inside the same horizontal scroller",sticky_name_column=True,source_selectors=[".oew-tblwrap","table.oew-tbl","@media (max-width:760px)"],geometry_note="1200px is an explicit editable specimen width, not an assertion about the runtime table's measured width.")
                frag["intended_actions"].append("horizontal scrolling exposes all ten Overview columns; the name column remains visible")

        elif mode=="ticker":
            header=s.panel(s.col(s.row(s.col(s.text("SPY",28,weight=800,mono=True),s.text("S&P 500 ETF",12.5,s.c["muted"]),gap=4),s.col(s.label("Last close"),s.text("755.72",28,weight=700,mono=True),gap=4),justify_content="space-between",align_items="center"),s.source(TARGET),s.text("Jumpy — moves get amplified",17,weight=700),s.text("Dealer hedging at this source close trades with the market, so swings run larger and sell-offs can pick up speed.",12.5,s.c["muted"]),s.chip("Protect gains","warn"),s.text("1-day implied range 748.39–763.05 ±0.97%",12.5,weight=500,mono=True),gap=16),"SPY dated close and regime")
            set_fragment(board,s,"SPY dated close and regime",header,[TARGET],"modes.ticker.panels[0]",400 if s.mobile else 340)
            film=s.panel(s.col(s.heading("How the day traded","Partial intraday record","2026-10-16"),s.row(s.text("09:30",12.5,s.c["muted"],mono=True),s.text("16:00",12.5,s.c["muted"],mono=True),justify_content="space-between"),s.text("The intraday record covers only part of the session — Premium built steadily in one direction and stayed.",14),gap=20),"How the day traded")
            set_fragment(board,s,"How the day traded",film,["2026-10-16"],"modes.ticker.panels[1]",300 if s.mobile else 250)
            track,_=level_track(s,INDEXES[1],s.inner,pad_ratio=0.12)
            magnet_pct=(770-(750-50*0.12))/(50*1.24)*100
            marker=div(name="SPY source magnet 770",position="absolute",left=f"calc({magnet_pct:.5f}% - 4px)",top="10px",width="8px",height="8px",border=f"1px solid {s.c['muted']}",background=s.c["panel"])
            track=track[:-6]+marker+"</div>"
            levelrows=[]
            for label,value,description,disagreement in [("Ceiling — call wall","800","+5.9% from close",True),("Flip — the regime line","772.93","+2.3% from close",False),("Magnet — max pain","770","+1.9% from close",False),("Floor — put wall","750","−0.8% from close",True)]:
                left=s.col(s.text(label,14,weight=600),s.text(description,12.5,s.c["muted"]),s.chip("Open interest disagrees","warn") if disagreement else "",gap=8,flex="1")
                levelrows.append(s.row(left,s.text(value,15,weight=600,mono=True),gap=16,align_items="center",padding="12px 0",border_bottom=f"1px solid {s.c['line']}"))
            content=s.panel(s.col(s.heading("The map — where dealer hedging sits",date=TARGET),track,s.repeat_col("Ticker dealer level rows",*levelrows,gap=0),s.text("Model estimates from the source close shown here. Intraday moves do not confirm a level.",11,s.c["muted"]),gap=20),"SPY dealer map")
            set_fragment(board,s,"SPY dealer map and level detail",content,[TARGET],"modes.ticker.panels[2]",700 if s.mobile else 590,dict(magnet=770,wall_check="open interest disagrees at both walls",level_strengths="not supplied; no confidence bars inferred"))
            rich=s.panel(s.col(s.heading("Rich or cheap?",date=TARGET),s.chip("Vol rich","warn"),s.text("Options on SPY cost more than 98% of the last 40 sessions we have on file.",17,weight=600),s.text("Still building toward a full year of history — read this as a rough placement, not a settled rank.",12.5,s.c["muted"]),gap=16),"Rich or cheap")
            set_fragment(board,s,"Rich or cheap?",rich,[TARGET],"modes.ticker.panels[3]",320 if s.mobile else 260)
            position_cards=[]
            for label,rows in [("Built",[("570P","+149,684"),("670P","+74,919"),("640P","+74,582")]),("Unwound",[("785C","−16,685"),("788C","−15,847"),("755P","−10,947")])]:
                position_cards.append(s.panel(s.col(s.label(label),s.repeat_col(label+" position rows",*(s.row(s.text(k,14,weight=600,mono=True),s.text(v,14,weight=600,mono=True),justify_content="space-between",gap=12) for k,v in rows),gap=12),gap=16),label,16))
            content=s.panel(s.col(s.heading("Where positions built","Open-interest change between the last two chain snapshots","2026-08-13"),s.repeat_col("Position-change panels",*position_cards,gap=12) if s.mobile else s.repeat_row("Position-change panels",*position_cards,gap=20),s.text("A count of contracts opened or closed, not a direction call.",12.5,s.c["muted"]),s.text("Separate record: net dealer gamma is above 15% of 40 stored trading-day readings, 2026-08-20 to 2026-10-30. This is a short history.",11,s.c["muted"]),gap=20),"Where positions built")
            set_fragment(board,s,"Where positions built",content,["2026-08-13",TARGET],"modes.ticker.panels[4]",600 if s.mobile else 400)
            reads=[s.panel(s.col(s.label(label),s.text(value,17,weight=700),s.text(description,12.5,s.c["muted"]),gap=12),label,16) for label,value,description in [("The tape — calm or jumpy?","Jumpy","Dealer hedging adds to moves."),("The mood — what options cost","15.4% IV","What the options market charges for 30-day cover."),("The lean — direction by time window","Put-heavy","Weaker evidence than the tape read; context, not a signal.")]]
            set_fragment(board,s,"Three independent ticker readings",s.repeat_col("Ticker independent readings",*reads,gap=12) if s.mobile else s.repeat_row("Ticker independent readings",*reads,gap=20),[TARGET],"modes.ticker.panels[5:8]")
            unmeasured=[s.panel(s.col(s.heading(title),s.text(description,12.5,s.c["muted"]),s.text("Not measured yet — nothing here to act on.",12.5,weight=600),gap=16),title,16) for title,description in [("What the move is worth","The expected move is in the header. Its accuracy against what actually happened is not measured yet."),("Expiration pressure","The share of open interest rolling off in the next few days, and whether that concentration feeds on itself, is not measured yet.")]]
            set_fragment(board,s,"Move value and expiration pressure",s.repeat_col("Ticker unmeasured capabilities",*unmeasured,gap=16) if s.mobile else s.repeat_row("Ticker unmeasured capabilities",*unmeasured,gap=20),[],"modes.ticker.panels[8:10]")
            content=s.panel(s.col(s.heading("Measured options flow","What actually traded, before any interpretation","2026-08-13"),metrics(s,"Ticker measured flow metrics",[("Premium","$1.8B"),("Same-day","65%"),("Put/call","0.95x"),("Net premium","+$404M")]),s.text("Size is a solid read. Direction comes from tick-rule signing and is not reliable enough to read on its own.",11,s.c["muted"]),gap=20),"Measured options flow")
            set_fragment(board,s,"Measured options flow",content,["2026-08-13"],"modes.ticker.panels[10]")
            content=s.panel(s.col(s.heading("Under the hood — the raw options structure","Charts and the full strike record ↓",TARGET),metrics(s,"Ticker raw structure metrics",[("Net gamma","-11.87B"),("Strikes","5428"),("Put/call OI","1.71x"),("Max pain","770"),("Chain depth","full")]),s.text("Every figure is reconstructed from the options chain. Real dealer books are unobservable.",11,s.c["muted"]),gap=20),"Advanced research entry",16)
            set_fragment(board,s,"Advanced research entry",content,[TARGET],"modes.ticker.panels[11]",440 if s.mobile else 280)
            for raw_i,raw in enumerate(modes["ticker"]["raw"]):
                title=raw["title"]
                paragraphs=[x.strip() for x in raw["text"].split("\n\n") if x.strip()]
                subtitle=paragraphs[1] if len(paragraphs)>1 else None
                extra={}
                if raw.get("svgs"):
                    svg,svg_proof=source_svg(s,raw["svgs"][0])
                    legends={"Dealer gamma by strike":["Call gamma","Put gamma","Call wall","Flip","Last close","Put wall"],"Net gamma against price":["Last close","Flip"],"What cover costs by strike":["Call side","Put side","Nov 03 · 2d"],"What cover costs by date":[]}[title]
                    legend_colors={"Call gamma":s.c["up"],"Put gamma":s.c["down"],"Call wall":s.c["up"],"Put wall":s.c["down"],"Flip":s.c["info"],"Last close":s.c["text"],"Call side":s.c["up"],"Put side":s.c["down"]}
                    legend=s.row(*(s.row(div(width="8px",height="8px",border_radius="2px",background=legend_colors.get(v,s.c["muted"])),s.text(v,11,s.c["muted"]),gap=8,align_items="center") for v in legends),gap=12,flex_wrap="wrap")
                    body=s.col(div(svg,display="flex",justify_content="center",width="100%"),legend,gap=12)
                    extra["svg"]=svg_proof
                    height=450 if s.mobile else 670 if raw_i==0 else 550
                elif title=="Every expiry on file":
                    lines=raw["text"].splitlines()
                    headers=["Expiry","Days","ATM IV","Implied move","Straddle","Magnet"]
                    rows=[line.split("\t") for line in lines if line.startswith("Nov ")]
                    rendered=[]
                    for row in rows:
                        if s.mobile:
                            rendered.append(s.panel(s.col(s.text(row[0],15,weight=700),s.row(*(s.col(s.label(k),s.text(v,12.5,weight=500,mono=True),gap=4,width="calc((100% - 12px) / 2)") for k,v in zip(headers[1:],row[1:])),gap=12,flex_wrap="wrap"),gap=12),row[0]+" expiry",12))
                        else:
                            rendered.append(s.row(*(s.text(v,12.5,weight=500,mono=True,flex="1") for v in row),gap=12,padding="12px 0",border_bottom=f"1px solid {s.c['line']}"))
                    head="" if s.mobile else s.row(*(s.text(v,11,s.c["muted"],600,flex="1") for v in headers),gap=12)
                    body=s.col(head,s.repeat_col("Expiry record rows",*rendered,gap=12 if s.mobile else 0),gap=12)
                    height=2950 if s.mobile else 850
                    extra["rendered_expiries"]=len(rows)
                elif title=="Positioning greeks":
                    body=metrics(s,"Positioning Greek metrics",[("Net delta","+$205.4B"),("Net vanna","4.30B"),("Charm bias","↓ drifts down"),("Put/call OI","1.71x"),("Put/call volume","1.63x"),("Busiest strike","700"),("Strikes","5428")])
                    height=600 if s.mobile else 350
                else:
                    lines=raw["text"].splitlines()
                    records=[line.split("\t") for line in lines if re.match(r"^\d{3}\t",line)]
                    selected=[row for row in records if row[0] in ["780","775","770","765","760","755","750","745"]]
                    expiries=["Nov 02","Nov 03","Nov 04","Nov 05","Nov 06","Nov 09","Nov 13","Nov 20","Nov 27","Nov 30","Dec 04","Dec 18"]
                    shown=3 if s.mobile else 12
                    headers=["Strike"]+expiries[:shown]
                    subtitle="Rows are strikes and columns are expiries. Green marks positive values; red marks negative values."
                    head=s.row(*(s.text(v,10 if not s.mobile else 11,s.c["muted"],600,flex="1",min_width="0",padding="4px") for v in headers),gap=4)
                    values=[]
                    for row in selected:
                        cells=[]
                        for j,v in enumerate(row[:shown+1]):
                            # Paper Text supports foreground color, not a cell fill.
                            # Encode source sign only; blank/zero/strike cells keep base ink.
                            sign_color=s.c["text"]
                            if j and v.strip():
                                try:
                                    value=float(v.replace(",", "").replace("−", "-"))
                                except ValueError:
                                    value=None
                                if value is not None and value>0:
                                    sign_color=s.c["ink_up"]
                                elif value is not None and value<0:
                                    sign_color=s.c["ink_down"]
                            cells.append(s.text(v,12.5,color=sign_color,weight=600 if j==0 else 400,mono=True,
                                                flex="1",min_width="0",padding="4px"))
                        values.append(s.row(*cells,gap=4,padding="12px 0",border_bottom=f"1px solid {s.c['line']}"))
                    body=s.col(s.text("Selected strikes around the close",12.5,s.c["muted"]),head,s.repeat_col("Surface strike rows",*values,gap=0),s.text("Scroll for more expiries →" if s.mobile else "Source record: 26 strike rows and 12 expiries.",11,s.c["muted"]),gap=12)
                    height=700
                    extra.update(source_strike_rows=len(records),rendered_strike_rows=len(selected),source_expiries=12,visible_expiry_columns=shown,selection="bounded design viewport; full record remains in the production structure table",empty_cells="preserved as blank; never relabeled as zero or unavailable")
                content=s.panel(s.col(s.heading(title,subtitle,TARGET),body,gap=20),title,16)
                set_fragment(board,s,title,content,[TARGET],f"modes.ticker.raw[{raw_i}]",height,extra)

        elif mode=="leaders":
            for title,fragment_name in [("Money keeps showing up","Recurring-money candidates"),("Turned back up after a washout","Washout-recovery candidates")]:
                p=panel("leaders",title)
                records,show_all=source_leaders(p)
                rows=[]
                for r in records:
                    head=s.row(s.text(r["rank"],11,s.c["muted"],mono=True),s.text(r["symbol"]+" ↗",15,s.c["ink_link"],700,mono=True),s.chip(r["state"]),gap=12,align_items="center",flex_wrap="wrap")
                    source_read="turned up in this session" if r["read"]=="turned up today" else r["read"]
                    row=s.col(head,s.text(r["sector"],11,s.c["muted"]) if r["sector"] else "",s.text(r["evidence"]+" · "+source_read,12.5,s.c["muted"]),s.row(*(s.chip(c) for c in r["cautions"]),gap=8,flex_wrap="wrap"),gap=8,padding="16px 0",border_bottom=f"1px solid {s.c['line']}")
                    rows.append(row)
                content=s.panel(s.col(s.heading(title,"Top 12 from the source board · evidence belongs to this session","2026-08-12"),s.repeat_col(title+" candidates",*rows,gap=0),s.button(show_all,compact=True),s.text("Names to investigate. This historical research is not a queue to buy.",11,s.c["muted"]),gap=16),title)
                set_fragment(board,s,fragment_name,content,["2026-08-12"],"modes.leaders.panels[0]" if title.startswith("Money") else "modes.leaders.panels[1]",2450 if s.mobile else 2050,dict(rendered_candidates=len(records),evidence_value_meaning="source ladder fraction; not a probability or invented confidence score"))
            p=panel("leaders","Sector ETF flows")
            records=[]
            lines=p["text"].splitlines()
            for i,line in enumerate(lines):
                if re.fullmatch(r"[A-Z]{2,4}",line) and i+2<len(lines) and lines[i+2]=="net premium":
                    records.append((line,lines[i+1],["net premium"]))
            content=s.panel(s.col(s.heading("Sector ETF flows","Net premium labels from the source record","2026-08-12"),etf_cards(s,"Leader ETF cards",records),s.text("These are estimates, not reported fund flows. Useful as a background check, not as a signal.",11,s.c["muted"]),gap=20),"Sector ETF flows")
            set_fragment(board,s,"Leader sector ETF context",content,["2026-08-12"],"modes.leaders.panels[2]",1750 if s.mobile else 1000)
    return boards


def build():
    template = TEMPLATE.read_bytes()
    builder = BUILDER.read_bytes()
    boards=[]
    for mode,desktop,mobile,fn in [("brief","light","dark",brief),("flow","dark","light",flow),("scanner","light","dark",scanner),("ticker","dark","light",ticker),("leaders","light","dark",leaders)]:
        for is_mobile,theme in [(False,desktop),(True,mobile)]:
            s=Screen(mode,is_mobile,theme)
            s.shell();s.chrome();fn(s)
            if mode in ("brief","ticker"):
                s.terminal()
            boards.append(s.board())
    boards += [components(),recovery()]
    if OBSERVED:
        boards=enrich_with_actual_samples(boards,OBSERVED)
    status_original=MOBILE_STATUS_BAR.read_text()
    for board in boards:
        if board["width"]==390:
            markup=status_original if board["theme"]=="dark" else status_original.replace("color: white","color: black").replace('fill="white"','fill="black"')
            board["fragments"].insert(0,dict(id=board["id"]+"/00-mobile-status-bar",name="Official mobile status bar",html=markup,estimated_height=62,source_selectors=[],source_dates=[],data_state="Paper_guide_framing_only",intended_actions=[],note="Exact official Paper mobile status-bar markup, first child. Light boards change only white text/fill to black. Spacing, SVG paths, structure and system-ui font are preserved. This is mockup framing and must never be added to website source.",provenance=dict(file=str(MOBILE_STATUS_BAR),sha256=hashlib.sha256(status_original.encode()).hexdigest(),allowed_change="white to black colors on light boards only")))
        split_repeated_items(board)
        if board["id"].startswith("flow-"):
            for fragment in board["fragments"]:
                if fragment["name"].endswith("Tide chart frames · item 02"):
                    fragment["source_dates"]=[]
                    fragment["note"]="Intraday record unavailable. The exact fixture did not record its requested LIVE_SESSION_DATE; no intraday source date is asserted."
    result=dict(
        schema="mastermind.options.paper_blueprint.v2",
        status="NOT_APPLIED_TO_PAPER",
        generated_at=datetime.now(timezone.utc).isoformat(),
        source=dict(template=dict(path=str(TEMPLATE),sha256=hashlib.sha256(template).hexdigest()),builder=dict(path=str(BUILDER),sha256=hashlib.sha256(builder).hexdigest()),source_kind="current local production candidate plus parent-supplied verified source values", live_Paper_document=None, artboard_ids=[], live_page_verification=False),
        scope="Editable design import preflight. No Paper edits, implementation claim, market-data synthesis, or production approval.",
        tokens=dict(themes=TOKENS,font_ui=UI,font_machine=MONO,font_available_cjk="PingFang SC",qualified_font_weights={"Inter":[400,500,600,700,800,900],"Menlo":[400,700],"PingFang SC":[100,200,300,400,500,600]},type_px=[10,11,12,12.5,13,14,15,17,22,28,38,46],weights=[400,500,600,700,800],spacing_px=[4,8,12,16,20,24,32,44],radii_px=[8,10,12,14,999],note="Verified 91-token subset of the inspected live Paper catalog. Website soft-contrast is a canonical runtime transformation. CJK never uses Menlo. Designed Menlo values use only 400/700. Official status framing retains supplied system-ui pending actual render inspection; no unsupported-font correction is assumed."),
        data_provenance=dict(target_session=TARGET,sources=[dict(name=n,source_session=d,status=st) for n,d,st in SOURCES],indexes=INDEXES,index_regime="short",index_regime_source="gex/<symbol>.json summary.regime",regime_passport=dict(basis="assumption",verdict="display-only"),vix=19.4,flow_sector_premium_millions=[dict(name=n,value=v,label=l) for n,v,l in SECTORS],scanner_coverage=dict(covered=372,universe=408,source_session="2026-08-13"),leader_samples=dict(symbols=["AAL","AAPL","ABNB","ACLS","ADBE"],state="On radar",source_session="2026-08-12",build_date="2026-11-02",build_date_usage="metadata only; never the source-session label"),unavailable_values="Unavailable modules are explicit design states for values absent from the supplied evidence. They do not assert that all corresponding production APIs are unavailable."),
        coverage=dict(modes=["brief","flow","scanner","ticker","leaders"],desktop_width=1440,mobile_width=390,paired_workspace_boards=10,component_state_boards=2,scanner_presets=PRESETS,scanner_ranges=RANGES+["From flip maximum"],scanner_views=["Overview","Flow","Positioning"],scanner_columns=dict(Overview=["Name","Spot","IV 30d","IV rank","Expected move","Put/call OI","Volume","Premium","Tone","Row lag"],Flow=["Name","Net premium","Same-day share","Volume","Premium","Tone","Row lag"],Positioning=["Name","Spot","From flip","Ceiling","Floor","Behaviour","Tone","Row lag"]),scanner_lag_meaning="Row lag / 行数据滞后 is relative to the scanner snapshot, not selected-session freshness.",terminal_heading={"en":"Continue in the live Terminal","zh":"前往实时交易终端"},mobile_payoff=dict(breakpoint_max_width=760,expanded_card="spans full index row",minimum_money_level_font_px=12.5,detail_row_font_px=13,note_font_px=12),raw_ticker_panels=RAW_PANELS,leader_evidence_A=EVIDENCE_A,leader_evidence_B=EVIDENCE_B,advanced_capability_note="Verified source rows/SVGs are design content. They are not proof of implemented or functioning advanced engines.",shared_assistant="Retain existing shared assistant. Verify actual shared-shell viewport and scroll/focus behavior after Paper import and implementation."),
        import_contract=dict(version=2,root_registry="Register each created native artboard node ID under board.import_root_ref before importing fragments.",parent_field="logical_parent_ref",binding_field="provides_nodes",binding_matches=dict(created_root="Bind the single native root returned/observed after this write.",named_descendant="Within that newly created root, resolve exactly one native node whose name equals layer_name; bind its actual native ID under logical_ref."),fragment_order="Use boards[].fragments[] in import_sequence order. Parent refs are always registered before their children.",write_unit="Exactly one write_html call per fragment.html. Never concatenate repeated_item fragments or send an unresolved logical reference as a Paper node ID.",container_marking="Native layer-name attributes identify empty flex containers. Internal data-paper-repeat markers have been removed from all payloads.",tool_arguments="Use the reviewed live write_html schema to append to the resolved native parent. This JSON does not guess upstream argument names or native IDs.",section_review="After reaching a board_group's section_complete_after fragment, request get_screenshot for the new section and inspect actual layout before proceeding.",final_measurement="After all sections are visually checked, fit the artboard height to content using the live schema. Estimated heights are planning metadata only.",mobile_first_child="Official status-bar fragment is first on every mobile board. It is framing only, never production website markup."),
        application_constraints=["OFFLINE BLUEPRINT: do not represent as applied until the intended Paper document is bound and guarded edits succeed.","Use the inspected live catalog schema and guards. These are HTML payloads with logical binding instructions, not upstream API envelopes.","Create each artboard with vertical flex layout and canonical background; follow logical_parent_ref for every write, not blanket appends to the artboard.","Repeated card, list, row, range-control and metric items are separate writes into named empty flex containers.","Content uses inline styles, editable native text/div shapes and source-backed SVG. No CSS grid, margins, JavaScript, raster screenshots, external assets or fetched fonts.","Official mobile status-bar markup is preserved except permitted light-theme color substitutions; it remains framing only.","Absolute positioning is confined to measured dealer-level markers; page and module layout use flex.","Request a screenshot after each completed section, inspect overflow and typography, and finish with artboard height fit to content.","Default Brief keeps history and sources collapsed. Scanner filters and Ticker advanced disclosure are opened on review boards deliberately.","Preserve real shared navigation, tokens, source dates and advanced functionality in implementation; this artifact is not replacement runtime code.","Do not promote stale values, coverage or a build timestamp into current-session facts, and do not interpolate missing observations."],
        review_criteria=["At 390px all five task labels are discoverable without a hidden horizontal rail, controls have at least 44px hit targets, and first index prices are reached without a giant absence hero.","Index close, floor, flip and ceiling geometry is proportional, retains exact numbers and date, and has a visible last-close/flip legend plus model-estimate text.","Source disclosure distinguishes Oct30 GEX/volatility, Oct20 index context, Aug19 brief, Aug13 Flow/Scanner and Aug12 Leaders; each module retains its source date.","Actual imported text is legible in both themes; 11px machine labels are supporting facts, body decisions remain 12.5–17px. No clipped labels, accidental overflow or low-contrast active states.","Compact unavailable Brief, source details and history disclosures remain obvious keyboard targets and do not cover useful evidence or reset task context.","Scanner advanced ranges, three views, seven presets, CSV and clear remain present; Ticker original raw panels, Leaders evidence and the four payoff rows are all inspectable.","Unavailable data, loading, timeout/retry and zero filtered matches are visually distinct; no skeleton, empty state or historical context implies current trade authority.","Inspect actual Paper screenshots and the real shared-shell browser candidate separately. No quality label, Paper approval or production-readiness claim follows from this JSON."],
        boards=boards,
    )
    result["tokens"].update(css_variables=TOKEN_VALUES, semantic_references=TOKEN_REFERENCES)
    result["source"]["design_tokens"] = dict(path=str(DESIGN_TOKENS_FILE), sha256=hashlib.sha256(DESIGN_TOKENS_FILE.read_bytes()).hexdigest(), count=len(DESIGN_TOKENS), catalog_scope="verified_subset", parent_reported_live_catalog_count=110, parent_reported_content_hash="cfd3d65c", usage="Verified 91-token subset of the live Paper catalog; every saved name/value matches. This is not the exhaustive catalog. No new tokens or palette.")
    result["source"]["brand_glyph"] = dict(path=str(BRAND_GLYPH_FILE), sha256=hashlib.sha256(BRAND_GLYPH_FILE.read_bytes()).hexdigest(), source_path="templates/_navlinks.html.j2", source_verification="Parent-supplied unchanged production SVG", usage="Inline unchanged, including immutable gradient colors and source dimensions.")
    result["source"]["template"]["rstrip_sha256"] = hashlib.sha256(template.rstrip()).hexdigest()
    result["source"]["builder"]["rstrip_sha256"] = hashlib.sha256(builder.rstrip()).hexdigest()
    result["import_contract"]["token_binding"] = "Use the existing live CSS variables named in tokens.css_variables; the verified 91-token subset supplies local preview values only and is not the exhaustive live catalog. Do not recreate or rename live tokens. Official mobile status framing and the exact production brand SVG are immutable exceptions."
    if OBSERVED:
        result["source"]["actual_samples"]=dict(path=str(ACTUAL_SAMPLES),sha256=hashlib.sha256(ACTUAL_SAMPLES.read_bytes()).hexdigest(),manifest=OBSERVED["manifest"],usage="Historical rendered sample extraction; the sample bytes and manifest are unchanged. Not re-extracted from the finalized implementation.")
        input_reads={entry["path"]:entry for entry in OBSERVED["manifest"]["reads"]}
        result["data_provenance"]["index_daily_moves"]=dict(source_pin=INDEX_DAILY_MOVE_SOURCE_PIN,source_field="expected_move.daily_pct",source_date_field="meta.asof",source_session=TARGET,verification_basis="Parent read the exact pinned published JSON on M2; no source data changed and no values inferred from the historical rendered sample text.",records=[dict(symbol=symbol,daily_pct=value,path=f"site/gex/{symbol}.json",source_file_sha256=input_reads[f"site/gex/{symbol}.json"]["sha256"]) for symbol,value in INDEX_DAILY_MOVES.items()])
        result["data_provenance"]["additional_module_sources"]=[dict(name="Flow sector ETF estimate",source_session="2026-10-19"),dict(name="Ticker intraday record",source_session="2026-10-16"),dict(name="Ticker position changes",source_session="2026-08-13"),dict(name="Ticker measured flow",source_session="2026-08-13"),dict(name="Ticker raw GEX charts, tables and Greeks",source_session=TARGET),dict(name="Leaders sector ETF context",source_session="2026-08-12")]
        result["data_provenance"]["leader_samples"].update(state="On the radar",rendered_candidates_per_board=12,source_totals=dict(recurring=368,washout=63))
    all_html=[f["html"] for b in boards for f in b["fragments"]]
    forbidden=["display:grid", "display: grid", "margin:", "margin-", "<script", "<img", "<image", "<canvas", "<style", "http://", "https://", "url(","data-paper-repeat"]
    for fragment in all_html:
        inspected = fragment.replace(BRAND_GLYPH, "")
        assert not any(token in inspected for token in forbidden), "Noneditable or disallowed HTML/CSS"
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", inspected), "Unbound palette color outside immutable brand SVG"
        assert all(name in TOKEN_VALUES for name in re.findall(r"var\((--[\w-]+)\)", inspected)), "Reference to an unknown design token"
        assert fragment.count("<div") == fragment.count("</div>"), "Unbalanced editable shapes"
    assert sum(fragment.count(BRAND_GLYPH) for fragment in all_html) == 10, "Shared navigation must retain the exact production brand glyph"
    assert len(boards)==12
    assert all(len(f["html"].encode()) < 32000 for b in boards for f in b["fragments"]), "Split oversized major group"
    for board in boards:
        registry={board["import_root_ref"]}
        for fragment in board["fragments"]:
            assert fragment["logical_parent_ref"] in registry,"Parent not registered before child"
            for binding in fragment["provides_nodes"]:
                assert binding["logical_ref"] not in registry,"Duplicate logical node reference"
                registry.add(binding["logical_ref"])
            EditableHTML(fragment["html"])
        if board["width"]==390:
            expected=status_original if board["theme"]=="dark" else status_original.replace("color: white","color: black").replace('fill="white"','fill="black"')
            assert board["fragments"][0]["html"]==expected,"Status bar changed beyond allowed colors"
    result["offline_validation"] = dict(board_count=len(boards),fragment_count=len(all_html),repeated_item_writes=sum(f["write_kind"]=="repeated_item" for b in boards for f in b["fragments"]),maximum_fragment_bytes=max(len(h.encode()) for h in all_html),no_grid_or_margin=True,no_script_remote_assets_or_raster=True,source_backed_SVG_allowed=True,balanced_editable_HTML=True,logical_parents_precede_children=True,mobile_guide_markup_exact_except_colors=True,actual_Paper_visual_review=False)
    result["offline_validation"].update(existing_token_references_only=True, canonical_brand_glyph_copies=10, brand_svg_bytes_unchanged=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result["offline_validation"]


if __name__ == "__main__":
    print(json.dumps(build(),indent=2))
