# Demucs provider execution audit

The Demucs source-separation boundary records execution state through the shared provider runtime registry.

## Contract

- `unavailable`: the `demucs` command is not installed.
- `configured`: the command is available but has not executed.
- `attempted`: execution started.
- `succeeded`: `no_vocals.wav` exists, is a file, has a minimum valid artifact size, and has the expected `.wav` suffix.
- `failed`: execution failed or the expected artifact was missing/invalid.
- `skipped`: reserved for deliberate future pipeline skips.

Only a validated `succeeded` execution can have `applied: true`.

## Safety

The provider never treats a successful process exit as sufficient. Missing or invalid background output fails closed, preventing the manifest from claiming that background preservation succeeded when it did not.

The deterministic tests do not download model weights or call external services.

## Integration status

This module is the audited provider boundary. The remaining integration step is to replace the legacy `separate_background()` implementation in `drama_dubbing.py` with this boundary and include the runtime snapshot in the top-level final manifest.
