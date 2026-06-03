from openai import OpenAI

from config import settings
from review_agent.llm.base import BaseLLM


class ProLLM(BaseLLM):
    """Primary (pro) or secondary (pro2) professional model."""

    def __init__(self, profile: str = "pro") -> None:
        if profile not in ("pro", "pro2"):
            raise ValueError(f"Invalid Pro profile: {profile}")
        self.profile = profile
        key, base, model = settings.pro_profile_config(profile)
        self._api_key = key.strip()
        self._base_url = settings.normalize_openai_base_url(base) if base else ""
        self._model = model.strip()
        self._client: OpenAI | None = None
        if self._has_credentials():
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url or None,
            )

    def _has_credentials(self) -> bool:
        return bool(self._api_key and self._model)

    def generate(self, prompt: str) -> str:
        if self._stub_enabled():
            label = "PRO2" if self.profile == "pro2" else "PRO"
            preview = prompt[:200].replace("\n", " ")
            return (
                f"[STUB {label} LLM RESPONSE]\n\n"
                "Configure API keys in .env and disable LLM_STUB to use a real model.\n\n"
                f"Prompt preview: {preview}..."
            )
        assert self._client is not None
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""
