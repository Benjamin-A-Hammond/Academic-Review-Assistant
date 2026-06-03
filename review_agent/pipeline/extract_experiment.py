from config import settings
from review_agent.llm.pro_model import ProLLM
from review_agent.state import ReviewState
from review_agent.utils.file_utils import load_prompt, write_text
from review_agent.utils.logger import get_logger

from .review_common import markdown_for_experiment
from .step_utils import load_step_output, step_output_exists

logger = get_logger(__name__)


def extract_experiment(state: ReviewState) -> None:
    if step_output_exists(state, "experiment.md"):
        state.experiment_report = load_step_output(state, "experiment.md") or ""
        logger.info("Step 5: Skipping experiment analysis; already exists")
        return

    logger.info("Step 5: Extracting experiment analysis (Pro, section-focused excerpts)")
    md = markdown_for_experiment(state)
    template = load_prompt("experiment_prompt.md", settings.PROMPTS_DIR)
    prompt = template.replace("{{MARKDOWN}}", md)

    result = ProLLM("pro").generate(prompt)
    state.experiment_report = result

    out_path = state.output_path("experiment.md")
    write_text(out_path, result)
    logger.info("Experiment report: %s", out_path)
