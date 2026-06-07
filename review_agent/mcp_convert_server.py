"""
MCP server for PDF → Markdown conversion only (MinerU).

Use this entry when agents should parse PDFs without running the review pipeline.
Run: python run_mcp_convert.py
"""

from __future__ import annotations

import json
import traceback

from fastmcp import FastMCP

from review_agent import service

mcp = FastMCP(
    name="PDF to Markdown",
    instructions=(
        "Convert academic PDFs to structured Markdown via MinerU. "
        "Does not run LLM review, section mapping, or simulated peer review. "
        "Outputs land in data/runs/<paper>_<timestamp>/."
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
def pdf2md_check_env() -> str:
    """Verify MinerU API connectivity. Call before a long PDF conversion."""
    try:
        return _json_result(service.check_mineru_environment())
    except Exception as exc:
        return _json_error(exc)


@mcp.tool
def pdf2md_convert(
    pdf_path: str,
    skip_preflight: bool = False,
    quality_check: bool = False,
) -> str:
    """
    Convert a PDF to Markdown (MinerU). Creates a workspace under data/runs/.
    Does not run any LLM review steps. May take several minutes for large PDFs.
    """
    try:
        return _json_result(
            service.run_convert_pdf(
                pdf_path,
                skip_preflight=skip_preflight,
                quality_check=quality_check,
            )
        )
    except Exception as exc:
        return _json_error(exc)


@mcp.tool
def pdf2md_resume(
    work_dir: str,
    skip_preflight: bool = False,
    quality_check: bool = False,
) -> str:
    """
    Resume PDF→MD in an existing workspace under data/runs/.
    Skips conversion if markdown already exists in that folder.
    """
    try:
        return _json_result(
            service.run_convert_pdf(
                pdf_path=None,
                work_dir=work_dir,
                skip_preflight=skip_preflight,
                quality_check=quality_check,
            )
        )
    except Exception as exc:
        return _json_error(exc)


@mcp.tool
def pdf2md_read_markdown(
    work_dir: str,
    max_chars: int = 12000,
) -> str:
    """Read the converted Markdown from a run workspace."""
    try:
        return _json_result(
            service.read_run_markdown(work_dir, max_chars=max_chars)
        )
    except Exception as exc:
        return _json_error(exc)


def main() -> None:
    """Start PDF→MD MCP server on stdio."""
    mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
