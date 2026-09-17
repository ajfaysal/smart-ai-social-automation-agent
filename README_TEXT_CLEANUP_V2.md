# Text Cleanup V2

The current Chinese drama pipeline performs OCR-guided visible-text cleanup before dubbing. It uses EasyOCR and OpenCV inpainting, records a cleanup report, then temporarily remuxes the source audio for the existing dubbing pipeline. Final audio follows the V1 replacement-dialogue policy.
