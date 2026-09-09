# UI revision 03 — screenshot reference from the user

The user supplied a screenshot of the New Stripe Website Figma community design after access to Figma was blocked. This screenshot supersedes the previous stylistic preference against Stripe-inspired composition and colorful backgrounds. No assets from Stripe are copied into the application.

## Applied direction

- Large left-aligned headline and concise explanation on a spacious white page.
- Multicolor CSS field with diagonal lower edge, based on the supplied screenshot.
- Layered desktop/phone product preview on the right, with restrained shadows and rounded device shapes.
- Preview uses actual synthetic document fixtures; it is explicitly labeled as a preview, with no invented OCR values or success statistics.
- Hero actions connect to the existing uploader and real perspective sample processing.
- The full inspection workspace follows immediately below; view switching, comparison, upload/replacement, and quality categories remain available.
- Work area uses calmer white and pale blue surfaces, clear category labels, and separate status/action/report hierarchy.
- Mobile stacks the headline and preview, then the work area. Existing keyboard, focus, error, and reduced-motion behavior remains.

## Implementation

`static/stripe-direction.css` overrides revision 02's layout and palette. `static/index.html` adds the hero and synthetic preview. `static/app.js` connects hero actions to the same inspection workflow rather than duplicating processing.

Browser validation includes real sample processing, responsive widths 360–1440 px, hero upload delegation, hero/preview sample actions, view switching, keyboard comparison, and replacement errors. Screenshots in artifacts/ show the latest revision. User/design review and the full competition checklist remain pending; this revision does not add OCR, agent AI, or AWS.
