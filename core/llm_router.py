# core/llm_router.py
"""
LLM router for the conversational *chat* path (the agents' due-diligence
analysis path lives in core/base_agent.py and runs on Featherless).

Providers (BYO keys via env) — both hackathon partner APIs:
  - aimlapi      AIMLAPI_KEY          (OpenAI-compatible, https://aimlapi.com)
  - featherless  FEATHERLESS_API_KEY  (native Featherless API. If you only have
                                        a HuggingFace hf_ token, set
                                        ARGUS_FEATHERLESS_BASE_URL=https://
                                        router.huggingface.co/featherless-ai/v1)

Usage:
    router = LLMRouter()
    text = await router.call_llm("Summarize this deal...", model="auto")

"auto" tries the chat primary (AIML) first and falls back to Featherless on
error. If the chain is empty (no keys), callers fall back to the deterministic
local engine, so the chat path never stalls.
"""
import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger("argus.llm_router")

DEFAULT_TIMEOUT = 30.0

OPENAI_COMPAT_ENDPOINTS = {
    # provider: (base_url_env_var, default_base_url, default_model)
    "aimlapi": ("ARGUS_AIMLAPI_BASE_URL", "https://api.aimlapi.com/v1", "gpt-4o-mini"),
    "featherless": (
        "ARGUS_FEATHERLESS_BASE_URL",
        "https://api.featherless.ai/v1",
        "Qwen/Qwen2.5-72B-Instruct",
    ),
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
        # Ensure .env keys are present regardless of when the router is first
        # built (it caches keys at construction). Mirrors base_agent's load.
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except Exception:
            pass
        self.keys = {
            "aimlapi": os.getenv("AIMLAPI_KEY"),
            "featherless": os.getenv("FEATHERLESS_API_KEY"),
        }
        # Chat runs on AIML first, then falls back to Featherless. ARGUS_LLM_PRIMARY
        # can override the chat primary; default is aimlapi.
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
        # Non-"auto" model strings are provider keys (e.g. "aimlapi"), not model names.
        # If the string isn't a known provider key, fall back to the full chain so
        # callers passing a model name (e.g. "gpt-4o-mini") don't silently get nothing.
        providers = self.chain if model == "auto" or model not in self.keys else [model]
        if not providers:
            raise RuntimeError("No LLM provider configured. Set AIMLAPI_KEY and/or FEATHERLESS_API_KEY.")

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
        base_env, default_base, default_model = OPENAI_COMPAT_ENDPOINTS[provider]
        url = os.getenv(base_env, default_base).rstrip("/") + "/chat/completions"
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
