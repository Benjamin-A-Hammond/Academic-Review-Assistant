"""Unified LLM interface. All AI calls go through subclasses of BaseLLM."""

from abc import ABC, abstractmethod

from config import settings


class BaseLLM(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

    def _stub_enabled(self) -> bool:
        return settings.LLM_STUB or not self._has_credentials()

    @abstractmethod
    def _has_credentials(self) -> bool:
        pass

    def _stub_response(self, prompt: str) -> str:
        preview = prompt[:200].replace("\n", " ")
        return (
            "[STUB LLM RESPONSE]\n\n"
            "This is a placeholder response for skeleton testing. "
            "Configure API keys in .env and disable LLM_STUB to use a real model.\n\n"
            f"Prompt preview: {preview}..."
        )
