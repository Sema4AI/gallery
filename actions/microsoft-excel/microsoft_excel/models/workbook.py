from typing import Annotated

from pydantic import AliasPath, BaseModel, Field

from .worksheet import WorksheetInfo


class Workbook(BaseModel, extra="ignore", populate_by_name=True):
    id: Annotated[str, Field(description="Workbook ID")]
    name: str
    web_url: Annotated[
        str, Field(description="Workbook Web URL", validation_alias=AliasPath("webUrl"))
    ]
    worksheets: Annotated[
        list[WorksheetInfo] | None,
        Field(
            description="List of worksheets attached to this workbook. "
            "If this field has a null value then the worksheets where not loaded."
        ),
    ] = None
    download_url: Annotated[
        str | None,
        Field(validation_alias=AliasPath("@microsoft.graph.downloadUrl")),
    ] = None
