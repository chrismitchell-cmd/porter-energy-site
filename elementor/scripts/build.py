#!/usr/bin/env python3
"""Build Elementor templates for Porter Energy Systems pages.

    python3 elementor/scripts/build.py                     # every file in elementor/content/
    python3 elementor/scripts/build.py elementor/content/home.json

For each content file this writes:
    elementor/dist/<slug>.json          full page  -> Templates > Saved Templates > Import
    elementor/dist/preview/<slug>.html  rough browser preview (no WordPress needed)
and, once, one file per reusable block:
    elementor/dist/blocks/pes-*.json    single sections to insert into any page

Templates use classic Sections/Columns (not Flexbox Containers) so they import
on every Elementor version, with or without the Container feature switched on.
The page template carries its own styles in a hidden "PES Styles" section, so
nothing has to be pasted into the Customizer for it to look right.
"""
import hashlib
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
CSS_FILE = ROOT / "css" / "pes-global.css"
TEMPLATE_VERSION = "0.4"


# ---------------------------------------------------------------------------
# Elementor element helpers
# ---------------------------------------------------------------------------
class Ids:
    """Deterministic 7-char hex ids so rebuilding gives a stable diff."""

    def __init__(self, seed):
        self.seed, self.n = seed, 0

    def __call__(self):
        self.n += 1
        return hashlib.sha1(f"{self.seed}:{self.n}".encode()).hexdigest()[:7]


def px(size, unit="px"):
    return {"unit": unit, "size": size, "sizes": []}


def box(top, right, bottom, left, unit="px"):
    return {"unit": unit, "top": str(top), "right": str(right), "bottom": str(bottom),
            "left": str(left), "isLinked": False}


def section(ids, columns, classes="", title="", inner=False, **settings):
    s = {"layout": "boxed", "gap": "default", "content_width": px(1140)}
    if classes:
        s["css_classes"] = classes
    if title:
        s["_title"] = title  # name shown in Elementor's Navigator
    s.update(settings)
    for c in columns:
        c["isInner"] = inner
    return {"id": ids(), "elType": "section", "isInner": inner, "settings": s, "elements": columns}


def column(ids, size, widgets, classes="", **settings):
    s = {"_column_size": 100 if size == 100 else 50, "_inline_size": size}
    if classes:
        s["css_classes"] = classes
    s.update(settings)
    return {"id": ids(), "elType": "column", "isInner": False, "settings": s, "elements": widgets}


def widget(ids, kind, classes="", **settings):
    if classes:
        settings["_css_classes"] = classes
    return {"id": ids(), "elType": "widget", "widgetType": kind, "isInner": False,
            "settings": settings, "elements": []}


def heading(ids, text, tag, classes):
    return widget(ids, "heading", classes, title=text, header_size=tag)


def text(ids, body, classes="pes-body"):
    return widget(ids, "text-editor", classes, editor=f"<p>{body}</p>")


def button(ids, btn, classes="pes-btn"):
    return widget(ids, "button", classes, text=btn["text"],
                  link={"url": btn["url"], "is_external": "", "nofollow": "", "custom_attributes": ""})


def image(ids, url, classes, alt=""):
    # No url -> leave the setting out so Elementor shows its own placeholder.
    extra = {"image": {"url": url, "id": "", "alt": alt, "source": "library"}} if url else {}
    return widget(ids, "image", classes, image_size="full", **extra)


def fa(fa_class):
    library = "fa-regular" if fa_class.startswith("far ") else "fa-solid"
    return {"value": fa_class, "library": library}


def icon_box(ids, fa_class, classes, title="", description="", position="top", title_tag="h3"):
    return widget(ids, "icon-box", classes, selected_icon=fa(fa_class), view="default",
                  position=position, title_text=title, description_text=description,
                  title_size=title_tag, content_vertical_alignment="middle")


# ---------------------------------------------------------------------------
# Blocks – one function per section type in the design
# ---------------------------------------------------------------------------
def block_styles(ids, _b=None):
    css = CSS_FILE.read_text()
    return section(
        ids,
        [column(ids, 100, [widget(ids, "html", "pes-styles-widget", html=f"<style>\n{css}</style>")])],
        "pes-styles",
        title="PES Styles – keep this section (hidden on the live site)",
        layout="full_width",
        gap="no",
    )


def block_hero(ids, b):
    bg = {}
    if b.get("image"):
        bg = {"background_background": "classic",
              "background_image": {"url": b["image"], "id": "", "source": "library"},
              "background_position": "center center", "background_size": "cover"}
    return section(
        ids,
        [column(ids, 100, [
            heading(ids, b["kicker"], "p", "pes-kicker"),
            heading(ids, b["title"], "h1", "pes-h1"),
            text(ids, b["text"], "pes-lead"),
            button(ids, b["button"]),
        ])],
        "pes-section pes-hero",
        title="Hero",
        height="min-height",
        custom_height=px(640),
        custom_height_mobile=px(520),
        column_position="middle",
        padding=box(80, 0, 80, 0),
        background_overlay_background="gradient",
        background_overlay_color="rgba(0,0,0,0.78)",
        background_overlay_color_stop=px(0, "%"),
        background_overlay_color_b="rgba(0,0,0,0.05)",
        background_overlay_color_b_stop=px(80, "%"),
        background_overlay_gradient_angle=px(90, "deg"),
        **bg,
    )


def block_feature(ids, b):
    reverse = b.get("layout") == "image-left"
    frame = "pes-frame pes-frame-blue" if b.get("frame") == "blue" else "pes-frame"
    copy = column(ids, 50, [
        heading(ids, b["title"], "h2", "pes-h2"),
        heading(ids, b["subtitle"], "p", "pes-subhead"),
        text(ids, b["text"]),
        button(ids, b["button"]),
    ], content_position="center")
    media = column(ids, 50, [image(ids, b.get("image"), frame, b["title"])], content_position="center")
    return section(
        ids,
        [media, copy] if reverse else [copy, media],
        "pes-section pes-feature" + (" pes-feature-reverse" if reverse else ""),
        title=f"Feature – {b['title']}",
        gap="extended",
        structure="20",
        column_position="middle",
        padding=box(110, 0, 110, 0),
        padding_mobile=box(70, 0, 70, 0),
    )


def block_process(ids, b):
    steps = [
        column(ids, 33.333, [
            heading(ids, str(i), "h3", "pes-step-num"),
            icon_box(ids, s["icon"], "pes-step-card", description=s["text"]),
        ], "pes-step")
        for i, s in enumerate(b["steps"], 1)
    ]
    cards = section(ids, steps, "pes-steps", inner=True, gap="extended", structure="30")
    return section(
        ids,
        [column(ids, 100, [heading(ids, b["title"], "h2", "pes-title-circuit"), cards])],
        "pes-section pes-process",
        title="Our Process",
        padding=box(60, 0, 120, 0),
    )


def block_cta(ids, b):
    return section(
        ids,
        [
            column(ids, 70, [icon_box(ids, "far fa-calendar-alt", "pes-cta-box", b["title"],
                                      b["subtitle"], position="left", title_tag="h2")],
                   content_position="center"),
            column(ids, 30, [button(ids, b["button"], "pes-btn-solid pes-align-right")],
                   content_position="center"),
        ],
        "pes-cta",
        title="CTA – Schedule a consultation",
        structure="20",
        column_position="middle",
        padding=box(30, 0, 30, 0),
    )


def block_header(ids, b):
    return section(
        ids,
        [
            column(ids, 18, [image(ids, b.get("logo"), "pes-logo")], content_position="center"),
            column(ids, 64, [widget(ids, "wp-widget-nav_menu", "pes-nav", wp={"title": "", "nav_menu": ""})],
                   content_position="center"),
            column(ids, 18, [button(ids, b["button"], "pes-btn-solid pes-align-right")],
                   content_position="center"),
        ],
        "pes-header",
        title="Header",
        structure="30",
        column_position="middle",
        padding=box(8, 0, 8, 0),
    )


BLOCKS = {
    "styles": block_styles,
    "hero": block_hero,
    "feature": block_feature,
    "process": block_process,
    "cta": block_cta,
    "header": block_header,
}

STYLES_BLOCK = {"type": "styles"}
HEADER_DEFAULTS = {"type": "header", "logo": "", "button": {"text": "Get A Quote", "url": "/contact/"}}


def block_name(b):
    if b["type"] == "feature":
        return f"pes-feature-{b.get('layout', 'image-right')}"
    return f"pes-{b['type']}"


# ---------------------------------------------------------------------------
# Template files
# ---------------------------------------------------------------------------
def template(title, kind, content, page_settings=None):
    return {"version": TEMPLATE_VERSION, "title": title, "type": kind,
            "page_settings": page_settings or [], "content": content}


PAGE_SETTINGS = {
    "template": "elementor_header_footer",  # "Elementor Full Width": keeps the theme header/footer
    "hide_title": "yes",
    "background_background": "classic",
    "background_color": "#1B1B1C",
}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print("wrote", path.relative_to(ROOT.parent))


def build(content_path, seen_blocks):
    page = json.loads(Path(content_path).read_text())
    ids = Ids(page["slug"])
    sections = [block_styles(ids)] + [BLOCKS[b["type"]](ids, b) for b in page["blocks"]]
    write_json(DIST / f"{page['slug']}.json",
               template(page["title"], "page", sections, PAGE_SETTINGS))
    write_preview(DIST / "preview" / f"{page['slug']}.html", page["title"],
                  [BLOCKS["header"](ids, HEADER_DEFAULTS)] + sections)

    # one standalone file per block variant (first occurrence wins)
    for b in [STYLES_BLOCK] + page["blocks"] + [HEADER_DEFAULTS]:
        name = block_name(b)
        if name in seen_blocks:
            continue
        seen_blocks.add(name)
        title = "PES – " + name[4:].replace("-", " ").title()
        write_json(DIST / "blocks" / f"{name}.json",
                   template(title, "section", [BLOCKS[b["type"]](Ids(name), b)]))


# ---------------------------------------------------------------------------
# Preview: renders the same element tree with Elementor-like markup so the
# CSS can be checked in a browser without WordPress. Approximate only.
# ---------------------------------------------------------------------------
PREVIEW_IMAGES = []
PREVIEW_ICON = '<svg viewBox="0 0 24 24" width="1em" height="1em"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg>'


def render(el):
    s = el["settings"]
    if el["elType"] == "section":
        style = []
        if s.get("padding"):
            p = s["padding"]
            style.append(f"padding:{p['top']}px 0 {p['bottom']}px")
        bg_url = s.get("background_image", {}).get("url")
        if not bg_url and "pes-hero" in s.get("css_classes", ""):
            bg_url = "img/hero.jpg"  # preview stand-in only
        if bg_url:
            style.append(f"background-image:url({bg_url});background-size:cover;background-position:center")
        overlay = ('<div class="elementor-background-overlay"></div>'
                   if s.get("background_overlay_background") else "")
        cstyle = f"min-height:{s['custom_height']['size']}px" if s.get("height") == "min-height" else ""
        layout = "elementor-section-full_width" if s.get("layout") == "full_width" else "elementor-section-boxed"
        middle = " pv-middle" if s.get("column_position") == "middle" else ""
        kids = "".join(render(c) for c in el["elements"])
        return (f'<section class="elementor-section elementor-element {layout}{middle} {s.get("css_classes", "")}" '
                f'style="{";".join(style)}">{overlay}'
                f'<div class="elementor-container elementor-column-gap-{s.get("gap", "default")}" style="{cstyle}">'
                f'{kids}</div></section>')
    if el["elType"] == "column":
        center = " pv-center" if s.get("content_position") == "center" else ""
        kids = "".join(render(c) for c in el["elements"])
        return (f'<div class="elementor-column elementor-element{center} {s.get("css_classes", "")}" '
                f'style="width:{s["_inline_size"]}%"><div class="elementor-widget-wrap elementor-element-populated">'
                f'{kids}</div></div>')

    kind = el["widgetType"]
    extra = ""
    if kind == "heading":
        tag = s["header_size"]
        body = f'<{tag} class="elementor-heading-title">{s["title"]}</{tag}>'
    elif kind == "text-editor":
        body = s["editor"]
    elif kind == "html":
        body = s["html"]
    elif kind == "button":
        body = (f'<div class="elementor-button-wrapper"><a class="elementor-button" href="{html.escape(s["link"]["url"])}">'
                f'<span class="elementor-button-content-wrapper"><span class="elementor-button-text">'
                f'{s["text"]}</span></span></a></div>')
    elif kind == "image":
        if "pes-logo" in s.get("_css_classes", ""):
            src = "img/logo.png"
        else:
            src = s.get("image", {}).get("url") or (PREVIEW_IMAGES.pop(0) if PREVIEW_IMAGES else "")
        body = f'<img src="{src}" alt="">'
    elif kind == "icon-box":
        extra = f" elementor-position-{s['position']} elementor-view-default"
        title = (f'<{s["title_size"]} class="elementor-icon-box-title"><span>{s["title_text"]}</span>'
                 f'</{s["title_size"]}>' if s["title_text"] else "")
        body = (f'<div class="elementor-icon-box-wrapper"><div class="elementor-icon-box-icon">'
                f'<span class="elementor-icon">{PREVIEW_ICON}</span></div>'
                f'<div class="elementor-icon-box-content">{title}'
                f'<p class="elementor-icon-box-description">{s["description_text"]}</p></div></div>')
    elif kind == "wp-widget-nav_menu":
        items = ["Solution", "Service O&amp;M", "Projects", "Company", "Contact Us", "Industry"]
        body = '<ul class="menu">' + "".join(
            f'<li class="menu-item menu-item-has-children"><a href="#">{i}</a></li>' for i in items) + "</ul>"
    else:
        body = ""
    return (f'<div class="elementor-element elementor-widget elementor-widget-{kind}{extra} {s.get("_css_classes", "")}">'
            f'<div class="elementor-widget-container">{body}</div></div>')


# Minimal stand-in for Elementor's own frontend CSS.
PREVIEW_BASE_CSS = """
*{box-sizing:border-box} body{margin:0;background:#fff;font-family:sans-serif}
.elementor-section{position:relative}
.elementor-background-overlay{position:absolute;inset:0;background:linear-gradient(90deg,rgba(0,0,0,.78),rgba(0,0,0,.05) 80%)}
.elementor-container{display:flex;margin:0 auto;position:relative}
.elementor-section-boxed>.elementor-container{max-width:1140px}
.pv-middle>.elementor-container{align-items:center}
.elementor-column{display:flex;min-height:1px;position:relative}
.elementor-widget-wrap{display:flex;flex-wrap:wrap;align-content:flex-start;width:100%;position:relative}
.pv-center>.elementor-widget-wrap{align-content:center}
.elementor-column-gap-default>.elementor-column>.elementor-element-populated{padding:10px}
.elementor-column-gap-extended>.elementor-column>.elementor-element-populated{padding:15px}
.elementor-widget-wrap>.elementor-element{width:100%}
.elementor-widget:not(:last-child){margin-bottom:20px}
.elementor-heading-title{margin:0;padding:0;line-height:1}
.elementor-widget-container p{margin:0 0 1em}
.elementor-button{display:inline-block;text-decoration:none}
.elementor-widget-image{text-align:center}
.elementor-widget-image img{max-width:100%;height:auto;vertical-align:middle}
.elementor-icon{display:inline-block;line-height:1;font-size:50px}
.elementor-icon svg{width:1em;height:1em;display:block}
.elementor-widget-icon-box .elementor-icon-box-wrapper{text-align:center}
.elementor-icon-box-title{margin:0}
.elementor-icon-box-description{margin:0}
.pes-logo img{height:44px;width:auto}
@media(max-width:767px){.elementor-container{flex-wrap:wrap}.elementor-column{width:100%!important}}
"""


def write_preview(path, title, sections):
    path.parent.mkdir(parents=True, exist_ok=True)
    preview_dir = ROOT / "dist" / "preview" / "img"
    PREVIEW_IMAGES[:] = sorted(f"img/{p.name}" for p in preview_dir.glob("frame-*.jpg")) if preview_dir.exists() else []
    body = "".join(render(s) for s in sections)
    path.write_text(
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(re.sub('<[^>]+>', ' ', title))} – preview</title>"
        f"<style>{PREVIEW_BASE_CSS}</style></head>"
        f"<body><div class='elementor elementor-preview'>{body}</div></body></html>\n")
    print("wrote", path.relative_to(ROOT.parent))


def main(argv):
    files = argv[1:] or sorted(str(p) for p in (ROOT / "content").glob("*.json"))
    seen = set()
    for f in files:
        build(f, seen)


if __name__ == "__main__":
    main(sys.argv)
