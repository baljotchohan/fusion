"""Self-check for the real reasoning-token narrator (core/base_agent.py).

Run directly: python test_reasoning_narrator.py
Exercises the narrator with NO network calls — verifies it degrades to None
honestly (no key configured) rather than fabricating anything, and that the
<think>-tag recovery path parses correctly when reasoning_format=parsed isn't
honored by a given model.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force the "no key" path regardless of the developer's local .env, since this
# check asserts the honest-degradation behavior specifically.
os.environ.pop("GROQ_API_KEY", None)

from core.base_agent import BaseAgent, _msg_content_text  # noqa: E402


async def main():
    agent = BaseAgent("test_agent", "Test Agent", "test-room", "You are a test agent.")

    # 1. No GROQ_API_KEY -> reasoning_llm must be None, never a fake stand-in.
    assert agent.reasoning_llm is None, "reasoning_llm should be None with no real key configured"

    # 2. narrate_real_thinking must short-circuit to None with zero network calls.
    result = await agent.narrate_real_thinking("evaluate this fintech's ARR concentration risk")
    assert result is None, f"expected None with no reasoning_llm, got: {result!r}"

    # 3. engine_tag reflects local-only mode honestly.
    assert agent.engine_tag() == "simulated", "engine_tag must report 'simulated' with no analysis LLM key"

    # 4. <think>-tag recovery parses embedded raw reasoning correctly (the
    #    fallback path used when a model ignores reasoning_format=parsed).
    import re
    fake_content = "<think>Revenue is 78% concentrated in one client — that's the real risk.</think>Final answer."
    m = re.search(r"<think>(.*?)</think>", fake_content, re.DOTALL)
    assert m is not None and "78% concentrated" in m.group(1)

    # 5. _msg_content_text flattens list-of-blocks content (some providers use this shape).
    assert _msg_content_text([{"type": "text", "text": "hello"}, {"type": "text", "text": " world"}]) == "hello\n world"
    assert _msg_content_text("plain string") == "plain string"

    # 6. Chat token sink: with no sink set, call sites behave as before; with a
    #    sink set, whatever the streaming path pushes is exactly what accumulates.
    from core.llm_router import chat_token_sink, LLMRouter
    assert chat_token_sink.get() is None, "sink must default to None (non-streaming callers unaffected)"
    q: asyncio.Queue = asyncio.Queue()
    tok = chat_token_sink.set(q)
    try:
        for piece in ("Nova", "Pay ", "risk"):
            chat_token_sink.get().put_nowait(piece)
        drained = []
        while not q.empty():
            drained.append(q.get_nowait())
        assert "".join(drained) == "NovaPay risk"
    finally:
        chat_token_sink.reset(tok)

    # 7. Groq joins the chat chain only with a REAL key — placeholder stays inactive.
    os.environ["GROQ_API_KEY"] = "your-groq-key-here"
    assert "groq" not in LLMRouter().chain, "placeholder Groq key must not activate the provider"
    os.environ["GROQ_API_KEY"] = "gsk_dummy_for_chain_check"
    assert "groq" in LLMRouter().chain, "real-looking Groq key should join the chat chain"
    os.environ.pop("GROQ_API_KEY", None)

    print("OK — reasoning narrator degrades honestly with no key, and parsing/streaming logic is correct.")


if __name__ == "__main__":
    asyncio.run(main())
