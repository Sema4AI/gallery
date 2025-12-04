from typing import Annotated, Literal

from pydantic import BaseModel, Field
from reducto.types.shared.parse_response import (
    ParseResponse,
    ResultFullResult,
    ResultFullResultChunk,
    ResultFullResultChunkBlock,
)


class Sema4aiParseResponseBlock(BaseModel):
    """
    A component of a chunk.
    """

    type: str = Field(description="The type of the block.")
    content: str = Field(description="The content of the block.")

    @classmethod
    def from_block(
        cls, result: ResultFullResultChunkBlock
    ) -> "Sema4aiParseResponseBlock":
        """
        Convert a ResultFullResultChunkBlock to a Sema4aiParseResponseBlock.
        """
        return cls(type=result.type, content=result.content)


class Sema4aiParseResponseChunk(BaseModel):
    """
    A piece of the parsed document.
    """

    content: str = Field(description="The content of the block.")
    embed: str | None = Field(description="The embed of the block.")
    blocks: list[Sema4aiParseResponseBlock] | None = Field(
        description="The discrete components of this chunk."
    )

    @classmethod
    def from_chunk(
        cls,
        result: ResultFullResultChunk,
        *,
        include_embed: bool = False,
        include_blocks: bool = False,
    ) -> "Sema4aiParseResponseChunk":
        """
        Convert a ResultFullResultChunk to a Sema4aiParseResponseChunk.
        """
        if include_blocks:
            blocks = [
                Sema4aiParseResponseBlock.from_block(block) for block in result.blocks
            ]
        else:
            blocks = None

        return cls(
            content=result.content,
            embed=result.embed if include_embed else None,
            blocks=blocks,
        )


class Sema4aiParseResponse(BaseModel):
    """
    Response from Parse output.
    """

    job_id: Annotated[
        str,
        Field(description="The job ID of the parse."),
    ]
    chunks: Annotated[
        list[Sema4aiParseResponseChunk] | None,
        Field(description="The chunks of the parsed document if full_output is False."),
    ] = None
    full_result: Annotated[
        ResultFullResult | None,
        Field(description="The full result of the parse if full_output is True."),
    ] = None

    @classmethod
    def from_result(
        cls,
        response: ParseResponse,
        *,
        include_embed: bool = False,
        include_blocks: bool = False,
        full_output: bool = False,
    ) -> "Sema4aiParseResponse":
        """
        Convert a ResultFullResult to a Sema4aiParseResponse.
        """
        # sema4ai-docint will localize the result to a ResultFullResult automatically.
        if not isinstance(response.result, ResultFullResult):
            raise ValueError(f"Expected ResultFullResult, got {type(response.result)}")

        if full_output:
            return cls(
                job_id=response.job_id,
                full_result=response.result,
            )

        return cls(
            job_id=response.job_id,
            chunks=[
                Sema4aiParseResponseChunk.from_chunk(
                    chunk, include_embed=include_embed, include_blocks=include_blocks
                )
                for chunk in response.result.chunks
            ],
        )


class ParseInput(BaseModel):
    """Input model for parse function parameters"""

    file_name: Annotated[
        str,
        Field(
            description=(
                "The name of the file to parse. This should be the file name only "
                "and not a path or URL."
            )
        ),
    ]
    chunking_mode: Annotated[
        Literal["disabled", "page", "variable"],
        Field(
            description=(
                "Chunking strategy for the document. Use 'page' for most documents "
                "(chunks by page), 'variable' for multi-page documents where content "
                "flows across pages, 'disabled' to return the entire document as a single chunk. "
                "Defaults to 'disabled'."
            )
        ),
    ] = "disabled"
    full_output: Annotated[
        bool,
        Field(
            description=(
                "If True, returns complete document structure with coordinates, metadata, "
                "and job details (recommended for tables/complex documents). If False, "
                "returns only basic text content."
            )
        ),
    ] = False
    force_reload: Annotated[
        bool,
        Field(
            description="Force a new parse even if the file has already been parsed."
        ),
    ] = False
