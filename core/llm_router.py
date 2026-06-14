# core/llm_router.py
"""
Multi-provider LLM router with automatic fallback.

Providers (BYO keys via env):
  - gemini       GOOGLE_API_KEY       (Google Gemini REST API)
  - groq         GROQ_API_KEY         (OpenAI-compatible, free tier)
  - featherless  FEATHERLESS_API_KEY  (OpenAI-compatible, OSS models)
  - aimlapi      AIMLAPI_KEY          (OpenAI-compatible, https://aimlapi.com)

Usage:
    router = LLMRouter()
    text = await router.call_llm("Summarize this incident...", model="auto")

"auto" tries the configured primary first and walks the fallback chain on
any error, so an outage on one provider never stalls the agent pipeline.
"""
import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger("argus.llm_router")

DEFAULT_TIMEOUT = 30.0

OPENAI_COMPAT_ENDPOINTS = {
    "featherless": ("https://api.featherless.ai/v1/chat/completions", "mistralai/Mistral-Small-24B-Instruct-2501"),
    "aimlapi": ("https://api.aimlapi.com/v1/chat/completions", "gpt-4o-mini"),
}

SYSTEM_PROMPT = (
    "You are an expert AI investment partner on the FUSION VC committee. "
    "You evaluate startups with precision, cite evidence, and give decisive recommendations.\n\n"
    "FORMATTING RULES (always follow):\n"
    "- Write in clean, natural prose and short bullet points using '- '.\n"
    "- NEVER use markdown headers (#, ##, ###) or hashtags like #Finance. Use **bold** for emphasis instead.\n"
    "- Use a few tasteful emojis where they help (e.g. 📊 ⚖️ 🚩), never as decoration spam.\n"
    "- No raw JSON, code fences, or developer jargon. Sound like a real, warm, elite human partner."
)


def _is_placeholder(key: Optional[str]) -> bool:
    return not key or "your-" in key or "get-from" in key


class LLMRouter:
    def __init__(self):
        self.keys = {
            "featherless": os.getenv("FEATHERLESS_API_KEY"),
            "aimlapi": os.getenv("AIMLAPI_KEY"),
        }
        # Fallback chain: primary first, then everything else that has a key
        primary = os.getenv("ARGUS_LLM_PRIMARY", "aimlapi")
        if primary not in ("aimlapi", "featherless"):
            primary = "aimlapi"
        chain = [primary] + [p for p in ("aimlapi", "featherless") if p != primary]
        self.chain = [p for p in chain if not _is_placeholder(self.keys.get(p))]

    def available_providers(self) -> list:
        return list(self.chain)

    async def call_llm(
        self,
        prompt: str,
        model: str = "auto",
        max_tokens: int = 2000,
        system: str = SYSTEM_PROMPT,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> str:
        """Route a prompt to a provider, falling back down the chain on errors."""
        providers = self.chain if model == "auto" else [model]
        if not providers:
            raise RuntimeError(
                "No LLM provider configured. Set GOOGLE_API_KEY, GROQ_API_KEY, "
                "FEATHERLESS_API_KEY, or AIMLAPI_KEY."
            )

        last_error: Optional[Exception] = None
        for provider in providers:
            if _is_placeholder(self.keys.get(provider)):
                logger.debug(f"LLM provider '{provider}' has no key — skipping")
                continue
            try:
                return await self._call_openai_compat(provider, prompt, max_tokens, system, timeout)
            except Exception as e:
                logger.warning(f"LLM provider '{provider}' failed: {e} — falling back...")
                last_error = e

        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")

    async def _call_openai_compat(
        self, provider: str, prompt: str, max_tokens: int, system: str, timeout: float = DEFAULT_TIMEOUT
    ) -> str:
        url, default_model = OPENAI_COMPAT_ENDPOINTS[provider]
        payload = {
            "model": os.getenv(f"ARGUS_{provider.upper()}_MODEL", default_model),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        headers = {
            "Authorization": f"Bearer {self.keys[provider]}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


# Lazy global router (env may not be loaded at import time)
_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
