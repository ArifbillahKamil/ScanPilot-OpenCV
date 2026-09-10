# ScanPilot

[English](README.en.md) | [Bahasa Indonesia](README.md)

Inspect an entire PDF or photo package, prioritize the pages that need attention, and recover covered regions using a second photo of the selected page. OpenCV 5 aligns the evidence, local OCR reads it, and recovered regions retain their sources. Missing numbers are never generated.

## Run locally

Use Python 3.12. From the project directory on Windows:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

On macOS/Linux, use `.venv/bin/python` instead of `.venv\Scripts\python` after creating the environment. The Windows environment has been tested; the Linux Docker build still requires validation.

Open http://127.0.0.1:8765. The interface defaults to English. Use the language selector in the header to switch to Indonesian; the browser remembers your preference. Switching languages preserves the active document, manual regions, and comparison view. OCR text and user filenames are never translated.

## Try the demo

1. Upload one PDF or a set of photos, or choose **Try a three-page sample**.
2. Watch the per-page checks. Pages needing attention appear first; exports retain the original order.
3. Open a flagged page, inspect its guidance, and add a second photo of that same page when needed.
4. Review source crops and decide whether to use the result in the package export.
5. Return to all pages and export one reviewed PDF plus its JSON report. The PDF also contains the report as an attachment.

Samples are generated documents and processed on demand. English and Indonesian sample pages are available. If you change the interface language after choosing a sample, its second photo retains the first sample's language so the images still describe the same document.

## Three core features

- **Inspect and read:** JPEG/PNG/WebP upload, EXIF orientation, page detection, perspective and lighting correction, OCR scores, and uncertain-region markers.
- **Recover from a second photo:** capture guidance, manual region selection, SIFT/RANSAC alignment, conflicting-reading checks, evidence-backed region copies, and OCR verification of the composite.
- **Review the evidence:** image/OCR comparisons, source crops, unresolved markers, process traces, and exports. Interface messages and export annotations follow the selected language; document text remains verbatim.

Limits: 20 pages per package; one PDF up to 20 MB or photos up to 12 MB / 24 MP each. Recovery uses two photos for the selected page. Package export is capped at 80 MB per request and 50 MP across raster replacements. Unchanged PDF pages retain their original text and graphics; corrected image pages are rasterized. Interactive, signed, password-protected PDFs, HEIC, and generative completion are not supported. Refreshing the tab clears the in-memory package. See [package workflow](docs/PACKAGES.md).

## Architecture and AWS status

FastAPI serves the frontend and runs OpenCV 5 and RapidOCR / ONNX Runtime. A bounded policy planner selects processing steps and requests new visual evidence. It does not use a language model. Requests are stateless; the browser resubmits both images for recovery. The application does not store document history.

AWS deployment artifacts are included: `Dockerfile`, `infra/ecs-express.yaml`, and `tools/deploy_aws.py`. ECS Express Mode is configured to run the full processing pipeline on Fargate, with ECR, Secrets Manager, and CloudWatch support. The hosted application uses a demo password. **A live AWS deployment and cloud performance/cost measurements have not been validated.**

Preview the deployment plan without making AWS calls:

```powershell
.venv\Scripts\python tools/deploy_aws.py --region ap-southeast-1
```

The `--apply` option creates billable resources and requires configured AWS access, Docker with Linux containers, and an appropriate VPC. Review the template before deploying. In local mode, images remain on the local server; in AWS mode, uploaded photos are processed on AWS servers. The footer identifies the runtime.

## Validation and limitations

The original workflow passed 20 backend tests and desktop/mobile browser checks. Five synthetic pairs with new amounts recovered the hidden amount from the second image; direct OCR and fixed preprocessing could not read the covered amount. This is a single-template synthetic experiment, not a real-photo accuracy benchmark. See `docs/benchmark-synthetic.json` for measurements and `docs/I18N.md` for language-specific checks.

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
node tests/test_i18n.cjs
node --check static/app.js
node --check static/recovery.js
node --check static/i18n.js
```

OCR scores are not calibrated probabilities of correctness. White covers may require manual marking. Visual matching cannot prove that two photos show the same physical page; different documents with differences only in a hidden region can be indistinguishable. Results require human review. A small set of real phone photos has been tested; this is not a general accuracy benchmark. The Linux container build, AWS deployment, and human design-review checklist remain outstanding.

OCR uses [RapidOCR](https://github.com/RapidAI/RapidOCR); see upstream licensing and model attribution. Historical planning documents and the user-provided master prompt are retained in their original language.
