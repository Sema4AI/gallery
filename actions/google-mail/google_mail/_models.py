from pydantic import BaseModel, Field
from typing import Annotated, Optional, Dict


class Attachment(BaseModel):
    filename: str = Field(description="The name of the attachment", default="")
    mimetype: str = Field(description="The MIME type of the attachment", default="")
    filesize: int = Field(
        description="The filesize of the attachment in bytes", default=0
    )


class Email(BaseModel):
    id_: Optional[str] = Field(
        alias="id", description="The ID of the email", default=""
    )
    subject: str = Field(description="The subject of the email", default="")
    body: str = Field(description="The body of the email", default="")
    from_: str = Field(alias="from", description="The sender of the email", default="")
    to: str = Field(description="The recipient of the email", default="")
    date: str = Field(description="The date the email was sent", default="")
    labels: list[str] = Field(
        description="The labels associated with the email", default=[]
    )
    attachments: list[Attachment] = Field(
        decscription="The attachments of the email", default=[]
    )

    def get_size_in_bytes(self) -> int:
        json_str = self.model_dump_json()
        json_bytes = json_str.encode("utf-8")
        return len(json_bytes)


class Emails(BaseModel):
    items: Annotated[
        list[Email],
        Field(description="A list of emails matching the filter", default=[]),
    ]
    error_message: str = Field(description="Possible error message", default="")


class EmailIdList(BaseModel):
    id_list: list[str] = Field(description="A list of email ids", default=[])


class Attachments(BaseModel):
    items: Annotated[
        list[Attachment],
        Field(description="A list of attachments", default=[]),
    ]


class Draft(BaseModel):
    draft_id: str = Field(description="The ID of the draft", default="")
    message: Dict = Field(description="The message of the draft", default={})


class Drafts(BaseModel):
    items: Annotated[
        list[Draft],
        Field(description="A list of drafts matching the filter", default=[]),
    ]
    error_message: str = Field(description="Possible error message", default="")
