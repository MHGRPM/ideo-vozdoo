import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_engine import ApiKeyEngine, OllamaEngine, build_prompt, get_engine


def test_build_prompt_contains_instruction_and_text():
    prompt = build_prompt("hola mundo", "hazlo formal")
    assert "hola mundo" in prompt
    assert "hazlo formal" in prompt


def test_get_engine_returns_api_key_engine_when_key_set():
    env = {
        "VOZDOO_LLM_API_KEY": "sk-test",
        "VOZDOO_LLM_API_URL": "https://api.openai.com/v1/chat/completions",
        "VOZDOO_LLM_API_MODEL": "gpt-4o-mini",
    }
    engine = get_engine(env)
    assert isinstance(engine, ApiKeyEngine)


def test_get_engine_returns_ollama_engine_when_no_key():
    env = {
        "VOZDOO_LLM_API_KEY": "",
        "VOZDOO_LLM_HOST": "http://localhost:11434",
        "VOZDOO_LLM_MODEL": "qwen2.5:3b-instruct",
    }
    engine = get_engine(env)
    assert isinstance(engine, OllamaEngine)


@patch("llm_engine.requests.post")
def test_ollama_engine_polish_calls_generate_endpoint(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200, json=lambda: {"response": "  texto pulido  "}
    )
    mock_post.return_value.raise_for_status = MagicMock()

    engine = OllamaEngine(host="http://localhost:11434", model="qwen2.5:3b-instruct")
    result = engine.polish("hola", "hazlo formal")

    assert result == "texto pulido"
    called_url = mock_post.call_args.args[0]
    assert called_url == "http://localhost:11434/api/generate"
    payload = mock_post.call_args.kwargs["json"]
    assert payload["model"] == "qwen2.5:3b-instruct"
    assert payload["stream"] is False


@patch("llm_engine.requests.post")
def test_api_key_engine_polish_calls_chat_completions(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"choices": [{"message": {"content": "  texto pulido  "}}]},
    )
    mock_post.return_value.raise_for_status = MagicMock()

    engine = ApiKeyEngine(
        api_url="https://api.openai.com/v1/chat/completions",
        api_key="sk-test",
        model="gpt-4o-mini",
    )
    result = engine.polish("hola", "hazlo formal")

    assert result == "texto pulido"
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer sk-test"
    payload = mock_post.call_args.kwargs["json"]
    assert payload["model"] == "gpt-4o-mini"
    assert payload["messages"][0]["role"] == "user"


def test_api_key_engine_is_available_is_always_true():
    engine = ApiKeyEngine(api_url="x", api_key="sk-test", model="m")
    assert engine.is_available() is True


def test_ollama_engine_is_available_delegates_to_ollama_setup():
    with patch("ollama_setup.is_ollama_running", return_value=True) as mock_check:
        engine = OllamaEngine(host="http://localhost:11434", model="m")
        assert engine.is_available() is True
        mock_check.assert_called_once_with("http://localhost:11434")
