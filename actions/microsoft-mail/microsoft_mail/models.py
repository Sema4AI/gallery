from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Annotated, Literal, Dict


class Recipient(BaseModel):
    address: str = Field(description="Email address of the recipient")
    name: Optional[str] = Field(description="Name of the recipient")


class CC_Recipient(Recipient):
    pass


class BCC_Recipient(Recipient):
    pass


class EmailAttachment(BaseModel):
    name: Optional[str] = Field(description="Name of the attachment", default="")
    content_bytes: Optional[str] = Field(
        description="Base64-encoded content of the attachment", default=""
    )
    filepath: Optional[str] = Field(
        description="Path to the file to attach", default=""
    )


class EmailAttachmentList(BaseModel):
    attachments: Annotated[
        List[EmailAttachment], Field(description="A list of attachments")
    ] = []


class Email(BaseModel):
    subject: Optional[str] = Field(default="", description="Subject of the email")
    body: Optional[str] = Field(default="", description="Body of the email")
    to: Optional[List[Recipient]] = Field(
        default_factory=list, description="Recipients of the email"
    )
    cc: Optional[List[CC_Recipient]] = Field(
        default_factory=list, description="CC recipients of the email"
    )
    bcc: Optional[List[BCC_Recipient]] = Field(
        default_factory=list, description="BCC recipients of the email"
    )
    attachments: Optional["EmailAttachmentList"] = Field(
        default_factory=EmailAttachmentList,
        description="Attachments to include with the email",
    )
    importance: Optional[Literal["low", "normal", "high"]] = Field(
        default="normal", description="Importance level of the email"
    )
    reply_to: Optional["Recipient"] = Field(
        default=None, description="Reply-to address"
    )


class Emails(BaseModel):
    items: List[Dict] = Field(description="List of emails")
    count: int = Field(description="Number of emails matching the search query")


class FlagStatus(str, Enum):
    not_flagged = "notFlagged"
    flagged = "flagged"
    complete = "complete"


class MessageFlag(BaseModel):
    flag_status: FlagStatus = Field(description="Flag status of the message")

    class Config:
        use_enum_values = True


class Category(BaseModel):
    display_name: str = Field(description="Display name of the category")
    color: Optional[str] = Field(
        default="Preset19",
        description="Color of the category (e.g., Preset19, Preset0, etc.)",
    )


class CategoryList(BaseModel):
    categories: Annotated[
        List[Category], Field(description="A list of categories")
    ] = []
