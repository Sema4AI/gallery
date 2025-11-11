from pydantic import BaseModel, Field
from reducto.types.shared.parse_response import (
    ResultFullResult,
    ParseResponse,
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

    job_id: str = Field(description="The job ID of the parse.")
    chunks: list[Sema4aiParseResponseChunk] = Field(
        description="The chunks of the parsed document."
    )

    @classmethod
    def from_result(
        cls,
        response: ParseResponse,
        *,
        include_embed: bool = False,
        include_blocks: bool = False,
    ) -> "Sema4aiParseResponse":
        """
        Convert a ResultFullResult to a Sema4aiParseResponse.
        """
        # sema4ai-docint will localize the result to a ResultFullResult automatically.
        if not isinstance(response.result, ResultFullResult):
            raise ValueError(f"Expected ResultFullResult, got {type(response.result)}")

        return cls(
            job_id=response.job_id,
            chunks=[
                Sema4aiParseResponseChunk.from_chunk(
                    chunk, include_embed=include_embed, include_blocks=include_blocks
                )
                for chunk in response.result.chunks
            ],
        )
