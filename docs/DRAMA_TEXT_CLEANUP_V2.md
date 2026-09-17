# Drama text cleanup V2

OCR-guided EasyOCR + OpenCV Telea inpainting is executed before dubbing. The cleanup stage is video-only, and the original audio is temporarily remuxed only so the dubbing pipeline can extract it. Final V1 audio is replacement dialogue only with the original music/dialogue removed.

This is best-effort spatial restoration; final visual QC remains mandatory.
