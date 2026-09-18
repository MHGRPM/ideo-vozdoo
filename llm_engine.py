"""Motores de IA para pulir texto: Ollama local o una API key personal
(formato chat completions compatible con OpenAI, sirve también para
Gemini vía su capa de compatibilidad)."""

from __future__ import annotations

import requests


def build_prompt(text: str, instruction: str) -> str:
    return (
        "Eres un asistente de escritura. Se te da un texto dictado por voz "
        "y una instrucción sobre cómo reescribirlo.\n\n"
        f"Instrucción: {instruction}\n\n"
        f"Texto original:\n{text}\n\n"
        "Devuelve SOLO el texto reescrito, sin explicaciones ni comillas."
    )


class LLMEngine:
    def polish(self, text: str, instruction: str) -> str:
        raise NotImplementedError

    def is_available(self) -> bool:
        raise NotImplementedError


class OllamaEngine(LLMEngine):
    def __init__(self, host: str, model: str):
        self.host = host.rstrip("/")
        self.model = model

    def polish(self, text: str, instruction: str) -> str:
        prompt = build_prompt(text, instruction)
        resp = requests.post(
            f"{self.host}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()

    def is_available(self) -> bool:
        from ollama_setup import is_ollama_running

        return is_ollama_running(self.host)


class ApiKeyEngine(LLMEngine):
    def __init__(self, api_url: str, api_key: str, model: str):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model

    def polish(self, text: str, instruction: str) -> str:
        prompt = build_prompt(text, instruction)
        resp = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def is_available(self) -> bool:
        return True


def get_engine(env: dict[str, str]) -> LLMEngine:
    api_key = env.get("VOZDOO_LLM_API_KEY", "").strip()
    if api_key:
        return ApiKeyEngine(
            api_url=env.get(
                "VOZDOO_LLM_API_URL", "https://api.openai.com/v1/chat/completions"
            ),
            api_key=api_key,
            model=env.get("VOZDOO_LLM_API_MODEL", "gpt-4o-mini"),
        )
    return OllamaEngine(
        host=env.get("VOZDOO_LLM_HOST", "http://localhost:11434"),
        model=env.get("VOZDOO_LLM_MODEL", "qwen2.5:3b-instruct"),
    )
