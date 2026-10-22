"""Build the copy deck (copy-deck.html) from pages.py.

Usage: python3 build_copy.py
"""
import html
import os
import re

from pages import PAGES

HERE = os.path.dirname(os.path.abspath(__file__))
GROUPS = ["Solutions", "Service O&M", "Industries"]


def esc(s):
    """Escape text and highlight [bracketed] items the team must confirm."""
    return re.sub(r"\[([^\]]+)\]", r'<mark>[\1]</mark>', html.escape(s))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def field(label, text, big=False):
    cls = "val big" if big else "val"
    return (f'<div class="field"><span class="lbl">{label}</span>'
            f'<div class="{cls}">{esc(text)}</div>'
            f'<button class="cp" type="button" data-copy="{html.escape(text, quote=True)}">Copy</button></div>')


def section(n, name, body):
    return f'<section class="sec"><h3><span class="n">{n:02d}</span>{name}</h3>{body}</section>'


def render_page(p):
    pid = slug(p["group"] + "-" + p["name"])
    industry = p["group"] == "Industries"
    h_title, h_sub, h_cta = p["hero"]
    i_kicker, i_title, i_accent, i_text, i_points = p["intro"]
    b_kicker, b_title, b_accent, b_text = p["band"]
    k_title, k_accent, k_text, k_list, k_items, k_cta = p["benefits"]
    m_title, m_accent, m_text, m_video = p["media"]
    a_kicker, a_title, a_cards = p["audience"]
    proc = p["process"]

    s = []
    s.append(section(1, "Hero", field("Heading", h_title, True) + field("Subheader", h_sub) + field("Button", h_cta)))
    pts = "".join(field(f"Misconception {i + 1}", t) + field("Answer", a) for i, (t, a) in enumerate(i_points))
    s.append(section(2, "What Is It", field("Kicker", i_kicker) + field("Heading", i_title, True)
                     + field("Gradient line", i_accent) + field("Text", i_text) + pts))
    s.append(section(3, "Why It Matters (band)", field("Kicker", b_kicker) + field("Heading", b_title, True)
                     + field("Gradient line", b_accent) + field("Text", b_text)))
    items = "".join(field(f"Benefit {i + 1}", t) for i, t in enumerate(k_items))
    s.append(section(4, "Key Benefits", field("Heading", k_title, True) + field("Gradient line", k_accent)
                     + field("Text", k_text) + field("List title", k_list) + items + field("Button", k_cta)))
    steps = "".join(field(f"Step {i + 1}: {t}", d) for i, (t, d) in enumerate(proc["steps"]))
    shared = '<p class="note">Shared on every ' + ("Service O&amp;M" if p["group"] == "Service O&M" else "Solutions and Industry") + ' page.</p>'
    s.append(section(5, "Process", shared + field("Heading", proc["title"], True) + field("Subtitle", proc["subtitle"])
                     + steps + field("Button", proc["button"])))
    s.append(section(6, "Video", field("Heading", m_title, True) + field("Gradient line", m_accent)
                     + field("Text", m_text) + f'<p class="note">{esc(m_video)}</p>'))
    cards = "".join(field(t, d) for t, d in a_cards)
    note = '<p class="note">On industry pages these cards link to the matching solution pages.</p>' if industry else ""
    s.append(section(7, "Solutions For This Industry" if industry else "Who It's For",
                     note + field("Kicker", a_kicker) + field("Heading", a_title, True) + cards))
    t = p["testimonials"]
    s.append(section(8, "Testimonials", field("Kicker", t["kicker"]) + field("Heading", t["title"], True)
                     + f'<p class="note">{esc(t["note"])}</p>'))
    faqs = "".join(field(f"Q{i + 1}", q) + field("Answer", a) for i, (q, a) in enumerate(p["faqs"]))
    s.append(section(9, "FAQs", field("Heading", f"FAQs About {p['name']}", True) + faqs))
    c = p["cta"]
    s.append(section(10, "Bottom CTA", field("Heading", c["title"], True) + field("Subtitle", c["subtitle"])
                     + field("Button", c["button"])))

    return (f'<article class="page" id="{pid}"><header class="ph"><span class="grp">{html.escape(p["group"])}</span>'
            f'<h2>{html.escape(p["name"])}</h2><code>{html.escape(p["url"])}</code></header>{"".join(s)}</article>')


def build():
    nav, body = [], []
    for g in GROUPS:
        ps = [p for p in PAGES if p["group"] == g]
        links = "".join(f'<a href="#{slug(g + "-" + p["name"])}">{html.escape(p["name"])}</a>' for p in ps)
        nav.append(f'<div class="ng"><h4>{html.escape(g)} <span>{len(ps)}</span></h4>{links}</div>')
        body.append(f'<h1 class="gh" id="{slug(g)}">{html.escape(g)}</h1>' + "".join(render_page(p) for p in ps))
    todo = sum(b.count("<mark>") for b in body)
    out = TEMPLATE.replace("{{NAV}}", "".join(nav)).replace("{{BODY}}", "".join(body)) \
                  .replace("{{COUNT}}", str(len(PAGES))).replace("{{TODO}}", str(todo))
    path = os.path.join(HERE, "copy-deck.html")
    with open(path, "w") as f:
        f.write(out)
    print("wrote", path)


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PES Page Copy Deck</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Saira:wght@700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#f6f4f1;--panel:#fff;--ink:#1b1a1a;--muted:#6b6560;--line:#e4dfd8;--accent:#c75e22;
--grad:linear-gradient(90deg,#dd7033,#eaa24e,#f8da72);--mark:#fde7b0;--markink:#5a3a00}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121111;--panel:#1b1a1a;--ink:#f1ece6;
--muted:#9c958e;--line:#2e2b29;--accent:#eaa24e;--mark:#4a3410;--markink:#f8da72}}
:root[data-theme="dark"]{--bg:#121111;--panel:#1b1a1a;--ink:#f1ece6;--muted:#9c958e;--line:#2e2b29;--accent:#eaa24e;--mark:#4a3410;--markink:#f8da72}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 Inter,system-ui,sans-serif}
.wrap{display:grid;grid-template-columns:250px 1fr;max-width:1200px;margin:0 auto}
nav{position:sticky;top:0;height:100vh;overflow:auto;padding:24px 16px;border-right:1px solid var(--line)}
nav .brand{font:700 18px Saira,sans-serif;text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px}
nav .brand b{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
nav .meta{color:var(--muted);font-size:13px;margin-bottom:20px}
.ng h4{font:700 12px Saira,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:var(--accent);margin:18px 0 6px}
.ng h4 span{color:var(--muted)}
.ng a{display:block;color:var(--ink);text-decoration:none;padding:4px 8px;border-radius:4px;font-size:14px}
.ng a:hover{background:var(--line)}
main{padding:24px 32px 80px;min-width:0}
.intro{background:var(--panel);border:1px solid var(--line);border-left:4px solid #dd7033;padding:16px 20px;border-radius:6px;margin-bottom:8px}
.intro p{margin:6px 0}
mark{background:var(--mark);color:var(--markink);padding:0 3px;border-radius:3px}
.gh{font:700 28px Saira,sans-serif;text-transform:uppercase;margin:48px 0 0;padding-bottom:8px;border-bottom:3px solid;border-image:var(--grad) 1}
.page{margin-top:28px;background:var(--panel);border:1px solid var(--line);border-radius:8px;overflow:hidden;scroll-margin-top:12px}
.ph{padding:18px 20px;border-bottom:1px solid var(--line)}
.ph .grp{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.ph h2{font:700 22px Saira,sans-serif;text-transform:uppercase;margin:2px 0}
.ph code{color:var(--accent);font-size:13px}
.sec{padding:14px 20px;border-bottom:1px solid var(--line)}.sec:last-child{border-bottom:0}
.sec h3{font:700 14px Saira,sans-serif;text-transform:uppercase;letter-spacing:.05em;margin:0 0 8px}
.sec h3 .n{color:var(--accent);margin-right:8px}
.field{display:grid;grid-template-columns:140px 1fr auto;gap:12px;align-items:start;padding:5px 0}
.lbl{color:var(--muted);font-size:13px;padding-top:2px}
.val.big{font-weight:600}
.cp{font:600 12px Inter,sans-serif;border:1px solid var(--line);background:transparent;color:var(--muted);border-radius:4px;padding:3px 8px;cursor:pointer}
.cp:hover{color:var(--ink);border-color:var(--accent)}.cp.ok{color:var(--accent);border-color:var(--accent)}
.note{color:var(--muted);font-size:13px;font-style:italic;margin:2px 0 8px}
@media (max-width:820px){.wrap{display:block}nav{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line)}
main{padding:16px}.field{grid-template-columns:1fr auto}.lbl{grid-column:1/-1;padding:0}}
</style></head><body><div class="wrap">
<nav><div class="brand">PES <b>Copy Deck</b></div><div class="meta">{{COUNT}} pages · Service / Industry template</div>{{NAV}}</nav>
<main>
<div class="intro"><p><strong>Copy for every section of each Solutions, Service O&amp;M and Industry page</strong>, in the same order as the PES Service / Industry template. Click <em>Copy</em> next to a field, then paste it into the matching Elementor widget.</p>
<p><mark>[Highlighted brackets]</mark> are facts we need you to confirm or fill in ({{TODO}} total), such as incentive eligibility, brands, timelines and pricing.</p></div>
{{BODY}}
</main></div>
<script>
document.addEventListener('click',function(e){var b=e.target.closest('.cp');if(!b)return;
var t=b.getAttribute('data-copy');function done(){b.textContent='Copied';b.classList.add('ok');
setTimeout(function(){b.textContent='Copy';b.classList.remove('ok')},1200)}
if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(done,fallback)}else fallback();
function fallback(){var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();
try{document.execCommand('copy');done()}catch(_){}a.remove()}});
</script></body></html>
"""

if __name__ == "__main__":
    build()
