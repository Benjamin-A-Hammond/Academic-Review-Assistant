"""Startup API connectivity checks."""

from config import settings
from review_agent.llm.fast_model import FastLLM
from review_agent.llm.pro_model import ProLLM
from review_agent.llm.base import BaseLLM
from review_agent.parser.mineru_parser import MinerUParseError
from review_agent.utils.logger import get_logger

logger = get_logger(__name__)

_PING_PROMPT = "Reply with exactly: OK"
# Reasoning models (e.g. deepseek-v4-pro) may consume budget before visible content
_PING_MAX_TOKENS = 64


def _ping_llm(name: str, llm: BaseLLM) -> None:
    if llm._stub_enabled():
        logger.warning("%s: skipped (LLM_STUB or missing credentials)", name)
        return
    try:
        client = llm._client
        assert client is not None
        if isinstance(llm, ProLLM):
            model = llm._model
            base_url = llm._base_url
        else:
            model = settings.FAST_MODEL
            base_url = settings.FAST_BASE_URL
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": _PING_PROMPT}],
            max_tokens=_PING_MAX_TOKENS,
        )
        choice = response.choices[0]
        content = (choice.message.content or "").strip()
        finish = choice.finish_reason or "unknown"

        if content:
            logger.info("%s: OK (%s)", name, content[:40])
            return

        # Some gateways return empty content with finish_reason=length on wrong base URL
        if finish in ("stop", "length") and response.id:
            logger.warning(
                "%s: API reachable but empty content (finish_reason=%s, base_url=%s). "
                "If this persists, verify BASE_URL ends with /v1 and model name.",
                name,
                finish,
                base_url,
            )
            return

        raise RuntimeError(
            f"empty response (finish_reason={finish}, model={model}, base_url={base_url})"
        )
    except Exception as exc:
        raise RuntimeError(f"{name} API check failed: {exc}") from exc


def _ping_mineru() -> None:
    if not settings.has_mineru_credentials():
        raise RuntimeError(
            "MinerU: MINERU_API_TOKEN is not set "
            "(https://mineru.net/apiManage/token)"
        )
    if settings.LLM_STUB:
        logger.warning("MinerU: token present (connectivity not probed in LLM_STUB mode)")
        return
    try:
        from mineru import MinerU
    except ImportError as exc:
        raise RuntimeError(
            "MinerU: mineru-open-sdk not installed. Run: pip install mineru-open-sdk"
        ) from exc
    try:
        client = MinerU(token=settings.MINERU_API_TOKEN, base_url=settings.MINERU_BASE_URL)
        client.__enter__()
        client.__exit__(None, None, None)
        logger.info("MinerU: client initialized OK")
    except Exception as exc:
        raise RuntimeError(f"MinerU API check failed: {exc}") from exc


def run_preflight(
    *,
    need_mineru: bool = True,
    need_fast: bool = True,
    need_pro: bool = True,
    need_pro2: bool = False,
) -> None:
    """Raise RuntimeError if required APIs are not reachable."""
    errors: list[str] = []

    def collect(label: str, fn) -> None:
        try:
            fn()
        except RuntimeError as exc:
            errors.append(str(exc))
        except MinerUParseError as exc:
            errors.append(str(exc))

    if need_mineru:
        collect("MinerU", _ping_mineru)
    if need_fast:
        if not settings.has_fast_credentials() and not settings.LLM_STUB:
            errors.append(
                "Fast: FAST_API_KEY and FAST_MODEL are required for markdown section mapping"
            )
        else:
            collect("Fast", lambda: _ping_llm("Fast", FastLLM()))
    if need_pro:
        if not settings.has_pro_credentials("pro") and not settings.LLM_STUB:
            errors.append("Pro: PRO_API_KEY and PRO_MODEL are required")
        else:
            collect("Pro", lambda: _ping_llm("Pro", ProLLM("pro")))
    if need_pro2:
        if not settings.has_pro_credentials("pro2") and not settings.LLM_STUB:
            errors.append("Pro2: PRO2_API_KEY and PRO2_MODEL are required for compare")
        else:
            collect("Pro2", lambda: _ping_llm("Pro2", ProLLM("pro2")))

    if errors:
        detail = "\n  - ".join([""] + errors)
        raise RuntimeError(f"Preflight failed:{detail}")
