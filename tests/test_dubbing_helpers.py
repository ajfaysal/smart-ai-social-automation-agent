from drama_dubbing import LANGUAGES, VOICES, SUPPORTED_EXTENSIONS


def test_chinese_languages_are_available():
    assert LANGUAGES["Chinese (Simplified)"] == "zh-CN"
    assert LANGUAGES["Chinese (Traditional)"] == "zh-TW"


def test_supported_video_formats():
    assert {".mp4", ".mov", ".mkv", ".webm", ".avi"}.issubset(SUPPORTED_EXTENSIONS)


def test_voice_pool_is_valid():
    assert VOICES
    assert len(VOICES) >= 6
