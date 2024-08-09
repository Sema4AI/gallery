from pydantic import BaseModel, Field
from typing import List, Optional


class Recipient(BaseModel):
    address: str = Field(description="Email address of the recipient")
    name: Optional[str] = Field(description="Name of the recipient", default=None)


class CC_Repient(Recipient):
    pass


class BCC_Repient(Recipient):
    pass


class MessageAttachment(BaseModel):
    message_id: str = Field(description="Id of the message")
    name: Optional[str] = Field(description="Name of the attachment", default=None)
    content_bytes: Optional[str] = Field(
        description="Base64-encoded content of the attachment", default=None
    )
    filepath: Optional[str] = Field(
        description="Path to the file to attach", default=None
    )


class Message(BaseModel):
    subject: str = Field(description="Subject of the message", default="")
    body: str = Field(description="Body of the message", default="")
    to: Optional[List[Recipient]] = Field(
        description="Recipients of the message", default=None
    )
    cc: Optional[List[CC_Repient]] = Field(
        description="CC recipients of the message", default=None
    )
    bcc: Optional[List[BCC_Repient]] = Field(
        description="BCC recipients of the message", default=None
    )
    attachments: Optional[List[MessageAttachment]] = Field(
        description="Attachments to include with the message", default=None
    )
    importance: Optional[str] = Field(
        description="Importance level of the message",
        default="normal",
        enum=["low", "normal", "high"],
    )
    reply_to: Optional[Recipient] = Field(description="Reply-to address", default=None)
