import shutil
from datetime import datetime
from pathlib import Path

from config import settings


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text(path: Path, encoding: str = "utf-8") -> str:
    return path.read_text(encoding=encoding)


def write_text(path: Path, content: str, encoding: str = "utf-8") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)
    return path


def list_pdfs_in_dir(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.pdf"))


def resolve_pdf_path(pdf_arg: str | None) -> Path:
    """Resolve CLI pdf_path. When omitted, require exactly one PDF in project root."""
    if pdf_arg:
        pdf = Path(pdf_arg).expanduser()
        if not pdf.is_absolute():
            pdf = Path.cwd() / pdf
        pdf = pdf.resolve()
        if not pdf.exists():
            raise FileNotFoundError(f"PDF not found: {pdf}")
        if pdf.suffix.lower() != ".pdf":
            raise ValueError(f"Not a PDF file: {pdf}")
        return pdf

    pdfs = list_pdfs_in_dir(settings.PROJECT_ROOT)
    root = settings.PROJECT_ROOT
    if not pdfs:
        raise FileNotFoundError(
            f"No PDF files in project root ({root}). "
            "Place exactly one PDF there or pass pdf_path on the command line."
        )
    if len(pdfs) > 1:
        names = ", ".join(p.name for p in pdfs)
        raise ValueError(
            f"Multiple PDFs in project root: {names}. "
            "Pass the target file explicitly: python main.py <path>.pdf"
        )
    return pdfs[0].resolve()


def prepare_paper_workspace(source_pdf: Path) -> tuple[Path, Path]:
    """Create an isolated run folder and copy the source PDF into it."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = ensure_dir(settings.RUNS_DIR / f"{source_pdf.stem}_{stamp}")
    copied_pdf = work_dir / source_pdf.name
    shutil.copy2(source_pdf, copied_pdf)
    return work_dir, copied_pdf


def resolve_work_dir(work_dir_arg: str) -> tuple[Path, Path]:
    """Resume an existing run: return (work_dir, pdf inside it)."""
    work_dir = Path(work_dir_arg).expanduser()
    if not work_dir.is_absolute():
        work_dir = Path.cwd() / work_dir
    work_dir = work_dir.resolve()
    if not work_dir.is_dir():
        raise FileNotFoundError(f"Work directory not found: {work_dir}")

    pdfs = sorted(work_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDF in work directory: {work_dir}")
    if len(pdfs) > 1:
        names = ", ".join(p.name for p in pdfs)
        raise ValueError(f"Multiple PDFs in work directory: {names}")
    return work_dir, pdfs[0].resolve()


def init_workspace(
    source_pdf: Path, work_dir_arg: str | None
) -> tuple[Path, Path]:
    if work_dir_arg:
        return resolve_work_dir(work_dir_arg)
    return prepare_paper_workspace(source_pdf)


def markdown_path_for_pdf(pdf_path: Path | str, work_dir: Path | str) -> Path:
    stem = Path(pdf_path).stem
    return Path(work_dir) / f"{stem}.md"


def load_prompt(prompt_name: str, prompts_dir: Path) -> str:
    path = prompts_dir / prompt_name
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return read_text(path)
