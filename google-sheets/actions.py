"""Set of actions operating on Google Sheets.

Currently supporting:
- Creating a new sheet
- Get a sheet schema
- Retrieve the contents of a sheet
- Update a sheet row
- Add rows to a sheet
"""

import gspread
import os
import json

from pathlib import Path
from typing import Annotated, List

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from robocorp.actions import Secret, action
from gspread import Worksheet

load_dotenv(Path("devdata") / ".env")

DEFAULT_CREDENTIALS = Secret.model_validate(os.getenv("GSPREAD_CREDENTIALS", ""))
ALPHA_LENGTH = ord("Z") - ord("A") + 1


class Row(BaseModel):
    columns: Annotated[List[str], Field(description="The columns that make up the row")]


class RowData(BaseModel):
    rows: Annotated[List[Row], Field(description="The rows that need to be added")]

    def to_raw_data(self) -> List[List[str]]:
        return [row.columns for row in self.rows]


@action(is_consequential=False)
def create_spreadsheet(name: str, credentials: Secret = DEFAULT_CREDENTIALS) -> str:
    """Creates a new Spreadsheet.

    Args:
        name: name of the Spreadsheet, which will be later used when reading or writing into it

    Returns:
        Message containing the spreadsheet title and url.
    """
    gc = gspread.service_account_from_dict(json.loads(credentials.value))

    spreadsheet = gc.create(name)

    return f"Sheet created: {spreadsheet.title}: {spreadsheet.url}"


@action(is_consequential=False)
def get_sheet_content(
    spreadsheet: str,
    worksheet: str,
    from_row: int = 1,
    limit: int = 100,
    credentials: Secret = DEFAULT_CREDENTIALS,
) -> str:
    """Get all content from the chosen Google Spreadsheet Sheet.

    To avoid performance issues there is a limit of rows to retrieve starting
    from `from_row`. Default is 100 rows.

    Args:
        spreadsheet: spreadsheet object or name of the spreadsheet from which to get the data
        worksheet: name of the worksheet within the spreadsheet
        from_row: used for pagination, default is first row
        limit: how many rows to retrieve starting from line number defined in `from_row`

    Returns:
        The sheet's content.
    """

    gc = gspread.service_account_from_dict(json.loads(credentials.value))

    spreadsheet = gc.open(spreadsheet)
    worksheet = spreadsheet.worksheet(worksheet)

    return _get_sheet_content(worksheet, from_row, limit)


@action(is_consequential=False)
def get_google_spreadsheet_schema(
    spreadsheet: str, credentials: Secret = DEFAULT_CREDENTIALS
) -> str:
    """Get necessary information to be able to work with a Google Spreadsheets correctly.

    Method will return the first few rows of each Sheet as an example.

    Args:
        spreadsheet: name of the spreadsheet from which to get the data

    Returns:
        Names of the sheets, and the first rows from each sheet to explain the context.
    """
    gc = gspread.service_account_from_dict(json.loads(credentials.value))
    sh = gc.open(spreadsheet)

    output = "Here are the sheets and their first rows.\n\n"
    content = []

    for sheet in sh.worksheets():
        content.append(_get_sheet_content(sheet, from_row=1, limit=5))

    return output + "\n".join(content)


@action(is_consequential=False)
def add_sheet_rows(
    spreadsheet: str,
    worksheet: str,
    rows_to_add: RowData,
    credentials: Secret = DEFAULT_CREDENTIALS,
) -> str:
    """Add multiple rows to the Google sheet.

    Make sure the values are in correct columns (needs to be ordered the same as in the document).

    Args:
        spreadsheet: name of the spreadsheet you want to work on
        worksheet: name of the sheet where the data is added to
        rows_to_add: the rows to be added to the end of the sheet

    Returns:
        Message indicating the success of the operation.
    """

    gc = gspread.service_account_from_dict(json.loads(credentials.value))

    spreadsheet = gc.open(spreadsheet)
    worksheet = spreadsheet.worksheet(worksheet)

    worksheet.append_rows(values=rows_to_add.to_raw_data())

    return "Row(s) were successfully added."


@action(is_consequential=False)
def update_sheet_row(
    spreadsheet: str,
    worksheet: str,
    cells: str,
    data: RowData,
    credentials: Secret = DEFAULT_CREDENTIALS,
) -> str:
    """Update a cell or a range of cells in a worksheet using A1 or R1:C1 notation.

    Args:
        spreadsheet: name of the spreadsheet from which to get the data
        worksheet: name of the sheet where the data is added to
        cells: cell or range of cells to update
        data: data to be inserted into the cell or cells

    Example:
        ```python
            update_sheet_row("Orders", "January Sheet", "A1", [["Order number"]])
            update_sheet_row("Orders", "January Sheet", "B1", [["Item"]])
            update_sheet_row("Orders", "January Sheet", "A2:B3", [[5, "Macbook Pro"], [6, "iPhone"]])
        ```

    Returns:
         Message indicating the success or failure of the operation.
    """

    gc = gspread.service_account_from_dict(json.loads(credentials.value))

    spreadsheet = gc.open(spreadsheet)
    worksheet = spreadsheet.worksheet(worksheet)

    worksheet.update(data.to_raw_data(), range_name=cells)

    return "Row was successfully updated."


def _get_sheet_content(worksheet: Worksheet, from_row, limit) -> str:
    output = f"Sheet {worksheet.title} contains following rows:\n\n"
    is_empty = f"Sheet {worksheet.title} is empty."

    letter_column = _to_column_letter(worksheet.column_count)
    content = worksheet.get(f"A{from_row}:{letter_column}{limit}")
    if not list(filter(bool, content)):
        return is_empty

    for row in content:
        row_string = ", ".join(map(str, row))
        output += row_string + "\n"

    return output


def _to_column_letter(number: int) -> str:
    # Convert a column number into a column letter(s).

    if number < 1:
        raise ValueError("Number must be greater than 0")

    column_letter = ""
    while number > 0:
        remainder = (number - 1) % ALPHA_LENGTH
        column_letter = chr(ord("A") + remainder) + column_letter
        number = (number - 1) // ALPHA_LENGTH

    return column_letter
