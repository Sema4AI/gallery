# Sema4.ai Document Intelligence

This action package provides comprehensive document processing and intelligence capabilities for extracting, transforming, and querying structured data from documents. It includes 35+ actions and queries for managing data models, document layouts, extraction schemas, and intelligent document processing workflows.

## Overview

The Document Intelligence package enables:
- **Document Processing**: Extract structured data from PDFs and other documents
- **Schema Management**: Create and manage data models and extraction schemas
- **Layout Detection**: Automatically detect and classify document layouts
- **Data Transformation**: Transform extracted data using translation schemas
- **Intelligent Querying**: Execute natural language queries against document data
- **Validation**: Validate extracted data quality and accuracy
- **Database Integration**: Store and query document data using SQL


## Actions Reference

### Data Model Management

|| Action/Query | Description |
||--------------|-------------|
|| `generate_data_model_from_file` | Generate data model schema from document files |
|| `describe_data_model` | Get details of a specific data model |
|| `create_data_model_from_schema` | Create new data model from JSON schema |
|| `update_data_model` | Update existing data model |
|| `list_data_models` | List all available data models |
|| `choose_data_model` | Auto-select best data model for document |
|| `set_data_model_prompt` | Set system prompt for data model |
|| `set_data_model_summary` | Set summary for data model matching |
|| `create_business_views` | Create SQL views for data model |
|| `delete_data_model_after_explicit_confirmation` | Delete data model (requires confirmation) |

### Document Management

|| Action/Query | Description |
||--------------|-------------|
|| `extract_document` | Extract structured data from documents using custom schemas |
|| `translate_extracted_document` | Transform extracted content using translation rules |
|| `ingest` | Process and store documents with layout detection |
|| `list_documents` | List all documents for a data model |
|| `describe_document` | Get document details and metadata |
|| `query_document` | Retrieve document in data model format |
|| `delete_document` | Remove document from database |
|| `find_documents_by_layout` | Find documents using specific layout |
|| `extract_and_transform_content` | Extract and transform document content |

### Layout Management

|| Action/Query | Description |
||--------------|-------------|
|| `generate_layout` | Generate document layout from files |
|| `generate_translation_schema` | Create translation rules between schemas |
|| `describe_layout` | Get layout schema details |
|| `generate_layout_name` | Generate layout name for document |
|| `create_layout_from_schema` | Create layout from JSON schema |
|| `update_layout_from_schema` | Update existing layout schema |
|| `delete_layout` | Remove layout from database |
|| `list_layouts` | List all available layouts |
|| `list_layouts_by_model` | List layouts for specific data model |
|| `choose_document_layout` | Auto-select best layout for document |
|| `set_document_layout_summary` | Set layout summary for matching |
|| `set_translation_schema` | Set translation rules for layout |
|| `update_layout_extraction_config` | Update layout extraction configuration |
|| `set_document_layout_prompt` | Set system prompt for layout |

### Querying & Analysis

|| Query | Description |
||-------|-------------|
|| `execute_natural_language_query` | Execute natural language queries against data |
|| `run_sql` | Execute SQL queries directly |

### Validation & Quality

|| Query | Description |
||-------|-------------|
|| `generate_validation_rules` | Create validation rules for data model |
|| `test_validation_rules` | Test validation rules against documents |
|| `store_validation_rules` | Save validation rules to database |
|| `validate_document` | Validate document data quality |

