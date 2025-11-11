import json
from pathlib import Path
from typing import Any

import pytest
from reducto.types.shared.parse_response import ParseResponse, ResultFullResult

from src.models import (
    Sema4aiParseResponse,
    Sema4aiParseResponseBlock,
    Sema4aiParseResponseChunk,
)


@pytest.fixture
def parse_response_json() -> Any:
    """Load the parse-response.json test data."""
    test_dir = Path(__file__).parent
    with open(test_dir / "parse-response.json") as f:
        return json.load(f)


@pytest.fixture
def parse_response(parse_response_json: Any) -> ParseResponse:
    """Create a ParseResponse object from the test data."""
    return ParseResponse.model_validate(parse_response_json)


class TestSema4aiParseResponseBlock:
    """Tests for Sema4aiParseResponseBlock model."""

    def test_from_block_conversion(self, parse_response: ParseResponse) -> None:
        """Test converting a ResultFullResultChunkBlock to Sema4aiParseResponseBlock."""
        # Get the first block from the first chunk
        assert isinstance(parse_response.result, ResultFullResult)
        original_block = parse_response.result.chunks[0].blocks[0]

        # Convert using the from_block method
        block = Sema4aiParseResponseBlock.from_block(original_block)

        # Verify the conversion
        assert isinstance(block, Sema4aiParseResponseBlock)
        assert block.type == "Text"
        assert block.content.startswith("SkiGear Co.")
        assert "1661 Mesa Drive" in block.content

    def test_block_only_includes_type_and_content(
        self, parse_response: ParseResponse
    ) -> None:
        """Test that the block only includes type and content fields."""
        assert isinstance(parse_response.result, ResultFullResult)
        original_block = parse_response.result.chunks[0].blocks[0]
        block = Sema4aiParseResponseBlock.from_block(original_block)

        # Verify only expected fields are present
        block_dict = block.model_dump()
        assert set(block_dict.keys()) == {"type", "content"}

        # Verify fields that should be excluded are not present
        assert "bbox" not in block_dict
        assert "image_url" not in block_dict
        assert "confidence" not in block_dict
        assert "granular_confidence" not in block_dict

    def test_block_different_types(self, parse_response: ParseResponse) -> None:
        """Test block conversion with different block types."""
        assert isinstance(parse_response.result, ResultFullResult)
        blocks = parse_response.result.chunks[0].blocks

        # Test Title block
        title_block = Sema4aiParseResponseBlock.from_block(blocks[1])
        assert title_block.type == "Title"
        assert title_block.content == "EQUIPMENT INSPECTION"

        # Test Key Value block
        kv_block = Sema4aiParseResponseBlock.from_block(blocks[2])
        assert kv_block.type == "Key Value"
        assert "MACHINE: Injection Molder" in kv_block.content

        # Test Section Header block
        header_block = Sema4aiParseResponseBlock.from_block(blocks[3])
        assert header_block.type == "Section Header"
        assert header_block.content == "INSPECTION SUMMARY"


class TestSema4aiParseResponseChunk:
    """Tests for Sema4aiParseResponseChunk model."""

    def test_from_chunk_conversion_defaults(
        self, parse_response: ParseResponse
    ) -> None:
        """Test converting a ResultFullResultChunk with default parameters (exclude embed and blocks)."""
        assert isinstance(parse_response.result, ResultFullResult)
        original_chunk = parse_response.result.chunks[0]

        # Convert using the from_chunk method with defaults
        chunk = Sema4aiParseResponseChunk.from_chunk(original_chunk)

        # Verify the conversion
        assert isinstance(chunk, Sema4aiParseResponseChunk)
        assert chunk.content.startswith("SkiGear Co.")
        assert chunk.embed is None  # Default is to exclude embed
        assert chunk.blocks is None  # Default is to exclude blocks

    def test_from_chunk_conversion_with_embed(
        self, parse_response: ParseResponse
    ) -> None:
        """Test converting a ResultFullResultChunk with include_embed=True."""
        assert isinstance(parse_response.result, ResultFullResult)
        original_chunk = parse_response.result.chunks[0]

        # Convert with embed included
        chunk = Sema4aiParseResponseChunk.from_chunk(original_chunk, include_embed=True)

        # Verify the conversion
        assert isinstance(chunk, Sema4aiParseResponseChunk)
        assert chunk.content.startswith("SkiGear Co.")
        assert chunk.embed is not None
        assert chunk.embed.startswith("SkiGear Co.")
        assert chunk.blocks is None  # Still excluded by default

    def test_from_chunk_conversion_with_blocks(
        self, parse_response: ParseResponse
    ) -> None:
        """Test converting a ResultFullResultChunk with include_blocks=True."""
        assert isinstance(parse_response.result, ResultFullResult)
        original_chunk = parse_response.result.chunks[0]

        # Convert with blocks included
        chunk = Sema4aiParseResponseChunk.from_chunk(
            original_chunk, include_blocks=True
        )

        # Verify the conversion
        assert isinstance(chunk, Sema4aiParseResponseChunk)
        assert chunk.content.startswith("SkiGear Co.")
        assert chunk.embed is None  # Still excluded by default
        assert chunk.blocks is not None
        assert len(chunk.blocks) == 7
        assert all(len(b.content) > 0 for b in chunk.blocks), (
            "All blocks should have non-empty content: got {chunk.blocks}"
        )
        assert all(len(b.type) > 0 for b in chunk.blocks), (
            "All blocks should have non-empty type: got {chunk.blocks}"
        )

    def test_from_chunk_conversion_with_all_fields(
        self, parse_response: ParseResponse
    ) -> None:
        """Test converting a ResultFullResultChunk with both include_embed=True and include_blocks=True."""
        assert isinstance(parse_response.result, ResultFullResult)
        original_chunk = parse_response.result.chunks[0]

        # Convert with all fields included
        chunk = Sema4aiParseResponseChunk.from_chunk(
            original_chunk, include_embed=True, include_blocks=True
        )

        # Verify the conversion
        assert isinstance(chunk, Sema4aiParseResponseChunk)
        assert chunk.content.startswith("SkiGear Co.")
        assert chunk.embed is not None
        assert chunk.embed.startswith("SkiGear Co.")
        assert chunk.blocks is not None
        assert len(chunk.blocks) == 7
        assert all(len(b.content) > 0 for b in chunk.blocks), (
            "All blocks should have non-empty content: got {chunk.blocks}"
        )
        assert all(len(b.type) > 0 for b in chunk.blocks), (
            "All blocks should have non-empty type: got {chunk.blocks}"
        )

    def test_chunk_only_includes_expected_fields(
        self, parse_response: ParseResponse
    ) -> None:
        """Test that the chunk only includes content, embed, and blocks fields."""
        assert isinstance(parse_response.result, ResultFullResult)
        original_chunk = parse_response.result.chunks[0]

        # Test with all fields included
        chunk = Sema4aiParseResponseChunk.from_chunk(
            original_chunk, include_embed=True, include_blocks=True
        )

        # Verify only expected fields are present
        chunk_dict = chunk.model_dump()
        assert set(chunk_dict.keys()) == {"content", "embed", "blocks"}

        # Verify fields that should be excluded are not present
        assert "enriched" not in chunk_dict
        assert "enrichment_success" not in chunk_dict

    def test_chunk_blocks_are_converted_properly(
        self, parse_response: ParseResponse
    ) -> None:
        """Test that all blocks within a chunk are properly converted."""
        assert isinstance(parse_response.result, ResultFullResult)
        original_chunk = parse_response.result.chunks[0]
        chunk = Sema4aiParseResponseChunk.from_chunk(
            original_chunk, include_blocks=True
        )

        # Verify all blocks are Sema4aiParseResponseBlock instances
        assert chunk.blocks is not None
        assert all(
            isinstance(block, Sema4aiParseResponseBlock) for block in chunk.blocks
        )

        # Verify blocks have only type and content
        for block in chunk.blocks:
            block_dict = block.model_dump()
            assert set(block_dict.keys()) == {"type", "content"}

    def test_chunk_embed_excluded_by_default(
        self, parse_response: ParseResponse
    ) -> None:
        """Test that embed is None when include_embed=False (default)."""
        assert isinstance(parse_response.result, ResultFullResult)
        original_chunk = parse_response.result.chunks[0]

        # Default behavior - embed should be None
        chunk = Sema4aiParseResponseChunk.from_chunk(
            original_chunk, include_embed=False
        )
        assert chunk.embed is None

    def test_chunk_embed_included_when_requested(
        self, parse_response: ParseResponse
    ) -> None:
        """Test that embed is populated when include_embed=True."""
        assert isinstance(parse_response.result, ResultFullResult)
        original_chunk = parse_response.result.chunks[0]

        # With include_embed=True, embed should be populated
        chunk = Sema4aiParseResponseChunk.from_chunk(original_chunk, include_embed=True)
        assert chunk.embed is not None
        assert isinstance(chunk.embed, str)


class TestSema4aiParseResponse:
    """Tests for Sema4aiParseResponse model."""

    def test_from_result_conversion_defaults(
        self, parse_response: ParseResponse
    ) -> None:
        """Test converting a ParseResponse with default parameters (exclude embed and blocks)."""
        # Convert using the from_result method with defaults
        response = Sema4aiParseResponse.from_result(parse_response)

        # Verify the conversion
        assert isinstance(response, Sema4aiParseResponse)
        assert response.job_id == "3808c7d1-8189-4659-b58a-0d36abf6f774"
        assert len(response.chunks) == 1

        # Verify defaults: embed and blocks should be None
        chunk = response.chunks[0]
        assert chunk.embed is None
        assert chunk.blocks is None

    def test_from_result_conversion_with_embed(
        self, parse_response: ParseResponse
    ) -> None:
        """Test converting a ParseResponse with include_embed=True."""
        response = Sema4aiParseResponse.from_result(parse_response, include_embed=True)

        # Verify the conversion
        assert isinstance(response, Sema4aiParseResponse)
        assert response.job_id == "3808c7d1-8189-4659-b58a-0d36abf6f774"
        assert len(response.chunks) == 1

        # Verify embed is included but blocks are not
        chunk = response.chunks[0]
        assert chunk.embed is not None
        assert chunk.blocks is None

    def test_from_result_conversion_with_blocks(
        self, parse_response: ParseResponse
    ) -> None:
        """Test converting a ParseResponse with include_blocks=True."""
        response = Sema4aiParseResponse.from_result(parse_response, include_blocks=True)

        # Verify the conversion
        assert isinstance(response, Sema4aiParseResponse)
        assert response.job_id == "3808c7d1-8189-4659-b58a-0d36abf6f774"
        assert len(response.chunks) == 1

        # Verify blocks are included but embed is not
        chunk = response.chunks[0]
        assert chunk.embed is None
        assert chunk.blocks is not None
        assert len(chunk.blocks) == 7

    def test_from_result_conversion_with_all_fields(
        self, parse_response: ParseResponse
    ) -> None:
        """Test converting a ParseResponse with both include_embed=True and include_blocks=True."""
        response = Sema4aiParseResponse.from_result(
            parse_response, include_embed=True, include_blocks=True
        )

        # Verify the conversion
        assert isinstance(response, Sema4aiParseResponse)
        assert response.job_id == "3808c7d1-8189-4659-b58a-0d36abf6f774"
        assert len(response.chunks) == 1

        # Verify both embed and blocks are included
        chunk = response.chunks[0]
        assert chunk.embed is not None
        assert chunk.blocks is not None
        assert len(chunk.blocks) == 7

    def test_response_only_includes_expected_fields(
        self, parse_response: ParseResponse
    ) -> None:
        """Test that the response only includes job_id and chunks fields."""
        response = Sema4aiParseResponse.from_result(parse_response)

        # Verify only expected fields are present
        response_dict = response.model_dump()
        assert set(response_dict.keys()) == {"job_id", "chunks"}

        # Verify fields that should be excluded are not present
        assert "duration" not in response_dict
        assert "pdf_url" not in response_dict
        assert "studio_link" not in response_dict
        assert "usage" not in response_dict
        assert "result" not in response_dict

    def test_response_chunks_are_converted_properly(
        self, parse_response: ParseResponse
    ) -> None:
        """Test that all chunks in the response are properly converted."""
        response = Sema4aiParseResponse.from_result(
            parse_response, include_embed=True, include_blocks=True
        )

        # Verify all chunks are Sema4aiParseResponseChunk instances
        assert all(
            isinstance(chunk, Sema4aiParseResponseChunk) for chunk in response.chunks
        )

        # Verify each chunk has the correct structure
        for chunk in response.chunks:
            chunk_dict = chunk.model_dump()
            assert set(chunk_dict.keys()) == {"content", "embed", "blocks"}

            # Verify blocks within chunks
            assert chunk_dict["blocks"] is not None
            assert all(
                set(block.keys()) == {"type", "content"}
                for block in chunk_dict["blocks"]
            )

    def test_convert(self, parse_response: ParseResponse) -> None:
        """Test the complete conversion from ParseResponse to Sema4aiParseResponse."""
        response = Sema4aiParseResponse.from_result(
            parse_response, include_embed=True, include_blocks=True
        )

        # Verify job_id
        assert response.job_id == "3808c7d1-8189-4659-b58a-0d36abf6f774"

        # Verify chunks
        assert len(response.chunks) == 1
        chunk = response.chunks[0]
        assert chunk.content.startswith("SkiGear Co.")

        # Verify embed
        assert chunk.embed is not None
        assert chunk.embed.startswith("SkiGear Co.")

        # Verify blocks
        assert chunk.blocks is not None
        assert len(chunk.blocks) == 7
        assert chunk.blocks[0].type == "Text"
        assert chunk.blocks[1].type == "Title"
        assert chunk.blocks[2].type == "Key Value"

        # Verify specific content
        assert "EQUIPMENT INSPECTION" in chunk.blocks[1].content
        assert "INSPECTION SUMMARY" in chunk.blocks[3].content

    def test_model_can_be_serialized_to_json(
        self, parse_response: ParseResponse
    ) -> None:
        """Test that the model can be serialized to JSON."""
        response = Sema4aiParseResponse.from_result(
            parse_response, include_embed=True, include_blocks=True
        )

        # Convert to dict and then to JSON
        json_str = response.model_dump_json()

        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["job_id"] == "3808c7d1-8189-4659-b58a-0d36abf6f774"
        assert len(parsed["chunks"]) == 1
        assert parsed["chunks"][0]["embed"] is not None
        assert parsed["chunks"][0]["blocks"] is not None

    def test_model_can_be_deserialized_from_dict(
        self, parse_response: ParseResponse
    ) -> None:
        """Test that the model can be created from a dictionary."""
        response = Sema4aiParseResponse.from_result(
            parse_response, include_embed=True, include_blocks=True
        )
        response_dict = response.model_dump()

        # Recreate from dict
        recreated = Sema4aiParseResponse.model_validate(response_dict)

        # Verify it matches the original
        assert recreated.job_id == response.job_id
        assert len(recreated.chunks) == len(response.chunks)
        assert recreated.model_dump() == response.model_dump()

        # Verify embed and blocks are present
        assert recreated.chunks[0].embed is not None
        assert recreated.chunks[0].blocks is not None


class TestModelFieldDescriptions:
    """Tests to verify that model fields have proper descriptions."""

    def test_sema4ai_parse_response_block_has_descriptions(self) -> None:
        """Test that all fields in Sema4aiParseResponseBlock have descriptions."""
        schema = Sema4aiParseResponseBlock.model_json_schema()

        assert "type" in schema["properties"]
        assert "description" in schema["properties"]["type"]
        assert schema["properties"]["type"]["description"] == "The type of the block."

        assert "content" in schema["properties"]
        assert "description" in schema["properties"]["content"]
        assert (
            schema["properties"]["content"]["description"]
            == "The content of the block."
        )

    def test_sema4ai_parse_response_chunk_has_descriptions(self) -> None:
        """Test that all fields in Sema4aiParseResponseChunk have descriptions."""
        schema = Sema4aiParseResponseChunk.model_json_schema()

        assert "content" in schema["properties"]
        assert "description" in schema["properties"]["content"]

        assert "embed" in schema["properties"]
        assert "description" in schema["properties"]["embed"]

        assert "blocks" in schema["properties"]
        assert "description" in schema["properties"]["blocks"]

    def test_sema4ai_parse_response_has_descriptions(self) -> None:
        """Test that all fields in Sema4aiParseResponse have descriptions."""
        schema = Sema4aiParseResponse.model_json_schema()

        assert "job_id" in schema["properties"]
        assert "description" in schema["properties"]["job_id"]

        assert "chunks" in schema["properties"]
        assert "description" in schema["properties"]["chunks"]
