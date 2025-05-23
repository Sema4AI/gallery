from pydantic import BaseModel, Field, model_validator
from typing import Annotated
import random


class Link(BaseModel):
    href: str = Field(description="The URL of the link")
    text: str = Field(description="The text of the link")


class Links(BaseModel):
    links: Annotated[list[Link], Field(description="A list of links", default=[])]


class Option(BaseModel):
    value: str = Field(description="The value of the option")
    text: str = Field(description="The text of the option")


class FormElement(BaseModel):
    type: str = Field(description="The type of the form element")
    text: str = Field(description="The text of the form element", default="")
    placeholder: str = Field(
        description="The placeholder of the form element", default=""
    )
    aria_label: str = Field(
        description="The aria label of the form element", default=""
    )
    id: str = Field(description="The id of the form element", default="")
    name: str = Field(description="The name of the form element", default="")
    class_: str = Field(description="The class of the form element", default="")
    value_type: str = Field(
        description="The type of the form element value", default=""
    )
    value_to_fill: str = Field(
        description="The value to fill in the form element", default=""
    )
    options: Annotated[
        list[Option], Field(description="A list of select options", default=[])
    ]
    count: int = Field(description="The count of the form element", default=1)

    def __eq__(self, other):
        if not isinstance(other, FormElement):
            return NotImplemented
        return (
            (self.type == other.type)
            and (self.text == other.text)
            and (self.placeholder == other.placeholder)
            and (self.aria_label == other.aria_label)
            and (self.id == other.id)
            and (self.name == other.name)
            and (self.class_ == other.class_)
            and (self.value_type == other.value_type)
            and (self.options == other.options)
        )

    def __hash__(self):
        return hash(
            (
                self.type,
                self.text,
                self.placeholder,
                self.aria_label,
                self.id,
                self.name,
                self.class_,
                self.value_type,
            )
        )


class Form(BaseModel):
    url: str = Field(description="The URL of the website")
    elements: Annotated[
        list[FormElement], Field(description="A list of form elements", default=[])
    ]


class WebPage(BaseModel):
    url: str = Field(description="The URL of the website")
    text_content: str = Field(description="The text content of the website")
    form: Form
    links: Links

    def calculate_total_size(self) -> int:
        """Calculate the total size of all properties in bytes.

        Returns:
            The total size of the url, text_content, form, and links in bytes.
        """
        url_size = len(self.url.encode("utf-8"))
        text_content_size = len(self.text_content.encode("utf-8"))
        form_size = len(self.form.json().encode("utf-8"))
        links_size = len(self.links.json().encode("utf-8"))

        return url_size + text_content_size + form_size + links_size


class DownloadedFile(BaseModel):
    content: str = Field(description="The content of the downloaded file")
    filepath: str = Field(description="The path of the downloaded file")
    status: str = Field(description="The status of the download")
    request_status: int = Field(description="The status of the request")
    content_type: str = Field(description="The content type of the file")
    content_length: int = Field(description="The size of the content in bytes")


class UserAgent(BaseModel):
    name: str = Field(default="", description="The user agent to use for browsing")

    @model_validator(mode="before")
    def set_user_agent(cls, values):
        if not values:
            values = {"name": _get_random_user_agent()}
        if not values["name"]:
            values["name"] = _get_random_user_agent()
        return values


def _get_random_user_agent():
    user_agents = [
        # Google Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 6 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Mobile Safari/537.36",
        # Mozilla Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:118.0) Gecko/20100101 Firefox/118.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0",
        "Mozilla/5.0 (Android 13; Mobile; rv:118.0) Gecko/118.0 Firefox/118.0",
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        # Microsoft Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36 Edg/117.0.2045.43",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36 Edg/117.0.2045.43",
        # Opera
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36 OPR/102.0.4880.78",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36 OPR/102.0.4880.78",
        "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Mobile Safari/537.36 OPR/102.0.4880.78",
    ]

    return random.choice(user_agents)
