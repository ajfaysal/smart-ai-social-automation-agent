# Drama text cleanup

The Chinese-drama V1 pipeline runs OCR-guided visible-text cleanup before dubbing and lip-sync.

## Contract

- Input: validated video with its original audio.
- OCR: EasyOCR (`ch_sim`, `en` by default).
- Restoration: OpenCV Telea inpainting.
- Scene cuts reset the carried OCR mask.
- Optional normalized fixed regions can cover persistent logos/watermarks/stickers.
- Cleanup itself writes video only; the original audio is temporarily muxed back so the normal dubbing pipeline can extract it.
- The final dubbing stage replaces the original dialogue/music audio bed according to `V1_AUDIO_POLICY`.

## Quality boundary

This is spatial best-effort restoration. Text over faces, moving backgrounds, or complex repeated watermarks can leave artifacts and may require a temporal/neural restoration provider in a later version. The cleanup report must be retained and final visual QC remains mandatory.
