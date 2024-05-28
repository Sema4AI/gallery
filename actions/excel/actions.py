"""Set of actions interacting with local Excel files.

These are currently capable of managing workbooks and their worksheets, while
retrieving and setting data from/into their cells.
"""


import contextlib
from pathlib import Path

from robocorp import excel, log
from sema4ai.actions import ActionError, Response, action

from models import Row, Schema, Sheet, Table


def _search_excel_file(file_path: str, is_expected: bool = True) -> Path:
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
                # Otherwise we just pick a default favoured extension.
                path = Path(f"{file_path}.xlsx")

    return path.expanduser().resolve()


@contextlib.contextmanager
def _capture_error(exc_type: type = Exception):
    # Captures given error types and re-raises them as action errors in order to return
    #  a result containing an error message through the Action Server.
    try:
        yield
    except exc_type as exc:
        log.exception(exc)
        raise ActionError(exc) from exc


@contextlib.contextmanager
def _open_workbook(file_path: str, sheet_name: str | None = None, save: bool = True):
    # Opens a workbook, provides the control to a sheet optionally, then saves the
    #  changes that may have occurred in the caller.
    print(f"Opening workbook with file path: {file_path}")
    with _capture_error(FileNotFoundError):
        path = _search_excel_file(file_path)
        workbook = excel.open_workbook(path)

    if sheet_name:
        print(f"Opening worksheet with name: {sheet_name}")
        with _capture_error(KeyError):
            worksheet = workbook.worksheet(sheet_name)
        yield workbook, worksheet
    else:
        yield workbook, None

    if save:
        print(f"Saving workbook changes in path: {path}")
        workbook.save(path, overwrite=True)


@action(is_consequential=True)
def create_workbook(file_path: str, sheet_name: str = "") -> Response[str]:
    path = _search_excel_file(file_path, is_expected=False)
    extension = path.suffix.strip(".").lower()
    workbook = excel.create_workbook(
        "xls" if extension == "xls" else "xlsx", sheet_name=sheet_name or None
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    return Response(result=f"Created new Excel file in location: {path}")


@action(is_consequential=True)
def delete_workbook(file_path: str) -> Response[str]:
    print(f"Removing Excel file in path: {file_path}")
    with _capture_error(FileNotFoundError):
        path = _search_excel_file(file_path)
        path.unlink()

    return Response(result=f"Removed Excel file at location: {path}")


@action(is_consequential=True)
def create_worksheet(file_path: str, sheet_name: str) -> Response[str]:
    with _open_workbook(file_path) as (workbook, _):
        print(f"Creating sheet with name: {sheet_name}")
        try:
            workbook.create_worksheet(sheet_name)
        except ValueError as exc:
            raise ActionError(exc) from exc

    return Response(result=f"Successfully created sheet {sheet_name!r}!")


@action(is_consequential=True)
def delete_worksheet(file_path: str, sheet_name: str) -> Response[str]:
    with _open_workbook(file_path) as (workbook, _):
        print(f"Removing sheet with name: {sheet_name}")
        try:
            workbook.remove_worksheet(sheet_name)
        except KeyError as exc:
            raise ActionError(exc) from exc

    return Response(result=f"Successfully deleted sheet {sheet_name!r}!")


@action(is_consequential=True)
def add_rows(
    file_path: str, sheet_name: str, data_table: Table, header: Row = Row(cells=[])
) -> Response[str]:
    with _open_workbook(file_path, sheet_name) as (_, worksheet):
        table = [header.cells] if header else []
        table.extend(data_table.as_list())
        effect = f"{len(table)} rows to sheet {sheet_name!r}"
        print(f"Adding {effect}...")
        worksheet.append_rows_to_worksheet(table)

    return Response(result=f"{effect} were added successfully!")


@action(is_consequential=True)
def set_cell(
    file_path: str, sheet_name: str, row: str, column: str, value: str
) -> Response[str]:
    with _open_workbook(file_path, sheet_name) as (_, worksheet):
        worksheet.set_cell_value(int(row), column, value)

    return Response(
        result=f"Value {value!r} set successfully at row {row!r} column {column!r}."
    )


@action(is_consequential=False)
def get_cell(file_path: str, sheet_name: str, row: str, column: str) -> Response[str]:
    with _open_workbook(file_path, sheet_name, save=False) as (_, worksheet):
        value = worksheet.get_cell_value(int(row), column)

    return Response(result=value)


@action(is_consequential=False)
def get_table(
    file_path: str, sheet_name: str, has_header: bool = False
) -> Response[Table]:
    with _open_workbook(file_path, sheet_name, save=False) as (_, worksheet):
        sheet_table = worksheet.as_table(header=has_header)

    rows = []
    for sheet_row in sheet_table.iter_lists(with_index=False):
        row = Row(cells=sheet_row)
        rows.append(row)

    return Response(result=Table(rows=rows))


@action(is_consequential=False)
def get_workbook_schema(file_path: str) -> Response[Schema]:
    sheets = []

    with _open_workbook(file_path, save=False) as (workbook, _):
        sheet_names = workbook.list_worksheets()
        for sheet_name in sheet_names:
            worksheet = workbook.worksheet(sheet_name)
            try:
                first_row = next(worksheet.as_table().iter_lists(with_index=False))
            except StopIteration:
                first_row = []

            cells = [cell for cell in first_row if cell is not None]
            top_row = Row(cells=cells)
            sheet = Sheet(name=sheet_name, top_row=top_row)
            sheets.append(sheet)

    return Response(result=Schema(sheets=sheets))
