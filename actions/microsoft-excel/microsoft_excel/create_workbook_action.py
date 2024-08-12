from typing import Annotated, Literal

from pydantic import AliasPath, Field
from sema4ai.actions import OAuth2Secret, Response, action

from microsoft_excel._client import Client, get_client  # noqa: F401
from microsoft_excel._constants import EXCEL_MIME_TYPE
from microsoft_excel.models import Workbook


class NewWorkbook(Workbook):
    download_url: Annotated[
        str,
        Field(validation_alias=AliasPath("@microsoft.graph.downloadUrl")),
    ]
    web_url: Annotated[str, Field(validation_alias=AliasPath("webUrl"))]


@action(is_consequential=True)
def create_workbook_action(
    workbook_name: str,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Files.ReadWrite"]],
    ],
) -> Response[NewWorkbook]:
    """Creates a new empty workbook (Excel document).

    Args:
        token: The OAuth2 access token .
        workbook_name: Name of the new worksheet (Excel document)
    Returns:
        Structured data containing information about the new workbook.
    """

    with get_client(token) as client:  # type: Client
        response = client.put(
            NewWorkbook,
            f"/drive/root:/{workbook_name}.xlsx:/content",
            headers={"Content-Type": EXCEL_MIME_TYPE},
            data=b"",
        )

        return Response(result=response.load_worksheets(client))
