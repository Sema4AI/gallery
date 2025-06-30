from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any

class Location(BaseModel):
    name: str = Field(description="Name of the location", default="")
    url: str = Field(description="URL of the location", default="")


class File(BaseModel):
    file_id: str = Field(description="ID of the file", default="")
    name: str = Field(description="Name of the file", default="")
    location: Location = Field(description="Location details")
    file: Dict = Field(description="File details", default={})


class FileList(BaseModel):
    files: list[File] = Field(description="List of files", default=[])


class ColumnType(str, Enum):
    text = "text"
    boolean = "boolean"
    datetime = "dateTime"
    number = "number"


class ListColumn(BaseModel):
    column_name: str = Field(description="Name of the column", default="")
    column_type: ColumnType = Field(
        description="Type of the column", default=ColumnType.text
    )

    class Config:
        use_enum_values = True


class SharepointList(BaseModel):
    list_name: str = Field(description="Name of the list", default="")
    description: str = Field(description="Description of the list", default="")
    columns: list[ListColumn] = Field(description="List of columns", default=[])

class ListItem(BaseModel):
    fields: Any = Field(description="Field values for the list item as a dictionary", default=[])

class SharepointListItem(BaseModel):
    item_id: str = Field(description="ID of the list item", default="")
    fields: ListItem = Field(description="Field values for the list item")
