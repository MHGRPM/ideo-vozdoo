import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ollama_setup import (
    is_ollama_running,
    linux_mac_install_command,
    run_install_linux_mac,
    pull_model,
)


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

    # Assert on call_args to verify correct endpoint and payload
    assert mock_post.call_args == call(
        "http://localhost:11434/api/pull",
        json={"model": "qwen2.5:3b-instruct", "stream": True},
        stream=True,
        timeout=None,
    )

    assert len(seen) == 2
    assert seen[0] == "downloading"
    assert seen[-1] == "success"


@patch("ollama_setup.subprocess.Popen")
def test_run_install_linux_mac_succeeds_on_fallback_terminal(mock_popen):
    """Test that terminal-fallback succeeds on a later candidate when first ones fail."""
    # First 3 candidates (x-terminal-emulator, gnome-terminal, konsole) fail
    # Fourth candidate (xterm) succeeds
    mock_popen.side_effect = [
        FileNotFoundError(),
        FileNotFoundError(),
        FileNotFoundError(),
        MagicMock(),  # xterm succeeds
    ]

    result = run_install_linux_mac()

    assert result is not None
    assert mock_popen.call_count == 4


@patch("ollama_setup.subprocess.Popen")
def test_run_install_linux_mac_raises_on_all_terminals_fail(mock_popen):
    """Test that RuntimeError is raised when all terminal candidates fail."""
    # All candidates fail
    mock_popen.side_effect = FileNotFoundError()

    try:
        run_install_linux_mac()
        assert False, "Expected RuntimeError to be raised"
    except RuntimeError as e:
        assert "No se encontró un emulador de terminal" in str(e)
