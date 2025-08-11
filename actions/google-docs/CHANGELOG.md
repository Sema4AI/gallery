# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.0.0] - 2025-08-11

### Added

- **Google Docs Tabs Support**: Added comprehensive support for multi-tab Google Documents
  - New action: `list_document_tabs` - List all tabs in a Google Document with their IDs, titles, and positions
  - Enhanced existing actions with tab parameters:
    - `get_document_by_name` - Added `tab_index` and `tab_title` parameters to get content from specific tabs
    - `get_document_by_id` - Added `tab_index` and `tab_title` parameters to get content from specific tabs
    - `append_to_document_by_id` - Added `tab_index` and `tab_title` parameters to append to specific tabs
    - `append_to_document_by_name` - Added `tab_index` and `tab_title` parameters to append to specific tabs
  - New models: `TabInfo` for representing tab metadata
  - Enhanced `DocumentInfo` and `MarkdownDocument` models with tab information (`current_tab`, `tabs`, `tab_contents`)
  - Support for nested child tabs with hierarchical indexing
  - Automatic tab content aggregation when no specific tab is specified

### Changed

- **Breaking Change**: Document retrieval now includes structured tab content when available
- Enhanced error handling for tab-related operations
- Improved validation to prevent conflicts between `tab_index` and `tab_title` parameters
- Updated test data files to demonstrate new tab functionality

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
