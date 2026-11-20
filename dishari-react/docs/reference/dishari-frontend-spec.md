# Dishari Frontend Spec

The built frontend must look and behave like the design on the canvas. If this file and the canvas disagree, the canvas wins.

Design source: https://claude.ai/artifact/6Hrry3vEBbeyBDXPAWQqDY
Pages on the canvas: **Interactive flow** (all three steps, clickable), **Step 2: Review**, **Step 3: Citizen summary**.

Stack is not fixed. Everything below is plain CSS values and behaviour, so it works in React, Vue or vanilla JS. Examples assume a component-based setup.

---

## 1. What this is

A single-page, three-step tool for a service-centre operator who is helping a citizen (a farmer) check loan and scheme eligibility from their documents.

1. **Upload**: consent, case details, one file per document.
2. **Review**: what Dishari found, then a human approves.
3. **Citizen summary**: large Bengali text the operator prints and hands over.

### Rules the UI must never break

- **Nothing runs until consent is ticked.** Inputs, uploads and both buttons are locked until then.
- **A human submits.** Dishari prepares; the operator approves. No auto-submit anywhere.
- **Colour is never the only signal.** Every status uses colour + icon + word.
- **Inference is labelled.** Anything Dishari concluded on its own carries the badge "Dishari's inference, not an official rule".
- **Provisional is labelled.** Wherever `provisional` is true, show "Provisional, verify at the office".
- **Demo case must work offline.** "Use demo case" loads a bundled sample with no network call.

---

## 2. Design tokens

Put these in one place (CSS variables or a theme file) and use nothing else.

### Colour

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#F5F3EE` | Page background |
| `--surface` | `#FFFFFF` | Cards, header |
| `--surface-muted` | `#FAF9F6` | Document slot cards, "Operator view" chip |
| `--ink` | `#1C2024` | Body text |
| `--ink-muted` | `#4F5660` | Secondary text, labels |
| `--ink-soft` | `#3B424A` | Consent body text, Bengali footer |
| `--line` | `#D9D5CB` | Card borders, header border |
| `--line-strong` | `#8C8A80` | Input and select borders |
| `--line-faint` | `#CFCBBF` | Stepper line (not done), disabled border |
| `--primary` | `#0E5A6B` | Primary buttons, focus ring, active stepper |
| `--primary-dark` | `#083B47` | Primary hover |
| `--primary-tint` | `#E4EDEE` | Secondary button hover |

Status colours. Each status has a **fill**, a **border**, a **pill** (solid, white text) and a **text** colour for headings and body on the tint.

| Status | Card fill | Border | Pill | Heading | Body |
|---|---|---|---|---|---|
| Eligible (green) | `#E7F3EA` | `#2F7D4A` | `#1E6B3A` | `#0F2E17` | `#14401F` |
| Cannot determine (amber) | `#FFF3D1` | `#A86B00` | `#7A4E00` | `#3D2600` | `#4A2F00` |
| Not eligible / mismatch (red) | `#FDEBE8` | `#B3261E` | `#A82219` | `#4A0E0A` | `#6E1510` |

Extra red values for the mismatch card: tile border `#E3B9B4`, outlier text `#8A1C14`.

Disabled buttons: background `#E3E0D7`, text `#5E6360`, border `#CFCBBF`, cursor `not-allowed`.

### Typography

Load from Google Fonts: **Inter** (400, 500, 600), **Space Grotesk** (500, 600), **Noto Sans Bengali** (400, 600, 700).

| Role | Font | Size / weight |
|---|---|---|
| Wordmark "Dishari" | Space Grotesk | 24px / 600, letter-spacing -0.01em |
| Bengali wordmark "দিশারী" | Noto Sans Bengali | 18px, `--ink-muted` |
| Page title (h1) | Space Grotesk | 34px / 600, line-height 1.15, letter-spacing -0.01em |
| Section title (h2) | Space Grotesk | 24px / 600 |
| Card title (h3) | Inter | 20px / 600 |
| Body | Inter | 16px, line-height 1.5 |
| Step kicker ("STEP 2 OF 3") | Inter | 14px / 600, uppercase, letter-spacing 0.04em, `--primary` |
| Pill / badge text | Inter | 14px / 600 |
| Buttons | Inter | 17px / 600 (secondary action under the sheet: 16px) |
| Bengali sheet | Noto Sans Bengali | see section 5.3 |

### Shape and spacing

- Radius: cards 16px, inner tiles and slot cards 12px, buttons 10px, inputs 8px, pills 999px.
- Page container: `max-width: 1120px`, centred, side padding 24px, top 32px, bottom 64px.
- Vertical gap between page sections: 28px (step 1 uses 24px).
- Card padding: 24px (scheme cards 20px, approve bar 20px 24px).
- Minimum touch target: **44px**. Buttons are 52px tall. Inputs and selects are 48px.
- Focus ring on every interactive element: `outline: 3px solid var(--primary); outline-offset: 2px`.

### Icons

Inline SVG, 24px viewBox, `stroke: currentColor`, stroke width 2, round caps and joins, `aria-hidden="true"`. Sizes: 16, 18 or 20px in UI, 30 to 32px in the Bengali sheet. Needed: check, check-circle, x-circle, help-circle, alert-triangle, info, clock, wrench, external-link, printer.

Logo mark: 32px rounded square (radius 8) in `--primary` with a white upward arrow and a dot below it.

---

## 3. Global layout

### Header (hidden when printing)

White bar with a 1px `--line` bottom border. Inside the container: logo mark, "Dishari", "দিশারী" on the left; an "Operator view" chip on the right (14px, 500, `--ink-muted`, 1px `--line-faint` border, `--surface-muted` fill, 4px 12px padding, pill shape).

### Stepper (hidden when printing)

An `<ol>` in a `<nav aria-label="Progress">`. Three items: **Upload**, **Review**, **Citizen summary**. Each item is a 40px circle plus a two-line label (name, then state word).

| State | Circle | Label | State word |
|---|---|---|---|
| Done | Solid `--primary`, white check icon | 16px / 500, `--ink-muted` | "Done" |
| Current | White fill, 3px `--primary` border, step number in `--primary` | 16px / 600, `--ink` | "Current" |
| Next | White fill, 2px `--line-strong` border, number in `--ink-muted` | 16px / 500, `--ink-muted` | "Next" |

A 2px connector line follows the first two items: `--primary` after a done step, `--line-faint` otherwise. The first two items flex to fill the row; the last does not. The current item has `aria-current="step"`. State words are visible text, not just colour.

---

## 4. State model

```
step:       1 | 2 | 3
consent:    boolean
applicant:  'owner' | 'tenant' | 'joint' | 'other'
crop:       string
amount:     string            // digits as typed
slots:      [{ type: 'aadhaar' | 'khatian' | 'passbook', file: string }] x 3
```

Derived values:

- `anyFile = slots.some(s => s.file)`
- `locked = !consent`
- Check case disabled unless `consent && anyFile`
- Use demo case disabled unless `consent`
- Hint text next to the buttons (polite live region):
  - no consent: "Tick the consent box to begin."
  - consent, no file: "Add at least one document, or use the demo case."
  - otherwise: empty
- Case line on Review: `<applicant label> · <crop or "Crop or activity not entered"> · <₹ amount in Indian grouping or "Amount not entered">`

Transitions:

| Action | Result |
|---|---|
| Check case | `step = 2`, runs the real check |
| Use demo case | Fills applicant = owner, crop = "Boro paddy", amount = 40000, three sample slots, then `step = 2` |
| Back (on Review) | `step = 1`, form values kept |
| Approve and continue | `step = 3` |
| Back to review (on Summary) | `step = 2` |
| Print | `window.print()` |
| Start a new case | Reset every field, `consent = false`, `step = 1` |

Demo slot file labels: "Sample Aadhaar (saved demo)", "Sample khatian (saved demo)", "Sample passbook (saved demo)".

---

## 5. Screens

### 5.1 Step 1: Upload

Order, top to bottom:

1. **Heading block.** Kicker "Step 1 of 3", h1 "Upload the case", one line: "Tick consent, enter the case details, then add one file per document."
2. **Consent panel.** A whole-panel `<label>` containing a 24px checkbox (`accent-color: --primary`) and two lines: bold "Applicant consent", then "The applicant agrees that Dishari may read the documents below to check this case. Nothing runs until this box is ticked." Padding 18px 20px, radius 12, 2px border. Unticked: white fill, `--primary` border. Ticked: green fill `#E7F3EA`, green border `#2F7D4A`.
3. **Fieldset (disabled while `locked`, 55% opacity).** Two cards in a wrapping row, gap 24px:
   - **Case details** card (flex `1 1 320px`):
     - "Applicant type" select. Options: Individual farmer (owner-cultivator), Tenant farmer or sharecropper, Joint cultivator, Other.
     - "Crop or activity" text input, placeholder "e.g. Boro paddy".
     - "Requested loan amount (₹)" numeric input, placeholder "e.g. 40000".
   - **Documents** card (flex `2 1 480px`), subtitle "One slot per document. Say what it is, then add the file." Contains three slot cards in a grid `repeat(auto-fit, minmax(min(280px, 100%), 1fr))`, gap 16.
4. **Slot card** (`--surface-muted`, 1px `--line`, radius 12, padding 16). Contains:
   - Label "Document N is a" and a select: Aadhaar card, Khatian (Record of Rights), Bank passbook. Defaults are Aadhaar, Khatian, Passbook in order.
   - Label "File" and a native file input (`accept="image/*,application/pdf"`). Style the file button: min-height 44, 1px `--primary` border, white fill, `--primary` text, 600 weight, radius 8.
   - Status line: green check and the file name when a file is present, otherwise "No file added yet" in `--ink-muted`.
5. **Action row.** "Check case" (primary) and "Use demo case" (secondary) side by side with the hint text. Below, one 14px muted line: "Demo case loads a saved sample and needs no network."

Inputs and selects: 48px tall, 1px `--line-strong` border, radius 8, 16px Inter, white fill. Every input has a visible `<label for>`.

### 5.2 Step 2: Review

Order:

1. **Heading block.** Kicker "Step 2 of 3", h1 "Review the findings", then the case line in `--ink-muted`.

2. **Mismatch card** (red). 2px `#B3261E` border, `#FDEBE8` fill, radius 16, padding 24, 20px internal gap.
   - Header row: red solid pill with alert icon and the word "Mismatch", then h2 "Name differs across documents" (24px, `#4A0E0A`).
   - Three document tiles in an auto-fit grid (min 240px): white, 1px `#E3B9B4` border, radius 12, padding 16.
     - Aadhaar: "Mohammad Rafique", green check line "Matches the passbook".
     - Bank passbook: "Mohammad Rafique", green check line "Matches the Aadhaar".
     - Khatian: "Md. Rafiq", **3px `#B3261E` border** (14px padding to keep size), x-circle icon and "Likely outlier" in `#8A1C14`, 600 weight.
     - Tile text: source label 14px `--ink-muted`, name 20px / 600.
   - **Fix route** row (white, 1px `#E3B9B4`, radius 12, padding 16px 20px): wrench icon and uppercase label "Fix route"; the text "Minor correction of Record of Rights" (18px / 600); two chips, "Free" (green tint, green border) and "At the BL&LRO" (`#F5F3EE` fill, 1px `--line-strong`).
   - **Inference badge**, aligned left: white fill, 1px **dashed** `#8A1C14` border, pill, info icon, text "Dishari's inference, not an official rule".

3. **Scheme eligibility** (h2), then a grid of cards, auto-fit min 300px, gap 16. One card per scheme. Every card: 2px border in the status colour, radius 16, padding 20, 14px gap, a solid pill (icon + word) top-left, h3 scheme name, body text.

   | Card | Pill | Content |
   |---|---|---|
   | Kisan Credit Card (KCC) | Green, check-circle, "Eligible" | "Up to **₹50,000** on this document route", then the provisional badge |
   | PM-JAY (Ayushman Bharat) | Amber, help-circle, "Cannot determine" | "Dishari can't confirm this from the documents provided." and an outlined link-button "Look up on the PM-JAY site" with external-link icon (opens in a new tab, `rel="noopener"`, links to https://pmjay.gov.in; confirm the exact lookup URL) |
   | `[Scheme name]` | Red, x-circle, "Not eligible" | `[Reason, from your rules file]` |

   - **Provisional badge:** white fill, 1px green border, clock icon, "Provisional, verify at the office". Pinned to the bottom of the card (`margin-top: auto`).
   - Amber variant when documents are missing: same card, but list the missing documents in place of the link.
   - Cards in a row stretch to equal height.

4. **Approve bar.** White card, 1px `--line`, radius 16, padding 20px 24px. Left: bold "Dishari prepares. A person submits." and a 15px muted line "Approve only after you have checked the findings above." Right: "Back" (secondary) and "Approve and continue" (primary).

### 5.3 Step 3: Citizen summary

Above the sheet (hidden when printing): kicker "Step 3 of 3", h1 "Citizen summary", muted line "Hand this to the applicant. It prints on one page.", and two buttons: "Back to review" (secondary) and "Print" (primary, printer icon).

**The sheet** is a white card (1px `--line`, radius 16, padding 40, 28px gap) with `lang="bn"`, Noto Sans Bengali, line-height 1.7. Body text is **26px**, secondary lines **24px**, so it is readable at arm's length.

| Block | Content |
|---|---|
| Header, with a 2px `--ink` bottom rule | h2 (38px / 700) **আপনার আবেদনের সারসংক্ষেপ**; line (26px) "আবেদনকারী: **মোহাম্মদ রফিক**" |
| Red box (2px `#B3261E`, `#FDEBE8`, radius 12, padding 24) | h3 (28px / 700, `#6E1510`, alert icon 30px) **একটি বিষয় ঠিক করতে হবে**. Then: আধার ও ব্যাংকের পাসবইয়ে আপনার নাম “Mohammad Rafique”, কিন্তু খতিয়ানে লেখা আছে “Md. Rafiq”। Then: **কী করবেন:** ব্লক ভূমি ও ভূমি সংস্কার আধিকারিকের (BL&LRO) অফিসে গিয়ে রেকর্ড অব রাইটসে নামের ছোট সংশোধন করান। এর জন্য কোনো খরচ নেই। |
| Schemes heading | h3 (28px / 700) **প্রকল্প অনুযায়ী ফলাফল** |
| Green row | check-circle icon (32px), **কিষাণ ক্রেডিট কার্ড (KCC): যোগ্য**, then: এই নথিতে ₹৫০,০০০ পর্যন্ত। অফিসে যাচাই করিয়ে নিন। |
| Amber row | help-circle icon, **PM-JAY (আয়ুষ্মান ভারত): এখনই বলা যাচ্ছে না**, then: সরকারি ওয়েবসাইটে নিজের নাম খুঁজে দেখুন। |
| Red row | x-circle icon, **[প্রকল্পের নাম]: যোগ্য নন**, then: [কারণ] |
| Footer, with a 2px `--ink` top rule (22px, `--ink-soft`) | এটি সাময়িক ফলাফল। অফিসে গিয়ে যাচাই করিয়ে নিন; চূড়ান্ত সিদ্ধান্ত অফিসের কর্মকর্তার। |

Scheme rows: icon on the left (32px, 4px top margin), 18px 20px padding, 2px border in the status colour, radius 12, 16px gap. Titles 26px / 700, detail lines 24px. Each row carries the status in words as well as colour and icon.

Below the sheet: "Start a new case" (secondary, 48px tall).

**Bengali copy was written without a native review.** Have a Bengali speaker read it before it is shown to a citizen or a judge.

### Print

Print shows the sheet only.

```css
@media print {
  .no-print { display: none !important; }   /* header, stepper, buttons, page heading */
  body      { background: #fff; }
  .sheet    { border: none; padding: 0; }
}
```

Use `window.print()` with no PDF library. Keep status colours: add `print-color-adjust: exact` on the sheet so the tinted rows survive printing, and the icons and words still carry the meaning if a printer drops colour.

---

## 6. Data the Review screen needs

Suggested shape. Rename to fit the backend, but keep the fields.

```ts
type Check = {
  mismatches: Array<{
    field: 'name';
    values: Array<{ doc: 'aadhaar' | 'khatian' | 'passbook'; value: string }>;
    likelyOutlier?: 'aadhaar' | 'khatian' | 'passbook';
    fix: { label: string; cost: string; where: string };
    inferred: boolean;               // true shows the inference badge
  }>;
  schemes: Array<{
    name: string;
    status: 'eligible' | 'cannot_determine' | 'not_eligible';
    provisional: boolean;            // true shows the provisional badge
    detail: string;                  // e.g. "Up to ₹50,000 on this document route"
    missingDocuments?: string[];     // amber: list these
    lookupUrl?: string;              // amber: show the link
    reason?: string;                 // red: why not
  }>;
};
```

The demo case is a fixed `Check` object bundled in the app. It is the only data source when offline.

---

## 7. Accessibility

- Real elements only: `<button>`, `<a href>`, `<input>` with `<label>`, `<select>`. No clickable `div` or `span`.
- Icon-only buttons need `aria-label`. All decorative SVGs get `aria-hidden="true"`.
- Text contrast is at least 4.5:1 against its background (the colours above were picked to pass). Status is never colour alone.
- Hint text next to the buttons is an `aria-live="polite"` region.
- The disabled fieldset must actually be disabled (`<fieldset disabled>`), not just dimmed.
- Mark Bengali blocks with `lang="bn"`; the page itself is `lang="en"`.
- The page must work at phone width: the stepper and grids wrap, nothing scrolls sideways.

## 8. Responsive behaviour

- Desktop target 1280px; the container caps at 1120px.
- Step 1: the two cards wrap into one column when narrow.
- Review: tile and scheme grids use `repeat(auto-fit, minmax(min(240px | 300px, 100%), 1fr))`.
- Headings and buttons wrap; wide content gets its own scroll box, never page-level horizontal scroll.

---

## 9. Open items (fill before the demo)

- [ ] Real scheme list, with the "not eligible" scheme name and reason (currently `[Scheme name]` / `[Reason, from your rules file]`).
- [ ] Confirm the PM-JAY lookup URL.
- [ ] Confirm applicant-type options and demo values (Boro paddy, ₹40,000).
- [ ] Native Bengali review of every Bengali string.
- [ ] Decide whether "Use demo case" should skip the consent gate on stage (currently gated).
- [ ] Missing-documents variant of the amber card is specified here but not drawn on the canvas.

## 10. Acceptance checklist

Open the built app next to the canvas and check each line.

- [ ] Colours, fonts, radii and spacing match section 2.
- [ ] Stepper shows Done / Current / Next with words, correct on every step.
- [ ] Nothing is clickable or uploadable until consent is ticked.
- [ ] Check case stays disabled until consent and at least one file.
- [ ] Demo case works with the network off and lands on Review with the sample result.
- [ ] Mismatch card shows three tiles, the khatian marked "Likely outlier", the fix route, and the inference badge.
- [ ] Every scheme card has colour, icon and word; KCC shows the provisional badge.
- [ ] Approve is a deliberate click; nothing submits on its own.
- [ ] Bengali sheet is large and legible, and Print outputs only the sheet on one page.
- [ ] Tab order works, focus ring is visible everywhere, and the page works at phone width.
