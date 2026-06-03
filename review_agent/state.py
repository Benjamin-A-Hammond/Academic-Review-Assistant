from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ReviewState:
    pdf_path: str
    work_dir: str = ""
    markdown_path: str = ""
    section_map: dict[str, Any] = field(default_factory=dict)
    markdown_quality: str = ""
    contribution_report: str = ""
    experiment_report: str = ""
    review_report: str = ""
    review_draft_en: str = ""
    run_compare: bool = True

    def output_path(self, filename: str) -> Path:
        if not self.work_dir:
            raise ValueError("work_dir is empty; initialize workspace before pipeline steps")
        return Path(self.work_dir) / filename
