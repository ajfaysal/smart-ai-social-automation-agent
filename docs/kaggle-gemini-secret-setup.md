# Safe Gemini API key setup for Kaggle

Never commit an API key to GitHub, notebook source, logs, or chat messages. The key is not needed to implement or test the provider integration.

## Once Gemini text-provider integration is merged

1. Open Google AI Studio and create/copy a Gemini API key.
2. In Kaggle, open the account's **Add-ons / Secrets** panel for the certification notebook.
3. Add a secret named `GEMINI_API_KEY` and paste the key into Kaggle's secret-value field.
4. Set the notebook's text provider to `gemini` (the integrated notebook should expose this as a configuration option).
5. Run the notebook. Confirm its preflight reports Gemini as the selected text provider without printing the key.

Keep the key in Kaggle Secrets only. Do not paste it into a notebook cell, GitHub issue, pull request, commit, or ChatGPT message.

## Important status

This guide does not itself enable Gemini in the production dubbing pipeline. The provider adapter must first be wired into `director_plan()` and `translate()`, and the Kaggle notebook must load the selected provider's secret. Gemini is intended for text planning/translation only; the local Whisper, reference-voice TTS, Demucs, diarization, and Wav2Lip stages remain separate.