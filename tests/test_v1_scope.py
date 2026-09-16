import pytest

from v1_scope import V1_TARGET_LANGUAGES, validate_v1_selection


def test_v1_accepts_chinese_to_bangla_english_hindi():
    assert validate_v1_selection("Chinese (Simplified)", "Bangla").target_language == "Bangla"
    assert validate_v1_selection("Chinese (Simplified)", "English").target_language == "English"
    assert validate_v1_selection("Chinese (Traditional)", "Hindi").target_language == "Hindi"


def test_v1_rejects_non_chinese_source():
    with pytest.raises(ValueError):
        validate_v1_selection("English", "Bangla")


def test_v1_rejects_non_v1_target_without_deleting_future_options():
    assert V1_TARGET_LANGUAGES == {"Bangla", "English", "Hindi"}
    with pytest.raises(ValueError):
        validate_v1_selection("Chinese (Simplified)", "Spanish")


def test_v1_rejects_same_language_certification():
    with pytest.raises(ValueError):
        validate_v1_selection("Chinese (Simplified)", "Chinese (Simplified)")
