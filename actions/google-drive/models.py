from typing import Annotated, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field


class Owner(BaseModel):
    displayName: Annotated[str, Field(description="Display name")]
    emailAddress: Optional[Annotated[str, Field(description="Email address")]] = None


class Permission(BaseModel):
    emailAddress: Annotated[
        Optional[str],
        Field(description="The email address of the person who has permission"),
    ] = None
    role: Annotated[
        str,
        Field(
            description="The role assigned to the user, such as reader, writer, commenter, organizer or fileOrganizer"
        ),
    ]
    deleted: Annotated[
        bool,
        Field(
            description="Indicates whether the account associated with this permission has been deleted"
        ),
    ] = False


class File(BaseModel):
    id: Annotated[str, Field(description="The unique identifier for the file")]
    name: Annotated[str, Field(description="The name of the file")]
    mimeType: Annotated[str, Field(description="The MIME type of the file")]
    createdTime: Annotated[
        str,
        Field(
            description="The time at which the file was created (RFC 3339 date-time)"
        ),
    ]
    modifiedTime: Annotated[
        str,
        Field(
            description="The last time the file was modified by anyone (RFC 3339 date-time)"
        ),
    ]
    owners: Annotated[
        List[Owner] | None,
        Field(description="A list of owners associated with the file"),
    ] = None
    size: Annotated[str | None, Field(description="The file size in bytes")] = None
    version: Annotated[str, Field(description="The current version of the file")]
    webViewLink: Annotated[
        str, Field(description="A URL for viewing the file in a web browser")
    ]
    permissions: Annotated[
        Optional[List[Permission]],
        Field(description="A list of permissions granted to the file"),
    ] = None
    location: Annotated[
        Optional[str],
        Field(description="The location of the drive item as a full folder path, e.g. /Folder1/Folder2/FileName")
    ] = None
    chat_filename: Annotated[
        Optional[str],
        Field(description="The filename used when attaching this file to chat, if applicable.")
    ] = None

    def is_excel(self) -> bool:
        return self.mimeType == "application/vnd.google-apps.spreadsheet"

    def is_doc(self) -> bool:
        return self.mimeType == "application/vnd.google-apps.document"


class BasicFile(BaseModel):
    id: Annotated[str, Field(description="The unique identifier for the file")]
    name: Annotated[str, Field(description="The name of the file")]
    location: Annotated[
        Optional[str],
        Field(description="The location of the drive item as a full folder path, e.g. /Folder1/Folder2/FileName")
    ] = None
    webViewLink: Annotated[
        Optional[str],
        Field(description="A URL for viewing the file in a web browser")
    ] = None


class FileList(BaseModel):
    files: Annotated[
        list[Union[File, BasicFile]], Field(description="A list of files matching the search query")
    ]


class BaseComment(BaseModel):
    id: Annotated[str, Field(description="The unique identifier for the comment")]
    kind: Annotated[
        str, Field(description="Indicating whether it is a comment or reply")
    ]
    createdTime: Annotated[
        str,
        Field(
            description="The time at which the comment/reply was created (RFC 3339 date-time)."
        ),
    ]
    modifiedTime: Annotated[
        str,
        Field(
            description="The last time the comment/reply was modified (RFC 3339 date-time)."
        ),
    ]
    htmlContent: Annotated[str, Field(description="The HTML content of the comment")]
    content: Annotated[str, Field(description="The plain text content of the comment")]
    author: Annotated[Owner, Field(description="The author of the comment")]
    deleted: Annotated[
        bool, Field(description="Indicates if the comment has been deleted")
    ]


class Reply(BaseComment):
    action: Optional[
        Annotated[
            str,
            Field(
                description="The action the reply performed to the parent comment which can be either resolve or reopen"
            ),
        ]
    ] = None


class Comment(BaseComment):
    resolved: Optional[
        Annotated[bool, Field(description="Indicates if the comment has been resolved")]
    ] = None
    replies: Annotated[
        List[Reply], Field(description="A list of replies to the comment")
    ]


class CommentList(BaseModel):
    comments: Annotated[
        List[Comment], Field(description="A list of comments on the file")
    ]


DataT = TypeVar("DataT")


class Response(BaseModel, Generic[DataT]):
    result: Optional[
        Annotated[DataT, Field(description="The resulting data from the request")]
    ] = None
    error: Optional[
        Annotated[str, Field(description="Error message, if any, from the request")]
    ] = None
