"""Application settings loaded from environment variables."""

from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RUNS_DIR = DATA_DIR / "runs"
CACHE_DIR = DATA_DIR / "cache"
MINERU_CACHE_DIR = CACHE_DIR / "mineru"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

def _strip_env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


def normalize_openai_base_url(url: str) -> str:
    """Ensure OpenAI-compatible base URL ends with /v1 (required by DeepSeek etc.)."""
    if not url:
        return url
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith("/v1"):
        return cleaned
    return f"{cleaned}/v1"


FAST_API_KEY = _strip_env("FAST_API_KEY")
FAST_BASE_URL = normalize_openai_base_url(_strip_env("FAST_BASE_URL"))
FAST_MODEL = _strip_env("FAST_MODEL")

PRO_API_KEY = _strip_env("PRO_API_KEY")
PRO_BASE_URL = normalize_openai_base_url(_strip_env("PRO_BASE_URL"))
PRO_MODEL = _strip_env("PRO_MODEL")

PRO2_API_KEY = _strip_env("PRO2_API_KEY")
PRO2_BASE_URL = normalize_openai_base_url(_strip_env("PRO2_BASE_URL"))
PRO2_MODEL = _strip_env("PRO2_MODEL")

MINERU_API_TOKEN = os.getenv("MINERU_API_TOKEN") or os.getenv("MINERU_TOKEN", "")
MINERU_BASE_URL = os.getenv("MINERU_BASE_URL", "https://mineru.net/api/v4")
MINERU_MODEL = os.getenv("MINERU_MODEL", "vlm")
MINERU_LANG = os.getenv("MINERU_LANG", "en")
MINERU_TIMEOUT = int(os.getenv("MINERU_TIMEOUT", "600"))

def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in ("1", "true", "yes")


MINERU_OCR = _env_bool("MINERU_OCR", True)
MINERU_FORMULA = _env_bool("MINERU_FORMULA", True)
MINERU_TABLE = _env_bool("MINERU_TABLE", True)

LLM_STUB = os.getenv("LLM_STUB", "").lower() in ("1", "true", "yes")


def normalize_output_lang(raw: str | None) -> str:
    """Output language for reports: zh (default) or en."""
    if not raw or not raw.strip():
        return "zh"
    value = raw.strip().lower()
    if value in ("zh", "cn", "ch", "chinese", "中文"):
        return "zh"
    if value in ("en", "english", "英文"):
        return "en"
    return "zh"


OUTPUT_LANG = normalize_output_lang(os.getenv("OUTPUT_LANG", "zh"))


def is_chinese_output() -> bool:
    return OUTPUT_LANG == "zh"


def pro_profile_config(profile: str) -> tuple[str, str, str]:
    """Return (api_key, base_url, model) for pro or pro2."""
    if profile == "pro2":
        return PRO2_API_KEY, PRO2_BASE_URL, PRO2_MODEL
    if profile != "pro":
        raise ValueError(f"Unknown Pro profile: {profile}")
    return PRO_API_KEY, PRO_BASE_URL, PRO_MODEL


def has_pro_credentials(profile: str) -> bool:
    key, _, model = pro_profile_config(profile)
    return bool(key and model)


def has_fast_credentials() -> bool:
    return bool(FAST_API_KEY and FAST_MODEL)


def has_mineru_credentials() -> bool:
    return bool(MINERU_API_TOKEN)


def compare_enabled_by_config() -> bool:
    """True when both Pro models are configured (compare can run)."""
    return has_pro_credentials("pro") and has_pro_credentials("pro2")
