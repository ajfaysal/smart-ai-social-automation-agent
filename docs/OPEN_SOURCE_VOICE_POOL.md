# Open-source voice pool

Production routing should be engine-agnostic. Candidate engines are selected at runtime and must be pinned/audited by checkpoint and license.

- CosyVoice: Chinese + cross-lingual zero-shot cloning.
- Fish Speech S2: multilingual, multi-speaker, short-reference cloning.
- GPT-SoVITS: Chinese-focused few-shot/zero-shot cloning.
- OpenVoice V2: cross-lingual voice cloning and style controls.

For a 30-character drama, the voice bank should hold 30 stable character references and the router may distribute those characters across the configured engines. A missing engine never changes the character identity; only the synthesis backend changes.
