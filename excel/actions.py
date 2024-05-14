"""Set of actions interacting with local Excel files.

These are currently capable of managing workbooks and their worksheets, while
retrieving and setting data from/into their cells.
"""


from pathlib import Path

from robocorp import excel
from sema4ai.actions import action


def _norm_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


@action(is_consequential=True)
def create_workbook(path: str, sheet_name: str = "") -> str:
    path = _norm_path(path)
    extension = path.suffix.strip(".").lower()
    format_type = extension if extension in ("xls", "xslx") else "xlsx"
    workbook = excel.create_workbook(format_type, sheet_name=sheet_name or None)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    print(f"Created new Excel file in location: {path}")
    return str(path)
