# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.10] - 2025-10-30

- Updated dependencies
- `sema4ai-data` v1.2.0 moved a lot of the Snowflake connection handling to the library side, simplifying the action codes.

## [1.0.8] - 2025-08-07

### Changed

- Update sema4ai-actions to `1.4.1` version

## [1.0.7] - 2025-06-18

- Updated sema4ai-actions version carrying a new version of pydantic

## [1.0.6] - 2025-06-05

### Changed

- Fixed handling of secrets in cortex search action.
- Further improvements to docstring to instruct LLM on correct tool usage.

## [1.0.5] - 2025-06-04

### Changed
- Added pydantic type for cortex_search request arg.
- Updated snowflake=1.5.1
- Added exclusion rules

## [1.0.4] - 2025-05-22

### Changed

- Update `sema4ai-data` to `1.0.5`

## [1.0.3] - 2025-04-29

### Changed

- Updated the search query docstrings so that agent will be better able to use the filter parameter.
- Updated the default limit to 10 to match the Snowflake Cortex Search API default.
- Dependency versions updated


## [1.0.2] - 2025-04-04

### Changed

- Dependency versions updated

## [1.0.1] - 2025-04-02

- Fixed the casing of the warehouse, database, schema, and service parameters.

## [1.0.0] - 2025-03-24

- This package is splitted from the Snowflake Cortex package and only contains actions to request Cortex Serach specification and make searches.
