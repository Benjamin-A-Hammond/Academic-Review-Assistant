from config import settings
from review_agent.llm.pro_model import ProLLM
from review_agent.state import ReviewState
from review_agent.utils.file_utils import load_prompt
from review_agent.utils.logger import get_logger

from .review_common import build_review_prompt, finalize_review_draft
from .step_utils import load_step_output, step_output_exists

logger = get_logger(__name__)


def compare_reviews(state: ReviewState) -> None:
    """Dual-expert mode: Pro + Pro2 reviews merged into a single review_draft.md."""
    if step_output_exists(state, "review_draft.md"):
        state.review_draft_en = load_step_output(state, "review_draft.md") or ""
        logger.info("Step 6: Skipping simulated review; review_draft.md already exists")
        finalize_review_draft(state, state.review_draft_en, write_english=False)
        return

    logger.info("Step 6: Generating Expert 1 review (Pro)")
    prompt = build_review_prompt(state)
    draft_pro = ProLLM("pro").generate(prompt)

    logger.info("Step 6: Generating Expert 2 review (Pro2)")
    draft_pro2 = ProLLM("pro2").generate(prompt)

    logger.info("Step 6: Merging expert reviews into review_draft.md (Pro)")
    template = load_prompt("merge_reviews_prompt.md", settings.PROMPTS_DIR)
    merge_prompt = (
        template.replace("{{REVIEW_EXPERT_1}}", draft_pro)
        .replace("{{REVIEW_EXPERT_2}}", draft_pro2)
        .replace("{{CONTRIBUTION}}", state.contribution_report)
        .replace("{{EXPERIMENT}}", state.experiment_report)
    )
    merged = ProLLM("pro").generate(merge_prompt)
    finalize_review_draft(state, merged)
