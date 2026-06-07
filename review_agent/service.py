"""Shared service API for CLI and MCP."""

from __future__ import annotations

from pathlib import Path

from config import settings
from review_agent.cli import run_convert_pipeline, run_pipeline
from review_agent.utils.file_utils import resolve_pdf_path, resolve_work_dir
from review_agent.utils.preflight import run_preflight
from review_agent.utils.runs_cli import clean_runs as _clean_runs
from review_agent.utils.runs_cli import list_runs_info

REPORT_FILES = (
    "quality_report.md",
    "section_map.json",
    "references.md",
    "contribution.md",
    "experiment.md",
    "review_draft.md",
    "review_draft_zh.md",
)


def check_mineru_environment() -> dict:
    run_preflight(
        need_mineru=True,
        need_fast=False,
        need_pro=False,
        need_pro2=False,
    )
    return {
        "ok": True,
        "llm_stub": settings.LLM_STUB,
        "message": "MinerU API check passed.",
    }


def check_environment(need_compare: bool | None = None) -> dict:
    if need_compare is None:
        need_compare = settings.compare_enabled_by_config()
    run_preflight(
        need_mineru=True,
        need_fast=True,
        need_pro=True,
        need_pro2=need_compare,
    )
    return {
        "ok": True,
        "need_compare": need_compare,
        "llm_stub": settings.LLM_STUB,
        "message": "All configured API checks passed.",
    }


def run_convert_pdf(
    pdf_path: str | None = None,
    *,
    work_dir: str | None = None,
    skip_preflight: bool = False,
    quality_check: bool = False,
) -> dict:
    if work_dir:
        _, pdf = resolve_work_dir(work_dir)
    elif pdf_path:
        pdf = resolve_pdf_path(pdf_path)
    else:
        raise ValueError("pdf_path or work_dir is required")

    state = run_convert_pipeline(
        pdf,
        work_dir=work_dir,
        skip_preflight=skip_preflight,
        with_quality_check=quality_check,
    )
    return _convert_result(state)


def run_review(
    pdf_path: str | None = None,
    *,
    work_dir: str | None = None,
    no_compare: bool = False,
    skip_preflight: bool = False,
) -> dict:
    if work_dir:
        _, pdf = resolve_work_dir(work_dir)
    elif pdf_path:
        pdf = resolve_pdf_path(pdf_path)
    else:
        raise ValueError("pdf_path or work_dir is required")

    state = run_pipeline(
        pdf,
        work_dir=work_dir,
        no_compare=no_compare,
        skip_preflight=skip_preflight,
    )
    return _state_result(state)


def get_run_status(work_dir: str) -> dict:
    root = Path(work_dir).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Work directory not found: {root}")

    outputs = {name: (root / name).is_file() for name in REPORT_FILES}
    md_files = [p.name for p in root.glob("*.md") if p.name not in outputs]
    pdfs = [p.name for p in root.glob("*.pdf")]

    return {
        "work_dir": str(root),
        "pdf_files": pdfs,
        "markdown_files": md_files,
        "outputs": outputs,
        "completed_steps": sum(outputs.values()),
    }


def read_run_report(work_dir: str, filename: str, max_chars: int = 12000) -> dict:
    if filename not in REPORT_FILES and not filename.endswith(".md"):
        raise ValueError(f"Unsupported file: {filename}")
    path = Path(work_dir).resolve() / filename
    if not path.is_file():
        raise FileNotFoundError(f"Report not found: {path}")
    text = path.read_text(encoding="utf-8")
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars] + "\n\n...[truncated]..."
    return {
        "work_dir": str(path.parent),
        "filename": filename,
        "truncated": truncated,
        "content": text,
    }


def list_runs() -> dict:
    runs = list_runs_info()
    return {"runs": runs, "total": len(runs), "runs_dir": str(settings.RUNS_DIR)}


def clean_runs(
    *,
    older_than_days: int | None = None,
    delete_all: bool = False,
    dry_run: bool = True,
) -> dict:
    return _clean_runs(
        older_than_days=older_than_days,
        dry_run=dry_run,
        delete_all=delete_all,
    )


def read_run_markdown(work_dir: str, max_chars: int = 12000) -> dict:
    root = Path(work_dir).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Work directory not found: {root}")

    md_files = sorted(root.glob("*.md"))
    md_files = [
        p
        for p in md_files
        if p.name not in REPORT_FILES and p.name != "quality_report.md"
    ]
    if not md_files:
        raise FileNotFoundError(f"No converted markdown in: {root}")
    if len(md_files) > 1:
        names = ", ".join(p.name for p in md_files)
        raise ValueError(f"Multiple markdown files in work directory: {names}")

    path = md_files[0]
    text = path.read_text(encoding="utf-8")
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars] + "\n\n...[truncated]..."
    return {
        "work_dir": str(root),
        "filename": path.name,
        "markdown_path": str(path),
        "truncated": truncated,
        "content": text,
    }


def _convert_result(state) -> dict:
    work = Path(state.work_dir)
    result = {
        "ok": True,
        "work_dir": state.work_dir,
        "pdf_path": state.pdf_path,
        "markdown_path": state.markdown_path,
    }
    if state.markdown_quality:
        result["markdown_quality"] = state.markdown_quality
        qr = work / "quality_report.md"
        if qr.is_file():
            result["quality_report_path"] = str(qr)
    return result


def _state_result(state) -> dict:
    work = Path(state.work_dir)
    return {
        "ok": True,
        "work_dir": state.work_dir,
        "pdf_path": state.pdf_path,
        "markdown_path": state.markdown_path,
        "markdown_quality": state.markdown_quality,
        "outputs": {name: (work / name).is_file() for name in REPORT_FILES},
    }
