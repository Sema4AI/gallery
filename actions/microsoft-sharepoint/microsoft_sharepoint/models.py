from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any
import re

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

class SiteIdentifier(BaseModel):
    """
    Identifier for a SharePoint site. Can be:
    - A full Microsoft site ID (as returned by other actions)
    - A plain name (e.g., 'my files', 'me', or the name of the site)
    Provide either site_id or site_name.
    """
    site_id: str = Field("", description="The unique Microsoft site ID, if known.")
    site_name: str = Field("", description="The human-readable name of the site, if known.")

    @field_validator("site_id")
    @classmethod
    def validate_site_id_format(cls, v):
        if v == "":
            return v
        # Allow special values
        if v.lower() in ["me", "my files", "myfiles"]:
            return v
        guid_regex = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        ms_format_regex = r"^[^,]+,[0-9a-fA-F\-]+,[0-9a-fA-F\-]+$"
        if re.match(guid_regex, v) or re.match(ms_format_regex, v):
            return v
        raise ValueError(
            "site_id must be a valid GUID, 'me', 'my files', 'myfiles', or in the format 'hostname,site-id,web-id'"
        )

    def is_valid_site_id(self):
        v = self.site_id
        if v == "":
            return False
        guid_regex = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        ms_format_regex = r"^[^,]+,[0-9a-fA-F\-]+,[0-9a-fA-F\-]+$"
        return bool(re.match(guid_regex, v) or re.match(ms_format_regex, v))
