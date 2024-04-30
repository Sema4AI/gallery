from datetime import datetime
from typing import List

from pydantic import BaseModel, Extra


class Messages(BaseModel, extra=Extra.allow):
    type: str
    user: str
    text: str
    ts: datetime


class MessageList(BaseModel, extra=Extra.ignore):
    messages: List[Messages]
