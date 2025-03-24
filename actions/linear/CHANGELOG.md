# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2025-03-07

### Added

- New `search_projects` action to search Linear projects
- Support for filtering projects by name, team, and initiative
- New models for project filtering and responses (`ProjectFilterOptions`, `Project`, `ProjectList`)
- Input validation for empty string handling in project filters
- Dependency versions updated

## [1.0.2] - 2025-03-06

### Changed

- Dependency versions updated
- Use `Response[T]` as return type to actions

## [1.0.1] - 2025-01-09

### Changed

- Dependency versions updated

### Fixed

- Bug with `create_issue` handling API response
- Bug with `search_issue` ordering

## [1.0.0] - 2024-11-25

First version published, changelog tracking starts.
