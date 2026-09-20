import unittest
from unittest.mock import Mock, patch

import text_chat_provider as provider


class TextChatProviderErrorTests(unittest.TestCase):
    @patch.dict("os.environ", {"DUBBING_TEXT_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"}, clear=True)
    def test_http_error_does_not_expose_provider_response_body(self):
        response = Mock(ok=False, status_code=403, text="sensitive provider diagnostic")
        session = Mock()
        session.post.return_value = response

        with self.assertRaises(provider.TextProviderError) as raised:
            provider.chat_completion([{"role": "user", "content": "hello"}], session=session)

        self.assertIn("HTTP 403", str(raised.exception))
        self.assertNotIn("sensitive provider diagnostic", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
