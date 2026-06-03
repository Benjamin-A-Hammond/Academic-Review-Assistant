from pathlib import Path

from review_agent.parser.mineru_parser import MinerUParser
from review_agent.state import ReviewState
from review_agent.utils.file_utils import markdown_path_for_pdf
from review_agent.utils.logger import get_logger
from review_agent.utils.mineru_cache import (
    copy_cache_to_workdir,
    has_cached_markdown,
    save_workdir_to_cache,
)

logger = get_logger(__name__)


def convert_pdf(state: ReviewState) -> None:
    pdf = Path(state.pdf_path).resolve()
    existing_md = markdown_path_for_pdf(state.pdf_path, state.work_dir)
    if existing_md.is_file():
        state.markdown_path = str(existing_md.resolve())
        logger.info(
            "Step 1: Skipping PDF conversion; markdown already exists: %s",
            state.markdown_path,
        )
        return

    if has_cached_markdown(pdf):
        logger.info("Step 1: Restoring Markdown from MinerU cache")
        dest_md = copy_cache_to_workdir(pdf, Path(state.work_dir))
        state.markdown_path = str(dest_md.resolve())
        logger.info("Markdown path: %s", state.markdown_path)
        return

    logger.info("Step 1: Converting PDF to Markdown (MinerU API)")
    parser = MinerUParser()
    state.markdown_path = parser.parse(state.pdf_path, md_dest=existing_md)
    save_workdir_to_cache(pdf, Path(state.work_dir))
    logger.info("Markdown path: %s", state.markdown_path)
