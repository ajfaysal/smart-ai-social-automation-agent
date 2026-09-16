import pytest

from core_language_config import SOURCE_LANGUAGES, TARGET_LANGUAGES, validate_target_language
from v1_dubbing import selected_target


def test_v1_keeps_mandarin_sources_and_limits_launch_targets():
    assert SOURCE_LANGUAGES == {
        "Chinese (Simplified)": "zh-CN",
        "Chinese (Traditional)": "zh-TW",
    }
    assert TARGET_LANGUAGES == {
        "Bangla": "bn",
        "English": "en",
        "Hindi": "hi",
    }


def test_selected_target_routes_to_chinese_source():
    assert selected_target("Bangla") == {"label": "Bangla", "code": "bn", "source": "zh"}
    assert selected_target("English") == {"label": "English", "code": "en", "source": "zh"}
    assert selected_target("Hindi") == {"label": "Hindi", "code": "hi", "source": "zh"}


def test_future_language_registry_is_not_deleted_but_v1_rejects_non_v1_targets():
    with pytest.raises(ValueError):
        validate_target_language("Spanish")
