from openai import OpenAI

from config import settings
from review_agent.llm.base import BaseLLM


class FastLLM(BaseLLM):
    def __init__(self) -> None:
        self._client: OpenAI | None = None
        if self._has_credentials():
            self._client = OpenAI(
                api_key=settings.FAST_API_KEY,
                base_url=settings.FAST_BASE_URL or None,
            )
            self._model = settings.FAST_MODEL

    def _has_credentials(self) -> bool:
        return bool(settings.FAST_API_KEY and settings.FAST_MODEL)

    def generate(self, prompt: str) -> str:
        if self._stub_enabled():
            return self._stub_response(prompt)
        assert self._client is not None
        response = self._client.chat.completions.create(
            model=settings.FAST_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""
