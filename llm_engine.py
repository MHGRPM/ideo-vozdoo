"""Motores de IA para pulir texto: Ollama local o una API key personal
(formato chat completions compatible con OpenAI, sirve también para
Gemini vía su capa de compatibilidad).

La personalidad va en el prompt de sistema (ver `polish_actions.py`) y la
tarea concreta en el mensaje de usuario. Mezclarlo todo en un solo bloque
de texto, como se hacía antes, daba resultados mucho más flojos: el
modelo trataba las reglas de comportamiento como parte del encargo."""

from __future__ import annotations

import requests

TIMEOUT = 240   # un prompt profesional largo en CPU no sale en 60 s
DEFAULT_OLLAMA_MODEL = "qwen3:4b-instruct"
# Mantener el modelo cargado en memoria entre órdenes: la primera tarda en
# cargar desde disco, las siguientes empiezan a escribir al momento.
KEEP_ALIVE = "30m"

DEFAULT_SYSTEM = (
    "Eres un editor profesional de textos en español de España. Devuelves "
    "SOLO el texto resultante, sin explicaciones ni comillas."
)


def build_prompt(text: str, instruction: str) -> str:
    return (
        f"ENCARGO: {instruction}\n\n"
        f"TEXTO SOBRE EL QUE TRABAJAR:\n<<<\n{text}\n>>>\n\n"
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
                "keep_alive": KEEP_ALIVE,
                "options": {"temperature": temperature, "num_ctx": 8192},
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()

    def is_available(self) -> bool:
        from ollama_setup import has_model, is_ollama_running

        return is_ollama_running(self.host) and has_model(self.host, self.model)

    def warm_up(self) -> None:
        """Carga el modelo en memoria sin generar nada, para que la primera
        orden del día no espere a leerlo del disco."""
        requests.post(
            f"{self.host}/api/generate",
            json={"model": self.model, "keep_alive": KEEP_ALIVE},
            timeout=TIMEOUT,
        )


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
        model=env.get("VOZDOO_LLM_MODEL") or DEFAULT_OLLAMA_MODEL,
    )
