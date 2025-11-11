# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.0.4] - 2025-10-30

### Changed

- Updated dependencies
- `sema4ai-data` v1.2.0 moved a lot of the Snowflake connection handling to the library side, simplifying the action codes.

## [2.0.2] - 2025-10-14

### Changed
- Updated error message to include information about the default role and schema/stage access permissions.

## [2.0.1] - 2025-10-09

### Changed
- Cortex Analyst REST API calls now use host with Snowflake account names with hyphens `-` instead of underscores `_`. This solves some of the reported issues with SSL certificates.

## [2.0.0] - 2025-10-07

**NOTE! This version changes the action parameters/secrets and will require the agents to be redeployed.**

### Changed
- Support for Semantic Views
- **Return results as Table instead of list**
- Return table is limited to 10000 rows by default to prevent memory issues, it can be overridden by the `row_limit` parameter
- Simplified parameter NOT to need database and schema when the semantic model is a view name - this means that all queries should be fully qualified now
- Added error handling for warehouse, database and schema name misspelling and query syntax error
- Updated dependencies
- Changed requests to have TLS verification enabled

## [1.0.5] - 2025-08-07

### Changed

- Update sema4ai-actions to `1.4.1` version

## [1.0.4] - 2025-06-18

- Updated sema4ai-actions version carrying a new version of pydantic

## [1.0.3] - 2025-05-20

### Changed

- Fixed the issue when the semantic model file path is copied from Snowsight and contains quotes and possibly whitespaces. These are now handled correctly.
- Dependency versions updated

## [1.0.2] - 2025-04-04

### Changed

- Dependency versions updated

## [1.0.1] - 2025-04-02

- Updated warehouse, database and schema to be used in the query to be uppercase fixing the issue when secrets are lowercase.

## [1.0.0] - 2025-03-23

- This package is splitted from the Snowflake Cortex package and only contains actions to send messages to the Cortex Analyst and execute queries.
