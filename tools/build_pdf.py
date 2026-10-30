#!/usr/bin/env python3
"""
Build a print-optimised PDF of the STA1610 exam-prep site.

The site is an interactive single-page app (tabbed topics, collapsible
solutions, calculators). This script re-lays the same content out for paper:

  * every topic becomes its own chapter, starting on a fresh page
  * all worked solutions are expanded (nothing to click in a PDF)
  * interactive furniture is removed (buttons, timers, search, pagers,
    sidebar) and calculators are reduced to their inputs + formula
  * LaTeX math is converted to typeset Unicode with real super/subscripts
  * tables get repeating header rows, callouts become tinted rule boxes,
    headings never end up orphaned at the bottom of a page
  * adds a cover, a navigable table of contents, PDF bookmarks,
    running headers and page numbers

Usage:
    python3 tools/build_pdf.py [source.html] [out.pdf]
"""

from __future__ import annotations

import copy
import re
import sys
import html as htmlmod
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Frame, HRFlowable, KeepTogether, ListFlowable, ListItem,
    NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table,
    TableStyle,
)
from reportlab.platypus.flowables import Flowable

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sta1610" / "index.html"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "sta1610-exam-prep.pdf"

# --------------------------------------------------------------------------
# fonts
# --------------------------------------------------------------------------
def _font_dir() -> Path:
    import matplotlib
    return Path(matplotlib.get_data_path()) / "fonts" / "ttf"


FD = _font_dir()
FONT_FILES = {
    "Body": "DejaVuSerif.ttf",
    "Body-Bold": "DejaVuSerif-Bold.ttf",
    "Body-Italic": "DejaVuSerif-Italic.ttf",
    "Body-BoldItalic": "DejaVuSerif-BoldItalic.ttf",
    "Sans": "DejaVuSans.ttf",
    "Sans-Bold": "DejaVuSans-Bold.ttf",
    "Sans-Italic": "DejaVuSans-Oblique.ttf",
    "Sans-BoldItalic": "DejaVuSans-BoldOblique.ttf",
    "Mono": "DejaVuSansMono.ttf",
    "Mono-Bold": "DejaVuSansMono-Bold.ttf",
}
for name, filename in FONT_FILES.items():
    pdfmetrics.registerFont(TTFont(name, str(FD / filename)))
registerFontFamily("Body", normal="Body", bold="Body-Bold",
                   italic="Body-Italic", boldItalic="Body-BoldItalic")
registerFontFamily("Sans", normal="Sans", bold="Sans-Bold",
                   italic="Sans-Italic", boldItalic="Sans-BoldItalic")
registerFontFamily("Mono", normal="Mono", bold="Mono-Bold",
                   italic="Mono", boldItalic="Mono-Bold")

# --------------------------------------------------------------------------
# palette (chosen to stay legible on mono printers)
# --------------------------------------------------------------------------
INK = colors.HexColor("#1b1f27")
MUTED = colors.HexColor("#5c6675")
RULE = colors.HexColor("#d9dee7")
ACCENT = colors.HexColor("#2743a8")
TEAL = colors.HexColor("#0b6f68")
GREEN = colors.HexColor("#146b47")
AMBER = colors.HexColor("#8a5a00")
RED = colors.HexColor("#a33232")
PURPLE = colors.HexColor("#54409f")
BAND = colors.HexColor("#f5f7fb")
BAND_GREEN = colors.HexColor("#f1f8f4")
BAND_AMBER = colors.HexColor("#fdf8ec")
BAND_RED = colors.HexColor("#fdf3f3")
BAND_BLUE = colors.HexColor("#f1f4fc")
BAND_TEAL = colors.HexColor("#eff8f6")

PAGE_W, PAGE_H = A4
LM, RM, TM, BM = 17 * mm, 17 * mm, 20 * mm, 18 * mm

# --------------------------------------------------------------------------
# LaTeX -> typeset Unicode (reportlab paragraph markup)
# --------------------------------------------------------------------------
SYMBOLS = {
    "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠",
    "approx": "≈", "equiv": "≡", "sim": "∼", "propto": "∝",
    "pm": "±", "mp": "∓", "times": "×", "cdot": "·", "div": "÷",
    "infty": "∞", "partial": "∂", "nabla": "∇", "degree": "°",
    "to": "→", "rightarrow": "→", "leftarrow": "←", "Rightarrow": "⇒",
    "Leftrightarrow": "⇔", "mapsto": "↦", "uparrow": "↑", "downarrow": "↓",
    "in": "∈", "notin": "∉", "subset": "⊂", "subseteq": "⊆", "cup": "∪",
    "cap": "∩", "emptyset": "∅", "forall": "∀", "exists": "∃",
    "sum": "Σ", "prod": "∏", "int": "∫", "sqrtsign": "√",
    "ldots": "…", "dots": "…", "cdots": "⋯", "vdots": "⋮",
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι",
    "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π",
    "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ",
    "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ",
    "Pi": "Π", "Sigma": "Σ", "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ",
    "Omega": "Ω", "ell": "ℓ", "hbar": "ℏ",
    "quad": " ", "qquad": " ", "enspace": " ", "thinspace": " ",
    "left": "", "right": "", "big": "", "Big": "", "bigg": "",
    "displaystyle": "", "textstyle": "", "limits": "", "nolimits": "",
    "{": "{", "}": "}", "%": "%", "$": "$", "&": "&", "#": "#", "_": "_",
    "|": "|", "mid": "|", "vert": "|", "Vert": "‖", "backslash": "\\",
    "prime": "′", "circ": "∘", "bullet": "•", "because": "∵", "therefore": "∴",
    "angle": "∠", "cong": "≅", "star": "⋆", "ast": "∗", "oplus": "⊕",
    "otimes": "⊗", "perp": "⊥", "parallel": "∥", "simeq": "≃", "asymp": "≍",
}
COMBINING = {"bar": "\u0304", "hat": "\u0302", "tilde": "\u0303", "vec": "\u20d7",
             "dot": "\u0307", "ddot": "\u0308"}
SPACING_CMDS = {"quad", "qquad", "enspace", "thinspace", ",", ";", ":", "!", " "}


def _esc_math(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _read_group(s: str, i: int):
    """Return (content, next_index) for a {...} group or a single token."""
    while i < len(s) and s[i] in " \t\n":
        i += 1
    if i >= len(s):
        return "", i
    if s[i] == "{":
        depth, j = 1, i + 1
        while j < len(s) and depth:
            if s[j] == "{":
                depth += 1
            elif s[j] == "}":
                depth -= 1
            j += 1
        return s[i + 1:j - 1], j
    if s[i] == "\\":
        m = re.match(r"\\([A-Za-z]+|.)", s[i:])
        return m.group(0) if m else s[i], i + (len(m.group(0)) if m else 1)
    return s[i], i + 1


def _needs_parens(content: str) -> bool:
    return bool(re.search(r"[+\-−±×/·]|\s\|\s", content)) and not (
        content.startswith("(") and content.endswith(")"))


def tex_to_markup(raw: str) -> str:
    """Convert a LaTeX snippet into reportlab paragraph markup."""
    s = _esc_math(raw)
    out, _ = _parse_tex(s, 0)
    return re.sub(r"\s+", " ", out).strip()


def _parse_tex(s: str, i: int, stop_at_brace: bool = False):
    parts = []
    while i < len(s):
        ch = s[i]
        if ch == "}":
            if stop_at_brace:
                return "".join(parts), i
            i += 1
            continue
        if ch == "{":
            content, i = _read_group(s, i)
            parts.append(_parse_tex(content, 0)[0])
            continue
        if ch == "\\":
            m = re.match(r"\\([A-Za-z]+|.)", s[i:])
            if not m:
                i += 1
                continue
            name = m.group(1)
            i += len(m.group(0))
            if name == "\\":  # line break
                parts.append("<br/>")
                continue
            if name in ("frac", "dfrac", "tfrac"):
                num, i = _read_group(s, i)
                den, i = _read_group(s, i)
                num_s = _parse_tex(num, 0)[0].strip()
                den_s = _parse_tex(den, 0)[0].strip()
                if _needs_parens(num_s):
                    num_s = f"({num_s})"
                if _needs_parens(den_s):
                    den_s = f"({den_s})"
                parts.append(f"{num_s} / {den_s}")
                continue
            if name in ("binom", "dbinom", "tbinom"):
                top, i = _read_group(s, i)
                bottom, i = _read_group(s, i)
                parts.append("C(%s, %s)" % (_parse_tex(top, 0)[0].strip(),
                                            _parse_tex(bottom, 0)[0].strip()))
                continue
            if name == "sqrt":
                arg, i = _read_group(s, i)
                inner = _parse_tex(arg, 0)[0].strip()
                parts.append(f"√({inner})")
                continue
            if name in ("text", "mathrm", "textrm", "operatorname", "mbox", "textnormal"):
                arg, i = _read_group(s, i)
                parts.append(arg)
                continue
            if name in ("mathbf", "textbf", "bm"):
                arg, i = _read_group(s, i)
                parts.append(f"<b>{_parse_tex(arg, 0)[0]}</b>")
                continue
            if name in ("mathit", "textit"):
                arg, i = _read_group(s, i)
                parts.append(f"<i>{_parse_tex(arg, 0)[0]}</i>")
                continue
            if name in COMBINING:
                arg, i = _read_group(s, i)
                base = _parse_tex(arg, 0)[0].strip()
                parts.append(base + COMBINING[name])
                continue
            if name in ("overline", "underline"):
                arg, i = _read_group(s, i)
                parts.append(_parse_tex(arg, 0)[0])
                continue
            if name in SYMBOLS:
                parts.append(SYMBOLS[name])
                continue
            if name in SPACING_CMDS:
                parts.append(" ")
                continue
            # unknown command: keep the bare name, it is usually readable
            parts.append(name)
            continue
        if ch in "^_":
            arg, i = _read_group(s, i + 1)
            inner = _parse_tex(arg, 0)[0].strip()
            tag = "super" if ch == "^" else "sub"
            parts.append(f"<{tag}>{inner}</{tag}>")
            continue
        if ch == "&":
            i += 1
            continue
        parts.append(ch)
        i += 1
    return "".join(parts), i


MATH_PATTERNS = [
    (re.compile(r"\\\[(.+?)\\\]", re.S), "display"),
    (re.compile(r"\\\((.+?)\\\)", re.S), "inline"),
    (re.compile(r"\$\$(.+?)\$\$", re.S), "display"),
    (re.compile(r"(?<!\$)\$([^$\n]+?)\$(?!\$)"), "inline"),
]


def inline_math_to_markup(text: str) -> str:
    """Replace LaTeX delimiters inside a plain-text run with typeset markup."""
    if "\\(" not in text and "\\[" not in text and "$" not in text:
        return xml_escape(text)

    tokens = []
    # split on the first matching pattern repeatedly
    remaining = text
    while remaining:
        best = None
        for pattern, kind in MATH_PATTERNS:
            m = pattern.search(remaining)
            if m and (best is None or m.start() < best[0].start()):
                best = (m, kind)
        if not best:
            tokens.append(("text", remaining))
            break
        m, kind = best
        if m.start():
            tokens.append(("text", remaining[:m.start()]))
        tokens.append(("math", m.group(1), kind))
        remaining = remaining[m.end():]

    out = []
    for token in tokens:
        if token[0] == "text":
            out.append(xml_escape(token[1]))
        else:
            body = tex_to_markup(token[1])
            out.append(f'<font color="#1b1f27">{body}</font>' if token[2] == "display" else body)
    return "".join(out)


# --------------------------------------------------------------------------
# tiny DOM
# --------------------------------------------------------------------------
@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    @property
    def classes(self) -> set:
        return set((self.attrs.get("class") or "").split())

    def text(self) -> str:
        bits = []
        for child in self.children:
            bits.append(child if isinstance(child, str) else child.text())
        return "".join(bits)

    def find_all(self, tag=None, cls=None):
        found = []
        for child in self.children:
            if isinstance(child, str):
                continue
            if (tag is None or child.tag == tag) and (cls is None or cls in child.classes):
                found.append(child)
            found.extend(child.find_all(tag, cls))
        return found

    def find(self, tag=None, cls=None):
        hits = self.find_all(tag, cls)
        return hits[0] if hits else None

    def first_text_of(self, tag=None, cls=None) -> str:
        node = self.find(tag, cls)
        return node.text().strip() if node else ""


VOID_TAGS = {"br", "hr", "img", "input", "meta", "link", "source", "track", "wbr", "area", "base", "col", "embed", "param"}


class DomBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, dict(attrs)))

    def handle_endtag(self, tag):
        for depth in range(len(self.stack) - 1, 0, -1):
            if self.stack[depth].tag == tag:
                del self.stack[depth:]
                return

    def handle_data(self, data):
        if data:
            self.stack[-1].children.append(data)


def parse_html(text: str) -> Node:
    builder = DomBuilder()
    builder.feed(text)
    builder.close()
    return builder.root


# --------------------------------------------------------------------------
# styles
# --------------------------------------------------------------------------
def style(name, **kw):
    base = dict(fontName="Body", fontSize=9.9, leading=14.5, textColor=INK,
                spaceBefore=0, spaceAfter=5.2, alignment=TA_LEFT,
                allowWidows=0, allowOrphans=0)
    base.update(kw)
    return ParagraphStyle(name, **base)


S = {
    "cover_kicker": style("cover_kicker", fontName="Sans-Bold", fontSize=9,
                          leading=12, textColor=TEAL, spaceAfter=10),
    "cover_title": style("cover_title", fontName="Sans-Bold", fontSize=34,
                         leading=40, textColor=INK, spaceAfter=10),
    "cover_sub": style("cover_sub", fontName="Body-Italic", fontSize=13,
                       leading=19, textColor=MUTED, spaceAfter=18),
    "cover_meta": style("cover_meta", fontName="Sans", fontSize=9,
                        leading=15, textColor=MUTED),
    "chapter_num": style("chapter_num", fontName="Sans-Bold", fontSize=8.4,
                         leading=11, textColor=TEAL, spaceAfter=3),
    "h1": style("h1", fontName="Sans-Bold", fontSize=20, leading=25,
                textColor=INK, spaceBefore=0, spaceAfter=4, keepWithNext=1),
    "chapter_sub": style("chapter_sub", fontName="Body-Italic", fontSize=10.6,
                         leading=15, textColor=MUTED, spaceAfter=10),
    "h2": style("h2", fontName="Sans-Bold", fontSize=12.4, leading=16,
                textColor=ACCENT, spaceBefore=13, spaceAfter=5, keepWithNext=1),
    "h3": style("h3", fontName="Sans-Bold", fontSize=10.2, leading=13.4,
                textColor=TEAL, spaceBefore=9.5, spaceAfter=3, keepWithNext=1),
    "body": style("body"),
    "body_first": style("body_first", spaceBefore=2),
    "sub": style("sub", fontName="Body-Italic", textColor=MUTED),
    "small": style("small", fontSize=8.5, leading=12.2, textColor=MUTED),
    "mono": style("mono", fontName="Mono", fontSize=8.0, leading=11.6),
    "bullet": style("bullet", fontSize=9.5, leading=13.4, spaceAfter=2.4),
    "box": style("box", fontSize=9.3, leading=13.4, spaceAfter=0),
    "box_tight": style("box_tight", fontSize=9.1, leading=13.1, spaceAfter=0),
    "box_head": style("box_head", fontName="Sans-Bold", fontSize=9.0, leading=12.4,
                      spaceAfter=2.4),
    "result": style("result", fontSize=9.4, leading=13.6, textColor=TEAL, spaceAfter=0),
    "answer": style("answer", fontSize=9.4, leading=13.6, textColor=GREEN, spaceAfter=0),
    "th": style("th", fontName="Sans-Bold", fontSize=8.2, leading=11, textColor=colors.white,
                spaceAfter=0),
    "td": style("td", fontSize=8.4, leading=11.8, spaceAfter=0),
    "td_bold": style("td_bold", fontName="Body-Bold", fontSize=8.4, leading=11.8, spaceAfter=0),
    "kicker": style("kicker", fontName="Sans-Bold", fontSize=7.4, leading=10,
                    textColor=TEAL, spaceAfter=2),
    "ref": style("ref", fontName="Mono", fontSize=7.6, leading=10.8, textColor=TEAL, spaceAfter=2),
    "question": style("question", fontSize=9.4, leading=13.6, spaceAfter=0),
    "label": style("label", fontName="Sans-Bold", fontSize=7.6, leading=10.4,
                   textColor=MUTED, spaceAfter=2),
    "step": style("step", fontName="Sans-Bold", fontSize=9.2, leading=12.6,
                  textColor=INK, spaceAfter=1.6),
    "ss": style("ss", fontSize=9.1, leading=13.2, spaceAfter=0),
    "toc_h": style("toc_h", fontName="Sans-Bold", fontSize=19, leading=24,
                   textColor=INK, spaceAfter=12),
    "toc0": style("toc0", fontName="Sans-Bold", fontSize=10.2, leading=17,
                  textColor=INK, spaceBefore=5),
    "toc1": style("toc1", fontName="Body", fontSize=9.0, leading=13.4,
                  textColor=MUTED, leftIndent=12),
}


# --------------------------------------------------------------------------
# flowable helpers
# --------------------------------------------------------------------------
CONTENT_W = PAGE_W - LM - RM


def rule(color=RULE, width=0.6, space_before=2, space_after=4):
    return HRFlowable(width="100%", thickness=width, color=color,
                      spaceBefore=space_before, spaceAfter=space_after, lineCap="butt")


def _as_flows(flowables):
    if isinstance(flowables, (list, tuple)):
        return [f for f in flowables if f is not None]
    return [flowables]


def boxed(flowables, border_color, background=BAND, pad=(7, 9, 7, 9)):
    """Tinted box with a thick left rule.

    Each inner flowable gets its own table row so the box splits across pages
    instead of overflowing when a callout is longer than one page.
    """
    flows = _as_flows(flowables)
    if not flows:
        return Spacer(1, 0)
    t = Table([[f] for f in flows], colWidths=[CONTENT_W], splitByRow=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("LINEBEFORE", (0, 0), (0, -1), 2.6, border_color),
        ("LEFTPADDING", (0, 0), (-1, -1), pad[0]),
        ("RIGHTPADDING", (0, 0), (-1, -1), pad[1]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
        ("TOPPADDING", (0, 0), (-1, 0), pad[2]),
        ("BOTTOMPADDING", (0, -1), (-1, -1), pad[3]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def framed(flowables, border_color=RULE, background=colors.white, pad=(10, 11, 9, 11)):
    """Bordered card that also splits by row across pages."""
    flows = _as_flows(flowables)
    if not flows:
        return Spacer(1, 0)
    t = Table([[f] for f in flows], colWidths=[CONTENT_W], splitByRow=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), 0.7, border_color),
        ("LEFTPADDING", (0, 0), (-1, -1), pad[0]),
        ("RIGHTPADDING", (0, 0), (-1, -1), pad[1]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4),
        ("TOPPADDING", (0, 0), (-1, 0), pad[2]),
        ("BOTTOMPADDING", (0, -1), (-1, -1), pad[3]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def data_table(rows, header=True, col_widths=None, first_col_bold=False):
    """Grid-light table with a shaded, repeating header row."""
    if not rows:
        return Spacer(1, 0)
    cols = max(len(r) for r in rows)
    rows = [r + [""] * (cols - len(r)) for r in rows]
    if col_widths is None:
        col_widths = [CONTENT_W / cols] * cols
    data = []
    for r_idx, row in enumerate(rows):
        cells = []
        for c_idx, cell in enumerate(row):
            if isinstance(cell, str):
                if header and r_idx == 0:
                    cells.append(Paragraph(inline_math_to_markup(cell), S["th"]))
                elif first_col_bold and c_idx == 0:
                    cells.append(Paragraph(inline_math_to_markup(cell), S["td_bold"]))
                else:
                    cells.append(Paragraph(inline_math_to_markup(cell), S["td"]))
            else:
                cells.append(cell)
        data.append(cells)
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0, hAlign="LEFT")
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
        ("LINEBELOW", (0, -1), (-1, -1), 0.7, RULE),
    ]
    if header:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("LINEBELOW", (0, 0), (-1, 0), 0.7, ACCENT),
        ]
        for c in range(cols):
            cmds.append(("BACKGROUND", (c, 1), (c, -1), colors.white if c % 2 == 0 else BAND))
    t.setStyle(TableStyle(cmds))
    return t


# --------------------------------------------------------------------------
# renderer: DOM -> flowables
# --------------------------------------------------------------------------
SKIP_CLASSES = {
    "topbar", "sidebar", "toc", "toast", "sheet", "backdrop", "page-pager",
    "exam-toolbar", "exam-search-empty", "resume-card", "nav-search",
    "nav-group", "nav-feature", "nav-label", "brand", "progress-wrap",
    "calendar", "skip-link", "to-top", "readbar", "ring-wrap",
}
SKIP_TAGS = {"script", "style", "nav", "button", "input", "select", "textarea",
             "svg", "form", "iframe", "noscript"}


TAG_RE = re.compile(r"<(/?)(b|i|u|link|font|super|sub)([^>]*)>")


def balance_tags(markup: str) -> str:
    """Close any inline tag left open (flattening can drop a </b>)."""
    stack = []
    for match in TAG_RE.finditer(markup):
        closing, name = match.group(1), match.group(2)
        if not closing:
            if name == "link" or match.group(3).strip().endswith("/"):
                if name == "link":
                    stack.append(name)
                continue
            stack.append(name)
        else:
            if name in stack:
                while stack and stack[-1] != name:
                    stack.pop()
                if stack:
                    stack.pop()
    tail = "".join("</%s>" % name for name in reversed(stack))
    return markup + tail


class Renderer:
    def __init__(self):
        self.story = []
        self.headings = []   # [(level, text)] in document order

    # ---------------------------------------------------------------- inline
    def inline(self, node) -> str:
        parts = []
        for child in node.children:
            if isinstance(child, str):
                parts.append(inline_math_to_markup(child))
                continue
            tag, cls = child.tag, child.classes
            if tag in ("script", "style", "button", "svg", "input", "select"):
                continue
            inner = self.inline(child)
            if tag == "br":
                parts.append("<br/>")
            elif tag in ("strong", "b"):
                parts.append(f"<b>{inner}</b>")
            elif tag in ("em", "i", "cite", "dfn"):
                parts.append(f"<i>{inner}</i>")
            elif tag in ("sup",):
                parts.append(f"<super>{inner}</super>")
            elif tag in ("sub",):
                parts.append(f"<sub>{inner}</sub>")
            elif tag == "code" or "mono" in cls:
                parts.append(f'<font face="Mono" size="8.2" color="#3b4250">{inner}</font>')
            elif tag == "kbd":
                parts.append(f'<font face="Sans" size="8" color="#5c6675">{inner}</font>')
            elif tag == "a":
                href = child.attrs.get("href") or ""
                if href.startswith("#") or not href:
                    parts.append(inner)
                else:
                    parts.append(f'<link href="{xml_escape(href)}" color="#2743a8">{inner}</link>')
            elif "exam-answer" in cls:
                parts.append(inner)
            elif "num" in cls or "nav-dot" in cls:
                continue
            else:
                parts.append(inner)
        return "".join(parts)

    def block_markup(self, node) -> str:
        """Flatten a container's mixed inline/block content into one run.

        Callouts put <strong> runs next to text; rendering each child as its own
        paragraph broke sentences apart, so they are joined here instead.
        """
        bits = []
        for child in node.children:
            if isinstance(child, str):
                bits.append(inline_math_to_markup(child))
                continue
            if child.tag in ("script", "style", "button", "svg", "table"):
                continue
            if child.tag in ("br", "hr"):
                bits.append("<br/>")
                continue
            is_block = child.tag in ("p", "div", "li") or child.classes & {"ss", "step"}
            markup = self.inline(child)
            if is_block:
                bits.append("<br/>" + markup + "<br/>")
            else:
                bits.append(markup)
        text = "".join(bits)
        text = re.sub(r"(\s|&nbsp;)+", " ", text)
        text = re.sub(r"(<br/>\s*){3,}", "<br/><br/>", text)
        text = re.sub(r"^(\s*<br/>)+|(<br/>\s*)+$", "", text)
        return balance_tags(text.strip())

    def paragraph(self, node, style_name="body") -> Paragraph | None:
        markup = self.inline(node).strip()
        markup = re.sub(r"(\s|&nbsp;)+", " ", markup).strip()
        markup = re.sub(r"<br/>\s*<br/>", "<br/>", markup)
        if not markup or markup in {"&nbsp;", " "}:
            return None
        return Paragraph(markup, S[style_name])

    # ---------------------------------------------------------------- blocks
    def render_children(self, node, out=None):
        target = self.story if out is None else out
        for child in node.children:
            if isinstance(child, str):
                continue
            self.render_node(child, target)
        return target

    def render_node(self, node, out):
        tag, cls = node.tag, node.classes
        if tag in SKIP_TAGS or (cls & SKIP_CLASSES):
            return
        if tag in ("h1",):
            out.append(self.chapter_title(node))
        elif tag == "h2":
            text = self.plain(node)
            if text:
                out.append(Paragraph(inline_math_to_markup(text), S["h2"]))
                out.append(rule(ACCENT, 0.9, 0, 6))
                self.register_toc(text, 1)
        elif tag == "h3":
            text = self.plain(node)
            if text:
                out.append(Paragraph(inline_math_to_markup(text), S["h3"]))
        elif tag == "p":
            para = self.paragraph(node, self.para_style(node))
            if para:
                out.append(para)
        elif tag == "hr":
            out.append(rule())
        elif tag in ("ul", "ol"):
            lst = self.make_list(node)
            if lst:
                out.append(lst)
        elif tag == "table":
            out.append(self.make_table(node))
        elif tag == "details":
            out.extend(self.make_details(node))
        elif tag == "article":
            out.extend(self.make_exam_card(node))
        elif tag == "header":
            out.extend(self.make_hero(node))
        elif tag == "div":
            out.extend(self.make_div(node))
        elif tag == "blockquote":
            out.append(boxed([p for p in [self.paragraph(node)] if p], PURPLE))
        elif tag in ("figure", "section", "main", "article", "span", "li", "dl", "dt", "dd"):
            self.render_children(node, out)
        else:
            para = self.paragraph(node)
            if para:
                out.append(para)

    def para_style(self, node) -> str:
        cls = node.classes
        if "sub" in cls:
            return "sub"
        if "exam-q" in cls:
            return "question"
        if "exam-ref" in cls:
            return "ref"
        if "exam-also" in cls or "exam-note" in cls or "exam-small-tip" in cls:
            return "small"
        return "body"

    def plain(self, node) -> str:
        return re.sub(r"\s+", " ", node.text()).strip()

    def register_toc(self, text, level):
        clean = re.sub(r"\s+", " ", text).strip()
        self.headings.append((level, clean))
        self.story.append(_TOCHook(level, clean))

    # ---------------------------------------------------------------- pieces
    def chapter_title(self, node) -> Paragraph:
        text = self.plain(node)
        self.register_toc(text, 0)
        return Paragraph(inline_math_to_markup(text), S["h1"])

    def make_hero(self, node):
        flow = []
        # build() already prints the chapter kicker, so the hero only repeats
        # the in-page kicker when it carries real information (exam mode)
        kicker = node.find(cls="exam-kicker")
        if getattr(self, "suppress_kicker", True):
            kicker = None
        title = node.find("h1")
        sub = node.find("p", "sub") or node.find("p")
        if kicker:
            flow.append(Paragraph(self.plain(kicker).upper(), S["kicker"]))
        if title:
            text = self.plain(title)
            self.register_toc(text, 0)
            flow.append(Paragraph(inline_math_to_markup(text), S["h1"]))
        if sub and sub is not title:
            para = self.paragraph(sub, "chapter_sub")
            if para:
                flow.append(para)
        flow.append(rule())
        return flow

    def make_list(self, node) -> ListFlowable | None:
        items = []
        for child in node.children:
            if isinstance(child, str) or child.tag != "li":
                continue
            nested = [c for c in child.children
                      if not isinstance(c, str) and c.tag in ("ul", "ol")]
            inline_node = Node("span", {}, [c for c in child.children
                                            if isinstance(c, str) or c not in nested])
            markup = self.paragraph(inline_node, "bullet")
            if not markup:
                continue
            sub_flows = []
            for sub in nested:
                sub_list = self.make_list(sub)
                if sub_list:
                    sub_flows.append(sub_list)
            items.append(ListItem([markup] + sub_flows, leftIndent=12,
                                  value=None, bulletColor=INK))
        if not items:
            return None
        ordered = node.tag == "ol"
        return ListFlowable(
            items,
            bulletType="1" if ordered else "bullet",
            bulletFontName="Body" if ordered else "Sans-Bold",
            bulletFontSize=8.6,
            bulletColor=ACCENT if ordered else TEAL,
            leftIndent=15,
            bulletOffsetY=0.5,
            spaceAfter=6,
        )

    def make_table(self, node) -> Table:
        rows = []
        first_col_bold = "data-table" in node.classes
        for tr in node.find_all("tr"):
            cells = [td for td in tr.children if not isinstance(td, str) and td.tag in ("td", "th")]
            if not cells:
                continue
            row = []
            for cell in cells:
                row.append(self.cell_text(cell))
            rows.append(row)
        ncols = max((len(r) for r in rows), default=1)
        if ncols == 2 and first_col_bold:
            widths = [CONTENT_W * 0.36, CONTENT_W * 0.64]
        elif ncols == 3:
            widths = [CONTENT_W * 0.20, CONTENT_W * 0.45, CONTENT_W * 0.35]
        else:
            widths = [CONTENT_W / ncols] * ncols
        tbl = data_table(rows, header=True, col_widths=widths,
                         first_col_bold=first_col_bold)
        if len(rows) <= 9 and node.find_all("tr"):
            return KeepTogether([tbl])
        return tbl

    def cell_text(self, cell) -> str:
        bits = []
        for child in cell.children:
            if isinstance(child, str):
                bits.append(child)
            elif child.tag == "br":
                bits.append(" ")
            else:
                bits.append(child.text())
        return re.sub(r"\s+", " ", "".join(bits)).strip()

    def make_details(self, node):
        flow = []
        simple = "example" in node.classes
        summary = node.find("summary")
        head = self.plain(summary) if summary else "Show more"
        if not simple and head:
            flow.append(Paragraph(head.upper(), S["label"]))
        for child in node.children:
            if isinstance(child, str) or child.tag == "summary":
                continue
            self.render_node(child, flow)
        for i, f in enumerate(flow):
            if isinstance(f, _TOCHook):
                flow[i] = Spacer(1, 0)
        return flow

    def make_exam_card(self, node):
        flow = []
        num = node.find("span", "exam-num")
        title = node.find("h3")
        badge = node.find("span", "exam-source-badge")
        head_bits = []
        if num:
            head_bits.append(f'<font face="Sans-Bold" size="8" color="#0b6f68">{self.plain(num)}</font>')
        if title:
            head_bits.append(f'<b>{self.inline(title)}</b>')
        if badge:
            colour = "#8a5a00" if "gap" in badge.classes else "#146b47"
            head_bits.append(f' <font face="Sans-Bold" size="7" color="{colour}">[{self.plain(badge).upper()}]</font>')
        if head_bits:
            flow.append(Paragraph("&nbsp;&nbsp;".join(head_bits), S["box_head"]))

        ref = node.find("div", "exam-ref")
        if ref:
            bits = []
            href = None
            for child in ref.children:
                if isinstance(child, str):
                    bits.append(child)
                elif child.tag == "a":
                    href = child.attrs.get("href") or href
            ref_text = re.sub(r"\s+", " ", "".join(bits)).strip(" ·|")
            if ref_text:
                markup = xml_escape(ref_text)
                if href:
                    markup += '  <link href="%s" color="#0b6f68"><font size="7">↗ source</font></link>' % xml_escape(href)
                flow.append(Paragraph(markup, S["ref"]))

        question = node.find("p", "exam-question")
        if question:
            para = self.paragraph(question, "question")
            if para:
                flow.append(boxed([para], ACCENT, BAND_BLUE, (7, 8, 6, 8)))

        for extra in node.children:
            if isinstance(extra, str) or extra.tag != "p" or extra is question:
                continue
            if extra.classes & {"exam-also", "exam-note", "exam-small-tip"}:
                para = self.paragraph(extra, "small")
                if para:
                    flow.append(Spacer(1, 3))
                    flow.append(para)

        solution = node.find("details")
        if solution:
            flow.append(Spacer(1, 5))
            flow.append(Paragraph("WORKED SOLUTION", S["label"]))
            for child in solution.children:
                if isinstance(child, str) or child.tag == "summary":
                    continue
                if child.classes & {"exam-answer"}:
                    para = self.paragraph(child, "answer")
                    if para:
                        flow.append(boxed([para], GREEN, BAND_GREEN, (8, 9, 6, 8)))
                    continue
                if child.classes & {"exam-small-tip"}:
                    para = self.paragraph(child, "small")
                    if para:
                        flow.append(Spacer(1, 3))
                        flow.append(para)
                    continue
                if child.tag == "p":
                    para = self.paragraph(child, "box_tight")
                    if para:
                        flow.append(para)
                    continue
                self.render_node(child, flow)
        return flow

    def make_div(self, node):
        cls = node.classes
        out = []
        if cls & {"law", "insight", "warn", "exam-tip"}:
            kind = next(iter(cls & {"law", "insight", "warn", "exam-tip"}))
            colour, band = {
                "law": (GREEN, BAND_GREEN),
                "insight": (PURPLE, BAND),
                "warn": (RED, BAND_RED),
                "exam-tip": (AMBER, BAND_AMBER),
            }[kind]
            markup = self.block_markup(node)
            if markup:
                out.append(Spacer(1, 2))
                out.append(boxed([Paragraph(markup, S["box"])], colour, band))
                out.append(Spacer(1, 5))
            return out

        if "result" in cls:
            if node.find("table"):
                out.append(self.make_table(node))
                return out
            markup = self.block_markup(node)
            if markup:
                out.append(Spacer(1, 2))
                out.append(boxed([Paragraph(markup, S["result"])], TEAL, BAND_TEAL))
                out.append(Spacer(1, 5))
            return out

        if "example" in cls:
            return [self.make_example(node)]

        if "step" in cls:
            steps = []
            for child in node.children:
                if isinstance(child, str):
                    continue
                if child.tag == "p":
                    para = self.paragraph(child, "step")
                    if para:
                        steps.append(para)
                elif "ss" in child.classes:
                    para = self.paragraph(child, "ss")
                    if para:
                        steps.append(boxed([para], RULE, BAND, (8, 9, 5, 6)))
                else:
                    self.render_node(child, steps)
            if steps:
                out.append(KeepTogether(steps))
                out.append(Spacer(1, 4))
            return out

        if "ss" in cls:
            para = self.paragraph(node, "ss")
            if para:
                out.append(boxed([para], RULE, BAND, (8, 9, 5, 6)))
            return out

        if "exam-hero" in cls:
            return self.make_hero(node)

        if "exam-stat-grid" in cls:
            rows = []
            for stat in node.find_all("div", "exam-stat"):
                value = stat.find("strong")
                text = stat.find("span")
                rows.append([
                    Paragraph(
                        f'<font face="Sans-Bold" size="16" color="#2743a8">'
                        f'{xml_escape(self.plain(value)) if value else ""}</font>',
                        S["box"]),
                    Paragraph(inline_math_to_markup(self.plain(text)) if text else "",
                              S["small"]),
                ])
            if rows:
                t = Table(rows, colWidths=[CONTENT_W * 0.12, CONTENT_W * 0.88],
                          hAlign="LEFT", splitByRow=1)
                t.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
                ]))
                out.append(Spacer(1, 2))
                out.append(t)
                out.append(Spacer(1, 6))
            return out

        if "paper-grid" in cls:
            for card in node.find_all("article", "paper-card"):
                inner = []
                title = card.find("h3")
                if title:
                    inner.append(Paragraph(f"<b>{self.inline(title)}</b>", S["box_head"]))
                for p in card.find_all("p"):
                    strong = p.find("strong")
                    if strong and self.plain(p).startswith(self.plain(strong)):
                        inner.append(Paragraph(f"<b>{self.inline(p)}</b>", S["box_tight"]))
                    else:
                        inner.append(Paragraph(self.inline(p), S["box_tight"]))
                for link in card.find_all("a"):
                    href = link.attrs.get("href", "")
                    inner.append(Paragraph(
                        f'<link href="{xml_escape(href)}" color="#2743a8">{xml_escape(href)}</link>',
                        S["mono"]))
                out.append(framed(inner, RULE, BAND, (9, 10, 7, 9)))
                out.append(Spacer(1, 6))
            return out

        if "exam-timer" in cls:
            out.append(boxed([Paragraph(
                "Two-hour practice timer — available in the interactive version of this guide "
                "(it cannot run on paper: use a clock and the 25-question structure above).",
                S["box"])], AMBER, BAND_AMBER))
            out.append(Spacer(1, 6))
            return out

        if "calc-box" in cls:
            bits = []
            for label in node.find_all("label"):
                text = re.sub(r"\s+", " ", label.text()).strip()
                name, _, meaning = text.partition(":")
                name = name.strip()
                meaning = meaning.strip()
                if not name:
                    continue
                bits.append(f"<b>{xml_escape(name)}</b>" + (f" ({xml_escape(meaning)})" if meaning else ""))
            if bits:
                out.append(Paragraph("Inputs: " + ", ".join(bits) + ".", S["small"]))
            return out

        if "topic-header" in cls:
            return self.make_hero(node)

        if "exam-hero" in cls:
            return self.make_hero(node)

        # transparent containers
        self.render_children(node, out)
        return out

    def make_example(self, node) -> KeepTogether | Table:
        inner = []
        head = node.find("div", "ex-head")
        if head:
            badge = head.find("span", "ex-badge")
            bits = []
            if badge:
                colour = "#8a5a00" if "exam" in badge.classes else "#0b6f68"
                bits.append(f'<font face="Sans-Bold" size="7" color="{colour}">[{self.plain(badge).upper()}]</font>')
            rest = [c for c in head.children if isinstance(c, str) or c is not badge]
            label = re.sub(r"\s+", " ", "".join(c if isinstance(c, str) else c.text() for c in rest)).strip()
            if label:
                bits.append(f"<b>{xml_escape(label)}</b>")
            if bits:
                inner.append(Paragraph(" ".join(bits), S["box_head"]))
        for child in node.children:
            if isinstance(child, str):
                continue
            if "ex-head" in child.classes:
                continue
            if "ex-q" in child.classes:
                para = self.paragraph(child, "question")
                if para:
                    inner.append(Paragraph("<i>%s</i>" % self.inline(child), S["question"]))
                continue
            if "step" in child.classes:
                for grand in child.children:
                    if isinstance(grand, str):
                        continue
                    if grand.tag == "p":
                        para = self.paragraph(grand, "step")
                        if para:
                            inner.append(para)
                    elif "ss" in grand.classes:
                        para = self.paragraph(grand, "ss")
                        if para:
                            inner.append(boxed([para], RULE, colors.white, (8, 8, 4, 5)))
                    else:
                        self.render_node(grand, inner)
                inner.append(Spacer(1, 3))
                continue
            if "result" in child.classes:
                para = self.paragraph(child, "answer")
                if para:
                    inner.append(boxed([para], TEAL, BAND_TEAL, (8, 8, 4, 5)))
                continue
            if child.tag == "p":
                para = self.paragraph(child, "box_tight")
                if para:
                    inner.append(para)
                continue
            self.render_node(child, inner)
        return framed(inner, RULE, BAND, (10, 11, 8, 10))


class TOCLine(Flowable):
    """One TOC row: label, dot leaders, right-aligned page number.

    A plain flowable of fixed height, so the contents paginate like normal
    content and page numbers can be computed in a pre-pass.
    """

    HEIGHT = {0: 16.4, 1: 12.5}
    STYLE = {0: ("Sans-Bold", 9.9, INK), 1: ("Body", 8.8, MUTED)}

    def __init__(self, level, text, page):
        super().__init__()
        self.level = min(level, 1)
        self.text = text
        self.page = page
        self.width = CONTENT_W

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        return (availWidth, self.HEIGHT[self.level])

    def draw(self):
        canv = self.canv
        font, size, colour = self.STYLE[self.level]
        indent = 0 if self.level == 0 else 14
        num_text = str(self.page)
        num_w = canv.stringWidth(num_text, font, size)
        label_w = self.width - indent - num_w - 16
        label = self.text
        if canv.stringWidth(label, font, size) > label_w:
            while label and canv.stringWidth(label + "…", font, size) > label_w:
                label = label[:-1]
            label += "…"
        baseline = 4.9 if self.level == 0 else 3.8
        canv.setFont(font, size)
        canv.setFillColor(colour)
        canv.drawString(indent, baseline, label)
        canv.drawRightString(self.width, baseline, num_text)
        start = indent + canv.stringWidth(label, font, size) + 5
        end = self.width - num_w - 5
        if end > start + 8:
            canv.setFillColor(RULE)
            dot_x = start
            while dot_x < end:
                canv.circle(dot_x, baseline + 1.5, 0.42, stroke=0, fill=1)
                dot_x += 3.4
        if self.level == 0:
            canv.setStrokeColor(RULE)
            canv.setLineWidth(0.35)
            canv.line(0, 0.6, self.width, 0.6)


class _TOCHook(Flowable):
    """Marker flowable that records a TOC entry + PDF bookmark."""

    def __init__(self, level, text):
        self.level = level
        self.text = text

    def wrap(self, availWidth, availHeight):
        return (0, 0)

    def draw(self):
        pass

    def split(self, availWidth, availHeight):
        return []


# --------------------------------------------------------------------------
# document with running headers, footer, TOC and bookmarks
# --------------------------------------------------------------------------
class Guide(BaseDocTemplate):
    def __init__(self, filename, **kw):
        super().__init__(filename, pagesize=A4, leftMargin=LM, rightMargin=RM,
                         topMargin=TM, bottomMargin=BM,
                         title="STA1610 Exam Prep — Past Papers, Worked Solutions & Formula Sheet",
                         author="STA1610 study notes",
                         subject="Introduction to Statistics — revision guide",
                         keywords="STA1610, statistics, exam prep, past papers, formula sheet",
                         **kw)
        frame = Frame(LM, BM, CONTENT_W, PAGE_H - TM - BM, id="main",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        cover_frame = Frame(LM, BM, CONTENT_W, PAGE_H - TM - BM, id="cover",
                            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id="cover", frames=[cover_frame], onPage=self.draw_cover),
            PageTemplate(id="body", frames=[frame], onPage=self.draw_page),
        ])
        self.chapter = ""
        self.heading_seq = 0
        self.heading_pages = []   # page number per registered heading

    def draw_cover(self, canv, doc):
        canv.saveState()
        canv.setFillColor(INK)
        canv.rect(0, 0, PAGE_W, 7, stroke=0, fill=1)
        canv.setFillColor(ACCENT)
        canv.rect(0, 0, PAGE_W * 0.38, 7, stroke=0, fill=1)
        canv.restoreState()

    def draw_page(self, canv, doc):
        canv.saveState()
        # header
        canv.setFont("Sans", 7.4)
        canv.setFillColor(MUTED)
        canv.drawString(LM, PAGE_H - TM + 12, "STA1610 · Introduction to Statistics")
        chapter = (self.chapter or "")[:78]
        canv.drawRightString(PAGE_W - RM, PAGE_H - TM + 12, chapter)
        canv.setStrokeColor(RULE)
        canv.setLineWidth(0.5)
        canv.line(LM, PAGE_H - TM + 7, PAGE_W - RM, PAGE_H - TM + 7)
        # footer
        canv.setFont("Sans", 7.2)
        canv.setFillColor(MUTED)
        canv.drawString(LM, BM - 12, "Revision guide · worked solutions are independent, not official memoranda")
        canv.setFont("Body-Italic", 7.6)
        canv.drawRightString(PAGE_W - RM, BM - 12, "page %d" % doc.page)
        canv.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, _TOCHook):
            level, text = flowable.level, flowable.text
            key = "h%d" % self.heading_seq
            self.heading_seq += 1
            if level == 0:
                self.chapter = text
            self.heading_pages.append(self.page)
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=(level > 0))


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
TOPIC_ORDER = ["exam", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10",
               "t23", "t11", "t12", "t13", "t14", "t15", "t16", "t17", "t18", "t19",
               "t20", "t21", "t22", "calc", "formulas"]

KICKERS = {"exam": "EXAM PREP", "calc": "TOOL", "formulas": "TOOL"}


def build():
    html_text = SRC.read_text(encoding="utf-8")
    dom = parse_html(html_text)
    pages = {}
    for div in dom.find_all("div", "page"):
        pages[div.attrs.get("id")] = div
    if not pages:
        raise SystemExit("no .page sections found — wrong source file?")

    renderer = Renderer()
    story = []

    # ---- cover ----------------------------------------------------------
    story.append(NextPageTemplate("cover"))
    story.append(Spacer(1, 48))
    story.append(Paragraph("STA1610 · INTRODUCTION TO STATISTICS", S["cover_kicker"]))
    story.append(Paragraph("Exam Prep<br/>Revision Guide", S["cover_title"]))
    hero = pages.get("exam")
    sub = hero.find("p", "sub") if hero else None
    story.append(Paragraph(
        xml_escape(re.sub(r"\s+", " ", sub.text()).strip()) if sub else
        "Topic notes, past-paper worked solutions, calculators and formula sheet.",
        S["cover_sub"]))
    story.append(rule(ACCENT, 1.6, 0, 14))

    counts = len([k for k in pages if k.startswith("t")])
    stats = [
        ["23", "topic chapters", "6", "calculator recipes"],
        ["48", "past-paper question entries", "2", "source papers with page references"],
        ["23", "worked solutions", "1", "complete formula sheet"],
    ]
    rows = []
    for row in stats:
        cells = []
        for i, cell in enumerate(row):
            if i % 2 == 0:
                cells.append(Paragraph(
                    f'<font face="Sans-Bold" size="15" color="#2743a8">{cell}</font>', S["cover_meta"]))
            else:
                cells.append(Paragraph(xml_escape(cell), S["cover_meta"]))
        rows.append(cells)
    t = Table(rows, colWidths=[CONTENT_W * 0.10, CONTENT_W * 0.40,
                               CONTENT_W * 0.10, CONTENT_W * 0.40], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
    ]))
    story.append(t)
    story.append(Spacer(1, 26))
    story.append(Paragraph(
        "This PDF is a print layout of the interactive study site. Every worked solution is shown "
        "in full — nothing is hidden behind a click. Past-paper references are exact; question "
        "wording is paraphrased and every solution is independently recomputed, so this is a "
        "revision aid, not an official memorandum.", S["small"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "How to use it: work the 23 chapters in order for coverage, or open the "
        "exam-prep chapter first and use the paper references to jump straight to weak topics. "
        "The formula sheet at the end is designed to be printed on its own for the final hour "
        "before the exam.", S["small"]))

    # at-a-glance chapter index (two columns) so the cover earns its space
    story.append(Spacer(1, 26))
    story.append(Paragraph("INSIDE THIS GUIDE", S["label"]))
    story.append(Spacer(1, 4))
    chapter_rows = []
    listing = [(pid, KICKERS.get(pid) or "TOPIC") for pid in TOPIC_ORDER
               if pid in pages and pid not in ("exam",)]
    titles = []
    for pid in TOPIC_ORDER:
        page = pages.get(pid)
        if page is None:
            continue
        h1 = page.find("h1")
        titles.append((pid, re.sub(r"\s+", " ", h1.text()).strip() if h1 else pid))
    half = (len(titles) + 1) // 2
    for left, right in zip(titles[:half], titles[half:] + [("", "")]):
        def cell(item):
            if not item[0]:
                return Paragraph("", S["small"])
            num = "EX" if item[0] == "exam" else (
                "T" if item[0] in ("calc", "formulas") else item[0].replace("t", "").zfill(2))
            return Paragraph(
                f'<font face="Mono" size="7.4" color="#0b6f68">{num}</font>&nbsp;&nbsp;'
                f'{xml_escape(item[1])}', S["small"])
        chapter_rows.append([cell(left), cell(right)])
    grid = Table(chapter_rows, colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.5], hAlign="LEFT")
    grid.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
    ]))
    story.append(grid)
    story.append(Spacer(1, 18))
    story.append(rule())
    story.append(Paragraph(
        "Generated from the interactive study site (single HTML file). "
        "Print double-sided on A4; the contents page and PDF bookmarks are clickable.", S["small"]))

    # ---- contents -------------------------------------------------------
    # A first pass renders the whole guide (TOC lines with placeholder page
    # numbers) to learn where every heading lands; the second pass draws the
    # real numbers. The TOC row count is fixed from pass one, so pagination
    # cannot drift between passes.
    def assemble(renderer, toc_pages):
        renderer.story = []
        renderer.headings = []
        out = []

        # cover (rebuilt so both passes are identical)
        out.extend(cover_flow)

        out.append(NextPageTemplate("body"))
        out.append(PageBreak())
        out.append(Paragraph("Contents", S["toc_h"]))
        for index, (level, text) in enumerate(renderer_headings):
            page = toc_pages[index] if index < len(toc_pages) else "·"
            out.append(TOCLine(level, text, page))
        # only break if the first chapter would not get a decent page
        out.append(CondPageBreak((PAGE_H - TM - BM) * 0.55))

        for index, page_id in enumerate(TOPIC_ORDER):
            page = pages.get(page_id)
            if page is None:
                continue
            if index > 0:
                out.append(CondPageBreak((PAGE_H - TM - BM) * 0.42))
            kicker = KICKERS.get(page_id) or "TOPIC %s" % page_id.replace("t", "").zfill(2)
            out.append(Paragraph(kicker, S["chapter_num"]))
            if page_id == "calc":
                out.append(Paragraph(
                    "Each tool below lists the quantities it needs and the formula it applies, so "
                    "every calculation can be reproduced by hand or on a calculator during the exam. "
                    "The interactive version performs the arithmetic for you.", S["chapter_sub"]))
            renderer.story = out
            renderer.render_children(page)
        return out

    # discover heading order first (cheap: same traversal, no document)
    probe = Renderer()
    probe.story = []
    probe_flow = []
    for index, page_id in enumerate(TOPIC_ORDER):
        page = pages.get(page_id)
        if page is None:
            continue
        probe.story = probe_flow
        kicker = KICKERS.get(page_id) or ""
        if kicker:
            probe_flow.append(Paragraph(kicker, S["chapter_num"]))
        probe.render_children(page)
    renderer_headings = probe.headings

    cover_flow = story[:]  # everything built before the contents (cover page)

    # pass 1
    pass1_story = assemble(Renderer(), [])
    doc1 = Guide(str(OUT), heading_pages=[])
    doc1.multiBuild(pass1_story)
    pages_found = list(doc1.heading_pages)

    # pass 2 (repeat until stable, at most three times)
    final_pages = pages_found
    for attempt in range(3):
        story2 = assemble(Renderer(), final_pages)
        doc2 = Guide(str(OUT))
        doc2.multiBuild(story2)
        if list(doc2.heading_pages) == final_pages:
            break
        final_pages = list(doc2.heading_pages)

    size_kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT} ({size_kb:.0f} KB, {doc2.page} pages, "
          f"{len(final_pages)} bookmarks)")


if __name__ == "__main__":
    build()
