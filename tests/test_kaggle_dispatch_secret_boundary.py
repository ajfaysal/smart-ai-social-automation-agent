from kaggle_gpu_orchestrator import main
from unittest.mock import patch

def test_dispatch_only_flag_exists():
    with patch("sys.argv", ["kaggle_gpu_orchestrator.py", "--video-url", "https://example.com/video.mp4", "--language", "Bangla", "--dispatch-only", "--dry-run"]):
        assert main() == 0
