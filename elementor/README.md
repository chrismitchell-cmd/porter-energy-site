# Porter Energy Systems – Elementor page kit

A reusable Elementor build of the page in `mockup/` (the PES Website Template).

- **`dist/pes-page-template.json`**: the landing page from the first mockup.
- **`dist/pes-service-industry-template.json`**: the master template for **every service
  and industry page**. It follows the porter-electrical.com flow in the PES design
  (screenshots in `mockup/service-industry/`).
- Each template holds the whole page **and its styles**, so nothing has to be pasted into
  the Customizer.
- It uses classic Elementor **Sections and Columns**, which work on every Elementor
  version (free or Pro, with or without the newer "Container" feature).

```
elementor/
├── dist/pes-page-template.json             ← landing page
├── dist/pes-service-industry-template.json ← service / industry pages
├── dist/blocks/*.json          ← optional: single sections to add rows to a page
├── dist/preview/*.html         ← browser preview of the result
├── css/pes-global.css          ← the styles (already inside the template)
├── content/*.json              ← the text each template is built from
├── scripts/build.py            ← rebuilds dist/ from content/*.json
└── mockup/                     ← the original design images
```

---

## Part A – Import the template (one time, about 2 minutes)

1. Download **`pes-page-template.json`** to your computer. Don't open or unzip it.
2. Log in to WordPress. In the left menu, hover over **Templates** and click **Saved Templates**.
   (Older Elementor versions: **Elementor → Templates**, or **Templates → Theme Builder → Saved Templates**.)
3. Click the **Import Templates** button at the top of the page, next to the page title.
4. Click **Choose File**, pick `pes-page-template.json`, and click **Import Now**.
5. ✅ A template called **PES – Page Template** now appears in the list.

## Part B – Make a page with it (repeat for every new page)

1. Go to **Pages → Add New Page**. Type a title such as *Commercial Solar*.
   Leave the content area empty.
2. Click **Edit with Elementor** (blue button at the top). If you only see the block editor,
   click **Save draft** first and the button appears.
3. In the middle of the empty Elementor page, click the **grey folder icon** (“Add Template”).
4. In the pop-up, click the **My Templates** tab. Hover over **PES – Page Template** and click **Insert**.
5. If asked *“Apply the settings of this template?”*, click **Apply** (or **Yes**).
6. ✅ The page now looks like the mockup. Edit it:
   - **Logo and menu (header):** click the grey image at the top left → **Choose Image** → your logo.
     Click the menu area → in the left panel pick your menu under **Menu**
     (create one first under **Appearance → Menus** if needed).
   - **Text:** click any heading, paragraph or button and type.
     For a button, also change the **Link** box in the left panel.
   - **Photos:** click a grey placeholder image → **Choose Image** in the left panel.
   - **Hero background photo:** hover over the hero, click its handle (the small
     **⋮⋮** tab at the top edge) → **Style** tab → **Background** → **Image**.
   - **Call Now button:** change the link from `tel:+10000000000` to the real number.
7. Click **Publish** (or **Save Draft** to review first).

### If you see two headers, white gaps, or the page title

The template brings its own header (logo, menu, Get A Quote). If your theme's header also
shows above it, click the **gear icon** (Page Settings) → **Page Layout** → choose
**Elementor Canvas**. That hides the theme's header and footer on this page.
To keep the theme's footer but hide only its header, use **Elementor Full Width** and turn the
header off in your theme settings, or use Elementor Pro's Theme Builder (see below).
Also switch **Hide Title** on.

### Don't delete the yellow “PES Styles” bar

At the top of the page in the editor you'll see a thin yellow bar that says
*“PES Styles – keep this section”*. It holds the design's colors, fonts and shapes.
Visitors never see it. If it's deleted, the page loses its styling.

## Service and industry pages

Import **`pes-service-industry-template.json`** once (Part A), then for each service or industry
page follow Part B and insert **PES – Service / Industry Template**. Each row's name shows in the
**Navigator** (right-click → Navigator). From top to bottom:

| # | Row | What to fill in |
|---|-----|-----------------|
| 1 | **Header** | Logo and menu (same as the landing page) |
| 2 | **Hero** | Heading with the service name, 1–2 sentence subheader, main CTA. For a **video background**: select the Hero row → **Style → Background → Video** and paste an MP4 or YouTube link. Otherwise pick a photo under **Classic** |
| 3 | **Intro – What is it** | Kicker, two-tone heading, clarity paragraph, two common misconceptions, video link, "More About Us" |
| 4 | **Problem band – Why it matters** | The main problem or risk, plus a background photo (row → **Style → Background**) |
| 5 | **Key benefits** | Photo, two-tone heading, 5 benefits (Icon List; click **+ Add Item** for more), CTA |
| 6 | **Process** | 4 steps: icon, title, description, and the "Schedule An Appointment" button |
| 7 | **Punch line + video** | Two-tone heading, paragraph, this page's own video |
| 8 | **Who it's for** | 5 photo cards. The description appears on hover. Set each card's photo on its **column** → **Style → Background → Image** |
| 9 | **Testimonials** | Uses the Trustindex shortcode `[trustindex no-registration=google]` (the Trustindex plugin must be active) |
| 10 | **FAQs** | Click **+ Add Item** for more questions. FAQ schema is on, so Google can show them in search |
| 11 | **CTA banner** | Same banner as the landing page |

**Gold words in a heading:** the gold part of a two-tone heading is wrapped in a span, for example
`What Is Commercial Solar? <span class="pes-accent">Clarity In Plain English</span>`.
Change the words inside, or move the `<span …>` and `</span>` tags to change which words are gold.

**Videos:** click a video → **Link** → paste the YouTube or Vimeo URL. Until you do, Elementor's
sample video shows.

**Tool-grip edge on images and videos:** select the image or video → **Advanced → CSS Classes** and
add `pes-frame-grip` after the existing classes, for example `pes-frame pes-frame-grip` or
`pes-frame pes-frame-blue pes-frame-grip`. Remove it to go back to the straight edge. See
`dist/pes-media-grip-examples.json` for a ready-made example of each.

**Removing a section:** if a page doesn't need a row (for example the misconceptions), right-click it → **Delete**.

## Adding, removing and reordering rows

- **Copy a row:** right-click the row's handle → **Duplicate**.
- **Delete a row:** right-click the row's handle → **Delete**.
- **Move a row:** drag its handle up or down. You can also use the **Navigator**
  (right-click → Navigator) to drag rows.
- **Add a row from the kit:** import the files in `dist/blocks/` the same way as in
  Part A. Then click the folder icon → **My Templates** → insert the block you want.

---

## How the styling works

Each part of the design gets its look from a CSS class set on the element under
**Advanced → CSS Classes**. Keep these classes when editing. To give a new element the
same look, add the same class.

| Class                        | Put it on              | Gives you                                          |
|------------------------------|------------------------|----------------------------------------------------|
| `pes-section`                | section                | dark grid background                               |
| `pes-hero`                   | hero section           | orange line along the bottom                       |
| `pes-feature`                | feature section        | orange circuit lines on the left                   |
| `pes-feature-reverse`        | feature section (+ above) | circuit lines on the right instead              |
| `pes-kicker`                 | heading                | small caps line ("SOLAR • STORAGE …")              |
| `pes-h1` / `pes-h2`          | heading                | big hero title / uppercase section title           |
| `pes-subhead`                | heading                | bold white sub-line                                |
| `pes-lead` / `pes-body`      | text editor            | hero intro text / normal body text                 |
| `pes-btn`                    | button                 | transparent button, orange→gold gradient border, angled corners |
| `pes-btn pes-btn-more`       | button                 | same, italic text + gradient arrow ("Learn More →") |
| `pes-btn-solid`              | button                 | orange→gold gradient fill, angled corners ("Get A Quote") |
| `pes-btn-pill`               | button                 | rounded orange pill ("Call Now")                   |
| `pes-frame`                  | image                  | orange→gold gradient frame, angled corners         |
| `pes-frame pes-frame-blue`   | image                  | navy frame, angled corners                         |
| `pes-frame-grip`             | image / video (+ `pes-frame`) | "tool grip" edge: the middle of the top and bottom line steps in and runs through a row of grip notches, like a jobsite-speaker bumper. Works with orange and navy frames |
| `pes-header`                 | section                | dark header bar with the stepped gold line and tab |
| `pes-logo`                   | image                  | logo sizing in the header                          |
| `pes-title-circuit`          | heading                | centred title with circuit lines on both sides     |
| `pes-step-num`               | heading                | big white step number                              |
| `pes-step-card`              | icon box               | white card with angled corner and navy edge        |
| `pes-cta`                    | section                | blue banner with lightning bolt                    |
| `pes-cta-box`                | icon box               | calendar icon, divider line, title and subtitle    |
| `pes-hero-center`            | hero section (+ `pes-hero`) | centred hero for service / industry pages     |
| `pes-eyebrow`                | heading                | small gold-gradient label above a heading          |
| `pes-accent`                 | `<span>` inside a heading | gold-gradient words                             |
| `pes-h2-mixed`               | heading (+ `pes-h2`)   | big heading without forced capitals                |
| `pes-center`                 | heading / text         | centred text                                       |
| `pes-accent-title`           | heading                | small gold-gradient title (misconceptions)         |
| `pes-band`                   | section                | gradient lines top and bottom (problem band)       |
| `pes-checklist`              | icon list              | gold check marks with white text                   |
| `pes-audience-card`          | column                 | photo card with gradient border and hover text     |
| `pes-card-title` / `pes-card-text` | heading / text   | title and hover description in a photo card       |
| `pes-faq`                    | accordion              | dark FAQ rows with gradient bar and icons          |
| `pes-align-center`           | button                 | centres the button                                 |

Anything you set in a widget's own **Style** tab overrides these defaults for that widget.

### Optional: one stylesheet for the whole site

Once you have several pages, you can move the styles to one place so a change (such as
a new orange) updates every page. Paste `css/pes-global.css` into **Appearance → Customize →
Additional CSS** (or **Elementor → Site Settings → Custom CSS** with Pro), click **Publish**,
then delete the yellow **PES Styles** bar from each page. Leaving both in place is harmless too.

## Header and CTA banner

- **Header:** the page template includes the header (logo, menu, Get A Quote), sitting over the
  hero photo like the mockup. With Elementor Pro you can make it site-wide instead: import
  `dist/blocks/pes-header.json`, go to **Templates → Theme Builder → Header → Add New**, insert
  **PES – Header**, choose your menu, set it to show on the **Entire Site**, and then delete the
  Header row from each page. On phones the menu is hidden. Pro's **Nav Menu** widget adds a
  hamburger menu if you need one.
- **CTA banner:** it's part of the page template. With Pro, you can swap it for a **Template**
  widget pointing at **PES – Cta**, so editing the banner once updates every page.

## Building pages from a content file (optional)

The files in `dist/` are generated. To make a page from text (or have Claude make one), copy
`content/home.json`, change the text, URLs and blocks, then run:

```bash
python3 elementor/scripts/build.py
```

Then import the new `dist/<slug>.json`. For a new service or industry page, copy
`content/service-industry.json` (for example to `content/commercial-solar.json`), change `title`,
`slug` and the text, and build.

Block types: `hero` (`"align": "center"`, optional `"video"`), `feature`
(`"layout": "image-right" | "image-left"`, `"frame": "orange" | "blue"`), `intro`, `band`,
`benefits`, `process` (any number of steps, optional `subtitle` / `button`), `media`, `audience`,
`testimonials`, `faq`, `cta`.

## Placeholders to replace before going live

- **Photos:** the template uses Elementor's grey placeholder. The photos in the preview
  are crops of the mockup and are for preview only.
- **Logo:** pick your logo in the header image (a dark/black logo box works best, as in the mockup).
- **Process icons:** Font Awesome *solar panel*, *bolt* and *charging station*. Click the
  card and pick another icon, or upload your custom SVG icons.
- **Call Now** links to `tel:+10000000000`. Put in the real number.
- **Button links** (`/contact/`, `/commercial-solar/` …) are guesses. Point them at the real pages.
- The mockup's "SHEDULE" is spelled "Schedule". The third feature row repeats
  "Commercial Solar" exactly as in the mockup.

## Troubleshooting

| What you see | Fix |
|---|---|
| Import says **“Invalid file”** or **“This file type is not allowed”** | Make sure the file still ends in `.json`. Some browsers add `.txt`, and Macs sometimes unzip or rename downloads. Download it again and import the `.json` itself. |
| **Import Templates** button is missing | Your user needs the Administrator role. |
| Template imported but **My Templates is empty** in the pop-up | Reload the editor page. Check the template appears under **Templates → Saved Templates**. |
| Page is **white/unstyled** after inserting | The yellow **PES Styles** bar was deleted or not inserted. Insert the template again, or paste `css/pes-global.css` into **Appearance → Customize → Additional CSS**. |
| Styles show in the editor but **not on the live page** | Clear the cache. On GoDaddy, go to the WordPress dashboard → **GoDaddy/Managed WordPress → Flush Cache**. Then go to **Elementor → Tools → Regenerate CSS & Data**. |
| Header/footer from the theme is missing or doubled | Set **Page Layout** to **Elementor Full Width** (see above). |
