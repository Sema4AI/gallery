from typing import Literal

from sema4ai.actions import OAuth2Secret, Response, action

from microsoft_excel._client import Client, get_client  # noqa: F401
from microsoft_excel.models.worksheet import WorksheetInfo


@action(is_consequential=True)
def add_sheet_action(
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

    payload = {"name": worksheet_name} if worksheet_name.strip() else None

    with get_client(token) as client:  # type: Client
        response = client.post(
            WorksheetInfo,
            f"/me/drive/items/{workbook_id}/workbook/worksheets/add",
            json=payload,
        )

        return Response(result=response)
