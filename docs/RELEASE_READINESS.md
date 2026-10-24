# Deployment candidate — 23 October 2026

## Changes

- Added conservative colour-based paper candidates when standard edge detection fails. All four sides need contrast, convex geometry and sufficient area; photo-frame contours are rejected. The neutral sheet on a light tabletop now crops to the paper. Curled paper and ambiguous boundaries remain limitations.
- Recovered patches use a bounded exposure multiplier estimated from surrounding bright pixels. The replacement text remains sourced from the second photo; old text is never blended into it. This reduces exposure discontinuity but does not guarantee invisible seams on patterned or strongly coloured backgrounds.
- Uncertain OCR and uncertain page boundaries request review, not automatically a new photograph. Blur, absent OCR, physical obstruction and unresolved manual regions still require evidence. Unresolved regions remain visible in the package attention list and exports.

## Validation

- 44 existing Python tests passed after the changes.
- Four release-specific tests passed: neutral-background rejection, real-sheet crop, exposure/ink preservation, and review versus retake.
- JavaScript localization, package follow-up and browser integration passed, including PDF export/import order, recovery, both languages, and mobile layouts.
- Original benchmark remains at `output/benchmark-camera/`; new run is at `output/benchmark-release/`. The extra samples are now development/regression examples because the boundary change was informed by them. They must not be presented as independent accuracy evidence. Runtime measurements were collected alongside tests/build work and are not suitable for a latency comparison.

## Local Linux verification commands

Build `scanpilot:local-validated` passed on Linux/amd64 with dependency consistency and OCR model initialization checks. Image config digest: `sha256:f325d4c92e3789fe27629723f11ea6acfcaa2353d759acbb46a845aa2cf69d10`. The HTTP smoke test passed on port 8877: OpenCV 5.0.0, one recovered synthetic region, and successful PDF export/import with embedded report. This is a local Linux validation, not a live AWS deployment.

```powershell
docker build --platform linux/amd64 -t scanpilot:local-validated .
docker run --rm -d --name scanpilot-release-check -p 127.0.0.1:8877:8080 scanpilot:local-validated
.venv\Scripts\python tools/smoke_deployment.py --url http://127.0.0.1:8877
docker stop scanpilot-release-check
```

The smoke test uses synthetic documents to exercise health, OCR, two-photo recovery, and PDF export/import through HTTP. It does not send user documents to AWS.

## AWS handoff

The deployment template uses ECS Express Gateway Service. Its resource properties were checked against the [AWS CloudFormation reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ecs-expressgatewayservice.html). This documentation check is not an AWS-side template validation or deployment.

No AWS profile is configured in the current local session. Configure account access privately, then review the plan:

```powershell
.venv\Scripts\python tools/deploy_aws.py --region ap-southeast-1
```

Actual deployment uses `--profile <profile> --apply` and creates billable resources. After deployment, run the smoke test against its HTTPS endpoint with the demo password supplied through the `SCANPILOT_PASSWORD` environment variable. See `docs/AWS.md` for the full procedure. Cloud IAM/VPC availability, HTTPS endpoint, cloud latency and costs remain unverified until a live deployment succeeds.
