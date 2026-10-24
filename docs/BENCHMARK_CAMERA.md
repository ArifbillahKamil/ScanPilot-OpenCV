# Real-camera evaluation

Run from the project directory:

```powershell
.venv\Scripts\python tools/benchmark_camera.py
```

Open `output/benchmark-camera/index.html` in a browser. It contains original, processed, and recovered images, expandable raw/final OCR text, per-page processing times, unresolved area counts, and regression checks. `results.json` contains machine-readable results and source/code hashes. `review-template.json` is a separate human annotation template; rerunning the command overwrites generated files, so save completed annotations under another filename.

## Dataset and interpretation

- **Regression:** all 10 pages of `output/pdf/scanpilot-close-camera-10-pages.pdf`. These were used during development and must not be presented as independent test data.
- **Exploratory:** photos 00 and 01 of SmartDoc `sample04` and `sample12`, which are not among the document IDs in that PDF. They are still from the same public collection, not a new capture campaign or a certified held-out split.
- The existing photo files must be present in `tmp/pdfs/close-candidates/`. No downloads happen during execution. Source attribution and CC BY-SA 4.0 license appear in the report.
- Matching runs separately within each split. Recovery follows the package workflow: try up to two matched views for unresolved pages and retain the first successful recovery. Filename document IDs provide a limited check for cross-document candidate matches, not a full correspondence ground truth.
- This evaluates Python processing functions directly, not HTTP/browser end-to-end behavior. Matching receives bounded original images directly; the HTTP route additionally resizes to 1000 pixels before the matcher's 800-pixel resize. That interpolation difference can change candidate matches near thresholds. Browser regression tests remain the source of truth for the exact interactive path.
- Direct OCR reads the original bounded input image. It does **not** use `before_lines`, which already contains geometric alignment. This avoids crediting the baseline with ScanPilot's geometry corrections.
- Timing includes cold model startup for the first inspection. Median inspection excludes direct-baseline OCR, matching and recovery. Total script time includes those operations. These are local measurements, not AWS latency predictions.

## What is measured now

Four executable checks cover the known page 1/2 recovery, preservation of remaining uncertainty, a geometry correction on page 2, and absence of cross-document candidate matches in this small run. The report also records each page's actual decisions and processing time. A PASS is a workflow regression check, **not** evidence that all classifications, cropped boundaries or transcribed characters are correct.

No verified text transcription or exhaustive issue/region labels are available for these still photos. Character error rate is intentionally null. OCR confidence and line count must never be reported as accuracy. Dataset coordinates supplied for extracted video reference frames do not apply directly to these extra still photos.

## Completing the accuracy benchmark

Review the before/after panels and fill a copy of the annotation template: correct issue labels, content lost by cropping, straightness, readability, and whether copied text matches its source. Transcribe a consistent target area from a clear independent view before comparing OCR. Record unavailable text as unknown rather than guessing it. Include clean pages and wrong-document pairs as negative controls in the next capture set. Then compute classification precision/recall and normalized character error rate against verified labels, reporting the denominator and unreadable cases.

Do not tune production thresholds on the exploratory results and continue calling them held-out results. Any later tuning turns them into development data and requires a new document-level test set.
