from pydantic import BaseModel, Field
from typing import Optional, List, Annotated, Literal, Union


class Recipient(BaseModel):
    address: str = Field(description="Email address of the recipient")
    name: Optional[Union[str, None]] = Field(description="Name of the recipient")


class CC_Recipient(Recipient):
    pass


class BCC_Recipient(Recipient):
    pass


class MessageAttachment(BaseModel):
    name: Optional[str] = Field(description="Name of the attachment", default="")
    content_bytes: Optional[str] = Field(
        description="Base64-encoded content of the attachment", default=""
    )
    filepath: Optional[str] = Field(
        description="Path to the file to attach", default=""
    )


class MessageAttachmentList(BaseModel):
    attachments: Annotated[
        List[MessageAttachment], Field(description="A list of attachments")
    ] = []


class Message(BaseModel):
    subject: Optional[str] = Field(default="", description="Subject of the message")
    body: Optional[str] = Field(default="", description="Body of the message")
    to: Optional[List[Recipient]] = Field(
        default_factory=list, description="Recipients of the message"
    )
    cc: Optional[List[CC_Recipient]] = Field(
        default_factory=list, description="CC recipients of the message"
    )
    bcc: Optional[List[BCC_Recipient]] = Field(
        default_factory=list, description="BCC recipients of the message"
    )
    attachments: Optional["MessageAttachmentList"] = Field(
        default_factory=list, description="Attachments to include with the message"
    )
    importance: Optional[Union[Literal["low", "normal", "high"], None]] = Field(
        default="normal", description="Importance level of the message"
    )
    reply_to: Optional["Recipient"] = Field(
        default=None, description="Reply-to address"
    )
