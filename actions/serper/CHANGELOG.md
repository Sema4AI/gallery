# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.1.2] - 2025-08-07

### Changed

- Update sema4ai-actions to `1.4.1` version

## [1.2.1] - 2025-09-19

### Added

- Exponential backoff retries for Serper `search_google` action on 429 and 5xx responses, honoring `Retry-After` when present

## [1.1.1] - 2025-06-18

- Updated sema4ai-actions version carrying a new version of pydantic

## [1.1.0] - 2025-04-15

### Changed

- Use `sema4ai-http-helper` to make HTTP requests which now supports certificates and proxies

## [1.0.1] - 2025-04-04

### Changed

- Dependency versions updated

## [1.0.0] - 2025-03-24

### Added

- External endpoint definition added to package.yaml [Read more](https://sema4.ai/docs/team-edition/marketplace/snowflake-admin#managing-external-access)

## [0.0.1] - 2025-02-28

First version published, changelog tracking starts.

### Added

- Search Google action

### Changed

### Fixed

### Removed
