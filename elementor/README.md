# Porter Energy Systems – Elementor page kit

A reusable Elementor build of the page in `mockup/` (the PES Website Template).
The page is made of **blocks** (hero, feature row, process, CTA banner). Every
block gets its look from **one shared stylesheet**, so a new page is just
"insert blocks, change text and photos".

```
elementor/
├── css/pes-global.css          ← the whole look (colors, fonts, frames, circuit lines)
├── dist/pes-page-template.json ← full page, ready to import
├── dist/blocks/*.json          ← each block on its own, ready to import
├── dist/preview/*.html         ← browser preview (open locally, no WordPress needed)
├── content/home.json           ← the text that the templates are built from
├── scripts/build.py            ← rebuilds dist/ from content/*.json
└── mockup/                     ← the original design images
```

---

## 1. One-time setup on the WordPress site

1. **Add the stylesheet.** Copy everything in `css/pes-global.css` and paste it into
   **Elementor → Site Settings → Custom CSS** (Elementor Pro) *or*
   **Appearance → Customize → Additional CSS** (no Pro needed). It also loads the
   Saira and Inter fonts.
2. **Import the templates.** Go to **Templates → Saved Templates → Import Templates** and
   import `dist/pes-page-template.json` and every file in `dist/blocks/`.
   You'll then have these in **My Templates**:

   | Template                       | What it is                                        |
   |--------------------------------|---------------------------------------------------|
   | PES – Page Template            | The whole page from the mockup                    |
   | PES – Hero                     | Big photo header with kicker, H1, text, button    |
   | PES – Feature Image Right      | Text left, orange-framed photo right              |
   | PES – Feature Image Left       | Navy-framed photo left, text right                |
   | PES – Process                  | "Our Process" with 3 numbered cards               |
   | PES – Cta                      | Blue "Schedule a consultation" banner             |
   | PES – Header                   | Logo / menu / Get A Quote bar (see section 4)     |

## 2. Making a new page

1. **Pages → Add New**, give it a title, click **Edit with Elementor**.
2. Click the **folder icon** (Add Template) → **My Templates** → **PES – Page Template** → **Insert**.
   Say **Yes** when asked to apply the page settings (full-width, hidden title, dark background).
3. Click each heading, text and button to change the words, and click each image to choose
   a photo from the Media Library. For the hero photo, select the hero section →
   **Style → Background → Image**.
4. Need more or fewer rows? Right-click a section → **Duplicate** or **Delete**, or insert
   any block from **My Templates**. Drag sections to reorder them.

Shortcut: once one page is finished, you can also copy it with a duplicate-post plugin
(for example *Yoast Duplicate Post*) and only change the text.

## 3. Rules that keep the design consistent

Each part of the design is styled by a CSS class set in **Advanced → CSS Classes**.
**Don't delete these classes.** To style something new the same way, give it the same class.

| Class                        | Put it on                | Gives you                                          |
|------------------------------|--------------------------|----------------------------------------------------|
| `pes-section`                | a section (container)    | dark grid background                               |
| `pes-hero`                   | hero section             | orange line along the bottom                       |
| `pes-feature`                | feature section          | orange circuit lines on the left                   |
| `pes-feature-reverse`        | feature section (+ above)| circuit lines on the right instead                 |
| `pes-kicker`                 | heading                  | small caps line ("SOLAR • STORAGE …")              |
| `pes-h1` / `pes-h2`          | heading                  | big hero title / uppercase section title           |
| `pes-subhead`                | heading                  | bold white sub-line ("Put your property to work.") |
| `pes-lead` / `pes-body`      | text editor              | hero intro text / normal body text                 |
| `pes-btn`                    | button                   | dark italic button with orange outline             |
| `pes-btn-solid`              | button                   | orange gradient button                             |
| `pes-frame`                  | image                    | orange frame with angled corners                   |
| `pes-frame pes-frame-blue`   | image                    | navy frame, corners mirrored                       |
| `pes-title-circuit`          | heading                  | centred title with circuit lines on both sides     |
| `pes-step`                   | process column           | holds the number + card                            |
| `pes-step-num`               | heading                  | big white step number                              |
| `pes-step-card`              | container                | white card with angled corner and navy edge        |
| `pes-cta`, `pes-cta-*`       | CTA banner parts         | blue banner, lightning bolt, divider line          |

Anything set in a widget's own **Style** tab overrides these defaults for that one
widget, so one-off changes are fine. To change something site-wide (such as the orange
color), edit the variables at the top of `pes-global.css` and paste the file in again.

## 4. Header and CTA banner: set them up once, not on every page

These two repeat on every page, so they shouldn't be copied into each one:

- **Header:** with Elementor Pro, go to **Templates → Theme Builder → Header**, insert
  **PES – Header**, choose your menu in the menu widget, and set it to show on the entire site.
  Without Pro, keep the theme's header and style it there. The page template does
  **not** include the header.
- **CTA banner:** with Elementor Pro, drop a **Template** widget pointing at **PES – Cta**
  on each page (or put it in the Theme Builder footer). Editing the template then updates
  every page at once.

## 5. Building pages from a content file (optional)

The files in `dist/` are generated. To make a page in code (or have Claude make one),
copy `content/home.json`, change the text, URLs and blocks, then run:

```bash
python3 elementor/scripts/build.py                  # builds every file in content/
python3 elementor/scripts/build.py elementor/content/my-page.json
```

Then import the new `dist/<slug>.json`. Available block types: `hero`,
`feature` (`"layout": "image-right" | "image-left"`, `"frame": "orange" | "blue"`),
`process`, and `cta`. Images are optional; when there isn't one, Elementor's placeholder appears.

## Placeholders to replace before going live

- **Photos:** the templates use Elementor's grey placeholder. The photos in the preview are
  crops of the mockup and are for preview only.
- **Process icons:** Font Awesome *solar panel*, *bolt* and *charging station*. Swap them in the
  icon widget, or upload the custom line icons as SVGs.
- **Call Now** links to `tel:+10000000000`. Put in the real phone number.
- **Button links** (`/contact/`, `/commercial-solar/` …) are guesses. Point them at the real pages.
- The mockup's "SHEDULE" is spelled "Schedule". The third feature row repeats
  "Commercial Solar" exactly as in the mockup.
