from typing import Annotated

from pydantic import BaseModel, Field
from reducto.types.shared.parse_response import ResultFullResult


class Sema4aiParseResponse(BaseModel):
    """
    Filtered response from Reducto ParseResponse.
    """

    job_id: str
    result: ResultFullResult


class Sema4aiExtractRequest(BaseModel):
    """
    Request to extract the given schema from the given file.
    """

    file_name: str | None = Field(
        default=None,
        description="The name of the file to extract from. Mutually exclusive with job_id.",
    )
    job_id: str | None = Field(
        default=None,
        description="The job ID of the file to extract from a previous parse. Mutually exclusive with file_name.",
    )
    extraction_schema: Annotated[
        str | dict,
        Field(
            description="The JSONSchema which describes the desired extracted output from the file."
        ),
    ]
    extraction_config: Annotated[
        dict, Field(description="Advanced Reducto configuration.")
    ] = Field(default={})

    start_page: int | None = Field(
        default=None,
        description="The start page of the file to extract from.",
    )
    end_page: int | None = Field(
        default=None,
        description="The end page of the file to extract from.",
    )


class Sema4aiExtractResponse(BaseModel):
    """
    Response from Reducto ExtractResponse.
    """

    result: Annotated[dict, Field(description="The extracted data.")]


class Sema4aiCreateSchemaRequest(BaseModel):
    """
    Request to create a schema for the given file.
    """

    file_name: Annotated[
        str, Field(description="The name of the file to create a JSONSchema for.")
    ]
    start_page: int | None = Field(
        default=None,
        description="The start page of the file to create a JSONSchema for.",
    )
    end_page: int | None = Field(
        default=None,
        description="The end page of the file to create a JSONSchema for.",
    )


class Sema4aiCreateSchemaResponse(BaseModel):
    """
    Response from Sema4ai CreateSchemaResponse.
    """

    schema: Annotated[
        dict,
        Field(description="A JSONSchema which describes the given file."),
    ]


class Sema4aiQueryKnowledgeBaseRequest(BaseModel):
    """
    Request to query the knowledge base with natural language.
    """

    document_name: str | None = Field(
        default=None,
        description="The name of the document to query from.",
    )
    document_id: str | None = Field(
        default=None,
        description="The ID of the document to query from.",
    )
    natural_language_query: Annotated[
        str,
        Field(
            description="The natural language query to search for in the knowledge base."
        ),
    ]
    relevance: float = Field(
        default=0.7,
        description="The relevance threshold for search results.",
    )
