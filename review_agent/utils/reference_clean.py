"""Trim extracted bibliography slices using Fast + verbatim anchors."""

from __future__ import annotations

import json
import re
from typing import Any

from config import settings
from review_agent.llm.fast_model import FastLLM
from review_agent.utils.file_utils import load_prompt
from review_agent.utils.logger import get_logger
from review_agent.utils.section_map import parse_fast_response

logger = get_logger(__name__)

MAX_CLEAN_CHARS = 120_000

# Trailing non-bibliography blocks (heuristic fallback when Fast JSON fails).
TRAILING_JUNK_RE = re.compile(
    r"\n\n(?:"
    r"Table\s+\d+(?:\s|:)"
    r"|<table>"
    r"|!\["
    r"|#+\s*(?:Appendix|Supplementary|补充|附录)"
    r"|(?:Author\s+)?(?:contributions?|Declaration of competing interest)"
    r"|Acknowledgments?"
    r"|Funding\s*:"
    r"|Continued on next page"
    r")",
    re.IGNORECASE,
)

LEADING_JUNK_RE = re.compile(
    r"^(?:#+\s*)?(?:Appendix|Supplementary|Author contributions?|Declaration of)",
    re.IGNORECASE | re.MULTILINE,
)


def _clamp_index(value: Any, upper: int) -> int | None:
    if value is None:
        return None
    try:
        idx = int(value)
    except (TypeError, ValueError):
        return None
    return max(0, min(idx, upper))


def _unique_substring_pos(text: str, snippet: str | None) -> int | None:
    if not snippet or not snippet.strip():
        return None
    snippet = snippet.strip()
    first = text.find(snippet)
    if first < 0:
        return None
    if text.find(snippet, first + len(snippet)) >= 0:
        logger.warning("Reference clean snippet not unique; ignored: %r", snippet[:60])
        return None
    return first


def _heuristic_trim(text: str) -> tuple[str, int, int]:
    start = 0
    end = len(text)

    lead = LEADING_JUNK_RE.search(text)
    if lead and lead.start() == 0:
        next_heading = re.search(r"^#\s+References\b", text, re.I | re.MULTILINE)
        if next_heading:
            start = next_heading.start()

    trail = TRAILING_JUNK_RE.search(text, start)
    if trail:
        end = trail.start()

    cleaned = text[start:end].rstrip()
    if not cleaned:
        return text, 0, len(text)
    return cleaned, start, start + len(cleaned)


def apply_reference_clean_labels(text: str, labels: dict[str, Any]) -> tuple[str, int, int]:
    """Return (cleaned_text, keep_start, keep_end_exclusive)."""
    n = len(text)
    start = _clamp_index(labels.get("keep_start"), n) or 0
    end = _clamp_index(labels.get("keep_end"), n)
    if end is None:
        end = n

    start_snip = labels.get("start_after_snippet")
    pos = _unique_substring_pos(text, start_snip)
    if pos is not None:
        start = max(start, pos + len(start_snip.strip()))

    end_snip = labels.get("end_exclusive_snippet") or labels.get(
        "bibliography_end_exclusive_snippet"
    )
    pos = _unique_substring_pos(text, end_snip)
    if pos is not None:
        end = min(end, pos)

    start = max(0, min(start, n))
    end = max(start, min(end, n))
    cleaned = text[start:end].rstrip()
    if not cleaned:
        logger.warning("Reference clean produced empty text; keeping original slice")
        return text, 0, n
    end_exclusive = start + len(cleaned)
    return cleaned, start, end_exclusive


def clean_reference_slice(text: str) -> tuple[str, int, int]:
    """
    Run Fast trim pass on an extracted bibliography slice.
    Returns (cleaned_text, keep_start, keep_end_exclusive) relative to input.
    """
    if not text.strip():
        return text, 0, len(text)

    if len(text) > MAX_CLEAN_CHARS:
        logger.warning(
            "Reference slice length %s exceeds %s; heuristic trim only",
            len(text),
            MAX_CLEAN_CHARS,
        )
        return _heuristic_trim(text)

    template = load_prompt("reference_clean_prompt.md", settings.PROMPTS_DIR)
    prompt = (
        template.replace("{{SLICE_LENGTH}}", str(len(text)))
        .replace("{{REFERENCE_SLICE}}", text)
    )

    raw = FastLLM().generate(prompt)
    try:
        labels = parse_fast_response(raw)
        cleaned, start, end = apply_reference_clean_labels(text, labels)
        removed = labels.get("removed_summary")
        if removed:
            logger.info("Reference clean: %s", removed)
        if end < len(text) or start > 0:
            logger.info(
                "Reference clean trimmed slice: chars %s..%s (was %s)",
                start,
                end,
                len(text),
            )
        return cleaned, start, end
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("Reference clean Fast parse failed (%s); using heuristics", exc)
        return _heuristic_trim(text)


def adjust_binding_after_clean(
    binding: dict[str, Any], rel_start: int, rel_end_exclusive: int
) -> dict[str, Any]:
    """Map relative trim range onto absolute char positions in full markdown."""
    base = int(binding["start"])
    new_start = base + rel_start
    new_end = base + rel_end_exclusive - 1
    updated = dict(binding)
    updated["start"] = new_start
    updated["end"] = max(new_end, new_start)
    return updated
