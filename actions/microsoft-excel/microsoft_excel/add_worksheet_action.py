from typing import Literal

from sema4ai.actions import OAuth2Secret, Response, action

from microsoft_excel._client import Client, _create_worksheet  # noqa: F401


@action(is_consequential=True)
def add_sheet(
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Files.ReadWrite"]],
    ],
    workbook_id: str,
    worksheet_name: str = "",
) -> Response:
    """Add a new worksheet (page) to an existing workbook (Excel document).

    Args:
        token: The OAuth2 access token .
        workbook_id: The ID of the workbook.
        worksheet_name: Name of the new worksheet (Excel document).
        If not provided the default worksheet name is used.
    Returns:
        Message containing the spreadsheet title and url.
    """

    client = Client(token)

    return Response(
        result=_create_worksheet(
            client, workbook_id=workbook_id, worksheet_name=worksheet_name
        )
    )
