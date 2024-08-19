from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T], extra="ignore"):
    value: list[T]
    next_link: Annotated[str | None, Field(validation_alias="@odata.nextLink")] = None
