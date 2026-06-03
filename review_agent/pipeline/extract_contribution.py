from config import settings
from review_agent.llm.pro_model import ProLLM
from review_agent.state import ReviewState
from review_agent.utils.file_utils import load_prompt, write_text
from review_agent.utils.logger import get_logger

from .review_common import markdown_for_contribution
from .step_utils import load_step_output, step_output_exists

logger = get_logger(__name__)


def extract_contribution(state: ReviewState) -> None:
    if step_output_exists(state, "contribution.md"):
        state.contribution_report = load_step_output(state, "contribution.md") or ""
        logger.info("Step 4: Skipping contribution; already exists")
        return

    logger.info("Step 4: Extracting contribution (Pro, section-focused excerpts)")
    md = markdown_for_contribution(state)
    template = load_prompt("contribution_prompt.md", settings.PROMPTS_DIR)
    prompt = template.replace("{{MARKDOWN}}", md)

    result = ProLLM("pro").generate(prompt)
    state.contribution_report = result

    out_path = state.output_path("contribution.md")
    write_text(out_path, result)
    logger.info("Contribution report: %s", out_path)
