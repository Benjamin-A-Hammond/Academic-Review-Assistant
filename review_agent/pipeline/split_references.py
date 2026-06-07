import json
from pathlib import Path
from typing import Any

from config import settings
from review_agent.llm.fast_model import FastLLM
from review_agent.state import ReviewState
from review_agent.utils.file_utils import load_prompt, write_text
from review_agent.utils.logger import get_logger
from review_agent.utils.reference_clean import (
    adjust_binding_after_clean,
    clean_reference_slice,
)
from review_agent.utils.section_map import (
    apply_reference_to_section_map,
    build_outline_for_llm,
    extract_headings,
    parse_fast_response,
    slice_range,
)

from .review_common import load_paper_markdown
from .step_utils import step_output_exists

logger = get_logger(__name__)

REFERENCES_FILE = "references.md"
SECTION_MAP_FILE = "section_map.json"
PREVIEW_CHARS = 3000


def _persist_reference_outputs(
    state: ReviewState,
    md: str,
    ref_binding: dict[str, Any],
    *,
    map_path: Path,
) -> None:
    raw = slice_range(md, int(ref_binding["start"]), int(ref_binding["end"]))
    cleaned, rel_start, rel_end = clean_reference_slice(raw)
    out_path = state.output_path(REFERENCES_FILE)
    write_text(out_path, cleaned)
    state.references_path = str(out_path.resolve())

    trimmed_binding = adjust_binding_after_clean(ref_binding, rel_start, rel_end)
    state.section_map["reference_binding"] = trimmed_binding
    state.section_map["reference_range"] = [
        trimmed_binding["start"],
        trimmed_binding["end"],
    ]

    if map_path.is_file():
        write_text(
            map_path,
            json.dumps(state.section_map, ensure_ascii=False, indent=2),
        )

    logger.info(
        "References: %s (heading=%r, chars [%s, %s], cleaned %s -> %s chars)",
        out_path,
        trimmed_binding.get("heading"),
        trimmed_binding["start"],
        trimmed_binding["end"],
        len(raw),
        len(cleaned),
    )


def split_references(state: ReviewState) -> None:
    out_path = state.output_path(REFERENCES_FILE)

    if step_output_exists(state, REFERENCES_FILE):
        state.references_path = str(out_path.resolve())
        logger.info("Step 3b: Skipping reference split; %s already exists", REFERENCES_FILE)
        return

    if not state.markdown_path:
        raise ValueError("markdown_path is empty; run convert_pdf first")

    md = load_paper_markdown(state)
    map_path = state.output_path(SECTION_MAP_FILE)
    existing_binding = state.section_map.get("reference_binding")
    if existing_binding and existing_binding.get("start") is not None:
        logger.info(
            "Step 3b: Writing %s from section_map reference_binding (heading=%r)",
            REFERENCES_FILE,
            existing_binding.get("heading"),
        )
        _persist_reference_outputs(
            state, md, existing_binding, map_path=map_path
        )
        return

    logger.info("Step 3b: Splitting references (Fast, heading detection)")
    headings = extract_headings(md)
    outline = build_outline_for_llm(md, headings)
    head_preview = md[:PREVIEW_CHARS]
    tail_preview = md[-PREVIEW_CHARS:] if len(md) > PREVIEW_CHARS else md

    template = load_prompt("reference_split_prompt.md", settings.PROMPTS_DIR)
    prompt = (
        template.replace("{{OUTLINE}}", outline)
        .replace("{{DOC_PREVIEW}}", head_preview)
        .replace("{{DOC_TAIL_PREVIEW}}", tail_preview)
    )

    raw = FastLLM().generate(prompt)
    try:
        labels = parse_fast_response(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError(f"Failed to parse Fast reference split response: {exc}") from exc

    ref_idx = labels.get("reference_heading_index")
    if ref_idx is not None:
        ref_idx = int(ref_idx)

    binding = apply_reference_to_section_map(
        state.section_map, md, headings, ref_idx
    )

    if not binding.get("reference_binding"):
        detected = labels.get("detected_title")
        logger.info(
            "Step 3b: No bibliography heading identified (detected_title=%r); "
            "skipping %s",
            detected,
            REFERENCES_FILE,
        )
        return

    ref_binding = binding["reference_binding"]
    _persist_reference_outputs(
        state, md, ref_binding, map_path=map_path
    )
