"""Motores de IA para pulir texto: Ollama local o una API key personal
(formato chat completions compatible con OpenAI, sirve también para
Gemini vía su capa de compatibilidad).

La personalidad va en el prompt de sistema (ver `polish_actions.py`) y la
tarea concreta en el mensaje de usuario. Mezclarlo todo en un solo bloque
de texto, como se hacía antes, daba resultados mucho más flojos: el
modelo trataba las reglas de comportamiento como parte del encargo."""

from __future__ import annotations

import requests

TIMEOUT = 180   # un prompt profesional largo en CPU no sale en 60 s

DEFAULT_SYSTEM = (
    "Eres un editor profesional de textos en español de España. Devuelves "
    "SOLO el texto resultante, sin explicaciones ni comillas."
)


def build_prompt(text: str, instruction: str) -> str:
    return (
        f"Instrucción: {instruction}\n\n"
        f"Texto dictado:\n{text}\n\n"
        "Devuelve SOLO el resultado."
    )


class LLMEngine:
    def polish(
        self,
        text: str,
        instruction: str,
        system: str = DEFAULT_SYSTEM,
        temperature: float = 0.3,
    ) -> str:
        raise NotImplementedError

    def is_available(self) -> bool:
        raise NotImplementedError


class OllamaEngine(LLMEngine):
    def __init__(self, host: str, model: str):
        self.host = host.rstrip("/")
        self.model = model

    def polish(
        self,
        text: str,
        instruction: str,
        system: str = DEFAULT_SYSTEM,
        temperature: float = 0.3,
    ) -> str:
        prompt = build_prompt(text, instruction)
        resp = requests.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {"temperature": temperature, "num_ctx": 8192},
            },
            timeout=TIMEOUT,
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

    def polish(
        self,
        text: str,
        instruction: str,
        system: str = DEFAULT_SYSTEM,
        temperature: float = 0.3,
    ) -> str:
        prompt = build_prompt(text, instruction)
        resp = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
            },
            timeout=TIMEOUT,
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
