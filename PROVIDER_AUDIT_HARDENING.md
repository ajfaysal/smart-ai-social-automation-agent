# Provider audit hardening

Provider execution records are intended to be auditable and fail closed.

Rules:
- `applied=true` is valid only with `state=succeeded`.
- Failed, skipped, and unavailable terminal states require an explicit reason.
- QC validates the provider snapshot before it is exposed as a successful audit result.
- Heavy model execution remains opt-in; default CI remains credential-free and model-weight-free.

The runtime registry remains compatible with existing provider integrations; request isolation is a follow-up implementation concern where the deployment handles concurrent jobs in one process.
