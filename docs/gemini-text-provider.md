# Configurable text provider (Gemini / OpenAI)

The `text_chat_provider.py` adapter is currently standalone. It is **not yet wired into** `drama_dubbing.py` or the Kaggle notebook, so setting these variables alone does not switch the production dubbing pipeline.

## Intended configuration

For Gemini's OpenAI-compatible chat endpoint:

```bash
DUBBING_TEXT_PROVIDER=gemini
GEMINI_API_KEY=<your Gemini API key>
GEMINI_TEXT_MODEL=gemini-2.5-flash
# Optional; defaults to Google's OpenAI-compatible endpoint
GEMINI_OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
```

For OpenAI text chat:

```bash
DUBBING_TEXT_PROVIDER=openai
OPENAI_API_KEY=<your OpenAI API key>
DUBBING_TEXT_MODEL=gpt-4o-mini
```

Do not commit API keys. Add the selected provider's key as a Kaggle Secret only after the notebook is updated to load the selected provider. The current notebook still requires `OPENAI_API_KEY`.

## Scope and safety

This adapter is for text chat only (speaker/character planning and translation). It must not replace the configured STT, reference-voice TTS, Demucs, diarization, or Wav2Lip backends. Provider failures must fail closed; do not silently fall back to a different provider and misrepresent which backend ran.

## Remaining integration work

- Route `director_plan()` and `translate()` through `chat_completion()` while preserving their parsing/validation behavior.
- Update Kaggle notebook secret loading and preflight to require the key corresponding to `DUBBING_TEXT_PROVIDER`.
- Add integration/contract tests for both call sites and notebook configuration.
- Run CI and inspect results before merging or claiming verification.