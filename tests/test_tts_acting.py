from tts_acting import acting_directive, normalize_emotion

def test_normalizes_known_emotion():
    assert normalize_emotion(" ANGRY ") == "angry"

def test_unknown_emotion_fails_closed_to_neutral():
    assert normalize_emotion("melodramatic") == "neutral"

def test_directive_is_specific_and_contains_profile():
    text=acting_directive("sad","mature")
    assert "soft" in text.lower()
    assert "mature" in text

def test_directive_is_deterministic():
    assert acting_directive("romantic","adult") == acting_directive("romantic","adult")
