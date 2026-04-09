from __future__ import annotations

from pathlib import Path
import sys


def ensure_project_root_on_syspath(current_file: str) -> Path:
    """
    Allow running package files directly, e.g.:
      python data_pipeline/spiders/energy_gov.py
      python data_pipeline/scheduler/runner.py

    When executed as a script, Python puts the script's directory on sys.path,
    which breaks absolute imports like `import data_pipeline...`.
    This function finds the repository root (the directory containing
    the `data_pipeline/` package) and prepends it to sys.path.
    """

    file_path = Path(current_file).resolve()
    project_root: Path | None = None
    for parent in file_path.parents:
        if (parent / "data_pipeline").is_dir():
            project_root = parent
            break

    if project_root is None:
        raise RuntimeError(f"Cannot locate project root from {file_path}")

    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    return project_root

