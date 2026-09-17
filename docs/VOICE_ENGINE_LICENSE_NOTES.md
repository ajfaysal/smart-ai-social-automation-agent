# Voice engine licensing notes

The adapter layer intentionally does not vendor model weights.

- CosyVoice, GPT-SoVITS and OpenVoice have different code/model licensing terms; check the exact model checkpoint license before commercial deployment.
- Fish Speech S2 uses the Fish Audio Research License for code/weights; do not assume MIT/commercial permissions from older Fish Speech releases.
- Reference voice recordings must be owned, licensed, or otherwise authorized for cloning.
- The pipeline should record the selected engine/checkpoint identifier in the provider manifest for auditability.
