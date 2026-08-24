"""LLM provider abstraction. Default: DeepSeek (OpenAI-compatible). Tests use FakeProvider."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResult:
    text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    model: str


class LLMProvider(Protocol):
    def complete(
        self, system: str, user: str, temperature: float = 0.2, max_tokens: int = 900
    ) -> LLMResult: ...


class FakeProvider:
    """Deterministic provider for tests: `responder(system, user) -> str`."""

    def __init__(self, responder: Callable[[str, str], str] | str = "OK"):
        self._responder = responder
        self.calls: list[tuple[str, str]] = []

    def complete(
        self, system: str, user: str, temperature: float = 0.2, max_tokens: int = 900
    ) -> LLMResult:
        self.calls.append((system, user))
        text = self._responder(system, user) if callable(self._responder) else self._responder
        return LLMResult(
            text=text,
            tokens_in=len(user) // 4,
            tokens_out=len(text) // 4,
            cost_usd=0.0,
            model="fake",
        )


class OpenAICompatibleProvider:
    def __init__(
        self, api_key: str, base_url: str, model: str, price_in_per_m: float, price_out_per_m: float
    ):
        from openai import OpenAI  # imported lazily: tests never need it

        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self._pin = price_in_per_m
        self._pout = price_out_per_m

    def complete(
        self, system: str, user: str, temperature: float = 0.2, max_tokens: int = 900
    ) -> LLMResult:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        tin = usage.prompt_tokens if usage else 0
        tout = usage.completion_tokens if usage else 0
        cost = tin / 1e6 * self._pin + tout / 1e6 * self._pout
        return LLMResult(text=text, tokens_in=tin, tokens_out=tout, cost_usd=cost, model=self.model)


def provider_from_settings() -> LLMProvider:
    from pedibot.settings import get_settings

    s = get_settings()
    if s.llm_provider == "deepseek":
        if not s.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY missing in .env")
        return OpenAICompatibleProvider(
            s.deepseek_api_key,
            s.deepseek_base_url,
            s.deepseek_model,
            s.llm_price_in_per_m,
            s.llm_price_out_per_m,
        )
    if s.llm_provider == "fake":
        return FakeProvider()
    raise RuntimeError(f"unsupported LLM_PROVIDER={s.llm_provider}")
