#!/usr/bin/env python3
"""Build Elementor templates for Porter Energy Systems pages.

    python3 elementor/scripts/build.py                     # every file in elementor/content/
    python3 elementor/scripts/build.py elementor/content/home.json

For each content file this writes:
    elementor/dist/<slug>.json          full page  -> Templates > Saved Templates > Import
    elementor/dist/preview/<slug>.html  rough browser preview (no WordPress needed)
and, once, one file per reusable block:
    elementor/dist/blocks/pes-*.json    single sections to insert into any page

All styling lives in elementor/css/pes-global.css; the templates only carry
content, layout and the "pes-" CSS classes.
"""
import hashlib
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
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


def gap(column, row=None):
    row = column if row is None else row
    return {"column": str(column), "row": str(row), "isLinked": column == row, "unit": "px", "size": column}


def container(ids, children, classes="", inner=False, **settings):
    s = {"content_width": "full" if inner else "boxed", "flex_direction": "column"}
    if classes:
        s["css_classes"] = classes
    s.update(settings)
    return {"id": ids(), "elType": "container", "isInner": inner, "settings": s, "elements": children}


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


def icon(ids, fa_class, classes):
    library = "fa-regular" if fa_class.startswith("far ") else "fa-solid"
    return widget(ids, "icon", classes, selected_icon={"value": fa_class, "library": library},
                  align="center")


# ---------------------------------------------------------------------------
# Blocks – one function per section type in the design
# ---------------------------------------------------------------------------
def block_hero(ids, b):
    bg = {}
    if b.get("image"):
        bg = {"background_background": "classic",
              "background_image": {"url": b["image"], "id": "", "source": "library"},
              "background_position": "center center", "background_size": "cover"}
    return container(
        ids,
        [
            heading(ids, b["kicker"], "p", "pes-kicker"),
            heading(ids, b["title"], "h1", "pes-h1"),
            text(ids, b["text"], "pes-lead"),
            button(ids, b["button"]),
        ],
        "pes-section pes-hero",
        flex_justify_content="center",
        flex_align_items="flex-start",
        flex_gap=gap(18),
        min_height=px(640),
        min_height_mobile=px(520),
        padding=box(80, 24, 80, 24),
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
    copy = container(
        ids,
        [
            heading(ids, b["title"], "h2", "pes-h2"),
            heading(ids, b["subtitle"], "p", "pes-subhead"),
            text(ids, b["text"]),
            button(ids, b["button"]),
        ],
        inner=True,
        width=px(48, "%"), width_mobile=px(100, "%"),
        flex_gap=gap(16), flex_justify_content="center",
    )
    media = container(ids, [image(ids, b.get("image"), frame, b["title"])], inner=True,
                      width=px(46, "%"), width_mobile=px(100, "%"))
    return container(
        ids,
        [media, copy] if reverse else [copy, media],
        "pes-section pes-feature" + (" pes-feature-reverse" if reverse else ""),
        flex_direction="row",
        flex_direction_mobile="column",
        flex_align_items="center",
        flex_justify_content="space-between",
        flex_gap=gap(48),
        padding=box(110, 24, 110, 24),
        padding_mobile=box(70, 20, 70, 20),
    )


def block_process(ids, b):
    steps = [
        container(
            ids,
            [
                heading(ids, str(i), "h3", "pes-step-num"),
                container(ids, [icon(ids, s["icon"], "pes-step-icon"), text(ids, s["text"])],
                          "pes-step-card", inner=True, flex_gap=gap(20),
                          padding=box(30, 24, 30, 24)),
            ],
            "pes-step",
            inner=True,
            width=px(30, "%"), width_mobile=px(100, "%"),
            flex_align_items="center",
        )
        for i, s in enumerate(b["steps"], 1)
    ]
    row = container(ids, steps, inner=True, flex_direction="row", flex_direction_mobile="column",
                    flex_justify_content="space-between", flex_gap=gap(32, 56))
    return container(
        ids,
        [heading(ids, b["title"], "h2", "pes-title-circuit"), row],
        "pes-section pes-process",
        flex_align_items="center",
        flex_gap=gap(48),
        padding=box(60, 24, 120, 24),
    )


def block_cta(ids, b):
    left = container(
        ids,
        [
            icon(ids, "far fa-calendar-alt", "pes-cta-icon"),
            container(ids, [heading(ids, b["title"], "h2", "pes-cta-title"),
                            heading(ids, b["subtitle"], "p", "pes-cta-sub")],
                      "pes-cta-text", inner=True, width=px(100, "%"), width_mobile=px(100, "%"),
                      flex_gap=gap(4)),
        ],
        inner=True,
        width=px(75, "%"), width_mobile=px(100, "%"),
        flex_direction="row", flex_align_items="center", flex_gap=gap(20),
        flex_wrap="nowrap",
    )
    return container(
        ids,
        [left, button(ids, b["button"], "pes-btn-solid")],
        "pes-cta",
        flex_direction="row",
        flex_direction_mobile="column",
        flex_align_items="center",
        flex_align_items_mobile="flex-start",
        flex_justify_content="space-between",
        flex_gap=gap(24),
        padding=box(36, 24, 36, 24),
    )


def block_header(ids, b):
    return container(
        ids,
        [
            image(ids, b.get("logo"), "pes-logo"),
            widget(ids, "wp-widget-nav_menu", "pes-nav", wp={"title": "", "nav_menu": ""}),
            button(ids, b["button"], "pes-btn-solid"),
        ],
        "pes-header",
        flex_direction="row",
        flex_align_items="center",
        flex_justify_content="space-between",
        flex_gap=gap(24),
        padding=box(14, 24, 14, 24),
    )


BLOCKS = {
    "hero": block_hero,
    "feature": block_feature,
    "process": block_process,
    "cta": block_cta,
    "header": block_header,
}

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
    sections = [BLOCKS[b["type"]](ids, b) for b in page["blocks"]]
    write_json(DIST / f"{page['slug']}.json",
               template(page["title"], "page", sections, PAGE_SETTINGS))
    write_preview(DIST / "preview" / f"{page['slug']}.html", page["title"],
                  [BLOCKS["header"](ids, HEADER_DEFAULTS)] + sections)

    # one standalone file per block variant (first occurrence wins)
    for b in page["blocks"] + [HEADER_DEFAULTS]:
        name = block_name(b)
        if name in seen_blocks:
            continue
        seen_blocks.add(name)
        title = "PES – " + name[4:].replace("-", " ").title()
        write_json(DIST / "blocks" / f"{name}.json",
                   template(title, "container", [BLOCKS[b["type"]](Ids(name), b)]))


# ---------------------------------------------------------------------------
# Preview: renders the same element tree with Elementor-like markup so the
# CSS can be checked in a browser without WordPress. Approximate only.
# ---------------------------------------------------------------------------
FLEX = {"flex-start": "flex-start", "center": "center", "flex-end": "flex-end",
        "space-between": "space-between"}


def render(el):
    s = el["settings"]
    if el["elType"] == "container":
        style = [f"flex-direction:{s.get('flex_direction', 'column')}"]
        if "flex_align_items" in s:
            style.append(f"align-items:{FLEX[s['flex_align_items']]}")
        if "flex_justify_content" in s:
            style.append(f"justify-content:{FLEX[s['flex_justify_content']]}")
        if "flex_gap" in s:
            style.append(f"gap:{s['flex_gap']['row']}px {s['flex_gap']['column']}px")
        if "width" in s:
            style.append(f"width:{s['width']['size']}%")
        if "min_height" in s:
            style.append(f"min-height:{s['min_height']['size']}{s['min_height']['unit']}")
        if "padding" in s:
            p = s["padding"]
            style.append(f"padding:{p['top']}px {p['right']}px {p['bottom']}px {p['left']}px")
        if s.get("background_overlay_background") == "gradient":
            style.append("--pv-overlay:linear-gradient(90deg,rgba(0,0,0,.78),rgba(0,0,0,.05) 80%)")
        bg_url = s.get("background_image", {}).get("url")
        if not bg_url and "pes-hero" in s.get("css_classes", ""):
            bg_url = "img/hero.jpg"  # preview stand-in only
        if bg_url:
            style.append(f"background-image:url({bg_url});background-size:cover;background-position:center")
        kids = "".join(render(c) for c in el["elements"])
        mobile = " pv-stack" if s.get("flex_direction_mobile") == "column" else ""
        inner_style = ";".join(x for x in style if not x.startswith(("padding", "min-height", "width", "background", "--")))
        if s.get("content_width") == "boxed":
            outer = ";".join(x for x in style if x.startswith(("padding", "min-height", "background", "--")))
            return (f'<div class="elementor-element e-con e-con-boxed{mobile} {s.get("css_classes", "")}" style="{outer}">'
                    f'<div class="e-con-inner{mobile}" style="{inner_style}">{kids}</div></div>')
        return (f'<div class="elementor-element e-con e-con-full{mobile} {s.get("css_classes", "")}" '
                f'style="{";".join(style)}">{kids}</div>')

    kind = el["widgetType"]
    if kind == "heading":
        tag = s["header_size"]
        body = f'<{tag} class="elementor-heading-title">{s["title"]}</{tag}>'
    elif kind == "text-editor":
        body = s["editor"]
    elif kind == "button":
        body = (f'<a class="elementor-button" href="{html.escape(s["link"]["url"])}">'
                f'<span class="elementor-button-content-wrapper"><span class="elementor-button-text">'
                f'{s["text"]}</span></span></a>')
    elif kind == "image":
        if "pes-logo" in s.get("_css_classes", ""):
            src = "img/logo.png"
        else:
            src = s.get("image", {}).get("url") or (PREVIEW_IMAGES.pop(0) if PREVIEW_IMAGES else "")
        body = f'<img src="{src}" alt="">'
    elif kind == "icon":
        body = f'<div class="elementor-icon-wrapper"><div class="elementor-icon">{PREVIEW_ICON}</div></div>'
    elif kind == "wp-widget-nav_menu":
        items = ["Solution", "Service O&amp;M", "Projects", "Company", "Contact Us", "Industry"]
        body = '<ul class="menu">' + "".join(
            f'<li class="menu-item menu-item-has-children"><a href="#">{i}</a></li>' for i in items) + "</ul>"
    else:
        body = ""
    return (f'<div class="elementor-element elementor-widget elementor-widget-{kind} {s.get("_css_classes", "")}">'
            f'<div class="elementor-widget-container">{body}</div></div>')


PREVIEW_IMAGES = []
PREVIEW_ICON = ('<svg viewBox="0 0 24 24" width="1em" height="1em"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg>')

PREVIEW_BASE_CSS = """
*{box-sizing:border-box} body{margin:0;background:#1b1b1c}
.e-con{display:flex;position:relative}
.e-con-boxed{flex-direction:column;align-items:center}
.e-con-inner{display:flex;width:100%;max-width:1140px;margin:0 auto}
.e-con-full{display:flex}
.e-con[style*="--pv-overlay"]::before{content:"";position:absolute;inset:0;background:var(--pv-overlay)}
.e-con[style*="--pv-overlay"]>.e-con-inner{position:relative}
.elementor-heading-title{margin:0;padding:0}
.elementor-widget-container p{margin:0 0 1em}
.elementor-button{display:inline-block;text-decoration:none}
.elementor-widget-image img{max-width:100%;height:auto}
.elementor-widget-icon .elementor-icon-wrapper{text-align:center}
.elementor-icon{display:inline-block;line-height:1}
.elementor-icon svg{width:1em;height:1em;display:block}
.pes-logo img{height:44px;width:auto}
@media(max-width:767px){.pv-stack{flex-direction:column!important}.pv-stack>.e-con{width:100%!important}}
"""


def write_preview(path, title, sections):
    path.parent.mkdir(parents=True, exist_ok=True)
    preview_dir = ROOT / "dist" / "preview" / "img"
    PREVIEW_IMAGES[:] = sorted(f"img/{p.name}" for p in preview_dir.glob("frame-*.jpg")) if preview_dir.exists() else []
    css = (ROOT / "css" / "pes-global.css").read_text()
    body = "".join(render(s) for s in sections)
    path.write_text(
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(re.sub('<[^>]+>', ' ', title))} – preview</title>"
        f"<style>{PREVIEW_BASE_CSS}</style><style>{css}</style></head>"
        f"<body><div class='elementor elementor-preview'>{body}</div></body></html>\n")
    print("wrote", path.relative_to(ROOT.parent))


def main(argv):
    files = argv[1:] or sorted(str(p) for p in (ROOT / "content").glob("*.json"))
    seen = set()
    for f in files:
        build(f, seen)


if __name__ == "__main__":
    main(sys.argv)
