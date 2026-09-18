from multilingual_voice_routing import voice_for_character


def test_same_character_route_is_stable():
    assert voice_for_character("English", "C1", 0) == voice_for_character("English", "C1", 0)


def test_different_characters_can_use_distinct_voices():
    assert voice_for_character("English", "C1", 0) != voice_for_character("English", "C2", 1)


def test_hindi_has_deterministic_character_voice_route():
    assert voice_for_character("Hindi", "C3", 2) == "shimmer"


def test_explicit_voice_remains_authoritative():
    assert voice_for_character("English", "C1", 0, requested_voice="onyx") == "onyx"
