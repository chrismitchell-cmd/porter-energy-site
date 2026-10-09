"""Print the CSS for pes-frame-grip: a frame whose top/bottom line is indented with finger grips.

    python3 elementor/scripts/grip_outline.py

Paste the output over the pes-frame-grip block in css/pes-global.css (then run build.py).
Change CENTRES / TOP_W / N below to move, widen or deepen the finger indents.
"""
C, T = 20, 3            # corner cut, line thickness
D = 6                   # how far the middle section of the line steps in
N = 6                   # depth of each finger indent
TOP_W, SIDE = 30, 4     # indent width at the line, horizontal run of each angled side
SH0, SH1 = 120, 110     # shoulder: starts at ±120px from centre, reaches the recess at ±110px
CENTRES = [-72, -24, 24, 72]  # finger indents, ~48px apart (a finger's width)

# inner (3px in) offsets for the angled indent sides, from the side slope SIDE:N
INNER_TOP, INNER_BOT = 1.6, 2.4

def x(v):
    v = round(v, 1)
    return "50%" if v == 0 else f"calc(50% {'+' if v > 0 else '-'} {abs(v):g}px)"
def yb(v):
    return "100%" if v == 0 else f"calc(100% - {v:g}px)"
def xr(v):
    return "100%" if v == 0 else f"calc(100% - {v:g}px)"

def indents(y_line, y_floor, widen_top, widen_bot, flip):
    pts = []
    for c in (reversed(CENTRES) if flip else CENTRES):
        x0, x1 = c - TOP_W / 2 - widen_top, c + TOP_W / 2 + widen_top
        b0, b1 = c - TOP_W / 2 + SIDE - widen_bot, c + TOP_W / 2 - SIDE + widen_bot
        seq = [(x(x0), y_line), (x(b0), y_floor), (x(b1), y_floor), (x(x1), y_line)]
        pts += list(reversed(seq)) if flip else seq
    return pts

def outer():
    p = [("0", f"{C}px"), (f"{C}px", "0"), (x(-SH0), "0"), (x(-SH1), f"{D}px")]
    p += indents(f"{D}px", f"{D+N}px", 0, 0, False)
    p += [(x(SH1), f"{D}px"), (x(SH0), "0"), (xr(C), "0"), ("100%", f"{C}px"),
          ("100%", yb(C)), (xr(C), "100%"), (x(SH0), "100%"), (x(SH1), yb(D))]
    p += indents(yb(D), yb(D + N), 0, 0, True)
    p += [(x(-SH1), yb(D)), (x(-SH0), "100%"), (f"{C}px", "100%"), ("0", yb(C))]
    return p

def inner():  # the same outline moved 3px into the frame, so the line keeps an even thickness
    s0, s1 = SH0 + 1, SH1 + 1
    p = [(f"{T}px", f"{C+1}px"), (f"{C+1}px", f"{T}px"), (x(-s0), f"{T}px"), (x(-s1), f"{D+T}px")]
    p += indents(f"{D+T}px", f"{D+N+T}px", INNER_TOP, INNER_BOT, False)
    p += [(x(s1), f"{D+T}px"), (x(s0), f"{T}px"), (xr(C+1), f"{T}px"), (xr(T), f"{C+1}px"),
          (xr(T), yb(C+1)), (xr(C+1), yb(T)), (x(s0), yb(T)), (x(s1), yb(D+T))]
    p += indents(yb(D+T), yb(D+N+T), INNER_TOP, INNER_BOT, True)
    p += [(x(-s1), yb(D+T)), (x(-s0), yb(T)), (f"{C+1}px", yb(T)), (f"{T}px", yb(C+1))]
    return p

def poly(points):
    return "polygon(" + ", ".join(f"{a} {b}" for a, b in points) + ")"

print(f"""/* pes-frame-grip – add to a framed image/video (with pes-frame) for a "tool grip" edge.
   Like the bumper on a jobsite speaker, the middle of the top and bottom line steps in with
   angled shoulders and has four finger-grip indents, about a finger's width apart, cut into
   the frame line itself. (Generated outline: the line keeps an even {T}px thickness.)     */
.elementor .pes-frame.pes-frame-grip.elementor-widget {{
  padding: {D+N+T+8}px 10px;
  clip-path: {poly(outer())};
}}
.elementor .pes-frame.pes-frame-grip.elementor-widget::before {{
  inset: 0;
  clip-path: {poly(inner())};
}}""")
