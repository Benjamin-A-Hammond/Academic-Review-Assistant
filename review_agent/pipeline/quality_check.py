import re
from pathlib import Path

from review_agent.state import ReviewState
from review_agent.utils.file_utils import read_text, write_text
from review_agent.utils.logger import get_logger

from .step_utils import load_step_output, parse_quality_verdict, step_output_exists

logger = get_logger(__name__)


def quality_check(state: ReviewState) -> None:
    if step_output_exists(state, "quality_report.md"):
        report = load_step_output(state, "quality_report.md") or ""
        state.markdown_quality = parse_quality_verdict(report)
        logger.info(
            "Step 2: Skipping quality check; report exists (verdict=%s)",
            state.markdown_quality,
        )
        return

    logger.info("Step 2: Markdown quality check")
    if not state.markdown_path:
        raise ValueError("markdown_path is empty; run convert_pdf first")

    md = read_text(Path(state.markdown_path))
    report, verdict = _evaluate_markdown(md)
    state.markdown_quality = verdict

    out_path = state.output_path("quality_report.md")
    write_text(out_path, report)
    logger.info("Quality verdict: %s (report: %s)", verdict, out_path)


def _evaluate_markdown(text: str) -> tuple[str, str]:
    length = len(text)
    headers = len(re.findall(r"^#{1,6}\s", text, re.MULTILINE))
    images = len(re.findall(r"!\[.*?\]\(.*?\)", text))
    garbled_ratio = _garbled_ratio(text)
    has_refs = bool(
        re.search(r"(?i)(^|\n)#+\s*references?\b|^references?\s*$", text, re.MULTILINE)
    )

    checks = {
        "markdown_length": length >= 500,
        "header_count": headers >= 3,
        "image_count": images >= 1,
        "garbled_ratio": garbled_ratio < 0.05,
        "references_section": has_refs,
    }
    passed = all(checks.values())
    verdict = "GOOD" if passed else "BAD"

    lines = [
        "# Markdown Quality Report",
        "",
        f"**Verdict:** {verdict}",
        "",
        "## Metrics",
        "",
        f"- Markdown length: {length} chars",
        f"- Header count: {headers}",
        f"- Image count: {images}",
        f"- Garbled ratio: {garbled_ratio:.2%}",
        f"- References section: {'yes' if has_refs else 'no'}",
        "",
        "## Checks",
        "",
    ]
    for name, ok in checks.items():
        lines.append(f"- {name}: {'PASS' if ok else 'FAIL'}")
    lines.append("")

    return "\n".join(lines), verdict


def _garbled_ratio(text: str) -> float:
    if not text:
        return 1.0
    sample = text[:10000]
    bad = sum(1 for c in sample if ord(c) < 32 and c not in "\n\r\t")
    replacement = sample.count("\ufffd")
    suspicious = bad + replacement
    return suspicious / len(sample)
