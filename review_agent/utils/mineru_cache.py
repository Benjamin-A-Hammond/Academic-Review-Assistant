"""Cache MinerU markdown outputs by PDF content hash."""

import hashlib
import shutil
from pathlib import Path

from config import settings
from review_agent.utils.file_utils import ensure_dir
from review_agent.utils.logger import get_logger

logger = get_logger(__name__)


def pdf_content_hash(pdf_path: Path) -> str:
    digest = hashlib.sha256()
    with pdf_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_dir_for_pdf(pdf_path: Path) -> Path:
    return ensure_dir(settings.MINERU_CACHE_DIR / pdf_content_hash(pdf_path))


def cached_markdown_path(pdf_path: Path) -> Path:
    return cache_dir_for_pdf(pdf_path) / f"{pdf_path.stem}.md"


def has_cached_markdown(pdf_path: Path) -> bool:
    return cached_markdown_path(pdf_path).is_file()


def copy_cache_to_workdir(pdf_path: Path, work_dir: Path) -> Path:
    """Copy cached md + images into run workspace. Returns work_dir markdown path."""
    cache_root = cache_dir_for_pdf(pdf_path)
    stem = pdf_path.stem
    dest_md = work_dir / f"{stem}.md"
    src_md = cache_root / f"{stem}.md"
    if not src_md.is_file():
        raise FileNotFoundError(f"Cached markdown missing: {src_md}")

    ensure_dir(work_dir)
    shutil.copy2(src_md, dest_md)
    images_src = cache_root / "images"
    if images_src.is_dir():
        images_dest = work_dir / "images"
        if images_dest.exists():
            shutil.rmtree(images_dest)
        shutil.copytree(images_src, images_dest)
    for item in cache_root.iterdir():
        if item.name in (f"{stem}.md", "images"):
            continue
        dest = work_dir / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    logger.info("Restored MinerU output from cache: %s", cache_root)
    return dest_md


def save_workdir_to_cache(pdf_path: Path, work_dir: Path) -> None:
    """Persist run workspace markdown artifacts into content-addressed cache."""
    cache_root = ensure_dir(cache_dir_for_pdf(pdf_path))
    stem = pdf_path.stem
    src_md = work_dir / f"{stem}.md"
    if not src_md.is_file():
        return
    shutil.copy2(src_md, cache_root / f"{stem}.md")
    images_src = work_dir / "images"
    if images_src.is_dir():
        images_dest = cache_root / "images"
        if images_dest.exists():
            shutil.rmtree(images_dest)
        shutil.copytree(images_src, images_dest)
    logger.info("Saved MinerU output to cache: %s", cache_root)
