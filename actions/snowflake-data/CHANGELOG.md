# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.0.4] - 2025-06-18

- Updated sema4ai-actions version carrying a new version of pydantic

## [2.0.3] - 2025-05-22

### Changed

- Update `sema4ai-data` to `1.0.5`


## [2.0.2] - 2025-04-04

### Changed

- Dependency versions updated

## [2.0.1] - 2025-04-02

### Changed

- Updated Snowflake dependencies to latest versions

### Fixed

- Fixed issue with `snowflake_execute_query` when arguments are passed in lowercase

## [2.0.0] - 2025-03-24

**This version is not backwards compatible with previous versions.**

### Removed

- Split Cortex Search and Analyst actions into separate packages.

## [1.1.2] - 2025-03-13

### Changed

- Dependency versions updated

## [1.1.1] - 2025-02-28

### Fixed
- Private key password for unencrypted file fixed

## [1.1.0] - 2025-02-27

### Changed

- Add `cortex_llm_complete`, `cortex_agent_chat` cortex actions
- Add `snowflake_get_warehouses`, `snowflake_get_databases`, `snowflake_get_schemas`, `snowflake_get_tables`, `snowflake_get_columns` actions

#### Fixed

- NaT values in pandas dataframes are now converted to `None` for the execute query result

## [1.0.1] - 2025-02-25

### Changed

- Changed Cortex Search and Analyst actions to use Secrets for parameters, instead of relying them to be passed as strings by an agent based on Runbook instructions.
- Updated Snowflake dependencies to latest versions

### Fixed

- Changed the input parameter `columns` for the `cortex_search` action to be always required.

## [1.0.0] - 2025-02-20

- First version published, changelog tracking starts.

### Added

- Actions to search and query Snowflake Cortex Search
- Get Cortex Search specifications
- Send message to Snowflake Cortex Analyst and receive SQL
- Execute Snowflake query
