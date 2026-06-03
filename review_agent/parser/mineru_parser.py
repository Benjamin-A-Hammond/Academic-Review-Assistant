"""MinerU cloud API PDF parsing via mineru-open-sdk. No local parsing."""

from pathlib import Path

from config import settings
from review_agent.utils.file_utils import ensure_dir
from review_agent.utils.logger import get_logger

logger = get_logger(__name__)


class MinerUParseError(RuntimeError):
    """Raised when MinerU API parsing fails."""


class MinerUParser:
    def parse(self, pdf_path: str, md_dest: Path | None = None) -> str:
        pdf = Path(pdf_path).resolve()
        if not pdf.exists():
            raise FileNotFoundError(f"PDF not found: {pdf}")

        token = settings.MINERU_API_TOKEN
        if not token:
            raise MinerUParseError(
                "MINERU_API_TOKEN is not set. "
                "Get a token at https://mineru.net/apiManage/token"
            )

        try:
            from mineru import MinerU
            from mineru.exceptions import MinerUError
        except ImportError as exc:
            raise MinerUParseError(
                "mineru-open-sdk is not installed. Run: pip install mineru-open-sdk"
            ) from exc

        dest = md_dest or (pdf.parent / f"{pdf.stem}.md")
        dest = Path(dest)
        ensure_dir(dest.parent)
        logger.info("Parsing PDF via MinerU API: %s", pdf.name)

        try:
            with MinerU(token=token, base_url=settings.MINERU_BASE_URL) as client:
                result = client.extract(
                    str(pdf),
                    model=settings.MINERU_MODEL,
                    language=settings.MINERU_LANG,
                    ocr=settings.MINERU_OCR,
                    formula=settings.MINERU_FORMULA,
                    table=settings.MINERU_TABLE,
                    timeout=settings.MINERU_TIMEOUT,
                )
        except MinerUError as exc:
            raise MinerUParseError(f"MinerU API request failed: {exc}") from exc
        except Exception as exc:
            raise MinerUParseError(f"MinerU API request failed: {exc}") from exc

        if result.state != "done":
            detail = result.error or result.err_code or "unknown error"
            raise MinerUParseError(
                f"MinerU API task did not complete (state={result.state}): {detail}"
            )

        if not result.markdown or not result.markdown.strip():
            raise MinerUParseError(
                "MinerU API returned empty markdown for "
                f"{pdf.name} (task_id={result.task_id})"
            )

        result.save_markdown(str(dest), with_images=True)
        logger.info("Markdown saved to %s", dest)
        return str(dest)
