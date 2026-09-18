import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ollama_setup import is_ollama_running, linux_mac_install_command, pull_model


@patch("ollama_setup.requests.get")
def test_is_ollama_running_true_on_200(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    assert is_ollama_running("http://localhost:11434") is True


@patch("ollama_setup.requests.get")
def test_is_ollama_running_false_on_connection_error(mock_get):
    mock_get.side_effect = Exception("connection refused")
    assert is_ollama_running("http://localhost:11434") is False


def test_linux_mac_install_command_uses_official_script():
    cmd = linux_mac_install_command()
    assert "curl" in cmd
    assert "ollama.com/install.sh" in cmd
    assert "sh" in cmd


@patch("ollama_setup.requests.post")
def test_pull_model_reports_progress(mock_post):
    fake_lines = [
        b'{"status": "downloading", "completed": 10, "total": 100}',
        b'{"status": "success"}',
    ]
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = fake_lines
    mock_response.__enter__ = lambda self: mock_response
    mock_response.__exit__ = lambda self, *a: None
    mock_post.return_value = mock_response

    seen = []
    pull_model("http://localhost:11434", "qwen2.5:3b-instruct", on_progress=seen.append)

    assert len(seen) == 2
    assert "downloading" in seen[0] or "success" in seen[-1]
