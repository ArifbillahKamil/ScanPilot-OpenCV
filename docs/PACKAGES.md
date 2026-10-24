# Document package workflow

## Scope

ScanPilot accepts one PDF or up to 20 photos. PDF imports render a bounded preview per page; native text pages without image objects are recognized conservatively and retain the original PDF page by default. Image-bearing pages receive visual checks, including pages with an existing OCR layer. Native classification is not certification of the page's content or layout.

The browser owns the package, original PDF, page images, results, second photos and manual region selections. Requests are stateless and no document session is stored on the server. Refresh closes this in-memory workspace. Failed imports leave the current package intact. A failed page can be retried without reprocessing successful pages.

## Inspection and review

Pages are inspected sequentially with progress and a stop-after-current-page control. The queue prioritizes failures and pages requiring evidence, then improved and review-ready pages. Page numbers always refer to original order. The page editor reuses all region recovery, source comparison and review exports. A second photo is matched against the selected page; it is not silently routed to an arbitrary page.

Opening another page preserves each page's result, second photo and manual selections. After inspection, ScanPilot compares original images across the package using SIFT and geometric registration. Candidate views are then checked with the existing OCR identity and region coverage rules. Up to two candidates are tried per page; the first successful recovery is retained with its source page number. Uncovered text rows may be recovered while remaining parts of a dark obstruction stay unresolved. Related views are candidates, not a guarantee of matching document contents. Original pages remain in the export; this does not deduplicate the document.

The user can choose whether the current result replaces that page on export. Successful enhancements and partial recoveries are included by default even if review remains; pages without a successful improvement retain their original. OCR uncertainty and unknown boundaries request review rather than an automatic retake. Unresolved regions remain in the attention list and report. The package export is a review copy, not a certification that every page is correct.

PDF image frames no longer bypass paper geometry detection. When corners are unavailable, distributed text rows can estimate horizontal perspective convergence. This estimate straightens rows but cannot guarantee true paper proportions or repair curled surfaces. Broad coloured print alone is no longer sufficient to classify every graphic on a poster as an obstruction. Long dark objects are analysed separately. Thresholds remain heuristics; this is not a general accuracy guarantee.

## PDF export

Every original page is included in its original order. Unchanged PDF pages are copied without rasterizing native text/graphics. Corrected pages are rendered as image pages, fitted to the source page dimensions. Image-only packages become a multipage PDF. Unresolved region outlines are drawn on included processed pages. A JSON report is available separately and embedded as an attachment in the PDF.

The renderer uses PDFium behind a process-local mutex; the parser/writer uses pypdf. See [PDFium thread-safety and object lifetime](https://pypdfium2.readthedocs.io/en/stable/python_api.html) and [pypdf page merging](https://pypdf.readthedocs.io/en/stable/user/merging-pdfs.html).

Limits: 20 PDF pages, 20 MB original PDF, 12 MB and 24 MP per uploaded photo, 80 MB per package export and 50 MP across decoded export images. Interactive/signed PDFs are rejected instead of silently flattening forms or signatures. Password-protected PDFs must be unlocked before use. Very large or malformed files may be rejected. Images are resized for the document inspection workflow; raw camera-resolution archival storage is not provided.

## Validation

`tests/test_package.py` checks mixed native/raster import, native text preservation, unchanged unresolved pages, original order, report attachment, export dimensions, encryption, malformed input, page limits and API routes. `tools/make_package_fixture.py` creates a synthetic three-page native/scan PDF and renders exports for visual inspection. `tools/check_package_browser.py` exercises PDF triage, per-page recovery, page state restoration, export text/order/report, both languages, responsive widths and preservation after failed import.

AWS deployment is still pending. The same stateless routes fit the existing ECS container; PDF libraries are pinned in runtime requirements. Linux build and cloud memory/latency measurements still require verification before hosting.

The page list displays each issue with its action status. Follow-up buttons identify the original page number and open unresolved regions in the evidence viewer. Blur/boundary problems request a whole-page retake; uncertain OCR asks for review before a retake. Manual selections are included. Package JSON includes follow_up targets in processed-page pixel coordinates (null box means whole page).


The October 2026 regression fixture (local SmartDoc 2017 close-camera PDF) verified page 1 recovering two text regions from page 2, with remaining dark-obstruction areas still unresolved. Page 2 used text-based perspective estimation. The browser check also verified that related pages 8 and 9 were not combined without clearer evidence. This is a case-level result, not a measured dataset accuracy score.
