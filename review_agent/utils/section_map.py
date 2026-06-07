"""Markdown section map: heading detection + Fast task bindings + char ranges."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from review_agent.utils.logger import get_logger

logger = get_logger(__name__)

TaskName = Literal["contribution", "experiment", "review"]
TASK_NAMES: tuple[TaskName, ...] = ("contribution", "experiment", "review")

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

CONTRIBUTION_PREFERRED = (
    "Abstract",
    "Introduction",
    "Related Work",
    "Method",
    "Methodology",
    "Approach",
    "Problem",
    "Contributions",
    "Conclusion",
    "Discussion",
)

EXPERIMENT_PREFERRED = (
    "Abstract",
    "Experiments",
    "Experimental",
    "Results",
    "Evaluation",
    "Analysis",
    "Conclusion",
)

REVIEW_PREFERRED = (
    "Abstract",
    "Introduction",
    "Method",
    "Experiments",
    "Limitations",
    "Conclusion",
)

LEGACY_PREFERRED: dict[TaskName, tuple[str, ...]] = {
    "contribution": CONTRIBUTION_PREFERRED,
    "experiment": EXPERIMENT_PREFERRED,
    "review": REVIEW_PREFERRED,
}


def extract_headings(md: str) -> list[dict[str, Any]]:
    headings: list[dict[str, Any]] = []
    for match in HEADING_RE.finditer(md):
        headings.append(
            {
                "index": len(headings),
                "level": len(match.group(1)),
                "text": match.group(2).strip(),
                "start": match.start(),
                "line": md[: match.start()].count("\n") + 1,
            }
        )
    return headings


def infer_title(md: str, headings: list[dict[str, Any]]) -> str:
    for h in headings:
        if h["level"] == 1:
            return h["text"]
    first_line = md.strip().split("\n", 1)[0].strip()
    if first_line and not first_line.startswith("#"):
        return first_line[:500]
    if headings:
        return headings[0]["text"]
    return "Unknown"


def build_outline_for_llm(md: str, headings: list[dict[str, Any]]) -> str:
    lines = [
        f"Document length: {len(md)} characters",
        f"Detected title (heuristic): {infer_title(md, headings)}",
        "",
        "Headings (use heading_index in your JSON):",
    ]
    for h in headings:
        lines.append(
            f"- index={h['index']} level=H{h['level']} line={h['line']} "
            f"char={h['start']} text={h['text']!r}"
        )
    if not headings:
        lines.append("- (no markdown headings found)")
    return "\n".join(lines)


def parse_fast_response(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _range_from_heading_index(
    md: str, headings: list[dict[str, Any]], index: int | None
) -> list[int] | None:
    if index is None or index < 0 or index >= len(headings):
        return None
    start = headings[index]["start"]
    next_starts = [h["start"] for h in headings if h["start"] > start]
    end = min(next_starts) - 1 if next_starts else len(md) - 1
    end = max(end, start)
    return [start, end]


def _normalize_indices(raw: Any) -> list[int]:
    if raw is None:
        return []
    if isinstance(raw, int):
        return [raw]
    if not isinstance(raw, list):
        return []
    indices: list[int] = []
    for item in raw:
        if isinstance(item, int):
            indices.append(item)
        elif isinstance(item, dict) and item.get("heading_index") is not None:
            indices.append(int(item["heading_index"]))
    return indices


def _resolve_task_bindings(
    md: str,
    headings: list[dict[str, Any]],
    indices: list[int],
) -> list[dict[str, Any]]:
    seen: set[int] = set()
    bindings: list[dict[str, Any]] = []
    for idx in indices:
        if idx in seen:
            continue
        seen.add(idx)
        if idx < 0 or idx >= len(headings):
            continue
        rng = _range_from_heading_index(md, headings, idx)
        if not rng:
            continue
        bindings.append(
            {
                "heading_index": idx,
                "heading": headings[idx]["text"],
                "start": rng[0],
                "end": rng[1],
            }
        )
    bindings.sort(key=lambda b: b["start"])
    return bindings


def _catalog_sections(
    md: str, headings: list[dict[str, Any]], *, skip_index: int | None
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for h in headings:
        if h["index"] == skip_index:
            continue
        rng = _range_from_heading_index(md, headings, h["index"])
        if rng:
            sections.append({"name": h["text"], "start": rng[0], "end": rng[1]})
    sections.sort(key=lambda s: s["start"])
    for i, sec in enumerate(sections):
        if i + 1 < len(sections):
            sec["end"] = min(sec["end"], sections[i + 1]["start"] - 1)
        sec["end"] = min(sec["end"], len(md) - 1)
    return sections


def resolve_reference_binding(
    md: str, headings: list[dict[str, Any]], heading_index: int | None
) -> dict[str, Any] | None:
    """Resolve a single bibliography heading to a char-range binding."""
    if heading_index is None:
        return None
    bindings = _resolve_task_bindings(md, headings, [int(heading_index)])
    return bindings[0] if bindings else None


def apply_reference_to_section_map(
    section_map: dict[str, Any],
    md: str,
    headings: list[dict[str, Any]],
    heading_index: int | None,
) -> dict[str, Any]:
    binding = resolve_reference_binding(md, headings, heading_index)
    if binding:
        section_map["reference_binding"] = binding
        section_map["reference_range"] = [binding["start"], binding["end"]]
    else:
        section_map.pop("reference_binding", None)
        section_map.pop("reference_range", None)
    return section_map


def resolve_section_map(
    md: str, labels: dict[str, Any], headings: list[dict[str, Any]]
) -> dict[str, Any]:
    title = labels.get("title") or infer_title(md, headings)

    abstract_range = None
    abs_idx = labels.get("abstract_heading_index")
    if abs_idx is not None:
        abstract_range = _range_from_heading_index(md, headings, int(abs_idx))

    section_map: dict[str, Any] = {
        "title": title,
        "abstract_range": abstract_range,
        "sections": _catalog_sections(md, headings, skip_index=None),
        "document_length": len(md),
    }

    for task in TASK_NAMES:
        key = f"{task}_heading_indices"
        legacy_key = f"{task}_bindings"
        if isinstance(labels.get(legacy_key), list) and labels[legacy_key]:
            section_map[legacy_key] = labels[legacy_key]
            continue
        indices = _normalize_indices(labels.get(key))
        section_map[legacy_key] = _resolve_task_bindings(md, headings, indices)

    return section_map


def slice_range(md: str, start: int, end: int) -> str:
    return md[max(0, start) : min(len(md), end + 1)]


def get_range(section_map: dict[str, Any], name: str) -> list[int] | None:
    name_lower = name.lower()
    if name_lower == "abstract" and section_map.get("abstract_range"):
        return section_map["abstract_range"]
    for sec in section_map.get("sections") or []:
        if sec.get("name", "").lower() == name_lower:
            return [sec["start"], sec["end"]]
    for sec in section_map.get("sections") or []:
        sec_name = sec.get("name", "").lower()
        if name_lower in sec_name or sec_name in name_lower:
            return [sec["start"], sec["end"]]
    return None


def markdown_for_task(
    md: str,
    section_map: dict[str, Any],
    task: TaskName,
    *,
    fallback_full: bool = True,
) -> str:
    bindings = section_map.get(f"{task}_bindings") or []
    if bindings:
        parts: list[str] = []
        for binding in bindings:
            start = binding.get("start")
            end = binding.get("end")
            if start is None or end is None:
                continue
            label = binding.get("heading") or f"Section {binding.get('heading_index')}"
            text = slice_range(md, int(start), int(end)).strip()
            if text:
                parts.append(f"## [{label}]\n\n{text}")
        if parts:
            header = (
                f"# Structured excerpts ({task}, from section_map.json)\n\n"
                f"**Title:** {section_map.get('title', '')}\n\n"
            )
            return header + "\n\n---\n\n".join(parts)

    preferred = LEGACY_PREFERRED[task]
    return markdown_for_sections(
        md, section_map, preferred, fallback_full=fallback_full
    )


def markdown_for_sections(
    md: str,
    section_map: dict[str, Any],
    preferred_names: tuple[str, ...],
    *,
    fallback_full: bool = True,
) -> str:
    parts: list[str] = []
    seen_ranges: set[tuple[int, int]] = set()

    for name in preferred_names:
        rng = get_range(section_map, name)
        if not rng:
            continue
        key = (rng[0], rng[1])
        if key in seen_ranges:
            continue
        seen_ranges.add(key)
        text = slice_range(md, rng[0], rng[1]).strip()
        if text:
            parts.append(f"## [{name}]\n\n{text}")

    if parts:
        header = (
            f"# Structured excerpts (from section_map.json)\n\n"
            f"**Title:** {section_map.get('title', '')}\n\n"
        )
        return header + "\n\n---\n\n".join(parts)

    if fallback_full:
        logger.warning("No section_map slices matched; falling back to full markdown")
        return md
    return ""


def format_section_map_summary(section_map: dict[str, Any]) -> str:
    lines = [f"Title: {section_map.get('title', '')}"]
    if section_map.get("abstract_range"):
        lines.append(f"Abstract: chars {section_map['abstract_range']}")
    ref = section_map.get("reference_binding")
    if ref:
        lines.append(
            f"references: {ref.get('heading', '?')} "
            f"chars [{ref.get('start')}, {ref.get('end')}]"
        )
    for task in TASK_NAMES:
        bindings = section_map.get(f"{task}_bindings") or []
        if not bindings:
            continue
        headings = ", ".join(b.get("heading", "?") for b in bindings)
        lines.append(f"{task} ({len(bindings)}): {headings}")
    if not any(section_map.get(f"{t}_bindings") for t in TASK_NAMES):
        for sec in section_map.get("sections") or []:
            lines.append(
                f"- {sec.get('name')}: chars [{sec.get('start')}, {sec.get('end')}]"
            )
    return "\n".join(lines)
