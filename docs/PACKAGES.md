# Document package workflow

## Scope

ScanPilot accepts one PDF or up to 20 photos. PDF imports render a bounded preview per page; native text pages without image objects are recognized conservatively and retain the original PDF page by default. Image-bearing pages receive visual checks, including pages with an existing OCR layer. Native classification is not certification of the page's content or layout.

The browser owns the package, original PDF, page images, results, second photos and manual region selections. Requests are stateless and no document session is stored on the server. Refresh closes this in-memory workspace. Failed imports leave the current package intact. A failed page can be retried without reprocessing successful pages.

## Inspection and review

Pages are inspected sequentially with progress and a stop-after-current-page control. The queue prioritizes failures and pages requiring evidence, then improved and review-ready pages. Page numbers always refer to original order. The page editor reuses all region recovery, source comparison and review exports. A second photo is matched against the selected page; it is not silently routed to an arbitrary page.

Opening another page preserves each page's result, second photo and manual selections. The user can choose whether the current result replaces that page on export. Unresolved original pages are retained by default. A successful partial recovery may be included while remaining issues stay in the report. The package export is a review copy, not a certification that every page is correct.

## PDF export

Every original page is included in its original order. Unchanged PDF pages are copied without rasterizing native text/graphics. Corrected pages are rendered as image pages, fitted to the source page dimensions. Image-only packages become a multipage PDF. Unresolved region outlines are drawn on included processed pages. A JSON report is available separately and embedded as an attachment in the PDF.

The renderer uses PDFium behind a process-local mutex; the parser/writer uses pypdf. See [PDFium thread-safety and object lifetime](https://pypdfium2.readthedocs.io/en/stable/python_api.html) and [pypdf page merging](https://pypdf.readthedocs.io/en/stable/user/merging-pdfs.html).

Limits: 20 PDF pages, 20 MB original PDF, 12 MB and 24 MP per uploaded photo, 80 MB per package export and 50 MP across decoded export images. Interactive/signed PDFs are rejected instead of silently flattening forms or signatures. Password-protected PDFs must be unlocked before use. Very large or malformed files may be rejected. Images are resized for the document inspection workflow; raw camera-resolution archival storage is not provided.

## Validation

`tests/test_package.py` checks mixed native/raster import, native text preservation, unchanged unresolved pages, original order, report attachment, export dimensions, encryption, malformed input, page limits and API routes. `tools/make_package_fixture.py` creates a synthetic three-page native/scan PDF and renders exports for visual inspection. `tools/check_package_browser.py` exercises PDF triage, per-page recovery, page state restoration, export text/order/report, both languages, responsive widths and preservation after failed import.

AWS deployment is still pending. The same stateless routes fit the existing ECS container; PDF libraries are pinned in runtime requirements. Linux build and cloud memory/latency measurements still require verification before hosting.
