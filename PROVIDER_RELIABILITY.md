# Provider reliability contract

Optional production providers are never considered successful merely because they are configured.

States: `unavailable`, `configured`, `attempted`, `succeeded`, `failed`, and `skipped`.

Only `succeeded` may set `applied: true`. Failure and fallback reasons are retained as data for the manifest/QC layer. Default CI remains credential-free; real model execution is opt-in.
