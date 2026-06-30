"""
Cliente Gemini (Google AI). Usa la API REST directamente para evitar dependencias
pesadas. Modelo configurable vía env GEMINI_MODEL.
"""
import json
import re
from typing import Any

import requests

import config


class GeminiError(Exception):
    pass


_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json(text: str) -> Any:
    """Intenta sacar un JSON válido aunque Gemini lo envuelva en texto/```."""
    cleaned = _strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise GeminiError(f"No se pudo parsear JSON de Gemini: {text[:200]}...")


def _call(prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
    if not config.GEMINI_API_KEY:
        raise GeminiError("GEMINI_API_KEY no configurada. Define la variable de entorno.")

    body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    if system:
        body["systemInstruction"] = {"role": "system", "parts": [{"text": system}]}

    url = _API_URL.format(model=config.GEMINI_MODEL) + f"?key={config.GEMINI_API_KEY}"
    resp = requests.post(url, json=body, timeout=120)
    if resp.status_code != 200:
        raise GeminiError(f"Gemini HTTP {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise GeminiError(f"Respuesta Gemini inesperada: {data}") from e


def generate_json(prompt: str, system: str | None = None) -> Any:
    """Genera texto y lo devuelve ya parseado como JSON."""
    text = _call(prompt, system=system, temperature=0.6)
    return _extract_json(text)


def generate_text(prompt: str, system: str | None = None) -> str:
    """Genera texto plano."""
    return _call(prompt, system=system)
