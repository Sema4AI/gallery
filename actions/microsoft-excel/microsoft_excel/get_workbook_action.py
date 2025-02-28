from typing import Annotated, Literal

from pydantic import BaseModel, Field, OnErrorOmit
from sema4ai.actions import ActionError, OAuth2Secret, Response, action

from microsoft_excel._client import (  # noqa: F401
    Client,
    get_client,
    _load_worksheets_for_workbook,
)
from microsoft_excel._constants import EXCEL_MIME_TYPE, FILE_EXTENSION
from microsoft_excel.models import APIResponse
from microsoft_excel.models.workbook import Workbook


class _File(BaseModel, extra="ignore"):
    mime_type: Annotated[Literal[EXCEL_MIME_TYPE], Field(validation_alias="mimeType")]


class _Item(BaseModel, extra="ignore"):
    id: str
    name: str
    # Used to filter out non-Excel files.
    # "OnErrorOmit[_Item]" tells pydantic to omit any item from the list that fails validation,
    # and since we restrict file.mime_type to the Excel mimetype any non-Excel files will error out.
    file: _File
    web_url: Annotated[str, Field(validation_alias="webUrl")]

    def match_name(self, value: str) -> bool:
        return f"{value.lower()}.{FILE_EXTENSION}" == self.name.lower()

    def as_workbook(self, client: Client) -> Workbook:
        workbook = Workbook(id=self.id, name=self.name, web_url=self.web_url)
        return _load_worksheets_for_workbook(client, workbook)


_SearchResponse = APIResponse[OnErrorOmit[_Item]]


@action(is_consequential=False)
def get_workbook_by_name(
    workbook_name: str,
    token: OAuth2Secret[
        Literal["microsoft"],
        list[Literal["Files.Read"]],
    ],
) -> Response[Workbook]:
    """Retrieves an existing workbook (Excel document) by name.

    Args:
        token: The OAuth2 access token .
        workbook_name: Name of the workbook (Excel document) to retrieve
    Returns:
        Structured data containing information about the workbook.
    """

    # Make sure we don't add the suffix
    if workbook_name.endswith(f"f.{FILE_EXTENSION}"):
        workbook_name = workbook_name.removesuffix(f".{FILE_EXTENSION}")

    with get_client(token) as client:  # type: Client
        response = client.get(
            _SearchResponse,
            f"/me/drive/root/search(q='{workbook_name}')",
        )

        matches = []
        while True:
            for item in response.value:  # type: _Item
                if item.match_name(workbook_name):
                    return Response[Workbook](result=item.as_workbook(client))

                if item.name.lower() not in workbook_name.lower():
                    continue

                matches.append(item.name)

            if response.next_link:
                response = client.get(_SearchResponse, response.next_link)
            else:
                break

        if matches:
            matches = ", ".join(matches)
            raise ActionError(f"Multiple files found: {matches}")

    raise ActionError("File not found")
