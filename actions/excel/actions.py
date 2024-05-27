"""Set of actions interacting with local Excel files.

These are currently capable of managing workbooks and their worksheets, while
retrieving and setting data from/into their cells.
"""


import contextlib
from pathlib import Path

from robocorp import excel, log
from sema4ai.actions import action

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
    path = _search_excel_file(file_path, is_expected=False)
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
        path = _search_excel_file(file_path)
        print(f"Removing Excel file: {path}")
        path.unlink()
        return f"Removed Excel file: {path}"

    return error.message


@action(is_consequential=True)
def create_worksheet(file_path: str, sheet_name: str) -> str:
    with _capture_error(FileNotFoundError) as error:
        path = _search_excel_file(file_path)
        workbook = excel.open_workbook(path)
    if error.message:
        return error.message

    try:
        print(f"Creating sheet with name: {sheet_name}")
        workbook.create_worksheet(sheet_name)
    except ValueError as exc:
        return str(exc)
    else:
        workbook.save(path, overwrite=True)

    return f"Successfully created sheet {sheet_name!r} in Excel: {path}"


@action(is_consequential=True)
def delete_worksheet(file_path: str, sheet_name: str) -> str:
    with _capture_error(FileNotFoundError) as error:
        path = _search_excel_file(file_path)
        workbook = excel.open_workbook(path)
    if error.message:
        return error.message

    print(f"Removing sheet with name: {sheet_name}")
    with _capture_error(KeyError) as error:
        workbook.remove_worksheet(sheet_name)
    if error.message:
        return error.message

    workbook.save(path, overwrite=True)
    return f"Successfully deleted sheet {sheet_name!r} in Excel: {path}"


@action(is_consequential=True)
def add_rows(
    file_path: str, sheet_name: str, data_table: Table, header: Row = Row(cells=[])
) -> str:
    with _capture_error(FileNotFoundError) as error:
        path = _search_excel_file(file_path)
        workbook = excel.open_workbook(path)
    if error.message:
        return error.message

    with _capture_error(KeyError) as error:
        worksheet = workbook.worksheet(sheet_name)
    if error.message:
        return error.message

    table = [header.cells] if header else []
    table.extend(data_table.as_list())
    print(f"Adding {len(table)} rows to sheet {sheet_name!r}...")
    worksheet.append_rows_to_worksheet(table)
    workbook.save(path, overwrite=True)
    return "Rows were added successfully!"


@action(is_consequential=True)
def set_cell(file_path: str, sheet_name: str, row: str, column: str, value: str) -> str:
    with _capture_error(FileNotFoundError) as error:
        path = _search_excel_file(file_path)
        workbook = excel.open_workbook(path)
    if error.message:
        return error.message

    with _capture_error(KeyError) as error:
        worksheet = workbook.worksheet(sheet_name)
    if error.message:
        return error.message

    worksheet.set_cell_value(int(row), column, value)
    workbook.save(path, overwrite=True)
    return f"Value {value!r} set successfully at row {row!r} column {column!r}."


@action(is_consequential=False)
def get_cell(file_path: str, sheet_name: str, row: str, column: str) -> str:
    with _capture_error(FileNotFoundError) as error:
        path = _search_excel_file(file_path)
        workbook = excel.open_workbook(path)
    if error.message:
        return error.message

    with _capture_error(KeyError) as error:
        worksheet = workbook.worksheet(sheet_name)
    if error.message:
        return error.message

    value = worksheet.get_cell_value(int(row), column)
    return value


@action(is_consequential=False)
def get_table(file_path: str, sheet_name: str, has_header: bool = False) -> Table:
    with _capture_error(FileNotFoundError) as error:
        path = _search_excel_file(file_path)
        workbook = excel.open_workbook(path)
    if error.message:
        return error.message

    with _capture_error(KeyError) as error:
        worksheet = workbook.worksheet(sheet_name)
    if error.message:
        return error.message

    rows = []
    sheet_table = worksheet.as_table(header=has_header)
    for sheet_row in sheet_table.iter_lists(with_index=False):
        row = Row(cells=sheet_row)
        rows.append(row)

    return Table(rows=rows)


@action(is_consequential=False)
def get_workbook_schema(file_path: str) -> Schema:
    with _capture_error(FileNotFoundError) as error:
        path = _search_excel_file(file_path)
        workbook = excel.open_workbook(path)
    if error.message:
        return error.message

    sheets = []
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

    return Schema(sheets=sheets)
