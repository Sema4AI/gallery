# Snowflake Document AI

This action package enables you to upload PDF documents to Snowflake and extract their content using [Snowflake Document AI](https://docs.snowflake.com/en/user-guide/snowflake-cortex/document-ai/overview). It uses one-shot parsing with no training required, making it easy to extract structured data from PDFs.

## What it does

This action package provides two main capabilities:

1. **List Stage Files**: List all files currently stored in a Snowflake stage
2. **Parse Document**: Upload PDF files and extract their content using AI-powered parsing

The parsing uses Snowflake's `AI_PARSE_DOCUMENT` function which can extract text, tables, and other structured content from PDFs in layout-aware mode.

## Prerequisites

Before using this action, you need:

1. **Snowflake Account**: An active Snowflake account with Document AI enabled
2. **Database, Schema, and Stage**: A Snowflake stage configured to store your PDF files
3. **Authentication**: One of the following authentication methods:
   - Username and password
   - Key pair authentication
   - OAuth token
   - Running in Snowflake Container Services (SPCS)

## Actions

### 1. List Stage Files

Lists the most recently modified files in a specific Snowflake stage.

**Parameters:**
- `database_name` (Secret): The name of the database containing the stage
- `schema_name` (Secret): The name of the schema containing the stage
- `stage_name` (Secret): The name of the stage
- `limit` (int, optional): Maximum number of files to return (default: 10)

**Returns:** A list of the most recently modified files with their details (name, size, last modified, etc.), sorted by modification time in descending order

### 2. Parse Document

Uploads a PDF file from chat and parses its content using Snowflake Document AI.

**Parameters:**
- `filename` (string): The name of the file to upload from chat
- `database_name` (Secret): The database containing the stage
- `schema_name` (Secret): The schema containing the stage
- `stage_name` (Secret): The name of the stage
- `stage_path` (string, optional): Subfolder path within the stage

**Returns:** 
- Upload details (file path, upload time, query ID)
- Parsed document content in JSON format

**Response Structure:**
```json
{
  "upload": {
    "status": "success",
    "original_file": "invoice.pdf",
    "file": "invoice_20240108_143522.pdf",
    "stage": "MY_DATABASE.MY_SCHEMA.DOCUMENT_STAGE",
    "stage_path": "invoices/2024/invoice_20240108_143522.pdf",
    "fully_qualified_path": "@MY_DATABASE.MY_SCHEMA.DOCUMENT_STAGE/invoices/2024/invoice_20240108_143522.pdf",
    "upload_time": "2024-01-08 14:35:22.123456",
    "query_id": "01b2c3d4-..."
  },
  "parsed": {
    "MONTHLY_STATS": "... parsed content in JSON format ..."
  }
}
```

## Features

- **One-Shot Parsing**: No training or model setup required
- **Layout-Aware**: Preserves document structure and formatting
- **Page Splitting**: Processes multi-page documents with page-level granularity
- **Unique Naming**: Automatically adds timestamps to prevent file conflicts
- **Comprehensive Results**: Returns both upload details and parsed content

## Use Cases

- Extract data from invoices, receipts, and financial documents
- Parse contracts and legal documents
- Process forms and applications
- Extract tables and structured data from reports
- Convert PDF documents to structured JSON for further processing

## Limitations

- Only supports PDF files
- Requires Snowflake Document AI to be enabled in your account
- Processing time depends on document complexity and size - timeouts are possible with larger documents