import httpx
import asyncio
from typing import List

from app.core.config import settings


class GroqError(Exception):
    pass


async def call_groq(messages: List[dict], max_tokens: int = 512, retries: int = 2) -> str:
    """
    Async Groq inference via OpenAI-compatible API.
    Separated from route layer — no direct provider logic in routes.
    """
    if not settings.GROQ_API_KEY:
        raise GroqError("GROQ_API_KEY is not configured.")

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }

    last_error = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.GROQ_BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers,
                )

            if response.status_code == 429:
                # Rate limit — wait and retry
                wait = 2 ** attempt
                await asyncio.sleep(wait)
                last_error = GroqError("Groq rate limit reached. Please try again shortly.")
                continue

            if response.status_code != 200:
                raise GroqError(f"Groq API error: {response.status_code} — {response.text[:200]}")

            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

        except httpx.TimeoutException:
            last_error = GroqError("Groq request timed out. Please try again.")
            await asyncio.sleep(1)
        except GroqError:
            raise
        except Exception as e:
            last_error = GroqError(f"Unexpected error calling Groq: {str(e)}")

    raise last_error or GroqError("Groq call failed after retries.")
