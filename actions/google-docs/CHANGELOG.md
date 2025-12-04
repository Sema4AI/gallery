# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [3.0.0] - 2025-09-25

### Added

- **Image embedding**: Support for embedding images from local files, chat files (using `<<filename>>` syntax), and Vega-Lite charts in Google Documents
- **Document download**: Optional download functionality for documents in multiple formats (PDF, DOCX, TXT, HTML, RTF, ODT) with automatic attachment to chat
- **Document assets integration**: Automatic upload and management of files in a dedicated ".sema4ai-document-assets" folder in Google Drive
- **Chart visualization**: Automatic conversion of Vega-Lite markdown blocks to PNG images and embedding in documents
- **File management actions**: `list_sema4_files` and `cleanup_old_sema4_files` actions for managing uploaded files
- **Enhanced document search**: `search_documents` action with fuzzy matching on document names, content search, and metadata search (owners, descriptions)
- **Recent documents listing**: `list_recent_documents` action for finding documents modified within a specified time period

### Changed

- Enhanced `get_document_by_name` and `get_document_by_id` actions with optional `download` and `export_format` parameters
- Updated `create_document` action to support `image_files` parameter for embedding local images
- Document responses now include `document_url` field providing direct access to Google Docs editor
- README documentation expanded with detailed download features and usage examples

### Fixed

- Improved error handling for file uploads and image processing
- Better validation of export formats and file types

## [2.0.0] - 2025-08-13

### Added

- **Document tabs**: First-class support for multi-tab Google Docs (reading and appending to specific tabs).
- **Comments**: View document comments and map them to tabs; optional comment inclusion in document reads.

### Changed

- Document responses include structured tab content when available.
− Default append targets the first tab when a document has tabs and no tab is specified.

### Fixed

- Improved document parsing for tab-enabled Google Documents
- Better handling of tab titles and content extraction

## [1.4.3] - 2025-08-07

### Changed

- Update sema4ai-actions to `1.4.1` version

## [1.4.2] - 2025-06-18

- Updated sema4ai-actions version carrying a new version of pydantic

## [1.4.1] - 2025-04-04

### Changed

- Dependency versions updated

## [1.4.0] - 2025-03-24

### Added

- External endpoint definition added to package.yaml [Read more](https://sema4.ai/docs/team-edition/marketplace/snowflake-admin#managing-external-access)

## [1.3.3] - 2025-03-06

### Changed

- Dependency versions updated

## [1.3.2] - 2025-01-09

### Changed

- Dependency versions updated

## [1.3.1] - 2024-10-07

### Changed

- Update core dependencies


## [1.3.0] - 2024-09-02

### Added

Add two new actions:
- Append To Document By Id
- Append To Document By Name

## [1.2.1] - 2024-07-31

Description changed.

### Added

### Changed

- Improved the description of the package in `package.yaml`

### Fixed

### Removed

## [1.2.0] - 2025-07-11

### Fixed
- Fixed an issue with mapping response fields
- Improve error handling
- Add missing package icon
- Fixed issue in generating tables
- Fixed issue with generating the styles when reading a document

## [1.1.0] - 2025-07-10

Added to possibility to create a document from Markdown

### Added
- Create Document


## [1.0.0] - 2024-06-25

First version published, changelog tracking starts.

### Added
- Get a document by name
- Get a document by id

### Changed

### Fixed

### Removed
