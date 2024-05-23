"""Set of actions interacting with local Excel files.

These are currently capable of managing workbooks and their worksheets, while
retrieving and setting data from/into their cells.
"""


import contextlib
from pathlib import Path

from robocorp import excel, log
from sema4ai.actions import action


def _search_excel_file(file_path: str, is_expected: bool = False) -> Path:
    # Guesses the local Excel file path if the provided one isn't specific.
    path = Path(file_path)

    # Search for an existing Excel when the extension isn't provided, as usually the
    #  LLM may not receive a full path with directories, name and extension specified.
    #  (e.g.: "Create a new Excel file called 'data' please.")
    if not path.suffix:
        file_name = path.stem
        search_dir = path.parent
        try:
            path = next(search_dir.glob(f"{file_name}.xls*"))
        except StopIteration:
            if is_expected:
                # Since the file is expected to exist, we let the caller know that it
                #  wasn't found.
                raise FileNotFoundError(
                    f"No Excel file matching {file_name!r} found in: {search_dir}"
                )
            else:
                # Otherwise we just pick a default extension.
                path = Path(f"{file_path}.xlsx")

    return path.expanduser().resolve()


@contextlib.contextmanager
def _capture_error(exc_type: type = Exception):
    error = exc_type()
    error.message = None
    try:
        yield error
    except exc_type as exc:
        log.exception(exc)
        error.message = str(exc)


@action(is_consequential=True)
def create_workbook(file_path: str, sheet_name: str = "") -> str:
    path = _search_excel_file(file_path)
    extension = path.suffix.strip(".").lower()
    workbook = excel.create_workbook(
        "xls" if extension == "xls" else "xlsx", sheet_name=sheet_name or None
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    print(f"Created new Excel file in location: {path}")
    return str(path)


@action(is_consequential=True)
def delete_workbook(file_path: str) -> str:
    with _capture_error(FileNotFoundError) as error:
        path = _search_excel_file(file_path, is_expected=True)
        print(f"Removing Excel file: {path}")
        path.unlink()
        return f"Removed Excel file: {path}"

    return error.message


@action(is_consequential=False)
def get_workbook_schema(file_path: str) -> str:
    with _capture_error(FileNotFoundError) as error:
        path = _search_excel_file(file_path, is_expected=True)
        workbook = excel.open_workbook(path)
    if error.message:
        return error.message

    sheets = workbook.list_worksheets()
    schema = ", ".join(sheets)
    print(schema)
    return schema
