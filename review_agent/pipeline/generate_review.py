from review_agent.llm.pro_model import ProLLM
from review_agent.state import ReviewState
from review_agent.utils.logger import get_logger

from .review_common import build_review_prompt, finalize_review_draft
from .step_utils import load_step_output, step_output_exists

logger = get_logger(__name__)


def generate_review(state: ReviewState) -> None:
    """Single-expert review when dual-model compare is disabled."""
    if step_output_exists(state, "review_draft.md"):
        state.review_draft_en = load_step_output(state, "review_draft.md") or ""
        logger.info("Step 6: Skipping simulated review; review_draft.md already exists")
        finalize_review_draft(state, state.review_draft_en, write_english=False)
        return

    logger.info(
        "Step 6: Generating simulated review (Pro; section-focused when section_map exists)"
    )
    draft_en = ProLLM("pro").generate(build_review_prompt(state))
    finalize_review_draft(state, draft_en)
