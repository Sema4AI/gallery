from pydantic import BaseModel, Field
from typing import Optional, List, Annotated


class Recipient(BaseModel):
    address: str = Field(description="Email address of the recipient")
    name: Annotated[str, Field(description="Name of the recipient")] = None


class CC_Repient(Recipient):
    pass


class BCC_Repient(Recipient):
    pass


class MessageAttachment(BaseModel):
    name: Optional[str] = Field(description="Name of the attachment", default="")
    content_bytes: Optional[str] = Field(
        description="Base64-encoded content of the attachment", default=""
    )
    filepath: Optional[str] = Field(
        description="Path to the file to attach", default=""
    )


class Message(BaseModel):
    subject: str = Field(description="Subject of the message", default="")
    body: str = Field(description="Body of the message", default="")
    to: list[Recipient] = Field(description="Recipients of the message", default=[])
    cc: list[CC_Repient] = Field(description="CC recipients of the message", default=[])
    bcc: list[BCC_Repient] = Field(
        description="BCC recipients of the message", default=[]
    )
    attachments: list[MessageAttachment] = Field(
        description="Attachments to include with the message", default=[]
    )
    importance: str = Field(
        description="Importance level of the message",
        default="normal",
        enum=["low", "normal", "high"],
    )
    reply_to: Recipient = Field(description="Reply-to address", default=None)


class MessageAttachmentList(BaseModel):
    attachments: Annotated[
        List[MessageAttachment], Field(description="A list of attachments")
    ] = []
