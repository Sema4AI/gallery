# Change Log
All notable changes to this project will be documented in this file.
 
The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

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
