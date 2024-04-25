from pydantic import BaseModel, Field
from typing import Annotated


class Link(BaseModel):
    href: str = Field(description="The URL of the link")
    text: str = Field(description="The text of the link")


class Links(BaseModel):
    links: Annotated[list[Link], Field(description="A list of links", default=[])]


class SearchResult(BaseModel):
    title: str = Field(description="The title of the search result", default="")
    link: str = Field(description="The link of the search result", default="")


class SearchResultList(BaseModel):
    results: Annotated[
        list[SearchResult], Field(description="A list of google search results")
    ]


class PlaceSearchResult(BaseModel):
    title: str = Field(description="The title of the search result", default="")
    address: str = Field(description="The address of the search result", default="")
    phone: str = Field(description="The phone number of the search result", default="")
    desc: str = Field(description="The description of the search result", default="")
    source: str = Field(description="The source of the search result", default="")
    latitude: str = Field(description="The latitude of the search result", default="")
    longitude: str = Field(description="The longitude of the search result", default="")
    url: str = Field(description="The link of the search result", default="")
    hours: str = Field(description="The opening hours of the search result", default="")
    category: str = Field(description="The category of the search result", default="")


class PlaceSearchResultList(BaseModel):
    results: Annotated[
        list[PlaceSearchResult], Field(description="A list of place search results")
    ]


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


class DownloadedFile(BaseModel):
    content: str = Field(description="The content of the downloaded file")
    filepath: str = Field(description="The path of the downloaded file")
    status: str = Field(description="The status of the download")
    request_status: int = Field(description="The status of the request")
    content_type: str = Field(description="The content type of the file")
    content_length: int = Field(description="The size of the content in bytes")
