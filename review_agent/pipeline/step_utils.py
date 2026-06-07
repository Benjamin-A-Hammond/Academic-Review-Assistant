import json
import re
from pathlib import Path

from review_agent.state import ReviewState
from review_agent.utils.file_utils import read_text


def step_output_exists(state: ReviewState, filename: str) -> bool:
    return state.output_path(filename).is_file()


def load_step_output(state: ReviewState, filename: str) -> str | None:
    path = state.output_path(filename)
    if not path.is_file():
        return None
    return read_text(path)


def parse_quality_verdict(quality_report: str) -> str:
    match = re.search(r"\*\*Verdict:\*\*\s*(\w+)", quality_report)
    if match:
        return match.group(1).upper()
    return ""


def hydrate_state_from_workspace(state: ReviewState) -> None:
    """Load completed step outputs from work_dir (for resume)."""
    if state.markdown_path and Path(state.markdown_path).is_file():
        pass
    elif state.pdf_path:
        from review_agent.utils.file_utils import markdown_path_for_pdf

        md = markdown_path_for_pdf(state.pdf_path, state.work_dir)
        if md.is_file():
            state.markdown_path = str(md.resolve())

    qr = load_step_output(state, "quality_report.md")
    if qr:
        state.markdown_quality = parse_quality_verdict(qr)

    section_map_raw = load_step_output(state, "section_map.json")
    if section_map_raw:
        state.section_map = json.loads(section_map_raw)

    ref_md = state.output_path("references.md")
    if ref_md.is_file():
        state.references_path = str(ref_md.resolve())

    contrib = load_step_output(state, "contribution.md")
    if contrib:
        state.contribution_report = contrib

    exp = load_step_output(state, "experiment.md")
    if exp:
        state.experiment_report = exp

    draft_en = load_step_output(state, "review_draft.md")
    if draft_en:
        state.review_draft_en = draft_en

    if load_step_output(state, "review_draft_zh.md"):
        state.review_report = load_step_output(state, "review_draft_zh.md") or ""
    elif draft_en:
        state.review_report = draft_en
