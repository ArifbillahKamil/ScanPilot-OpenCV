# Automatic multi-issue diagnosis

## Cropped-page follow-up

The reported real photograph was subsequently located locally and reproduced. Page corners were outside the frame, so contour rectification could not run. An OCR-line orientation fallback now requires at least five confident, sufficiently long lines with 70% agreement within three degrees. It rotates on an expanded canvas without cutting away visible content; it does not claim perspective rectification. Possible colored obstructions are not inferred from the entire scene when page boundaries are unknown.

On the supplied real photo, estimated text tilt changed from -9.38 degrees to 0.0 degrees after processing, and the result was visually inspected. This is one real case, not a general accuracy benchmark. The local output is in ignored artifacts/real-photo-straightened.jpg; the personal photo and its OCR contents are not included in the source archive.

September 9, 2026: addressed a user report that real photos appeared unchanged or became monochrome.

The lighting operation previously converted the document to grayscale. It now estimates illumination and applies the same bounded gain to all BGR channels, retaining colored ink. Blur no longer prevents lighting correction: the checks run independently. Severe blur still requests another exposure, even when lighting or geometry is corrected.

The report lists suspected blur, page tilt, perspective distortion, uneven lighting, unclear page boundaries, possible obstructions and uncertain OCR as independent issues. Each issue has an action. Geometry is estimated from four page corners; uncertain boundaries do not produce a confident tilt estimate. Page detection considers soft edges and a bright foreground mask as well as strong edges.

Blur remains a heuristic based on normalized Laplacian variance, not a trained classifier. Blank pages, low contrast and sparse text can also produce weak-detail readings. Bright artwork and backgrounds can confuse page detection; colored artwork can be flagged as a possible obstruction. There is no generative deblurring or invention of hidden text.

Regression coverage includes a combined blurred, tilted, perspective-distorted and shadowed fixture; colored-ink hue preservation; clear-page negative detection; existing two-photo recovery; bilingual diagnosis and mobile layout. These are synthetic checks. The follow-up above records the subsequent real-photo reproduction.

## Perspective follow-up (September 10)

Added constrained continuation of four visible paper edges when corners are clipped. Frame boundaries are excluded from edge evidence; all four edges, bounded extrapolation and at least 90% photo coverage are required. Estimated corners remain explicitly unverified. The output crops the page and retains gray areas for missing camera evidence. This does not dewarp curved paper. The same real photograph was processed and visually inspected in artifacts/real-photo-perspective.jpg.

