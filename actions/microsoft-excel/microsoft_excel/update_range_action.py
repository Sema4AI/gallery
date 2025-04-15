import re
from decimal import Decimal
from functools import cached_property
from string import ascii_uppercase
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, validate_call
from sema4ai.actions import ActionError, OAuth2Secret, Response, action
from typing_extensions import assert_never

from microsoft_excel._client import Client  # noqa: F401

Values = list[list[str | Decimal]]

_ADDRESS_PATTERN = r"^([A-Z]+)(\d+)$"


def _letter_to_number(value: str) -> int:
    if (result := ascii_uppercase.find(value)) < 0:
        raise ValueError(f"'{value}' is not an uppercase ascii letter")

    return result + 1


@validate_call
def _number_to_letter(
    value: Annotated[int, Field(ge=1, le=len(ascii_uppercase))],
) -> str:
    # Excel uses 1-index "array" for letters while we use 0-index in Python
    return ascii_uppercase[value - 1]


@validate_call
def convert_column_label_to_number(
    value: Annotated[str, Field(pattern="^[A-Z]+$")],
) -> int:
    column_number = 0
    for i in range(len(value) - 1):
        letter = value[i]  # fetch the current letter

        # we read the label from "right-to-left" so the first letter of the string is the last later in the label
        position_in_string = len(value) - 1 - i

        # each letter is represent a number where A is 1 and Z is 26.
        # Once we overflow, we start adding letters so 27 is AA, 28 is AB, 56 is BA 57 is BB and so on.

        # To properly convert to number we need to raise the length of the alphabet (in our case the ascii_upper)
        # to the power of the position.
        position_multiplier = len(ascii_uppercase) ** position_in_string

        # Finally add the position of the letter in the alphabet
        column_number += position_multiplier * _letter_to_number(letter)

    column_number += _letter_to_number(value[-1])

    return column_number


def convert_column_number_to_label(value: int) -> str:
    if value < 1:
        raise ValueError(
            f"Column numbers should be non-zero, positive ints, got {value}"
        )

    column_address = ""
    while True:
        a, b = divmod(value, len(ascii_uppercase))
        if b == 0:  # when we get zero we need to get the last letter
            b = len(ascii_uppercase)
        letter = _number_to_letter(b)
        column_address = f"{letter}{column_address}"
        if not a:
            break

        value = a

    return column_address


def _convert_value_to_string(value: any) -> str:
    if value is None:
        return ""
    return str(value)


class UpdateRange(BaseModel):
    values: Annotated[
        Values,
        Field(
            description="The values must be in the shape of a matrix where all rows have the same length"
        ),
    ]
    start_cell: Annotated[str, Field(pattern=_ADDRESS_PATTERN)]
    operation: Annotated[
        str,
        Field(
            description="The operation to be performed on the range. "
            "Possible values: 'replace', 'insert_shift_right', 'insert_shift_down'."
        ),
    ]

    @field_validator("values", mode="after")
    @classmethod
    def validate_values_is_matrix(cls, values: Values) -> Values:
        row_length = len(values[0])
        if any(len(row) != row_length for row in values[1:]):
            raise ValueError(
                "values must have the shape of a matrix, where each row has the same number of elements"
            )

        # Convert all values to strings
        return [[_convert_value_to_string(cell) for cell in row] for row in values]

    @property
    def address(self) -> str:
        return f"{self.start_cell}:{self.end_cell}"

    @cached_property
    def end_cell(self) -> str:
        if result := re.match(_ADDRESS_PATTERN, self.start_cell):
            start_column_label, start_row = result.group(1), int(result.group(2))
        else:
            raise ActionError(
                "Invalid starting cell provided. "
                "The starting cell should the following format {start_column}:{start_row} "
                "where start_column is the letter of the first column and start_row is the number of the first row"
            )

        # we reduce 1 because we are also filling the first row
        end_row = start_row + len(self.values) - 1

        start_column_number = convert_column_label_to_number(start_column_label)
        # we reduce 1 because we are also filling the first column
        end_column_number = start_column_number + len(self.values[0]) - 1
        end_column_label = convert_column_number_to_label(end_column_number)

        return f"{end_column_label}{end_row}"


class _RangeResponse(BaseModel, extra="ignore"):
    address: str


@action(is_consequential=True)
def update_range(
    workbook_id: str,
    worksheet_id_or_name: str,
    data: UpdateRange,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Files.ReadWrite"]],
    ],
) -> Response[str]:
    """
    Inserts or replaces data into an existing worksheet (page) for the specified workbook (Excel document).
    The data can be also be in the shape of a table.
    If the user does not specify that the data should replace the existing one,
    always ask whether they want to replace or insert and it which direction they want to shift the existing data.

    Args:
        token: The OAuth2 access token .
        workbook_id: The ID fo the workbook (Excel document) to retrieve.
        worksheet_id_or_name: The ID or the name of the worksheet to retrieve.
        data: The data to be inserted into the worksheet (Excel document).
    Returns:
        Message indicating success or failure.
    """

    url = f"/me/drive/items/{workbook_id}/workbook/worksheets/{worksheet_id_or_name}/range(address='{data.address}')"

    client = Client(token)
    match data.operation:
        case "insert_shift_right" | "insert_shift_down" as op:
            match op:
                case "insert_shift_right":
                    shift = "Right"
                case "insert_shift_down":
                    shift = "Down"
                case _:
                    assert_never(op)

            # When inserting a new range we first shift everything and then we add the values
            client.post(_RangeResponse, f"{url}/insert", json={"shift": shift})

    client.patch(_RangeResponse, url, json={"values": data.values})

    return Response(result=f"Range updated successfully at address: {data.address}")
