import json

from audio_policy import AudioPolicy, V1_AUDIO_POLICY, describe_policy, validate_policy
from kaggle_full_pipeline import build_notebook


def test_full_notebook_is_secret_free_and_uses_canonical_pipeline():
    notebook = build_notebook(
        "https://drive.google.com/file/d/FILE_ID/view?usp=sharing",
        "ajfaysal/smart-ai-social-automation-agent",
        "main",
        "Chinese (Simplified)",
    )
    source = "".join(notebook["cells"][0]["source"])
    assert notebook["nbformat"] == 4
    assert "UserSecretsClient" in source
    assert "OPENAI_API_KEY" in source
    assert "WAV2LIP_CHECKPOINT_URL" in source
    assert "WAV2LIP_S3FD_URL" in source
    assert "dub_video(" in source
    assert "preserve_background=False" in source
    assert "add_mood_music=False" in source
    assert "original_dialogue_removed" in source
    assert "original_music_removed" in source
    assert "KAGGLE_API_TOKEN" not in source
    json.dumps(notebook)


def test_bangla_notebook_uses_neural_multicharacter_voice_pool_and_replacement_mix():
    notebook = build_notebook(
        "https://drive.google.com/file/d/FILE_ID/view?usp=sharing",
        "ajfaysal/smart-ai-social-automation-agent",
        "main",
        "Bangla",
    )
    source = "".join(notebook["cells"][0]["source"])
    assert "edge-tts" in source
    assert "synthesize_bangla" in source
    assert "natural_bangla_tts" in source
    assert "acting_directive=None" in source
    assert "acting_directive=acting_directive" in source
    assert "replacement-dialogue-only-no-original-music" in source
    assert "BANGLA_CHARACTER_VOICE_POOL" in source
    assert source.count("bn_c") >= 10
    assert "preserve_background=False" in source
    assert "add_mood_music=False" in source
    assert "lip_sync=True" in source
    assert "KAGGLE_API_TOKEN" not in source
    json.dumps(notebook)


def test_v1_audio_policy_requires_dialogue_and_music_replacement():
    assert describe_policy() == {
        "remove_original_dialogue": True,
        "remove_original_music": True,
        "preserve_original_sfx": False,
    }
    validate_policy(V1_AUDIO_POLICY)


def test_audio_policy_rejects_dialogue_or_music_preservation():
    for policy in (
        AudioPolicy(remove_original_dialogue=False),
        AudioPolicy(remove_original_music=False),
    ):
        try:
            validate_policy(policy)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid V1 audio policy was accepted")
