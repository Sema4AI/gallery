# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [4.0.5] - 2025-07-20

### Fixed

- Force sheet dimension calculation

### Changed

- Dependency versions updated

## [4.0.4] - 2025-06-18

- Updated sema4ai-actions version carrying a new version of pydantic

## [4.0.3] - 2025-04-04

### Changed

- Dependency versions updated

## [4.0.2] - 2025-03-06

### Changed

- Dependency versions updated
- Use `Response[T]` as return type to actions

## [4.0.1] - 2025-02-17

### Fixed

- The `create_workbook` needs to create temporary file for attaching that as a chat file

## [4.0.0] - 2025-02-17

### Changed

- Files are handled via Sema4.ai File API to access LLM chat files. This change prevents use
  of this action package version in the Sema4.ai Studio v1.1.8.
- Dependency versions updated

### Added

- Action `excel_download_file` to download chat file to local filesystem.

## [3.1.2] - 2025-01-14

### Fixed

- The `get_workbook_schema` fail if workbook "creator" or "last modified" user is missing

## [3.1.1] - 2025-01-09

### Changed

- Dependency versions updated

## [3.1.0] - 2024-12-12

### Added

- Add `find_cross_reference` action which will seek for cell(s) that cross given headers vertically and horizontally

### Fixed

- Modify cell update to keep any cell formatting and just modify the value. The parameter `overwrite=True` for action `update_sheet_rows` can be used to overwrite the cell formula.

### Changed

- The `get_workbook_schema` no longer gets the first row with values. Instead the action will get the list of all sheets within the workbook listing their names and data ranges. The returned information contains the workbook's creation time and creator, and last modified time, and who modified the workbook.

## [3.0.1] - 2024-10-08

### Changed

- Dependency versions updated

## [3.0.0] - 2024-08-14

### Added

- Added `update_sheet_rows` function to update individual cells or a range of cells, supporting both horizontal and vertical data insertion

### Changed

- Removed `headers` attribute from the `Table` model
- Removed `has_header` parameter from `get_cell` and `get_sheet_content` function to eliminate LLM confusion

### Removed

- Removed the `set_cell` function in favor of the more flexible `update_sheet_rows` function.

## [2.0.1] - 2024-07-31

Description changed.

### Added

### Changed

- Improved the description of the package in `package.yaml`

### Fixed

### Removed

## [2.0.0] - 2024-07-10

### Changed

- The `Get Table` action was renamed to `Get Sheet Content`

## [1.0.0] - 2024-07-04

First version published, changelog tracking starts.

### Added

- Crate a new workbook (Excel Document)
- Add a new worksheet to an existing workbook
- Add rows to an existing worksheet
- Set the value of a specific cell within a worksheet
- Get the value of a specific cell within a worksheet
- Get table. Retrieves the whole content of an already existing worksheet
- Get workbook schema
- Delete a worksheet from an existing workbook
- Delete workbook

### Changed

### Fixed

### Removed
