# OCR and region precision — September 10, 2026

Reproduced the user's photographed form with a finger covering part of a text line. The previous output misread the short word Modul, merged spaces, marked an adjacent confident line, and missed the finger because page corners were unavailable.

Changes:

- Increase OCR detection resolution to 1280 on the detector's short side.
- Disable individual crop orientation flipping; page tilt is handled by geometry. This workflow expects upright reading orientation and does not guarantee upside-down OCR.
- Re-read separated word crops to propose whitespace. Accept only if every non-whitespace character matches the original recognition and all word scores are at least 0.85. Numeric lines are left unchanged. Preserve raw_text alongside text.
- Tighten uncertain-line padding to two pixels and require more than 25% of a line's area to overlap before inheriting an unresolved mark.
- If paper corners are unknown, restrict colored-object suspicion to the observed text envelope. This can catch a finger intruding into text without labeling the whole table. It remains a color heuristic, not semantic hand detection.

On the local real photo, Modul and Menu are read correctly, ERP Estimation Framework gains spaces, and the finger region is flagged at [141, 926, 126, 147]. Some title spacing and character errors remain; model scores are not accuracy guarantees. No unseen text is completed. Personal photo outputs stay in ignored artifacts, outside the source archive.
