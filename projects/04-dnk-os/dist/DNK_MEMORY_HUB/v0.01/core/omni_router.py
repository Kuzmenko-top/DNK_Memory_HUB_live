"""
omni_router.py — OmniRoute Local wrapper
Єдиний інтерфейс для Claude/Gemini через OmniRoute (localhost:20128).
При недоступності роутера — автоматично fallback на пряме Gemini.
"""
from __future__ import annotations
import os
import re
import json
from loguru import logger
import httpx
from dotenv import load_dotenv

load_dotenv()


class OmniRouter:
    def __init__(self) -> None:
        self.base_url = os.getenv("OMNI_ROUTER_URL", "http://localhost:20128")
        self.api_key = os.getenv("OMNI_ROUTER_API_KEY", "local")
        self.default_model = os.getenv("OMNI_ROUTER_MODEL", "gemini-2.0-flash")
        self.timeout = 120

    def complete(self, prompt: str, model: str | None = None, temperature: float = 0.2) -> str:
        """Sync completion. Повертає текст відповіді."""
        model = model or self.default_model
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                        "max_tokens": 8000,
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except httpx.ConnectError:
            logger.warning(f"⚠️ OmniRoute недоступний ({self.base_url}) — fallback на Gemini")
            return self._gemini_fallback(prompt, temperature)
        except Exception as e:
            logger.error(f"❌ OmniRoute error: {e} — fallback на Gemini")
            return self._gemini_fallback(prompt, temperature)

    def complete_json(self, prompt: str, model: str | None = None, retries: int = 2) -> dict:
        """
        Completion з автоматичним парсингом JSON.
        При невалідному JSON — повторює запит до retries разів з уточненням промпту.
        """
        for attempt in range(retries + 1):
            raw = self.complete(prompt, model=model)
            raw = raw.strip()

            # Знімаємо markdown-обгортку
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            # Знаходимо JSON-об'єкт навіть якщо є текст навколо
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                raw = match.group(0)

            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                if attempt < retries:
                    logger.warning(f"⚠️ JSON parse error (спроба {attempt+1}/{retries+1}): {e}")
                    # Додаємо явне уточнення до промпту при retry
                    prompt = prompt + "\n\nВАЖЛИВО: Поверни ТІЛЬКИ валідний JSON об'єкт. Ніякого тексту до або після. Ніяких markdown блоків."
                else:
                    raise

    def _gemini_fallback(self, prompt: str, temperature: float = 0.2) -> str:
        try:
            from google import genai
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", "")))
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ Gemini fallback також не вдався: {e}")
            raise


router = OmniRouter()
