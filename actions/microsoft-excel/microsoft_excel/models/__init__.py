from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, Field
from typing_extensions import Self

from microsoft_excel._client import Client
from microsoft_excel.models.worksheet import WorksheetInfo

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T], extra="ignore"):
    value: list[T]
    next_link: Annotated[str | None, Field(validation_alias="@odata.nextLink")] = None


class Workbook(BaseModel, extra="ignore"):
    id: Annotated[str, Field(description="Workbook ID")]
    name: str
    worksheets: Annotated[
        list[WorksheetInfo] | None,
        Field(
            description="List of worksheets attached to this workbook. "
            "If this field has a null value then the worksheets where not loaded."
        ),
    ] = None

    def load_worksheets(self, client: Client) -> Self:
        if self.worksheets is None:
            response = client.get(
                APIResponse[WorksheetInfo],
                f"/me/drive/items/{self.id}/workbook/worksheets",
            )

            self.worksheets = response.value

        return self
