"""List and clean run workspaces under data/runs/."""

import shutil
from datetime import datetime, timedelta
from pathlib import Path

from config import settings
from review_agent.utils.logger import get_logger

logger = get_logger(__name__)


def _run_dirs() -> list[Path]:
    if not settings.RUNS_DIR.is_dir():
        return []
    return sorted(
        (p for p in settings.RUNS_DIR.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _dir_size(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total


def _format_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def _outputs_label(run_dir: Path) -> str:
    markers = [
        "section_map.json",
        "references.md",
        "contribution.md",
        "experiment.md",
        "review_draft.md",
    ]
    done = sum(1 for name in markers if (run_dir / name).is_file())
    return f"{done}/{len(markers)} reports"


def list_runs_info() -> list[dict]:
    runs = _run_dirs()
    result: list[dict] = []
    for run_dir in runs:
        mtime = datetime.fromtimestamp(run_dir.stat().st_mtime)
        result.append(
            {
                "name": run_dir.name,
                "path": str(run_dir.resolve()),
                "modified": mtime.isoformat(timespec="minutes"),
                "size": _format_size(_dir_size(run_dir)),
                "reports": _outputs_label(run_dir),
            }
        )
    return result


def clean_runs(
    *,
    older_than_days: int | None = None,
    dry_run: bool = False,
    delete_all: bool = False,
) -> dict:
    runs = _run_dirs()
    if not runs:
        return {"deleted": [], "dry_run": dry_run, "message": "No runs to clean"}

    cutoff = None
    if older_than_days is not None:
        cutoff = datetime.now() - timedelta(days=older_than_days)

    to_delete: list[Path] = []
    if delete_all:
        to_delete = runs
    elif cutoff is not None:
        for run_dir in runs:
            mtime = datetime.fromtimestamp(run_dir.stat().st_mtime)
            if mtime < cutoff:
                to_delete.append(run_dir)
    else:
        raise ValueError("Specify older_than_days or delete_all=True")

    deleted: list[str] = []
    for run_dir in to_delete:
        if dry_run:
            deleted.append(str(run_dir))
        else:
            shutil.rmtree(run_dir)
            deleted.append(str(run_dir))

    return {
        "dry_run": dry_run,
        "count": len(deleted),
        "paths": deleted,
    }


def cmd_runs_list() -> int:
    runs = list_runs_info()
    if not runs:
        logger.info("No runs under %s", settings.RUNS_DIR)
        return 0
    for item in runs:
        logger.info(
            "%s  |  %s  |  %s  |  %s",
            item["modified"].replace("T", " ")[:16],
            item["name"],
            item["size"],
            item["reports"],
        )
    logger.info("Total: %s run(s)", len(runs))
    return 0


def cmd_runs_clean(
    *,
    older_than_days: int | None = None,
    dry_run: bool = False,
    delete_all: bool = False,
) -> int:
    try:
        result = clean_runs(
            older_than_days=older_than_days,
            dry_run=dry_run,
            delete_all=delete_all,
        )
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    if result.get("message"):
        logger.info("%s", result["message"])
        return 0

    action = "Would remove" if dry_run else "Removed"
    for path in result["paths"]:
        prefix = "[dry-run] " if dry_run else ""
        logger.info("%s%s", prefix, path)
    logger.info("%s %s run(s)", action, result["count"])
    return 0
