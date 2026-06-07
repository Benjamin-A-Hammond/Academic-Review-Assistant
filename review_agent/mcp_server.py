"""
MCP server for Academic Review Assistant (Model Context Protocol).

Pre-submission self-check and simulated peer review for authors' own manuscripts.
Not for formal reviewers: do not upload others' unpublished or confidential
papers (e.g. blind-review assignments) to MinerU/LLM APIs configured in .env.
Run: python run_mcp.py
"""

from __future__ import annotations

import json
import traceback

from fastmcp import FastMCP

from review_agent import service

mcp = FastMCP(
    name="Review Agent",
    instructions=(
        "Pre-submission self-check and simulated peer review for authors' own "
        "manuscripts only. Pipeline: PDF → MinerU → Fast task section_map → Pro analysis "
        "→ review_draft.md (dual-model merge when PRO2 is set). "
        "Do not use for formal reviewer workflows or others' unpublished/confidential papers."
    ),
)


def _json_result(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _json_error(exc: Exception) -> str:
    return _json_result(
        {
            "ok": False,
            "error": str(exc),
            "type": type(exc).__name__,
        }
    )


@mcp.tool
def review_check_env(need_compare: bool | None = None) -> str:
    """
    Verify MinerU, Fast, and Pro API connectivity (and Pro2 if compare is enabled).
    Call this before starting a long review run.
    """
    try:
        return _json_result(service.check_environment(need_compare=need_compare))
    except Exception as exc:
        return _json_error(exc)


@mcp.tool
def review_run_pdf(
    pdf_path: str,
    no_compare: bool = False,
    skip_preflight: bool = False,
) -> str:
    """
    Run the full self-check / simulated-review pipeline on a PDF (author's own work).
    Creates a new workspace under data/runs/. May take 15+ minutes.
    Do not use with manuscripts received as a formal reviewer.
    """
    try:
        return _json_result(
            service.run_review(
                pdf_path,
                no_compare=no_compare,
                skip_preflight=skip_preflight,
            )
        )
    except Exception as exc:
        return _json_error(exc)


@mcp.tool
def review_resume(
    work_dir: str,
    no_compare: bool = False,
    skip_preflight: bool = False,
) -> str:
    """
    Resume from an existing workspace under data/runs/.
    Uses the PDF inside that folder; skips steps whose output files already exist.
    Delete specific outputs to force a step to re-run (see readme).
    """
    try:
        return _json_result(
            service.run_review(
                pdf_path=None,
                work_dir=work_dir,
                no_compare=no_compare,
                skip_preflight=skip_preflight,
            )
        )
    except Exception as exc:
        return _json_error(exc)


@mcp.tool
def review_list_runs() -> str:
    """List all run workspaces under data/runs/ with status summary."""
    try:
        return _json_result(service.list_runs())
    except Exception as exc:
        return _json_error(exc)


@mcp.tool
def review_clean_runs(
    older_than_days: int | None = None,
    delete_all: bool = False,
    dry_run: bool = True,
) -> str:
    """
    Delete old run directories. Requires older_than_days or delete_all.
    Defaults to dry_run=True (preview only); set dry_run=False to actually delete.
    """
    try:
        return _json_result(
            service.clean_runs(
                older_than_days=older_than_days,
                delete_all=delete_all,
                dry_run=dry_run,
            )
        )
    except Exception as exc:
        return _json_error(exc)


@mcp.tool
def review_run_status(work_dir: str) -> str:
    """Return which pipeline output files exist in a run workspace."""
    try:
        return _json_result(service.get_run_status(work_dir))
    except Exception as exc:
        return _json_error(exc)


@mcp.tool
def review_read_report(
    work_dir: str,
    filename: str = "review_draft.md",
    max_chars: int = 12000,
) -> str:
    """
    Read a generated report from a run workspace.
    filename: e.g. review_draft.md, contribution.md, experiment.md, references.md
    """
    try:
        return _json_result(
            service.read_run_report(work_dir, filename, max_chars=max_chars)
        )
    except Exception as exc:
        return _json_error(exc)


def main() -> None:
    """Start MCP server on stdio (default for Cursor)."""
    mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
