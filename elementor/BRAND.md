# Porter Energy Systems – brand colors and fonts

These are the colors and fonts the PES Elementor templates use (from `css/pes-global.css`).

## Elementor Global Colors

**Elementor → Site Settings → Design System → Global Colors**

### System colors

| Elementor slot | Name            | Hex       | Used for |
|----------------|-----------------|-----------|----------|
| Primary        | PES Orange      | `#DD7033` | Start of the brand gradient; main brand orange |
| Secondary      | PES Navy        | `#2D4A8F` | Navy image frames, step-card edges, process icons |
| Text           | PES Light Text  | `#E9E9EA` | Body text on dark backgrounds |
| Accent         | PES Button Orange | `#EF7828` | Solid buttons (the "Call Now" pill). White text reads well on it |

### Custom colors (click **+ Add Color**)

| Name                 | Hex       | Used for |
|----------------------|-----------|----------|
| PES Amber            | `#EAA24E` | Middle of the brand gradient, check marks |
| PES Gold             | `#F8DA72` | End of the brand gradient, link hover |
| PES Background       | `#1B1A1A` | Page and section background |
| PES Panel            | `#232121` | FAQ rows and other slightly raised panels |
| PES White            | `#FFFFFF` | Headings, button text, white cards |
| PES Dark Text        | `#1D1D1F` | Text on white cards |
| PES CTA Blue – Top   | `#10206A` | CTA banner gradient (top) |
| PES CTA Blue – Mid   | `#0A1850` | CTA banner gradient (middle) |
| PES CTA Blue – Deep  | `#020F24` | CTA banner gradient (bottom) |
| PES CTA Glow Blue    | `#2042CD` | Bright glow in the CTA banner |
| PES Neon Blue        | `#70C6FF` | Neon lightning bolt line |

## The brand gradient

Every orange line, border, frame, "Get A Quote" button, heading accent and circuit line uses one
left-to-right gradient:

```
#DD7033 (0%)  →  #EAA24E (50%)  →  #F8DA72 (100%)
```

Elementor's gradient control has only **two** colors. To recreate it in a widget's
**Background → Gradient**, use:

- Color: `#DD7033`, Location `0`
- Second Color: `#F8DA72`, Location `100`
- Type: Linear, Angle `90°`

## Overlays and transparent tones

| Use                                        | Value |
|--------------------------------------------|-------|
| Grid lines on dark sections                | `rgba(255,255,255,0.035)` |
| Photo overlay – problem band, process      | `rgba(16,16,17,0.82)` |
| Photo overlay – centered hero              | `rgba(12,12,14,0.62)` |
| Photo overlay – landing hero (left to right) | `rgba(0,0,0,0.78)` → `rgba(0,0,0,0.05)` at 80% |
| Divider line in the CTA banner             | `rgba(255,255,255,0.35)` |
| Panel border (FAQ rows)                    | `rgba(255,255,255,0.08)` |

## Elementor Global Fonts

**Elementor → Site Settings → Design System → Global Fonts**. All four are Google Fonts.

| Elementor slot | Font     | Weight | Used for |
|----------------|----------|--------|----------|
| Primary        | Saira    | 700 (800 for uppercase section titles) | Headings, step numbers |
| Secondary      | Poppins  | 600–700 | Buttons, menu, FAQ questions |
| Text           | Inter    | 400 (600 for small labels) | Body text |
| Accent         | Rajdhani | 700 / 500 | CTA banner title and subtitle |

## Good to know

- **The templates don't change with Global Colors.** They're styled by the `pes-` classes in
  `pes-global.css`, so the PES pages keep their look whatever is set in Global Colors. The global
  settings help when you build new widgets by hand: pick the swatch instead of typing hex codes.
- **To change a brand color everywhere** on PES pages, edit the variables at the top of
  `css/pes-global.css` (for example `--pes-orange`) and rebuild, or paste the CSS into Site
  Settings → Custom CSS.
- **Changing System Colors can affect older pages.** Existing site content that already uses
  Primary, Secondary, Text or Accent will pick up the new values, so check older pages after saving.
