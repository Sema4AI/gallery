from enum import Enum

from pydantic import BaseModel, Field


class DeleteOneDriveItemParams(BaseModel):
    item_id: str = Field(..., description="The ID of the file or folder to delete")


class GetOneDriveItemByIdParams(BaseModel):
    item_id: str = Field(..., description="The ID of the file or folder to retrieve")


class ItemType(str, Enum):
    files = "files"
    folders = "folders"
    all = "all"


class OneDriveFolderCreationParams(BaseModel):
    folder_name: str
    parent_folder_path: str = Field(
        default="/",
        description="The path of the parent folder where the new folder will be created. Use '/' for the root of OneDrive.",
    )


class OneDriveListingParams(BaseModel):
    folder_path: str = Field(
        default="/", description="The path of the folder to list items from"
    )
    item_type: ItemType = Field(
        default=ItemType.all, description="Type of items to list"
    )


class OneDriveSearchItemsRequest(BaseModel):
    query: str
    item_type: ItemType = Field(
        default=ItemType.all,
        description="Type of items to search for, 'files', 'folders', defaults to 'all'",
    )


class OneDriveUploadRequest(BaseModel):
    filename: str
    folder_path: str = Field(
        default="/",
        description="The path of the folder where the file will be uploaded. Use '/' for the root of OneDrive.",
    )


class RecursiveOneDriveFoldersParams(BaseModel):
    root_folder: str = Field(
        default="/",
        description="The root folder to start listing folders from. Use '/' for the root of OneDrive.",
    )


class RenameOneDriveItemParams(BaseModel):
    item_id: str = Field(..., description="The ID of the file or folder to rename")
    new_name: str = Field(
        ..., description="The new name for the file (including extension) or folder"
    )
