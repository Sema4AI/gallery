# Document Insights Action Package

Ad-hoc exploration of documents using Sema4.ai's Agents and Document Intelligence.

For documents, simple and complex:
* Parse: decompose the document into understandable chunks.
* Schema generation: generate meaningful JSONSchema objects which reflect document's shape and meaning.
* Extract: build a JSON object which matches the given schema based on the document.

## Overview

The Document Insights package enables:
- **Document Parsing**: Decompose documents into understandable, structured chunks
- **Schema Generation**: Automatically generate JSONSchema objects that reflect document structure and meaning
- **Data Extraction**: Extract structured JSON data from documents using custom schemas
- **Knowledge Base Integration**: Store parsed documents and query them with natural language
- **Vector Search**: Leverage PGVector for semantic search across document content

## Actions Reference

### Document Processing

|| Action/Query | Description |
||--------------|-------------|
|| `parse` | Parse the given file and return the parsed content with unique job ID |
|| `extract` | Extract structured data from documents using custom JSONSchema |

### Schema Generation

|| Action/Query | Description |
||--------------|-------------|
|| `create_schema` | Generate meaningful JSONSchema objects that reflect document's shape and meaning |

### Knowledge Base

|| Action/Query | Description |
||--------------|-------------|
|| `parse_and_store` | Insert parsed document chunks into the knowledge base for later querying |
|| `query_knowledge_base` | Execute natural language queries against stored document content |
