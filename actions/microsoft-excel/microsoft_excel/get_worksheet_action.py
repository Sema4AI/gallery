from typing import Literal

from sema4ai.actions import OAuth2Secret, Response, action

from microsoft_excel._client import Client, get_client  # noqa: F401
from microsoft_excel.models.worksheet import Range, Worksheet, WorksheetInfo


@action(is_consequential=False)
def get_worksheet_action(
    workbook_id: str,
    worksheet_id_or_name: str,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Files.Read"]],
    ],
) -> Response[Worksheet]:
    """Retrieves an existing worksheet (page) for the specified workbook (Excel document).

    Args:
        token: The OAuth2 access token .
        workbook_id: The ID fo the workbook (Excel document) to retrieve.
        worksheet_id_or_name: The ID or the name of the worksheet to retrieve.
    Returns:
        Structured data containing information about the worksheet.
    """
    worksheet_url = (
        f"/me/drive/items/{workbook_id}/workbook/worksheets/{worksheet_id_or_name}"
    )

    with get_client(token=token) as client:  # type: Client
        worksheet_info = client.get(WorksheetInfo, worksheet_url)
        worksheet_range = client.get(Range, f"{worksheet_url}/range/usedRange")

        worksheet = Worksheet.model_validate(
            {**worksheet_info.model_dump(), "range": worksheet_range}
        )

        return Response(result=worksheet)
