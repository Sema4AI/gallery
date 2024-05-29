"""Set of actions interacting with local Excel files.

These are currently capable of managing workbooks and their worksheets, while
retrieving and setting data from/into their cells.
"""


import contextlib
from pathlib import Path

from robocorp import excel, log
from robocorp.excel.tables import Table as ExcelTable
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


def _row2index(row: str, *, has_header: bool) -> int:
    # Computes the actual row index by excluding the header if present.
    row_offset = int(has_header)
    row_index = int(row) + row_offset
    return row_index


@action(is_consequential=True)
def create_workbook(file_path: str, sheet_name: str = "") -> Response[str]:
    """Create a new local Excel file defined as workbook.

    This will overwrite an already existing file and will try to guess the extension
    (xls or xlsx) if is not specified. It also creates a sheet with a default name
    which can be customized by providing an explicit `sheet_name`.

    Args:
        file_path: The file name or a local path pointing to the workbook file.
        sheet_name: The name of the initial sheet in the workbook. Leave it blank for
            relying on the default name ("Sheet").

    Returns:
        The absolute path of the newly created local Excel file.
    """
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
    """Delete an existing local Excel file defined as workbook.

    Will return an error message if the passed file is not found.

    Args:
        file_path: The file name or a local path pointing to the workbook file.

    Returns:
        The absolute path of the removed local Excel file.
    """
    print(f"Removing Excel file in path: {file_path}")
    with _capture_error(FileNotFoundError):
        path = _search_excel_file(file_path)
        path.unlink()

    return Response(result=f"Removed Excel file at location: {path}")


@action(is_consequential=True)
def create_worksheet(file_path: str, sheet_name: str) -> Response[str]:
    """Create a new sheet in an already existing workbook.

    Will return an error message if the sheet already exists.

    Args:
        file_path: The file name or a local path pointing to the workbook file.
        sheet_name: The name of the new sheet to be added in the workbook.

    Returns:
        The name of the newly created worksheet.
    """
    with _open_workbook(file_path) as (workbook, _):
        print(f"Creating sheet with name: {sheet_name}")
        with _capture_error(ValueError):
            workbook.create_worksheet(sheet_name)

    return Response(result=f"Successfully created sheet {sheet_name!r}!")


@action(is_consequential=True)
def delete_worksheet(file_path: str, sheet_name: str) -> Response[str]:
    """Remove a sheet from an already existing workbook.

    Will return an error message if the sheet is not present.

    Args:
        file_path: The file name or a local path pointing to the workbook file.
        sheet_name: The name of the sheet you want removed from the workbook.

    Returns:
        The name of the just removed worksheet.
    """
    with _open_workbook(file_path) as (workbook, _):
        print(f"Removing sheet with name: {sheet_name}")
        with _capture_error(KeyError):
            workbook.remove_worksheet(sheet_name)

    return Response(result=f"Successfully deleted sheet {sheet_name!r}!")


@action(is_consequential=True)
def add_rows(file_path: str, sheet_name: str, data_table: Table) -> Response[str]:
    """Add rows in an already existing worksheet of a workbook.

    This action expects a table (list of lists) structure representing the rows and
    columns you want to append in the sheet. Optionally, a header can be passed
    with the first call right in the `data_table`, so one would be set at the beginning
    of the sheet. This header is a vector containing the column names you want to have
    as the first row in the newly filled sheet.
    Will return an error message if the workbook or worksheet can't be found.

    Args:
        file_path: The file name or a local path pointing to the workbook file.
        sheet_name: The name of the sheet you want to store the rows into.
        data_table: A 2D matrix containing the sheet cell values.

    Returns:
        How many rows were added in the sheet, excluding the header if given.
    """
    header: list[str] = data_table.get_header()
    table = ExcelTable(data=data_table.as_list(), columns=header)
    effect = f"{len(table)} rows to sheet {sheet_name!r}"

    print(f"Adding {effect}...")
    with _open_workbook(file_path, sheet_name) as (_, worksheet):
        worksheet.append_rows_to_worksheet(table, header=bool(header))

    return Response(result=f"{effect} were added successfully!")


@action(is_consequential=True)
def set_cell(
    file_path: str,
    sheet_name: str,
    row: str,
    column: str,
    value: str,
    has_header: bool = False,
) -> Response[str]:
    """Set the value of a cell in an already existing worksheet of a workbook.

    This action expects a string `value` to be written in the cell identified by the
    given `row` and `column`. If `has_header` is true, then the row index number is
    adjusted so it matches the target row in the sheet.
    Will return an error message if the workbook or worksheet can't be found.

    Args:
        file_path: The file name or a local path pointing to the workbook file.
        sheet_name: The name of the sheet you want to store the rows into.
        row: The row number starting with 1.
        column: The column letter or index.
        value: The cell value to be set.
        has_header: Instructs the action about the presence of a header in the sheet.

    Returns:
        A confirmation with the cell set value given the provided position.
    """
    with _open_workbook(file_path, sheet_name) as (_, worksheet):
        worksheet.set_cell_value(
            _row2index(row, has_header=has_header), column, str(value)
        )

    return Response(
        result=f"Value {value!r} set successfully at row {row!r} column {column!r}."
    )


@action(is_consequential=False)
def get_cell(
    file_path: str, sheet_name: str, row: str, column: str, has_header: bool = False
) -> Response[str | None]:
    """Retrieve the value of a cell from an already existing worksheet of a workbook.

    This action works similarly to `set_cell`, but instead of setting a value it
    actually returns the value found at the given position in the sheet.

    Args:
        file_path: The file name or a local path pointing to the workbook file.
        sheet_name: The name of the sheet you want to store the rows into.
        row: The row number starting with 1.
        column: The column letter or index.
        has_header: Instructs the action about the presence of a header in the sheet.

    Returns:
        The value found at the given `row` and `column`.
    """
    with _open_workbook(file_path, sheet_name, save=False) as (_, worksheet):
        value = worksheet.get_cell_value(_row2index(row, has_header=has_header), column)

    return Response(result=value)


@action(is_consequential=False)
def get_table(
    file_path: str, sheet_name: str, has_header: bool = False
) -> Response[Table]:
    """Retrieve the whole content of an already existing worksheet of a workbook.

    This action retrieves all the cells found in the sheet and returns them in a table
    structure. The `has_header` parameter will allow the action to consider the first
    row in the sheet a header and not a table row.
    Will return an error message if the workbook or worksheet can't be found.

    Args:
        file_path: The file name or a local path pointing to the workbook file.
        sheet_name: The name of the sheet you want to store the rows into.
        has_header: Instructs the action about the presence of a header in the sheet.

    Returns:
        The value found at the given `row` and `column`.
    """
    with _open_workbook(file_path, sheet_name, save=False) as (_, worksheet):
        sheet_table = worksheet.as_table(header=has_header)

    rows = []
    for sheet_row in sheet_table.iter_lists(with_index=False):
        row = Row(cells=[str(cell) for cell in sheet_row])
        rows.append(row)

    header = Row(
        cells=[str(cell) for cell in sheet_table.columns] if has_header else []
    )
    return Response(result=Table(rows=rows, header=header))


@action(is_consequential=False)
def get_workbook_schema(file_path: str) -> Response[Schema]:
    """Retrieve the workbook overview defined as schema.

    This action identifies the sheets found in the given workbook and for each one of
    them it presents the first row which usually represents the header of the sheet.
    Will return an error message if the workbook can't be found.

    Args:
        file_path: The file name or a local path pointing to the workbook file.

    Returns:
        A list of sheets where for every sheet its name and first row are given.
    """
    sheets = []

    with _open_workbook(file_path, save=False) as (workbook, _):
        sheet_names = workbook.list_worksheets()
        for sheet_name in sheet_names:
            worksheet = workbook.worksheet(sheet_name)
            try:
                first_row = next(worksheet.as_table().iter_lists(with_index=False))
            except StopIteration:
                first_row = []

            cells = [str(cell) for cell in first_row if cell is not None]
            top_row = Row(cells=cells)
            sheet = Sheet(name=sheet_name, top_row=top_row)
            sheets.append(sheet)

    return Response(result=Schema(sheets=sheets))
