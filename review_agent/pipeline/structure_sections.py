import json

from config import settings
from review_agent.llm.fast_model import FastLLM
from review_agent.state import ReviewState
from review_agent.utils.file_utils import load_prompt, read_text, write_text
from review_agent.utils.logger import get_logger
from review_agent.utils.section_map import (
    build_outline_for_llm,
    extract_headings,
    format_section_map_summary,
    parse_fast_response,
    resolve_section_map,
)

from .review_common import load_paper_markdown
from .step_utils import step_output_exists

logger = get_logger(__name__)

SECTION_MAP_FILE = "section_map.json"
PREVIEW_CHARS = 3000


def structure_sections(state: ReviewState) -> None:
    out_path = state.output_path(SECTION_MAP_FILE)

    if step_output_exists(state, SECTION_MAP_FILE):
        state.section_map = json.loads(read_text(out_path))
        logger.info(
            "Step 3: Skipping section map; already exists "
            "(contribution=%s experiment=%s review=%s)",
            len(state.section_map.get("contribution_bindings") or []),
            len(state.section_map.get("experiment_bindings") or []),
            len(state.section_map.get("review_bindings") or []),
        )
        return

    logger.info("Step 3: Structuring sections (Fast model, task bindings)")
    md = load_paper_markdown(state)
    headings = extract_headings(md)
    outline = build_outline_for_llm(md, headings)
    preview = md[:PREVIEW_CHARS]

    template = load_prompt("section_map_prompt.md", settings.PROMPTS_DIR)
    prompt = (
        template.replace("{{OUTLINE}}", outline)
        .replace("{{DOC_PREVIEW}}", preview)
    )

    raw = FastLLM().generate(prompt)
    try:
        labels = parse_fast_response(raw)
        section_map = resolve_section_map(md, labels, headings)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Failed to parse Fast section map response: {exc}") from exc

    write_text(out_path, json.dumps(section_map, ensure_ascii=False, indent=2))
    state.section_map = section_map
    logger.info("Section map: %s", out_path)
    logger.info("%s", format_section_map_summary(section_map))
