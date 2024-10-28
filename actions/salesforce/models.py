from typing import Annotated

from pydantic import BaseModel, Field


class BaseRecord(BaseModel, extra="allow"):
    Id: Annotated[str | None, Field(description="Unique identifier for the contact")]


class SalesforceResponse(BaseModel):
    total_size: Annotated[
        int, Field(alias="totalSize", description="Total number of contacts")
    ]
    done: Annotated[bool, Field(description="Indicates if the query is complete")]
    records: Annotated[list[BaseRecord], Field(description="List of contact records")]
