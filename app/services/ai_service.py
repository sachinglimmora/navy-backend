import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OLLAMA_TIMEOUT = httpx.Timeout(180.0, connect=10.0)


async def chat(messages: list[dict[str, str]], model: str | None = None) -> str:
    """
    Send a chat completion request to Ollama.
    Returns the assistant response string.
    Falls back gracefully if Ollama is unavailable.
    """
    model = model or settings.OLLAMA_MODEL
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
    except httpx.ConnectError:
        logger.warning("Ollama unavailable — returning fallback response")
        return (
            "[AI OFFLINE] The onboard AI model is currently unavailable. "
            "Please contact the maintainer. Doctrine-based response not generated."
        )
    except httpx.TimeoutException:
        logger.warning("Ollama request timed out")
        return (
            "[AI TIMEOUT] The AI model did not respond in time. "
            "Please retry or proceed with manual assessment."
        )
    except Exception as exc:
        logger.error("Ollama chat error: %s", exc)
        return (
            "[AI ERROR] An unexpected error occurred while contacting the AI model. "
            f"Details: {str(exc)}"
        )


async def generate(prompt: str, model: str | None = None) -> str:
    """
    Single-turn text generation via Ollama /api/generate.
    Returns the generated text string.
    """
    model = model or settings.OLLAMA_MODEL
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    except httpx.ConnectError:
        logger.warning("Ollama unavailable for generate — returning fallback")
        return (
            "[AI OFFLINE] Generation unavailable. Ensure Ollama is running and the model is loaded."
        )
    except httpx.TimeoutException:
        logger.warning("Ollama generate timed out")
        return "[AI TIMEOUT] Generation timed out. Please retry."
    except Exception as exc:
        logger.error("Ollama generate error: %s", exc)
        return f"[AI ERROR] {str(exc)}"


async def embed(text: str, model: str | None = None) -> list[float]:
    """
    Generate a vector embedding for the given text via Ollama /api/embeddings.
    Returns a list of floats (embedding vector).
    Falls back to an empty list if unavailable.
    """
    model = model or settings.OLLAMA_MODEL
    payload = {"model": model, "prompt": text}
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
    except httpx.ConnectError:
        logger.warning("Ollama unavailable for embeddings")
        return []
    except httpx.TimeoutException:
        logger.warning("Ollama embed timed out")
        return []
    except Exception as exc:
        logger.error("Ollama embed error: %s", exc)
        return []


async def check_ollama_status() -> dict[str, Any]:
    """Check if Ollama is running and return model info."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name") for m in data.get("models", [])]
                return {
                    "available": True,
                    "status": "online",
                    "models": models,
                    "base_url": settings.OLLAMA_BASE_URL,
                }
    except Exception as exc:
        logger.error("Error checking Ollama status: %s", exc)
    return {
        "available": False,
        "status": "offline",
        "models": [],
        "base_url": settings.OLLAMA_BASE_URL,
    }
