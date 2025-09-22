# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.0.2] - 2025-09-19

### Changed

- **IMPROVED**: Updated connection management to work both locally and in SPCS
- The project now assumes an authenticated Snowflake connection is established externally
- Both `get_tables_info()` and `execute_select_query()` now require warehouse, database, and schema parameters
- Updated dependencies to the latest versions
- Better error handling for Snowflake-specific error messages
- Added `who_am_I()` action to return the current user and their role

## [0.0.1] - 2025-08-03

### Changed

- First version of the Snowflake Data Access Pack
