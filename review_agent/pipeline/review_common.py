from pathlib import Path

from config import settings
from review_agent.llm.pro_model import ProLLM
from review_agent.state import ReviewState
from review_agent.utils.file_utils import load_prompt, read_text, write_text
from review_agent.utils.logger import get_logger
from review_agent.utils.section_map import markdown_for_task

from .step_utils import load_step_output, step_output_exists

logger = get_logger(__name__)


def language_instruction() -> str:
    if settings.is_chinese_output():
        return (
            "Write the review draft in English first (for internal consistency); "
            "it will be translated to Simplified Chinese afterward."
        )
    return "Write the review draft in English."


def load_paper_markdown(state: ReviewState) -> str:
    if not state.markdown_path:
        raise ValueError("markdown_path is empty; run convert_pdf first")
    return read_text(Path(state.markdown_path))


def markdown_for_contribution(state: ReviewState) -> str:
    md = load_paper_markdown(state)
    if state.section_map:
        return markdown_for_task(md, state.section_map, "contribution")
    logger.warning("section_map missing; contribution step uses full markdown")
    return md


def markdown_for_experiment(state: ReviewState) -> str:
    md = load_paper_markdown(state)
    if state.section_map:
        return markdown_for_task(md, state.section_map, "experiment")
    logger.warning("section_map missing; experiment step uses full markdown")
    return md


def markdown_for_review(state: ReviewState) -> str:
    md = load_paper_markdown(state)
    if state.section_map:
        focused = markdown_for_task(md, state.section_map, "review")
        if focused != md:
            return focused
    return md


def build_review_prompt(state: ReviewState) -> str:
    md = markdown_for_review(state)
    review_style = load_prompt("review_style.md", settings.PROMPTS_DIR)
    template = load_prompt("review_prompt.md", settings.PROMPTS_DIR)
    return (
        template.replace("{{MARKDOWN}}", md)
        .replace("{{CONTRIBUTION}}", state.contribution_report)
        .replace("{{EXPERIMENT}}", state.experiment_report)
        .replace("{{REVIEW_STYLE}}", review_style)
        .replace("{{LANGUAGE_INSTRUCTION}}", language_instruction())
    )


def translate_review_to_chinese(review_en: str) -> str:
    template = load_prompt("translate_review_zh.md", settings.PROMPTS_DIR)
    prompt = template.replace("{{REVIEW}}", review_en)
    return ProLLM("pro").generate(prompt)


def finalize_review_draft(
    state: ReviewState, draft_en: str, *, write_english: bool = True
) -> None:
    """Write review_draft.md (optional) and review_draft_zh.md when OUTPUT_LANG=zh."""
    state.review_draft_en = draft_en
    out_en = state.output_path("review_draft.md")

    if write_english:
        write_text(out_en, draft_en)
        logger.info("Review draft: %s", out_en)
    elif not out_en.is_file():
        write_text(out_en, draft_en)

    if not settings.is_chinese_output():
        state.review_report = draft_en
        return

    out_zh = state.output_path("review_draft_zh.md")
    if step_output_exists(state, "review_draft_zh.md"):
        state.review_report = load_step_output(state, "review_draft_zh.md") or ""
        logger.info("Chinese review already exists: %s", out_zh)
        return

    logger.info("Translating review_draft to Simplified Chinese (OUTPUT_LANG=zh)")
    draft_zh = translate_review_to_chinese(draft_en)
    write_text(out_zh, draft_zh)
    state.review_report = draft_zh
    logger.info("Review draft (zh): %s", out_zh)
