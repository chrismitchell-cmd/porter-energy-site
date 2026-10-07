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
    classes = btn.get("style", classes)
    return widget(ids, "button", classes, text=btn["text"],
                  link={"url": btn["url"], "is_external": "", "nofollow": "", "custom_attributes": ""})


def image(ids, url, classes, alt="", preview=None):
    # No url -> leave the setting out so Elementor shows its own placeholder.
    extra = {"image": {"url": url, "id": "", "alt": alt, "source": "library"}} if url else {}
    w = widget(ids, "image", classes, image_size="full", **extra)
    PREVIEW_SRC[w["id"]] = preview
    return w


def two_tone(title, accent=""):
    """White heading text with an optional gold-gradient part ("SAY IT IN YOUR OWN WAY")."""
    return f'{title} <span class="pes-accent">{accent}</span>' if accent else title


def video(ids, url, classes, preview=None):
    # No url -> Elementor's sample video shows until the real YouTube/Vimeo link is pasted in.
    extra = {"youtube_url": url} if url else {}
    w = widget(ids, "video", classes, video_type="youtube", **extra)
    PREVIEW_SRC[w["id"]] = preview
    return w


def icon_list(ids, items, classes, fa_class="fas fa-check"):
    return widget(ids, "icon-list", classes, icon_list=[
        {"_id": ids(), "text": t, "selected_icon": fa(fa_class)} for t in items])


def accordion(ids, items, classes):
    return widget(ids, "accordion", classes,
                  tabs=[{"_id": ids(), "tab_title": q["q"], "tab_content": f"<p>{q['a']}</p>"} for q in items],
                  selected_icon=fa("fas fa-plus"), selected_active_icon=fa("fas fa-minus"),
                  title_html_tag="h3", faq_schema="yes")


def bg_image(url, overlay="rgba(16,16,17,0.82)"):
    """Section background photo with a dark overlay (empty url -> just the overlay colour)."""
    s = {"background_overlay_background": "classic", "background_overlay_color": overlay}
    if url:
        s.update({"background_background": "classic",
                  "background_image": {"url": url, "id": "", "source": "library"},
                  "background_position": "center center", "background_size": "cover"})
    return s


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
    centered = b.get("align") == "center"
    bg = {}
    if b.get("image"):
        bg = {"background_background": "classic",
              "background_image": {"url": b["image"], "id": "", "source": "library"},
              "background_position": "center center", "background_size": "cover"}
    if b.get("video"):  # MP4 or YouTube link; the image (if any) is the fallback on phones
        bg.update({"background_background": "video", "background_video_link": b["video"],
                   "background_play_on_mobile": "yes"})
        if b.get("image"):
            bg["background_video_fallback"] = {"url": b["image"], "id": "", "source": "library"}
    if centered:
        overlay = {"background_overlay_background": "classic",
                   "background_overlay_color": "rgba(12,12,14,0.62)"}
    else:
        overlay = {"background_overlay_background": "gradient",
                   "background_overlay_color": "rgba(0,0,0,0.78)",
                   "background_overlay_color_stop": px(0, "%"),
                   "background_overlay_color_b": "rgba(0,0,0,0.05)",
                   "background_overlay_color_b_stop": px(80, "%"),
                   "background_overlay_gradient_angle": px(90, "deg")}
    widgets = ([heading(ids, b["kicker"], "p", "pes-kicker")] if b.get("kicker") else []) + [
        heading(ids, b["title"], "h1", "pes-h1"),
        text(ids, b["text"], "pes-lead"),
        button(ids, b["button"]),
    ]
    return section(
        ids,
        [column(ids, 100, widgets)],
        "pes-section pes-hero" + (" pes-hero-center" if centered else ""),
        title="Hero",
        height="min-height",
        custom_height=px(680 if centered else 640),
        custom_height_mobile=px(560 if centered else 520),
        column_position="middle",
        padding=box(80, 0, 80, 0),
        **overlay,
        **bg,
    )


def block_feature(ids, b):
    reverse = b.get("layout") == "image-left"
    frame = "pes-frame pes-frame-blue" if b.get("frame") == "blue" else "pes-frame"
    copy = column(ids, 50, [
        heading(ids, b["title"], "h2", "pes-h2"),
        heading(ids, b["subtitle"], "p", "pes-subhead"),
        text(ids, b["text"]),
        button(ids, b["button"], "pes-btn pes-btn-more"),
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
    n = len(b["steps"])
    steps = [
        column(ids, round(100 / n, 3), [
            heading(ids, str(i), "h3", "pes-step-num"),
            icon_box(ids, s["icon"], "pes-step-card", title=s.get("title", ""), description=s["text"]),
        ], "pes-step")
        for i, s in enumerate(b["steps"], 1)
    ]
    cards = section(ids, steps, "pes-steps", inner=True, gap="extended", structure=f"{n}0")
    top = [heading(ids, b["title"], "h2", "pes-title-circuit")]
    if b.get("subtitle"):
        top.append(heading(ids, b["subtitle"], "p", "pes-eyebrow pes-center"))
    bottom = [button(ids, b["button"], "pes-btn-solid pes-align-center")] if b.get("button") else []
    return section(
        ids,
        [column(ids, 100, top + [cards] + bottom)],
        "pes-section pes-process",
        title=b.get("label", "Our Process"),
        padding=box(80, 0, 110, 0),
        **(bg_image(b["image"]) if b.get("image") else {}),
    )


def block_intro(ids, b):
    """'What is …' – kicker, two-tone heading, text, two misconceptions | video + button."""
    points = section(ids, [
        column(ids, 50, [heading(ids, p["title"], "h3", "pes-h4 pes-accent-title"), text(ids, p["text"])])
        for p in b.get("points", [])
    ], "pes-points", inner=True, gap="default", structure="20") if b.get("points") else None
    copy = column(ids, 55, [
        heading(ids, b["kicker"], "p", "pes-eyebrow"),
        heading(ids, two_tone(b["title"], b.get("accent")), "h2", "pes-h2"),
        text(ids, b["text"]),
    ] + ([points] if points else []), content_position="center")
    media = column(ids, 45, [video(ids, b.get("video"), "pes-frame pes-frame-blue", "img/video.jpg")]
                   + ([button(ids, b["button"], "pes-btn pes-align-center")] if b.get("button") else []),
                   content_position="center")
    return section(ids, [copy, media], "pes-section pes-feature", title="Intro – What is it",
                   gap="extended", structure="20", column_position="middle",
                   padding=box(110, 0, 110, 0), padding_mobile=box(70, 0, 70, 0))


def block_band(ids, b):
    """'Why it matters' – centred statement over a darkened photo, gradient lines top and bottom."""
    return section(ids, [column(ids, 100, [
        heading(ids, b["kicker"], "p", "pes-eyebrow pes-center"),
        heading(ids, two_tone(b["title"], b.get("accent")), "h2", "pes-h2 pes-h2-mixed pes-center"),
        text(ids, b["text"], "pes-lead pes-center"),
    ])], "pes-section pes-band", title="Problem band – Why it matters",
        column_position="middle", padding=box(110, 0, 110, 0), padding_mobile=box(80, 0, 80, 0),
        **bg_image(b.get("image")))


def block_benefits(ids, b):
    """Key benefits – framed photo | kicker, two-tone heading, text, checklist, CTA."""
    frame = "pes-frame pes-frame-blue" if b.get("frame") == "blue" else "pes-frame"
    media = column(ids, 47, [image(ids, b.get("image"), frame, b["title"], "img/sunset.jpg")],
                   content_position="center")
    copy = column(ids, 53, [
        heading(ids, b["kicker"], "p", "pes-eyebrow"),
        heading(ids, two_tone(b["title"], b.get("accent")), "h2", "pes-h2"),
        text(ids, b["text"]),
        heading(ids, b["list_title"], "h3", "pes-subhead"),
        icon_list(ids, b["items"], "pes-checklist"),
        button(ids, b["button"], "pes-btn-solid"),
    ], content_position="center")
    return section(ids, [media, copy], "pes-section pes-feature pes-feature-reverse", title="Key benefits",
                   gap="extended", structure="20", column_position="middle",
                   padding=box(110, 0, 110, 0), padding_mobile=box(70, 0, 70, 0))


def block_media(ids, b):
    """Punch line – two-tone heading + paragraph | framed video."""
    copy = column(ids, 48, [
        heading(ids, two_tone(b["title"], b.get("accent")), "h2", "pes-h2"),
        text(ids, b["text"]),
    ] + ([button(ids, b["button"], "pes-btn pes-btn-more")] if b.get("button") else []),
        content_position="center")
    media = column(ids, 52, [video(ids, b.get("video"), "pes-frame", "img/video.jpg")], content_position="center")
    return section(ids, [copy, media], "pes-section pes-feature", title="Punch line + video",
                   gap="extended", structure="20", column_position="middle",
                   padding=box(110, 0, 110, 0), padding_mobile=box(70, 0, 70, 0))


def block_audience(ids, b):
    """Who it's for – photo cards; the description slides in on hover (always shown on phones)."""
    n = len(b["cards"])
    cards = []
    for c in b["cards"]:
        col = column(ids, round(100 / n, 3), [
            heading(ids, c["title"], "h3", "pes-card-title"),
            text(ids, c["text"], "pes-card-text"),
        ], "pes-audience-card", **({"background_background": "classic",
                                    "background_image": {"url": c["image"], "id": "", "source": "library"},
                                    "background_position": "center center", "background_size": "cover"}
                                   if c.get("image") else {}))
        PREVIEW_SRC[col["id"]] = "img/rack.jpg"
        cards.append(col)
    grid = section(ids, cards, "pes-audience", inner=True, gap="narrow", structure=f"{n}0")
    return section(ids, [column(ids, 100, [
        heading(ids, b["kicker"], "p", "pes-eyebrow pes-center"),
        heading(ids, b["title"], "h2", "pes-h2 pes-h2-mixed pes-center"),
        grid,
    ])], "pes-section", title="Who it's for", padding=box(100, 0, 110, 0))


def block_testimonials(ids, b):
    return section(ids, [column(ids, 100, [
        heading(ids, b["kicker"], "p", "pes-eyebrow pes-center"),
        heading(ids, b["title"], "h2", "pes-title-circuit"),
        widget(ids, "shortcode", "pes-reviews", shortcode=b["shortcode"]),
    ])], "pes-section", title="Testimonials", padding=box(90, 0, 60, 0))


def block_faq(ids, b):
    return section(ids, [column(ids, 100, [
        heading(ids, b["kicker"], "p", "pes-eyebrow pes-center"),
        heading(ids, b["title"], "h2", "pes-h2 pes-h2-mixed pes-center"),
        accordion(ids, b["items"], "pes-faq"),
    ])], "pes-section", title="FAQs", content_width=px(960), padding=box(60, 0, 120, 0))


def block_cta(ids, b):
    return section(
        ids,
        [
            column(ids, 70, [icon_box(ids, "far fa-calendar-alt", "pes-cta-box", b["title"],
                                      b["subtitle"], position="left", title_tag="h2")],
                   content_position="center"),
            column(ids, 30, [button(ids, b["button"], "pes-btn-pill pes-align-right")],
                   content_position="center"),
        ],
        "pes-cta",
        title="CTA – Schedule a consultation",
        structure="20",
        column_position="middle",
        padding=box(48, 0, 48, 0),
    )


def block_header(ids, b):
    return section(
        ids,
        [
            column(ids, 18, [image(ids, b.get("logo"), "pes-logo", "Porter Energy Systems")],
                   content_position="center", _inline_size_mobile=50),
            column(ids, 60, [widget(ids, "wp-widget-nav_menu", "pes-nav", wp={"title": "", "nav_menu": ""})],
                   content_position="center", hide_mobile="hidden-mobile"),
            column(ids, 22, [button(ids, b["button"], "pes-btn-solid pes-align-right")],
                   "pes-header-cta", _inline_size_mobile=50),
        ],
        "pes-header",
        title="Header",
        layout="full_width",
        structure="30",
        column_position="middle",
        padding=box(6, 40, 6, 40),
        padding_mobile=box(6, 12, 6, 12),
    )


BLOCKS = {
    "styles": block_styles,
    "hero": block_hero,
    "feature": block_feature,
    "process": block_process,
    "intro": block_intro,
    "band": block_band,
    "benefits": block_benefits,
    "media": block_media,
    "audience": block_audience,
    "testimonials": block_testimonials,
    "faq": block_faq,
    "cta": block_cta,
    "header": block_header,
}

STYLES_BLOCK = {"type": "styles"}
HEADER_DEFAULTS = {"type": "header", "logo": "", "button": {"text": "Get A Quote", "url": "/contact/"}}


def block_name(b):
    if b["type"] == "feature":
        return f"pes-feature-{b.get('layout', 'image-right')}"
    if b["type"] == "hero" and b.get("align") == "center":
        return "pes-hero-center"
    if b["type"] == "process" and len(b["steps"]) != 3:
        return f"pes-process-{len(b['steps'])}-steps"
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
    header = page.get("header", HEADER_DEFAULTS)
    sections = ([block_styles(ids), block_header(ids, header)]
                + [BLOCKS[b["type"]](ids, b) for b in page["blocks"]])
    write_json(DIST / f"{page['slug']}.json",
               template(page["title"], "page", sections, PAGE_SETTINGS))
    write_preview(DIST / "preview" / f"{page['slug']}.html", page["title"], sections)

    # one standalone file per block variant (first occurrence wins)
    for b in [STYLES_BLOCK, header] + page["blocks"]:
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
PREVIEW_SRC = {}  # element id -> stand-in image used only by the HTML preview
PREVIEW_ICON = '<svg viewBox="0 0 24 24" width="1em" height="1em"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg>'
PREVIEW_CALENDAR = ('<svg viewBox="0 0 448 512" width="1em" height="1em"><path d="M0 464c0 26.5 21.5 48 48 48h352'
                    'c26.5 0 48-21.5 48-48V192H0v272zm320-196c0-6.6 5.4-12 12-12h40c6.6 0 12 5.4 12 12v40c0 6.6-5.4 12-12 12h-40'
                    'c-6.6 0-12-5.4-12-12v-40zm0 128c0-6.6 5.4-12 12-12h40c6.6 0 12 5.4 12 12v40c0 6.6-5.4 12-12 12h-40'
                    'c-6.6 0-12-5.4-12-12v-40zM192 268c0-6.6 5.4-12 12-12h40c6.6 0 12 5.4 12 12v40c0 6.6-5.4 12-12 12h-40'
                    'c-6.6 0-12-5.4-12-12v-40zm0 128c0-6.6 5.4-12 12-12h40c6.6 0 12 5.4 12 12v40c0 6.6-5.4 12-12 12h-40'
                    'c-6.6 0-12-5.4-12-12v-40zM64 268c0-6.6 5.4-12 12-12h40c6.6 0 12 5.4 12 12v40c0 6.6-5.4 12-12 12H76'
                    'c-6.6 0-12-5.4-12-12v-40zm0 128c0-6.6 5.4-12 12-12h40c6.6 0 12 5.4 12 12v40c0 6.6-5.4 12-12 12H76'
                    'c-6.6 0-12-5.4-12-12v-40zM400 64h-48V16c0-8.8-7.2-16-16-16h-32c-8.8 0-16 7.2-16 16v48H160V16'
                    'c0-8.8-7.2-16-16-16h-32c-8.8 0-16 7.2-16 16v48H48C21.5 64 0 85.5 0 112v48h448v-48c0-26.5-21.5-48-48-48z"/></svg>')


def render(el):
    s = el["settings"]
    if el["elType"] == "section":
        style = []
        if s.get("padding"):
            p = s["padding"]
            style.append(f"padding:{p['top']}px {p['right']}px {p['bottom']}px {p['left']}px")
        bg_url = s.get("background_image", {}).get("url")
        if not bg_url and "pes-hero" in s.get("css_classes", ""):
            bg_url = "img/hero.jpg"  # preview stand-ins only
        if not bg_url and "pes-band" in s.get("css_classes", ""):
            bg_url = "img/band.jpg"
        if bg_url:
            style.append(f"background-image:url({bg_url});background-size:cover;background-position:center")
        overlay = ""
        if s.get("background_overlay_background") == "classic":
            overlay = f'<div class="elementor-background-overlay" style="background:{s["background_overlay_color"]}"></div>'
        elif s.get("background_overlay_background"):
            overlay = '<div class="elementor-background-overlay"></div>'
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
        center += " elementor-hidden-mobile" if s.get("hide_mobile") else ""
        center += " pv-half-mobile" if s.get("_inline_size_mobile") == 50 else ""
        kids = "".join(render(c) for c in el["elements"])
        bg = s.get("background_image", {}).get("url") or PREVIEW_SRC.get(el["id"])
        wrap_style = f' style="background:url({bg}) center/cover"' if bg else ""
        return (f'<div class="elementor-column elementor-element{center} {s.get("css_classes", "")}" '
                f'style="width:{s["_inline_size"]}%"><div class="elementor-widget-wrap elementor-element-populated"{wrap_style}>'
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
            src = (s.get("image", {}).get("url") or PREVIEW_SRC.get(el["id"])
                   or (PREVIEW_IMAGES.pop(0) if PREVIEW_IMAGES else ""))
        body = f'<img src="{src}" alt="">'
    elif kind == "icon-box":
        extra = f" elementor-position-{s['position']} elementor-view-default"
        icon_svg = PREVIEW_CALENDAR if "calendar" in s["selected_icon"]["value"] else PREVIEW_ICON
        title = (f'<{s["title_size"]} class="elementor-icon-box-title"><span>{s["title_text"]}</span>'
                 f'</{s["title_size"]}>' if s["title_text"] else "")
        body = (f'<div class="elementor-icon-box-wrapper"><div class="elementor-icon-box-icon">'
                f'<span class="elementor-icon">{icon_svg}</span></div>'
                f'<div class="elementor-icon-box-content">{title}'
                f'<p class="elementor-icon-box-description">{s["description_text"]}</p></div></div>')
    elif kind == "video":
        body = (f'<div class="elementor-wrapper elementor-open-inline" style="aspect-ratio:16/9;'
                f'background:url({PREVIEW_SRC.get(el["id"])}) center/cover;display:grid;place-items:center">'
                f'<span style="width:64px;height:64px;border-radius:50%;background:rgba(0,0,0,.55);display:grid;'
                f'place-items:center;color:#fff;font-size:26px">&#9654;</span></div>')
    elif kind == "icon-list":
        body = '<ul class="elementor-icon-list-items">' + "".join(
            f'<li class="elementor-icon-list-item"><span class="elementor-icon-list-icon">'
            f'<svg viewBox="0 0 512 512" width="1em" height="1em"><path d="M173.9 439.4 7.5 273c-10-10-10-26.2 0-36.2l36.2-36.2'
            f'c10-10 26.2-10 36.2 0L192 312.7 432.1 72.6c10-10 26.2-10 36.2 0l36.2 36.2c10 10 10 26.2 0 36.2L210.1 439.4'
            f'c-10 10-26.2 10-36.2 0z"/></svg></span><span class="elementor-icon-list-text">{i["text"]}</span></li>'
            for i in s["icon_list"]) + "</ul>"
    elif kind == "accordion":
        body = '<div class="elementor-accordion">' + "".join(
            f'<div class="elementor-accordion-item"><div class="elementor-tab-title{" elementor-active" if n == 0 else ""}">'
            f'<span class="elementor-accordion-icon elementor-accordion-icon-left">'
            f'<span class="elementor-accordion-icon-{"opened" if n == 0 else "closed"}">{"&minus;" if n == 0 else "+"}</span></span>'
            f'<a class="elementor-accordion-title" href="#">{t["tab_title"]}</a></div>'
            f'<div class="elementor-tab-content" style="display:{"block" if n == 0 else "none"}">{t["tab_content"]}</div></div>'
            for n, t in enumerate(s["tabs"])) + "</div>"
    elif kind == "shortcode":
        body = (f'<div class="elementor-shortcode"><div style="padding:40px;text-align:center;color:#999;'
                f'border:1px dashed #555">Google reviews from {html.escape(s["shortcode"])} appear here</div></div>')
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
.elementor-icon-list-items{list-style:none;margin:0;padding:0}
.elementor-icon-list-item{display:flex;align-items:center}
.elementor-column-gap-narrow>.elementor-column>.elementor-element-populated{padding:5px}
.pes-logo img{height:44px;width:auto}
@media(max-width:767px){.elementor-container{flex-wrap:wrap}.elementor-column{width:100%!important}
.elementor-column.pv-half-mobile{width:50%!important}.elementor-hidden-mobile{display:none!important}}
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
