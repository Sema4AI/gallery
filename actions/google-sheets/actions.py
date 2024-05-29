"""Set of actions operating on Google Sheets.

Currently supporting:
- Creating a new sheet
- Get a sheet schema
- Retrieve the contents of a sheet
- Update a sheet row
- Add rows to a sheet
"""

from pathlib import Path
from typing import Annotated, List, Literal

import gspread
from dotenv import load_dotenv
from gspread import Worksheet
from gspread.auth import Credentials
from gspread.exceptions import APIError
from pydantic import BaseModel, Field
from sema4ai.actions import ActionError, OAuth2Secret, Response, action
from typing_extensions import Self

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


ALPHA_LENGTH = ord("Z") - ord("A") + 1

SCOPES = list[
    Literal[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
]


class _CatchError:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, APIError):
            raise ActionError(str(exc_val)) from None


class _Credentials(Credentials):
    @classmethod
    def from_oauth2_secret(cls, secret: OAuth2Secret) -> Self:
        credentials = cls()
        credentials.token = secret.access_token
        return credentials

    def refresh(self, request):
        raise ActionError("OAuth2 token expired")


class Row(BaseModel):
    columns: Annotated[List[str], Field(description="The columns that make up the row")]


class RowData(BaseModel):
    rows: Annotated[List[Row], Field(description="The rows that need to be added")]

    def to_raw_data(self) -> List[List[str]]:
        return [row.columns for row in self.rows]


@action(is_consequential=True)
def create_spreadsheet(
    oauth_access_token: OAuth2Secret[Literal["google"], SCOPES],
    name: str,
) -> Response[str]:
    """Creates a new Spreadsheet.

    Args:
        oauth_access_token: The OAuth2 access token .
        name: Name of the Spreadsheet, which will be later used when reading or writing into it.
    Returns:
        Message containing the spreadsheet title and url.
    """

    with _CatchError():
        gc = gspread.authorize(_Credentials.from_oauth2_secret(oauth_access_token))
        spreadsheet = gc.create(name)

        return Response[str](
            result=f"Sheet created: {spreadsheet.title}: {spreadsheet.url}"
        )


@action(is_consequential=True)
def create_worksheet(
    oauth_access_token: OAuth2Secret[Literal["google"], SCOPES],
    spreadsheet: str,
    title: str,
    rows: int = 100,
    columns: int = 20,
) -> Response[str]:
    """Creates a new Worksheet.

    Args:
        spreadsheet: Name of the Spreadsheet where to add the new Worksheet.
        title: The title of the new Worksheet.
        rows: Number of rows to be added in the new Worksheet.
        columns: Number of columns to be added in the new Worksheet.
        oauth_access_token: The OAuth2 access token .

    Returns:
        Message containing the newly created worksheet title and url.
    """

    with _CatchError():
        gc = gspread.authorize(_Credentials.from_oauth2_secret(oauth_access_token))

        spreadsheet = gc.open(spreadsheet)
        worksheet = spreadsheet.add_worksheet(title=title, rows=rows, cols=columns)

        return Response(
            result=f"Worksheet successfully created the worksheet: {worksheet.title}: {worksheet.url}"
        )


@action(is_consequential=False)
def get_sheet_content(
    oauth_access_token: OAuth2Secret[Literal["google"], SCOPES],
    spreadsheet: str,
    worksheet: str,
    from_row: int = 1,
    limit: int = 100,
) -> Response[str]:
    """Get all content from the chosen Google Spreadsheet Sheet.

    To avoid performance issues there is a limit of rows to retrieve starting
    from `from_row`. Default is 100 rows.

    Args:
        spreadsheet: Spreadsheet object or name of the spreadsheet from which to get the data.
        worksheet: Name of the worksheet within the spreadsheet.
        from_row: Used for pagination, default is first row.
        limit: How many rows to retrieve starting from line number defined in `from_row`.
        oauth_access_token: The OAuth2 access token .

    Returns:
        The sheet's content.
    """

    with _CatchError():
        gc = gspread.authorize(_Credentials.from_oauth2_secret(oauth_access_token))

        spreadsheet = gc.open(spreadsheet)
        worksheet = spreadsheet.worksheet(worksheet)

        return Response(result=_get_sheet_content(worksheet, from_row, limit))


@action(is_consequential=False)
def get_spreadsheet_schema(
    oauth_access_token: OAuth2Secret[Literal["google"], SCOPES],
    spreadsheet: str,
) -> Response[str]:
    """Get necessary information to be able to work with a Google Spreadsheets correctly.

    Method will return the first few rows of each Sheet as an example.

    Args:
        spreadsheet: Name of the spreadsheet from which to get the data.
        oauth_access_token: The OAuth2 access token .

    Returns:
        Names of the sheets, and the first rows from each sheet to explain the context.
    """

    with _CatchError():
        gc = gspread.authorize(_Credentials.from_oauth2_secret(oauth_access_token))
        sh = gc.open(spreadsheet)

        output = "Here are the sheets and their first rows.\n\n"
        content = []

        for sheet in sh.worksheets():
            content.append(_get_sheet_content(sheet, from_row=1, limit=5))

        result = f"output + {"\n".join(content)}"

        return Response(result=result)


@action(is_consequential=True)
def add_sheet_rows(
    oauth_access_token: OAuth2Secret[Literal["google"], SCOPES],
    spreadsheet: str,
    worksheet: str,
    rows_to_add: RowData,
) -> Response[str]:
    """Add multiple rows to the Google sheet.

    Make sure the values are in correct columns (needs to be ordered the same as in the document).

    Args:
        spreadsheet: Name of the spreadsheet you want to work on.
        worksheet: Name of the sheet where the data is added to.
        rows_to_add: The rows to be added to the end of the sheet.
        oauth_access_token: The OAuth2 access token .

    Returns:
        Message indicating the success of the operation.
    """

    with _CatchError():
        gc = gspread.authorize(_Credentials.from_oauth2_secret(oauth_access_token))

        spreadsheet = gc.open(spreadsheet)
        worksheet = spreadsheet.worksheet(worksheet)

        worksheet.append_rows(values=rows_to_add.to_raw_data())

        return Response(result="Row(s) were successfully added.")


@action(is_consequential=True)
def update_sheet_rows(
    oauth_access_token: OAuth2Secret[Literal["google"], SCOPES],
    spreadsheet: str,
    worksheet: str,
    cells: str,
    data: RowData,
) -> Response[str]:
    """Update a cell or a range of cells in a worksheet using A1 or R1:C1 notation.

    Args:
        spreadsheet: Name of the spreadsheet from which to get the data.
        worksheet: Name of the sheet where the data is added to.
        cells: Cell or range of cells to update.
        data: Data to be inserted into the cell or cells.
        oauth_access_token: The OAuth2 access token .

    Example:
        ```python
            update_sheet_rows("Orders", "January Sheet", "A1", [["Order number"]])
            update_sheet_rows("Orders", "January Sheet", "B1", [["Item"]])
            update_sheet_rows("Orders", "January Sheet", "A2:B3", [[5, "Macbook Pro"], [6, "iPhone"]])
        ```

    Returns:
         Message indicating the success or failure of the operation.
    """

    with _CatchError():
        gc = gspread.authorize(_Credentials.from_oauth2_secret(oauth_access_token))

        spreadsheet = gc.open(spreadsheet)
        worksheet = spreadsheet.worksheet(worksheet)

        worksheet.update(data.to_raw_data(), range_name=cells)

        return Response(result="Rows were successfully updated.")


def _get_sheet_content(worksheet: Worksheet, from_row, limit) -> str:
    output = f"{worksheet.title} contains following rows:\n\n"
    is_empty = f"{worksheet.title} is empty."

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
