import unittest
from unittest.mock import Mock, patch

import text_chat_provider as provider


class TextChatProviderTests(unittest.TestCase):
    @patch.dict("os.environ", {"DUBBING_TEXT_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key", "GEMINI_TEXT_MODEL": "gemini-test"}, clear=True)
    def test_gemini_uses_openai_compatible_endpoint(self):
        response = Mock(ok=True)
        response.json.return_value = {"choices": [{"message": {"content": "  नमस्ते  "}}]}
        session = Mock()
        session.post.return_value = response

        result = provider.chat_completion([{"role": "user", "content": "hello"}], session=session)

        self.assertEqual(result, "नमस्ते")
        args, kwargs = session.post.call_args
        self.assertEqual(args[0], "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["model"], "gemini-test")

    @patch.dict("os.environ", {"DUBBING_TEXT_PROVIDER": "gemini"}, clear=True)
    def test_missing_provider_key_fails_closed(self):
        with self.assertRaisesRegex(provider.TextProviderError, "GEMINI_API_KEY is required"):
            provider.chat_completion([{"role": "user", "content": "hello"}])

    @patch.dict("os.environ", {"DUBBING_TEXT_PROVIDER": "other"}, clear=True)
    def test_unknown_provider_is_rejected(self):
        with self.assertRaisesRegex(provider.TextProviderError, "Unsupported DUBBING_TEXT_PROVIDER"):
            provider.chat_completion([{"role": "user", "content": "hello"}])

    @patch.dict("os.environ", {"DUBBING_TEXT_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"}, clear=True)
    def test_empty_response_is_rejected(self):
        response = Mock(ok=True)
        response.json.return_value = {"choices": [{"message": {"content": "  "}}]}
        session = Mock()
        session.post.return_value = response
        with self.assertRaisesRegex(provider.TextProviderError, "empty assistant content"):
            provider.chat_completion([{"role": "user", "content": "hello"}], session=session)


if __name__ == "__main__":
    unittest.main()
