# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.2.1] - 2025-06-18

- Updated sema4ai-actions version carrying a new version of pydantic

## [2.2.0] - 2025-04-15

### Changed

- Use `sema4ai-http-helper` to make HTTP requests which now supports certificates and proxies

## [2.1.1] - 2025-04-04

### Changed

- Dependency versions updated

## [2.1.0] - 2025-03-24

### Added

- External endpoint definition added to package.yaml [Read more](https://sema4.ai/docs/team-edition/marketplace/snowflake-admin#managing-external-access)

## [2.0.2] - 2025-03-06

### Changed

- Dependency versions updated

## [2.0.1] - 2025-02-27

### Fixed

- Fix `create_workbook` action.

## [2.0.0] - 2025-02-26

### Changed

- Dropped `_action` from action names.

### Fixed

- Modified how `operation` parameter is defined for `update_range` action.
  This was problematic for LLM tool calling.

## [1.0.2] - 2025-01-09

### Changed

- Dependency versions updated

## [1.0.1] - 2024-10-03

### Changed

- Dependency versions updated

## [1.0.0] - 2024-09-19

First version published.

### Added

- Create workbook
- Get workbook By name
- Add sheet
- Get worksheet
- Update range
