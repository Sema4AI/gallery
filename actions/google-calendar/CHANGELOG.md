# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.1.3] - 2025-08-07

### Changed

- Update sema4ai-actions to `1.4.1` version

## [1.1.2] - 2025-06-18

- Updated sema4ai-actions version carrying a new version of pydantic

## [1.1.1] - 2025-04-04

### Changed

- Dependency versions updated

## [1.1.0] - 2025-03-24

### Added

- External endpoint definition added to package.yaml [Read more](https://sema4.ai/docs/team-edition/marketplace/snowflake-admin#managing-external-access)

## [1.0.6] - 2025-03-06

### Changed

- Dependency versions updated
- Use `Response[T]` as return type to actions

## [1.0.5] - 2025-01-28

### Fixed

- Event creation with attendees now sets `responseStatus` to `needsAction` by default.

## [1.0.4] - 2025-01-09

### Changed

- Dependency versions updated

## [1.0.3] - 2024-10-08

### Changed

- Dependency versions updated

## [1.0.2] - 2024-09-20

### Changed

- Add `needs_action` default value `responseStatus` field on `Attendee` object.

## [1.0.1] - 2024-07-31

Description changed.

### Added

### Changed

- Improved the description of the package in `package.yaml`

### Fixed

### Removed

## [1.0.0] - 2024-07-09

First version published, changelog tracking starts.

### Added

- List the calendars on which the user is subscribed to
- Search events from the user's calendar based on different properties such as summary, location, attendees, etc
- Create a new event
- Update an existing event

### Changed

### Fixed

### Removed
