# Provider reliability contract

Optional production providers are never considered successful merely because they are configured.

Each provider execution is represented by an explicit state:

- `unavailable` — dependency, executable, or model is missing.
- `configured` — provider is ready but has not executed.
- `attempted` — execution started but has not been marked successful.
- `succeeded` — execution completed and produced the expected artifact; only this state may set `applied: true`.
- `failed` — execution was attempted and failed; `applied` must remain false.
- `skipped` — the pipeline intentionally did not request or route work to the provider.

The default CI suite tests these invariants without API credentials or model weights. Real provider execution remains an opt-in validation concern.
