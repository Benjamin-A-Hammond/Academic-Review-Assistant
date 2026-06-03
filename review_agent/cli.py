"""CLI entry: run pipeline, check-env, runs list/clean."""

import argparse
import sys
from pathlib import Path

from config import settings
from review_agent.pipeline import (
    compare_reviews,
    convert_pdf,
    extract_contribution,
    extract_experiment,
    generate_review,
    quality_check,
    structure_sections,
)
from review_agent.pipeline.step_utils import hydrate_state_from_workspace
from review_agent.state import ReviewState
from review_agent.utils.file_utils import (
    init_workspace,
    resolve_pdf_path,
    resolve_work_dir,
)
from review_agent.utils.logger import get_logger
from review_agent.utils.preflight import run_preflight
from review_agent.utils.runs_cli import cmd_runs_clean, cmd_runs_list

logger = get_logger(__name__)


def run_pipeline(
    source_pdf: Path,
    *,
    work_dir: str | None = None,
    no_compare: bool = False,
    skip_preflight: bool = False,
) -> ReviewState:
    run_compare = not no_compare and settings.compare_enabled_by_config()
    workspace, copied_pdf = init_workspace(source_pdf, work_dir)

    if work_dir:
        logger.info("Resuming work directory: %s", workspace)
    else:
        logger.info("Paper workspace: %s", workspace)

    state = ReviewState(
        pdf_path=str(copied_pdf),
        work_dir=str(workspace),
        run_compare=run_compare,
    )
    hydrate_state_from_workspace(state)

    need_mineru = not (
        state.markdown_path and Path(state.markdown_path).is_file()
    )
    if not skip_preflight:
        run_preflight(
            need_mineru=need_mineru,
            need_fast=True,
            need_pro=True,
            need_pro2=run_compare,
        )

    convert_pdf(state)
    quality_check(state)

    if state.markdown_quality == "BAD":
        raise RuntimeError("Markdown quality too low")

    structure_sections(state)
    extract_contribution(state)
    extract_experiment(state)
    if state.run_compare:
        compare_reviews(state)
    else:
        generate_review(state)

    return state


def cmd_check_env(args: argparse.Namespace) -> int:
    need_compare = args.need_compare
    try:
        from review_agent import service

        service.check_environment(need_compare=need_compare)
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    logger.info("All configured API checks passed.")
    if settings.LLM_STUB:
        logger.warning("LLM_STUB=1: LLM connectivity was not fully exercised.")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    try:
        if args.work_dir:
            _, pdf = resolve_work_dir(args.work_dir)
            if args.pdf_path:
                logger.warning(
                    "Ignoring pdf_path with --work-dir; using PDF in workspace: %s",
                    pdf.name,
                )
        else:
            pdf = resolve_pdf_path(args.pdf_path)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        return 1

    if args.pdf_path is None and not args.work_dir:
        logger.info("No pdf_path argument; using: %s", pdf)

    try:
        state = run_pipeline(
            pdf,
            work_dir=args.work_dir,
            no_compare=args.no_compare,
            skip_preflight=args.skip_preflight,
        )
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        if args.work_dir:
            logger.info("Resume with: python main.py run --work-dir %s", args.work_dir)
        else:
            logger.info(
                "If a workspace was created, resume with: "
                "python main.py run --work-dir data/runs/<folder>"
            )
        return 1

    logger.info("Pipeline completed successfully.")
    logger.info("Paper workspace: %s", state.work_dir)
    logger.info("Markdown: %s", state.markdown_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Academic Review Assistant — pre-submission self-check and "
            "simulated peer review (authors' own manuscripts only)"
        ),
        epilog=(
            "Usage boundary: for authors to review their own work before submission. "
            "Do not use with others' unpublished manuscripts received as a formal "
            "reviewer (confidential / blind-review materials must not be sent to "
            "MinerU or LLM APIs)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser(
        "run",
        help="Run full self-check / simulated-review pipeline (default)",
    )
    run_p.add_argument(
        "pdf_path",
        nargs="?",
        default=None,
        help="Input PDF path (optional if resuming with --work-dir)",
    )
    run_p.add_argument(
        "--work-dir",
        default=None,
        help="Resume an existing run under data/runs/",
    )
    run_p.add_argument(
        "--no-compare",
        action="store_true",
        help="Skip dual-model compare even if PRO2_* is configured",
    )
    run_p.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip API connectivity checks at startup",
    )
    run_p.set_defaults(func=cmd_run)

    check_p = sub.add_parser("check-env", help="Verify API keys and connectivity")
    check_p.add_argument(
        "--need-compare",
        action="store_true",
        default=None,
        help="Also verify PRO2_* (default: on if PRO2 is configured)",
    )
    check_p.set_defaults(func=cmd_check_env)

    runs_p = sub.add_parser("runs", help="Manage run workspaces")
    runs_sub = runs_p.add_subparsers(dest="runs_command", required=True)

    list_p = runs_sub.add_parser("list", help="List run directories")
    list_p.set_defaults(func=lambda _a: cmd_runs_list())

    clean_p = runs_sub.add_parser("clean", help="Delete old run directories")
    clean_p.add_argument(
        "--older-than-days",
        type=int,
        default=None,
        metavar="N",
        help="Delete runs older than N days",
    )
    clean_p.add_argument(
        "--all",
        action="store_true",
        help="Delete all runs",
    )
    clean_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deletions only (default: delete immediately)",
    )
    clean_p.set_defaults(
        func=lambda a: cmd_runs_clean(
            older_than_days=a.older_than_days,
            dry_run=a.dry_run,
            delete_all=a.all,
        )
    )

    mcp_p = sub.add_parser("mcp", help="Start MCP server on stdio (for Cursor)")
    mcp_p.set_defaults(func=_cmd_mcp)

    return parser


def _cmd_mcp(_args: argparse.Namespace) -> int:
    from review_agent.mcp_server import main as mcp_main

    mcp_main()
    return 0


def _normalize_argv(argv: list[str]) -> list[str]:
    """Backward compatibility: `python main.py paper.pdf` → `run paper.pdf`."""
    if not argv:
        return ["run"]
    if argv[0] in ("run", "check-env", "runs", "mcp", "-h", "--help"):
        return argv
    if argv[0].startswith("-"):
        return ["run", *argv]
    return ["run", *argv]


def main(argv: list[str] | None = None) -> int:
    raw = list(argv if argv is not None else sys.argv[1:])
    normalized = _normalize_argv(raw)
    parser = build_parser()
    if normalized in (["-h"], ["--help"]):
        parser.print_help()
        return 0

    args = parser.parse_args(normalized)

    if args.command == "run":
        if not args.pdf_path and not args.work_dir:
            parser.error("run requires pdf_path or --work-dir")
        return cmd_run(args)

    if args.command == "check-env":
        return cmd_check_env(args)

    if args.command == "runs":
        func = getattr(args, "func", None)
        if func is None:
            parser.error("runs requires a subcommand: list | clean")
        return func(args)

    if args.command == "mcp":
        return _cmd_mcp(args)

    parser.print_help()
    return 0
