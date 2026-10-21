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
import base64
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


def frame_classes(b, default="orange"):
    """CSS classes for a framed image/video: orange-gradient line, or navy with "frame": "blue"."""
    return "pes-frame" + (" pes-frame-blue" if b.get("frame", default) == "blue" else "")


def fa(fa_class):
    library = "fa-regular" if fa_class.startswith("far ") else "fa-solid"
    return {"value": fa_class, "library": library}


def icon_box(ids, fa_class, classes, title="", description="", position="top", title_tag="h3", link=""):
    extra = {"link": {"url": link, "is_external": "", "nofollow": "", "custom_attributes": ""}} if link else {}
    return widget(ids, "icon-box", classes, **extra, selected_icon=fa(fa_class), view="default",
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
    ] + ([heading(ids, b["note"], "p", "pes-hero-note")] if b.get("note") else [])
    btns = [button(ids, b["button"])] if b.get("button") else []
    if b.get("button2"):
        btns.append(button(ids, b["button2"], "pes-btn"))
    if len(btns) > 1:  # side by side
        for w in btns:
            w["settings"]["_css_classes"] += " pes-btn-inline"
            w["settings"]["_element_width"] = "auto"
    widgets += btns
    tall = b.get("height", 680 if centered else 640)
    return section(
        ids,
        [column(ids, 100, widgets)],
        "pes-section pes-hero" + (" pes-hero-center" if centered else ""),
        title="Hero",
        height="min-height",
        custom_height=px(tall),
        custom_height_mobile=px(min(tall, 560 if centered else 520)),
        column_position="middle",
        padding=box(80, 0, 80, 0),
        **overlay,
        **bg,
    )


def block_feature(ids, b):
    reverse = b.get("layout") == "image-left"
    frame = frame_classes(b)
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
        gap="wider",
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
    media = column(ids, 45, [video(ids, b.get("video"), frame_classes(b, "blue"), "img/video.jpg")]
                   + ([button(ids, b["button"], "pes-btn pes-align-center")] if b.get("button") else []),
                   content_position="center")
    return section(ids, [copy, media], "pes-section pes-feature", title="Intro – What is it",
                   gap="wider", structure="20", column_position="middle",
                   padding=box(110, 0, 110, 0), padding_mobile=box(70, 0, 70, 0))


def block_band(ids, b):
    """'Why it matters' – centred statement over a darkened photo, gradient lines top and bottom."""
    return section(ids, [column(ids, 100, [
        heading(ids, b["kicker"], "p", "pes-eyebrow pes-center"),
        heading(ids, two_tone(b["title"], b.get("accent")), "h2", "pes-h2 pes-h2-mixed pes-center"),
        text(ids, b["text"], "pes-lead pes-center"),
    ] + ([button(ids, b["button"], "pes-btn-solid pes-align-center")] if b.get("button") else []))],
        "pes-section pes-band", title=b.get("label", "Problem band – Why it matters"),
        column_position="middle", padding=box(110, 0, 110, 0), padding_mobile=box(80, 0, 80, 0),
        **bg_image(b.get("image")))


def block_benefits(ids, b):
    """Key benefits – framed photo | kicker, two-tone heading, text, checklist, CTA."""
    frame = frame_classes(b)
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
                   gap="wider", structure="20", column_position="middle",
                   padding=box(110, 0, 110, 0), padding_mobile=box(70, 0, 70, 0))


def block_media(ids, b):
    """Punch line – two-tone heading + paragraph | framed video."""
    copy = column(ids, 48, ([heading(ids, b["kicker"], "p", "pes-eyebrow")] if b.get("kicker") else []) + [
        heading(ids, two_tone(b["title"], b.get("accent")), "h2", "pes-h2"),
        text(ids, b["text"]),
    ] + ([button(ids, b["button"], "pes-btn pes-btn-more")] if b.get("button") else []),
        content_position="center")
    media = column(ids, 52, [video(ids, b.get("video"), frame_classes(b), "img/video.jpg")], content_position="center")
    return section(ids, [copy, media], "pes-section pes-feature", title=b.get("label", "Punch line + video"),
                   gap="wider", structure="20", column_position="middle",
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
    per = b.get("per_row", n)
    if per < n:
        for c in cards:
            c["settings"]["_inline_size"] = round(100 / per, 3)
    rows = [section(ids, cards[i:i + per], "pes-audience", inner=True, gap="narrow", structure=f"{min(per, n - i)}0")
            for i in range(0, n, per)]
    return section(ids, [column(ids, 100, [
        heading(ids, b["kicker"], "p", "pes-eyebrow pes-center"),
        heading(ids, b["title"], "h2", "pes-h2 pes-h2-mixed pes-center"),
    ] + rows)], "pes-section", title="Who it's for", padding=box(100, 0, 110, 0))


def block_contact_cards(ids, b):
    """Call / Visit / Email cards – each whole card is a link (tel:, map, mailto:)."""
    n = len(b["cards"])
    cols = [column(ids, round(100 / n, 3),
                   [icon_box(ids, c["icon"], "pes-contact-card", c["title"], c["text"], link=c.get("url", ""))])
            for c in b["cards"]]
    return section(ids, cols, "pes-section pes-contact-cards", title="Contact cards",
                   gap="extended", structure=f"{n}0", padding=box(70, 0, 40, 0))


def block_form(ids, b):
    """Text + checklist | a panel holding an HTML widget for the GoHighLevel form embed."""
    copy = column(ids, 42, [
        heading(ids, b["kicker"], "p", "pes-eyebrow"),
        heading(ids, two_tone(b["title"], b.get("accent")), "h2", "pes-h2"),
        text(ids, b["text"]),
        heading(ids, b["list_title"], "h3", "pes-subhead"),
        icon_list(ids, b["items"], "pes-checklist"),
    ] + ([heading(ids, b["note"], "p", "pes-hero-note pes-note-left")] if b.get("note") else []),
        content_position="center")
    placeholder = ('<!-- PASTE YOUR GOHIGHLEVEL FORM EMBED CODE HERE (replace this whole box) -->\n'
                   '<div class="pes-form-placeholder">GoHighLevel form goes here<br>'
                   '<small>Edit this HTML widget and paste the embed code from GoHighLevel</small></div>')
    form = column(ids, 58, [widget(ids, "html", "pes-form-embed", html=placeholder)], "pes-form-panel",
                  content_position="center")
    return section(ids, [copy, form], "pes-section pes-feature", title="Form – GoHighLevel embed",
                   _element_id="book-appointment",
                   gap="wider", structure="20", column_position="middle",
                   padding=box(90, 0, 100, 0), padding_mobile=box(60, 0, 70, 0))


def block_map(ids, b):
    w = widget(ids, "google_maps", "pes-frame pes-map", address=b["address"], zoom=px(b.get("zoom", 12)),
               height=px(420), prevent_scroll="yes")
    return section(ids, [column(ids, 100, [
        heading(ids, b["kicker"], "p", "pes-eyebrow pes-center"),
        heading(ids, two_tone(b["title"], b.get("accent")), "h2", "pes-h2 pes-h2-mixed pes-center"),
        text(ids, b["text"], "pes-lead pes-center"),
        w,
    ] + ([button(ids, b["button"], "pes-btn pes-btn-more pes-align-center")] if b.get("button") else []))],
        "pes-section", title="Map – Visit us", padding=box(80, 0, 100, 0))


def section_intro(ids, b):
    """Centred eyebrow + heading (+ optional lead) used at the top of grid sections."""
    out = [heading(ids, b["kicker"], "p", "pes-eyebrow pes-center"),
           heading(ids, two_tone(b["title"], b.get("accent")), "h2", "pes-h2 pes-h2-mixed pes-center")]
    if b.get("text"):
        out.append(text(ids, b["text"], "pes-lead pes-center"))
    return out


def card_grid(ids, cols, gap="extended"):
    n = len(cols)
    return section(ids, cols, "pes-card-grid", inner=True, gap=gap, structure=f"{n}0")


def block_why_split(ids, b):
    """Why choose us – heading and stacked call-out boxes on the left, framed photo on the right."""
    boxes = [icon_box(ids, c["icon"], "pes-why-row", c["title"], c["text"], position="left", title_tag="h3")
             for c in b["cards"]]
    copy = column(ids, 55, [heading(ids, b["kicker"], "p", "pes-eyebrow"),
                            heading(ids, two_tone(b["title"], b.get("accent")), "h2", "pes-h2"),
                            text(ids, b["text"])] + boxes
                  + ([button(ids, b["button"], "pes-btn-solid")] if b.get("button") else []),
                  content_position="center")
    media = column(ids, 45, [image(ids, b.get("image"), frame_classes(b), b["title"], "img/video.jpg")],
                   content_position="center")
    return section(ids, [copy, media], "pes-section pes-feature", title="Why choose us",
                   gap="wider", structure="20", column_position="middle",
                   padding=box(110, 0, 110, 0), padding_mobile=box(70, 0, 70, 0))


def block_why(ids, b):
    """Why choose us – icon cards in the angled gradient-border style."""
    cards = [column(ids, round(100 / len(b["cards"]), 3),
                    [icon_box(ids, c["icon"], "pes-contact-card pes-why-card", c["title"], c["text"])])
             for c in b["cards"]]
    tail = [button(ids, b["button"], "pes-btn-solid pes-align-center")] if b.get("button") else []
    return section(ids, [column(ids, 100, section_intro(ids, b) + [card_grid(ids, cards)] + tail)],
                   "pes-section pes-why", title="Why choose us", padding=box(100, 0, 110, 0))


def block_team(ids, b):
    """Team – Elementor Pro Flip Box per person: headshot, name, title; bio on the back."""
    cards = []
    for m in b["members"]:
        img = {"image": {"url": m["image"], "id": "", "source": "library"}} if m.get("image") else {}
        w = widget(ids, "flip-box", "pes-team-card", graphic_element="image", image_size="full", **img,
                   title_text_a=m["name"], description_text_a=m["role"],
                   title_text_b=m["name"], description_text_b=m["bio"],
                   button_text=m.get("button", ""), link={"url": m.get("url", ""), "is_external": "",
                                                          "nofollow": "", "custom_attributes": ""},
                   link_click="button", height=px(480), flip_effect="flip", flip_direction="left",
                   background_a_background="classic", background_a_color="#232121",
                   background_b_background="classic", background_b_color="#121111")
        PREVIEW_SRC[w["id"]] = "img/placeholder.jpg"
        cards.append(column(ids, round(100 / len(b["members"]), 3), [w]))
    return section(ids, [column(ids, 100, section_intro(ids, b) + [card_grid(ids, cards)])],
                   "pes-section pes-team", title="Team", padding=box(100, 0, 110, 0))


def info_card(ids, title, items, btn=None, note=None, width=33.333):
    """Dark card with gradient border: title, gold line, checklist, optional note and button."""
    widgets = [heading(ids, title, "h3", "pes-job-title"), icon_list(ids, items, "pes-checklist pes-card-list")]
    if note:
        widgets.append(text(ids, note, "pes-card-note"))
    if btn:
        widgets.append(button(ids, btn, "pes-btn-solid pes-btn-block"))
    return column(ids, width, widgets, "pes-job-card")


def block_jobs(ids, b):
    """Open positions – one card per role with requirements and an apply button."""
    n = len(b["jobs"])
    cards = [info_card(ids, j["title"], j["items"], j.get("button", b.get("button")), width=round(100 / n, 3))
             for j in b["jobs"]]
    return section(ids, [column(ids, 100, section_intro(ids, b) + [card_grid(ids, cards)])],
                   "pes-section pes-jobs", title=b.get("label", "Open positions"), padding=box(100, 0, 110, 0),
                   _element_id="open-positions")


def block_licenses(ids, b):
    """Licenses – one card per state with what the company is licensed for."""
    n = len(b["states"])
    cards = [info_card(ids, st["state"], st["licenses"], note=st.get("note"), width=round(100 / n, 3))
             for st in b["states"]]
    return section(ids, [column(ids, 100, section_intro(ids, b) + [card_grid(ids, cards)])],
                   "pes-section pes-licenses", title="Licenses", padding=box(100, 0, 60, 0))


def block_areas(ids, b):
    """Service areas – map-pin chips for the main towns / regions."""
    chips = widget(ids, "icon-list", "pes-area-list", view="inline", icon_list=[
        {"_id": ids(), "text": t, "selected_icon": fa("fas fa-map-marker-alt")} for t in b["areas"]])
    tail = [button(ids, b["button"], "pes-btn pes-btn-more pes-align-center")] if b.get("button") else []
    return section(ids, [column(ids, 100, section_intro(ids, b) + [chips] + tail)],
                   "pes-section pes-areas", title="Service areas", padding=box(60, 0, 110, 0))


def block_partners(ids, b):
    """Partners – logos scrolling in a continuous loop (Image Carousel; add logos to its gallery)."""
    logos = [{"id": "", "url": u} for u in b.get("logos", [])]
    w = widget(ids, "image-carousel", "pes-logo-marquee", carousel=logos, thumbnail_size="medium",
               slides_to_show="6", slides_to_show_tablet="4", slides_to_show_mobile="3",
               slides_to_scroll="1", navigation="none", image_stretch="no",
               autoplay="yes", autoplay_speed=0, pause_on_hover="no", pause_on_interaction="no",
               infinite="yes", speed=b.get("speed", 4000), image_spacing="custom",
               image_spacing_custom=px(48))
    PREVIEW_SRC[w["id"]] = len(b.get("logos", [])) or 8
    return section(ids, [column(ids, 100, section_intro(ids, b) + [w])],
                   "pes-section pes-partners", title="Partners – logo scroller", padding=box(60, 0, 60, 0))


def block_service_grid(ids, b):
    """Compact grid of the remaining services – each card links to its service page."""
    cards = [column(ids, round(100 / len(b["services"]), 3),
                    [icon_box(ids, c["icon"], "pes-contact-card pes-why-card pes-service-card",
                              c["title"], c["text"], link=c.get("url", ""))])
             for c in b["services"]]
    tail = [button(ids, b["button"], "pes-btn pes-btn-more pes-align-center")] if b.get("button") else []
    return section(ids, [column(ids, 100, section_intro(ids, b) + [card_grid(ids, cards)] + tail)],
                   "pes-section", title=b.get("label", "More services"), padding=box(40, 0, 100, 0))


TOGGLE_JS = """<script>
(function () {
  function init(root) {
    var sec = root.closest('.pes-energy');
    if (!sec || sec.dataset.pesTabs) return;
    sec.dataset.pesTabs = '1';
    var btns = sec.querySelectorAll('.pes-toggle button');
    btns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        btns.forEach(function (b) { b.classList.toggle('is-active', b === btn); b.setAttribute('aria-selected', b === btn); });
        sec.querySelectorAll('.pes-tab-panel').forEach(function (p) {
          p.classList.toggle('is-active', p.classList.contains('pes-tab-' + btn.dataset.tab));
        });
        update();
      });
    });
    var more = sec.querySelector('.pes-more-toggle');
    function update() {
      if (!more) return;
      var hidden = sec.querySelectorAll('.pes-tab-panel.is-active.pes-tab-more').length;
      more.parentNode.style.display = hidden ? '' : 'none';
    }
    if (more) {
      more.addEventListener('click', function () {
        var open = sec.classList.toggle('is-expanded');
        more.setAttribute('aria-expanded', open);
        more.textContent = open ? more.dataset.less : more.dataset.more;
      });
    }
    update();
  }
  function run() { document.querySelectorAll('.pes-toggle').forEach(init); }
  // wait for the whole section (the See All button comes after this script)
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
  window.addEventListener('elementor/frontend/init', run);
})();
</script>"""


def service_card(ids, c, width):
    """Image, title, description; the title link stretches over the whole card."""
    link = {"url": c.get("url", ""), "is_external": "", "nofollow": "", "custom_attributes": ""}
    img = image(ids, c.get("image"), "pes-svc-img", c["title"], c.get("preview"))
    title = widget(ids, "heading", "pes-svc-title", title=c["title"], header_size="h3", link=link)
    return column(ids, width, [img, title, text(ids, c["text"], "pes-svc-text"),
                               heading(ids, "Learn More", "span", "pes-svc-more")], "pes-svc-card")


def block_energy_tabs(ids, b):
    """Energy management – toggle between two groups of linked service cards."""
    tabs = b["tabs"]
    btns = "".join(
        f'<button type="button" role="tab" data-tab="{t["key"]}" aria-selected="{"true" if i == 0 else "false"}"'
        f'{" class=\"is-active\"" if i == 0 else ""}>{t["label"]}</button>' for i, t in enumerate(tabs))
    toggle = widget(ids, "html", "pes-toggle-widget",
                    html=f'<div class="pes-toggle" role="tablist">{btns}</div>\n{TOGGLE_JS}')
    per = b.get("per_row", 3)
    panels = []
    for i, t in enumerate(tabs):
        cards = t["cards"]
        active = " is-active" if i == 0 else ""
        for r in range(0, len(cards), per):
            row = cards[r:r + per]
            more = " pes-tab-more" if r else ""
            label = f"Toggle – {t['label']} – " + ("featured" if not r else "more (shown by See All Services)")
            panels.append(section(ids, [service_card(ids, c, round(100 / per, 3)) for c in row],
                                  f'pes-tab-panel pes-tab-{t["key"]}{more}{active}', inner=True, title=label,
                                  gap="extended", structure=f"{len(row)}0"))
    more_btn = widget(ids, "html", "pes-more-widget", html=(
        '<div class="pes-more-wrap"><button type="button" class="pes-more-toggle" aria-expanded="false" '
        f'data-more="{b.get("more_label", "See All Services")}" data-less="{b.get("less_label", "Show Fewer Services")}">'
        f'{b.get("more_label", "See All Services")}</button></div>'))
    return section(ids, [column(ids, 100, section_intro(ids, b) + [toggle] + panels + [more_btn])],
                   "pes-section pes-energy", title="Energy management – Solutions / O&M toggle",
                   padding=box(100, 0, 110, 0))


def block_projects(ids, b):
    """Featured projects – photo, name, size and location, See Full Details."""
    cards = []
    for i, pr in enumerate(b["projects"]):
        img = image(ids, pr.get("image"), "pes-project-img", pr["title"],
                    ["img/frame-1.jpg", "img/frame-2.jpg", "img/frame-3.jpg"][i % 3])
        cards.append(column(ids, round(100 / len(b["projects"]), 3), [
            img,
            heading(ids, pr["title"], "h3", "pes-job-title"),
            text(ids, pr["meta"], "pes-card-note"),
            button(ids, {"text": "See Full Details", "url": pr.get("url", b.get("url", "/our-projects/"))},
                   "pes-btn pes-btn-more"),
        ], "pes-job-card pes-project-card"))
    tail = [button(ids, b["button"], "pes-btn-solid pes-align-center")] if b.get("button") else []
    return section(ids, [column(ids, 100, section_intro(ids, b) + [card_grid(ids, cards)] + tail)],
                   "pes-section", title="Featured projects", padding=box(100, 0, 110, 0))


FILTER_JS = """<script>
(function () {
  function init(bar) {
    if (bar.dataset.pesReady) return;
    bar.dataset.pesReady = '1';
    var sec = bar.closest('.pes-projects');
    bar.querySelectorAll('button').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var f = btn.dataset.filter;
        bar.querySelectorAll('button').forEach(function (b) {
          b.classList.toggle('is-active', b === btn); b.setAttribute('aria-pressed', b === btn);
        });
        sec.querySelectorAll('.pes-proj-card').forEach(function (card) {
          var show = f === 'all' || card.classList.contains('pes-cat-' + f);
          card.classList.toggle('is-hidden', !show);
        });
      });
    });
  }
  function run() { document.querySelectorAll('.pes-filter').forEach(init); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
  window.addEventListener('elementor/frontend/init', run);
})();
</script>"""


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def project_card(ids, pr, cats, k):
    """Photo gallery (first photo shows, click opens all in the lightbox), category, title,
    short line, and a See Project Details toggle with size / location / description."""
    cat = pr["category"]
    pics = pr.get("images") or []
    gallery = widget(ids, "image-gallery", "pes-proj-gallery",
                     wp_gallery=[{"id": "", "url": u} for u in pics], thumbnail_size="large",
                     gallery_columns="1", gallery_link="file", open_lightbox="yes", gallery_rand="")
    PREVIEW_SRC[gallery["id"]] = pr.get("preview", [])
    details = (f'<ul class="pes-proj-facts"><li><strong>Size:</strong> {pr["size"]}</li>'
               f'<li><strong>Location:</strong> {pr["location"]}</li></ul><p>{pr["description"]}</p>')
    toggle = widget(ids, "toggle", "pes-proj-toggle", tabs=[{"_id": ids(), "tab_title": "See Project Details",
                    "tab_content": details}], selected_icon=fa("fas fa-chevron-down"),
                    selected_active_icon=fa("fas fa-chevron-up"), icon_align="right", title_html_tag="div")
    return column(ids, 33.333, [
        gallery,
        heading(ids, cats[cat], "p", "pes-proj-cat"),
        heading(ids, pr["title"], "h3", "pes-proj-title"),
        text(ids, pr["summary"], "pes-proj-summary"),
        toggle,
    ], f"pes-proj-card pes-cat-{cat}")


def block_project_gallery(ids, b):
    """Projects page – category filter bar over a grid of project cards (rows of three)."""
    cats = {c["key"]: c["label"] for c in b["categories"]}
    btns = '<button type="button" class="is-active" data-filter="all" aria-pressed="true">All</button>' + "".join(
        f'<button type="button" data-filter="{c["key"]}" aria-pressed="false">{c["label"]}</button>'
        for c in b["categories"])
    bar = widget(ids, "html", "pes-filter-widget", html=f'<div class="pes-filter" role="group" aria-label="Filter projects">{btns}</div>\n{FILTER_JS}')
    cards = [project_card(ids, pr, cats, k) for k, pr in enumerate(b["projects"])]
    rows = [section(ids, cards[i:i + 3], "pes-proj-row", inner=True, gap="extended", structure=f"{len(cards[i:i + 3])}0",
                    title="Projects row (3 cards)") for i in range(0, len(cards), 3)]
    return section(ids, [column(ids, 100, section_intro(ids, b) + [bar] + rows, "pes-proj-grid")],
                   "pes-section pes-projects", title="Projects – filter + cards", padding=box(90, 0, 110, 0))


def block_posts(ids, b):
    """Latest blog posts – Elementor Pro Posts widget, pulls the newest posts automatically."""
    w = widget(ids, "posts", "pes-posts", _skin="classic", classic_columns="3", classic_columns_mobile="1",
               classic_posts_per_page=b.get("count", 3), classic_thumbnail="top", classic_title_tag="h3",
               classic_excerpt_length=20, classic_meta_data=["date"], classic_read_more_text="Read More",
               classic_show_read_more="yes", posts_post_type="post")
    tail = [button(ids, b["button"], "pes-btn pes-btn-more pes-align-center")] if b.get("button") else []
    return section(ids, [column(ids, 100, section_intro(ids, b) + [w] + tail)],
                   "pes-section", title="Latest from the blog", padding=box(100, 0, 110, 0))


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
            column(ids, 16, [image(ids, b.get("logo"), "pes-logo", "Porter Energy Systems"),
                             widget(ids, "html", "pes-header-styles",
                                    html=f"<style>\n{header_css()}\n</style>")],
                   content_position="center", _inline_size_tablet=30, _inline_size_mobile=42),
            # Elementor Pro Nav Menu: full menu on desktop, hamburger + dropdown on tablet and phone.
            # It shows the site's first menu until another one is picked in the widget.
            column(ids, 62, [widget(ids, "nav-menu", "pes-nav", layout="horizontal", pointer="none",
                                    submenu_icon=fa("fas fa-chevron-down"), dropdown="tablet",
                                    toggle="burger", toggle_align="right", full_width="",
                                    text_align="aside")],
                   "pes-nav-col", content_position="center", _inline_size_tablet=20, _inline_size_mobile=18),
            column(ids, 22, [button(ids, b["button"], "pes-btn-solid pes-align-right")],
                   "pes-header-cta", _inline_size_tablet=50, _inline_size_mobile=40),
        ],
        "pes-header",
        title="Header",
        layout="full_width",
        structure="30",
        column_position="middle",
        padding=box(6, 40, 6, 40),
        padding_mobile=box(6, 12, 6, 12),
    )


HEADER_KEYS = ("pes-header", "pes-nav", "pes-logo", "pes-btn-solid", "pes-align-right",
               "elementor-location-header", ":is(.pes-btn, .pes-btn-solid")


def header_css():
    """Only the header's rules (plus the colour variables), so the header template is
    self-contained: it looks right even if Site Settings holds an older stylesheet."""
    css = re.sub(r"/\*.*?\*/", "", CSS_FILE.read_text(), flags=re.S)
    css = re.sub(r"@import url\([^)]*\);", "", css)
    out, i = [], 0

    def rules(text):  # split top-level "selector { body }" chunks
        chunks, depth, start = [], 0, 0
        for j, ch in enumerate(text):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    chunks.append(text[start:j + 1].strip())
                    start = j + 1
        return chunks

    for chunk in rules(css):
        head = chunk[:chunk.index("{")]
        if head.strip().startswith("@media"):
            inner = [r for r in rules(chunk[chunk.index("{") + 1:-1])
                     if any(k in r[:r.index("{")] for k in HEADER_KEYS) or r.startswith(":root")]
            if inner:
                out.append(head.strip() + " {\n" + "\n".join(inner) + "\n}")
        elif head.strip() == ":root" or any(k in head for k in HEADER_KEYS):
            out.append(chunk)
    return "\n".join(out)


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
    "contact_cards": block_contact_cards,
    "why": block_why,
    "why_split": block_why_split,
    "partners": block_partners,
    "energy_tabs": block_energy_tabs,
    "service_grid": block_service_grid,
    "projects": block_projects,
    "posts": block_posts,
    "project_gallery": block_project_gallery,
    "team": block_team,
    "jobs": block_jobs,
    "licenses": block_licenses,
    "areas": block_areas,
    "form": block_form,
    "map": block_map,
    "cta": block_cta,
    "header": block_header,
}

STYLES_BLOCK = {"type": "styles"}
HEADER_DEFAULTS = {"type": "header", "logo": "",
                   "button": {"text": "Book An Appointment", "url": "/contact-us/#book-appointment"}}


def block_name(b):
    if b["type"] == "feature":
        return f"pes-feature-{b.get('layout', 'image-right')}"
    if b["type"] == "hero" and b.get("align") == "center":
        return "pes-hero-center"
    if b["type"] == "process" and len(b["steps"]) != 3:
        return f"pes-process-{len(b['steps'])}-steps"
    return f"pes-{b['type'].replace('_', '-')}"


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
    "background_color": "#1B1A1A",
}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print("wrote", path.relative_to(ROOT.parent))


def build(content_path, seen_blocks):
    page = json.loads(Path(content_path).read_text())
    ids = Ids(page["slug"])
    header = page.get("header", HEADER_DEFAULTS)
    content = []
    for b in page["blocks"]:
        sec = BLOCKS[b["type"]](ids, b)
        if b.get("divider"):
            sec["settings"]["css_classes"] = (sec["settings"].get("css_classes", "") + " pes-divider").strip()
        content.append(sec)
    # The page template holds only the page's own content: the styles live in
    # Site Settings > Custom CSS and the header is the site-wide Theme Builder header.
    write_json(DIST / f"{page['slug']}.json",
               template(page["title"], "page", content, PAGE_SETTINGS))
    # The preview shows the page as it appears on the site, header and styles included.
    write_preview(DIST / "preview" / f"{page['slug']}.html", page["title"],
                  [block_styles(ids), block_header(ids, header)] + content)

    # one standalone file per block variant (first occurrence wins)
    for b in [STYLES_BLOCK, header] + page["blocks"]:
        name = block_name(b)
        if name in seen_blocks:
            continue
        seen_blocks.add(name)
        title = "PES – " + name[4:].replace("-", " ").title()
        write_json(DIST / "blocks" / f"{name}.json",
                   template(title, "section", [BLOCKS[b["type"]](Ids("block:" + name), b)]))


# ---------------------------------------------------------------------------
# Preview: renders the same element tree with Elementor-like markup so the
# CSS can be checked in a browser without WordPress. Approximate only.
# ---------------------------------------------------------------------------
PREVIEW_MENU = ["Solution", "Service O&amp;M", "Projects", "Company", "Contact Us", "Industry"]
PREVIEW_SUBMENUS = {
    "Solution": ["Commercial Solar", "Battery Energy Storage", "EV Charging", "Electrical"],
    "Service O&amp;M": ["Operations &amp; Maintenance", "Monitoring", "Repairs"],
    "Industry": ["Agriculture", "Municipal", "Commercial Real Estate"],
}
PREVIEW_ICONS = {
    "phone": '<svg viewBox="0 0 24 24" width="1em" height="1em"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1z"/></svg>',
    "map": '<svg viewBox="0 0 24 24" width="1em" height="1em"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z"/></svg>',
    "envelope": '<svg viewBox="0 0 24 24" width="1em" height="1em"><path d="M2 5h20v14H2zm2 2v.5l8 5 8-5V7l-8 5z"/></svg>',
}
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
        inner = (f'<a href="{html.escape(s["link"]["url"])}">{s["title"]}</a>' if s.get("link", {}).get("url")
                 else s["title"])
        body = f'<{tag} class="elementor-heading-title">{inner}</{tag}>'
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
                   or (PREVIEW_IMAGES.pop(0) if PREVIEW_IMAGES else "img/placeholder.jpg"))
        body = f'<img src="{src}" alt="">'
    elif kind == "icon-box":
        extra = f" elementor-position-{s['position']} elementor-view-default"
        v = s["selected_icon"]["value"]
        icon_svg = next((svg for k, svg in PREVIEW_ICONS.items() if k in v),
                        PREVIEW_CALENDAR if "calendar" in v else PREVIEW_ICON)
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
        inline = " elementor-inline-items" if s.get("view") == "inline" else ""
        extra = " elementor-icon-list--layout-inline" if inline else ""
        pin = "map" in (s["icon_list"][0]["selected_icon"]["value"] if s["icon_list"] else "")
        body = f'<ul class="elementor-icon-list-items{inline}">' + "".join(
            f'<li class="elementor-icon-list-item"><span class="elementor-icon-list-icon">'
            f'<svg viewBox="0 0 512 512" width="1em" height="1em"><path d="M173.9 439.4 7.5 273c-10-10-10-26.2 0-36.2l36.2-36.2'
            f'c10-10 26.2-10 36.2 0L192 312.7 432.1 72.6c10-10 26.2-10 36.2 0l36.2 36.2c10 10 10 26.2 0 36.2L210.1 439.4'
            f'c-10 10-26.2 10-36.2 0z"/></svg></span><span class="elementor-icon-list-text">{i["text"]}</span></li>'
            if not pin else
            f'<li class="elementor-icon-list-item"><span class="elementor-icon-list-icon">{PREVIEW_ICONS["map"]}</span>'
            f'<span class="elementor-icon-list-text">{i["text"]}</span></li>'
            for i in s["icon_list"]) + "</ul>"
    elif kind == "accordion":
        body = '<div class="elementor-accordion">' + "".join(
            f'<div class="elementor-accordion-item"><div class="elementor-tab-title{" elementor-active" if n == 0 else ""}">'
            f'<span class="elementor-accordion-icon elementor-accordion-icon-left">'
            f'<span class="elementor-accordion-icon-{"opened" if n == 0 else "closed"}">{"&minus;" if n == 0 else "+"}</span></span>'
            f'<a class="elementor-accordion-title" href="#">{t["tab_title"]}</a></div>'
            f'<div class="elementor-tab-content" style="display:{"block" if n == 0 else "none"}">{t["tab_content"]}</div></div>'
            for n, t in enumerate(s["tabs"])) + "</div>"
    elif kind == "image-gallery":
        pics = [p["url"] for p in s.get("wp_gallery", [])] or PREVIEW_SRC.get(el["id"]) or ["img/placeholder.jpg"]
        body = '<div class="gallery">' + "".join(
            f'<figure class="gallery-item"><div class="gallery-icon"><a href="{u}" data-elementor-open-lightbox="yes">'
            f'<img src="{u}" alt=""></a></div></figure>' for u in pics) + '</div>'
    elif kind == "toggle":
        t = s["tabs"][0]
        body = (f'<div class="elementor-toggle"><div class="elementor-toggle-item">'
                f'<div class="elementor-tab-title" onclick="this.classList.toggle(\'elementor-active\');'
                f'this.nextElementSibling.style.display=this.classList.contains(\'elementor-active\')?\'block\':\'none\'">'
                f'<span class="elementor-toggle-icon elementor-toggle-icon-right"><span class="elementor-toggle-icon-closed">&#9662;</span></span>'
                f'<a class="elementor-toggle-title" href="#" onclick="return false">{t["tab_title"]}</a></div>'
                f'<div class="elementor-tab-content" style="display:none">{t["tab_content"]}</div></div></div>')
    elif kind == "image-carousel":
        n = PREVIEW_SRC.get(el["id"], 8) if isinstance(PREVIEW_SRC.get(el["id"]), int) else 8
        logo = ('<div class="pv-logo">PARTNER {k}</div>')
        items = "".join(logo.format(k=k % n + 1) for k in range(n * 2))
        body = f'<div class="pv-marquee"><div class="pv-marquee-track">{items}</div></div>'
    elif kind == "posts":
        cards = "".join(
            f'<article class="elementor-post"><a class="elementor-post__thumbnail__link" href="#"><div class="elementor-post__thumbnail">'
            f'<img src="img/frame-{k}.jpg" alt=""></div></a><div class="elementor-post__text">'
            f'<h3 class="elementor-post__title"><a href="#">Blog post title number {k} goes here</a></h3>'
            f'<div class="elementor-post__meta-data"><span class="elementor-post-date">October {k}, 2026</span></div>'
            f'<div class="elementor-post__excerpt"><p>The first lines of the post appear here automatically as a short excerpt…</p></div>'
            f'<a class="elementor-post__read-more" href="#">Read More</a></div></article>' for k in (1, 2, 3))
        body = f'<div class="elementor-posts-container elementor-posts elementor-grid">{cards}</div>'
    elif kind == "flip-box":
        src = s.get("image", {}).get("url") or PREVIEW_SRC.get(el["id"], "")
        btn = (f'<a class="elementor-flip-box__button elementor-button" href="#">{s["button_text"]}</a>'
               if s.get("button_text") else "")
        body = ('<div class="elementor-flip-box" tabindex="0">'
                '<div class="elementor-flip-box__layer elementor-flip-box__front"><div class="elementor-flip-box__layer__overlay">'
                f'<div class="elementor-flip-box__layer__inner"><div class="elementor-flip-box__image"><img src="{src}" alt=""></div>'
                f'<h3 class="elementor-flip-box__layer__title">{s["title_text_a"]}</h3>'
                f'<div class="elementor-flip-box__layer__description">{s["description_text_a"]}</div></div></div></div>'
                '<div class="elementor-flip-box__layer elementor-flip-box__back"><div class="elementor-flip-box__layer__overlay">'
                f'<div class="elementor-flip-box__layer__inner"><h3 class="elementor-flip-box__layer__title">{s["title_text_b"]}</h3>'
                f'<div class="elementor-flip-box__layer__description">{s["description_text_b"]}</div>{btn}</div></div></div></div>')
        extra = " elementor-flip-box--effect-flip elementor-flip-box--direction-left"
    elif kind == "google_maps":
        q = html.escape(s["address"])
        body = (f'<div class="elementor-custom-embed"><div style="height:{s["height"]["size"]}px;display:grid;place-items:center;'
                f'background:#2b2b2d;color:#bbb;font:15px sans-serif;text-align:center">Google Map<br>{q}</div></div>')
    elif kind == "shortcode":
        body = (f'<div class="elementor-shortcode"><div style="padding:40px;text-align:center;color:#999;'
                f'border:1px dashed #555">Google reviews from {html.escape(s["shortcode"])} appear here</div></div>')
    elif kind == "nav-menu":
        extra = " elementor-nav-menu--dropdown-tablet elementor-nav-menu__text-align-aside elementor-nav-menu--toggle elementor-nav-menu--burger"
        def items(sub_class):
            out = ""
            for name in PREVIEW_MENU:
                subs = PREVIEW_SUBMENUS.get(name)
                arrow = '<span class="sub-arrow"><i class="pv-chev"></i></span>' if subs else ""
                link = f'<a href="#" class="{"elementor-item" if not sub_class else "elementor-item"}{" has-submenu" if subs else ""}">{name}{arrow}</a>'
                sub = ""
                if subs:
                    sub = '<ul class="sub-menu elementor-nav-menu--dropdown">' + "".join(
                        f'<li class="menu-item"><a href="#" class="elementor-sub-item">{x}</a></li>' for x in subs) + "</ul>"
                out += f'<li class="menu-item{" menu-item-has-children" if subs else ""}">{link}{sub}</li>'
            return out
        body = ('<nav class="elementor-nav-menu--main elementor-nav-menu__container elementor-nav-menu--layout-horizontal e--pointer-none">'
                f'<ul class="elementor-nav-menu">{items("")}</ul></nav>'
                '<div class="elementor-menu-toggle" role="button" tabindex="0" aria-label="Menu" '
                'onclick="this.classList.toggle(\'elementor-active\')"><span class="pv-burger">&#9776;</span></div>'
                '<nav class="elementor-nav-menu--dropdown elementor-nav-menu__container">'
                f'<ul class="elementor-nav-menu">{items("sub")}</ul></nav>')
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
.elementor-column-gap-wider>.elementor-column>.elementor-element-populated{padding:30px}
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
.elementor-flip-box{position:relative;height:480px;perspective:1000px}
.elementor-flip-box__layer{position:absolute;inset:0;transition:transform .6s;backface-visibility:hidden;transform-style:preserve-3d}
.elementor-flip-box__layer__overlay{display:flex;height:100%;align-items:center;justify-content:center;text-align:center}
.elementor-flip-box__back{transform:rotateY(180deg)}
.elementor-flip-box:hover .elementor-flip-box__front{transform:rotateY(-180deg)}
.elementor-flip-box:hover .elementor-flip-box__back{transform:none}
.elementor-inline-items{display:flex;flex-wrap:wrap}
.pv-marquee{overflow:hidden}.pv-marquee-track{display:flex;gap:48px;width:max-content;animation:pvm 30s linear infinite}
.pv-logo{width:150px;height:70px;display:grid;place-items:center;border:1px dashed #666;color:#999;font:600 13px sans-serif}
@keyframes pvm{to{transform:translateX(-50%)}}
.elementor-posts{display:grid;grid-template-columns:repeat(3,1fr);gap:30px}
.elementor-post__thumbnail img{width:100%;display:block}
.elementor-widget-wrap>.elementor-element.pes-btn-inline{width:auto}
@media(max-width:767px){.elementor-posts{grid-template-columns:1fr}}
.elementor-column-gap-narrow>.elementor-column>.elementor-element-populated{padding:5px}
.pes-logo img{height:44px;width:auto}
.elementor-nav-menu{display:flex;flex-wrap:wrap;list-style:none;margin:0;padding:0}
.elementor-nav-menu li{position:relative}
.elementor-nav-menu--main .sub-menu{display:none;position:absolute;top:100%;left:0;list-style:none;margin:0;padding:0;min-width:220px;z-index:60}
.elementor-nav-menu--main li:hover>.sub-menu{display:block}
.elementor-nav-menu a{display:flex;align-items:center}
.pv-chev{display:inline-block;width:6px;height:6px;border-right:1.5px solid currentColor;border-bottom:1.5px solid currentColor;transform:rotate(45deg);margin:0 0 3px}
.elementor-menu-toggle{display:none;cursor:pointer}
.elementor-nav-menu--dropdown.elementor-nav-menu__container{display:none}
.pes-header .elementor-column,.pes-header .elementor-widget-wrap{position:static}
@media(max-width:1024px){
 .elementor-nav-menu--dropdown-tablet .elementor-nav-menu--main{display:none}
 .elementor-nav-menu--dropdown-tablet .elementor-menu-toggle{display:flex}
 .elementor-menu-toggle.elementor-active+.elementor-nav-menu__container{display:block}
 .elementor-nav-menu--dropdown .elementor-nav-menu{flex-direction:column;flex-wrap:nowrap}
 .elementor-nav-menu--dropdown .sub-menu{list-style:none;margin:0;padding:0}
 .pes-header .elementor-column:nth-child(1){width:30%!important}.pes-header .elementor-column:nth-child(2){width:20%!important}.pes-header .elementor-column:nth-child(3){width:50%!important}
}
@media(max-width:767px){
 .pes-header .elementor-container{flex-wrap:nowrap}
 .pes-header .elementor-column:nth-child(1){width:42%!important}.pes-header .elementor-column:nth-child(2){width:18%!important}.pes-header .elementor-column:nth-child(3){width:40%!important}
}
@media(max-width:767px){.elementor-container{flex-wrap:wrap}.elementor-column{width:100%!important}
.elementor-column.pv-half-mobile{width:50%!important}.elementor-hidden-mobile{display:none!important}}
"""


def write_preview(path, title, sections):
    path.parent.mkdir(parents=True, exist_ok=True)
    preview_dir = ROOT / "dist" / "preview" / "img"
    PREVIEW_IMAGES[:] = sorted(f"img/{p.name}" for p in preview_dir.glob("frame-*.jpg")) if preview_dir.exists() else []
    body = "".join(render(s) for s in sections)

    def embed(m):  # inline every preview image so the file works on its own, anywhere
        f = preview_dir / m.group(2)
        if not f.exists():
            return m.group(0)
        mime = "image/png" if f.suffix == ".png" else "image/jpeg"
        return f"{m.group(1)}data:{mime};base64,{base64.b64encode(f.read_bytes()).decode()}"
    body = re.sub(r'(src="|url\()img/([\w.-]+)', embed, body)
    path.write_text(
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(re.sub('<[^>]+>', ' ', title))} – preview</title>"
        f"<style>{PREVIEW_BASE_CSS}</style></head>"
        f"<body><div class='elementor elementor-preview'>{body}</div></body></html>\n")
    print("wrote", path.relative_to(ROOT.parent))


def write_site_css():
    """dist/pes-site.css – the stylesheet for Elementor > Site Settings > Custom CSS.
    Elementor puts its own styles first in that file, so an @import there would be
    ignored; the fonts are loaded by setting them as Global Fonts instead."""
    css = re.sub(r'@import url\([^)]*\);\n*', "", CSS_FILE.read_text())
    css = css.replace("This CSS already ships inside", "Site-wide copy. The same CSS also ships inside", 1)
    (DIST / "pes-site.css").write_text(
        "/* PES site-wide styles – paste ALL of this into Elementor > Site Settings > Custom CSS.\n"
        "   Fonts (Saira, Poppins, Inter, Rajdhani) load from Site Settings > Global Fonts. */\n\n" + css)
    print("wrote", (DIST / "pes-site.css").relative_to(ROOT.parent))

    # compact copy (no comments / blank lines) that is easier to copy and paste in one go
    small = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    small = "\n".join(l.strip() for l in small.splitlines() if l.strip())
    small = re.sub(r"\{\n", " { ", small)
    small = re.sub(r";\n(?=[^}])", "; ", small)
    small = re.sub(r"\n\}", " }", small)
    (DIST / "pes-site.min.css").write_text(
        "/* PES site-wide styles – paste into Elementor > Site Settings > Custom CSS */\n" + small + "\n")
    print("wrote", (DIST / "pes-site.min.css").relative_to(ROOT.parent))


def main(argv):
    files = argv[1:] or sorted(str(p) for p in (ROOT / "content").glob("*.json"))
    seen = set()
    for f in files:
        build(f, seen)
    write_site_css()


if __name__ == "__main__":
    main(sys.argv)
