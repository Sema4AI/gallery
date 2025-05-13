# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.4.0] - 2025-05-08

### Added

- Add sideloading organization data to `TicketsApi`
- Add `Organization` datamodel
- Add check for `Comment`datamodel for user validation
- Add search ticket by only number instruction to `search_tickets`

### Changed

- Change email validation for `User` datamodel to allow `None` email for deleted users

## [1.3.0] - 2025-04-15

### Changed

- Use `sema4ai-http-helper` to make HTTP requests which now supports certificates and proxies

## [1.2.1] - 2025-04-04

### Changed

- Dependency versions updated

## [1.2.0] - 2025-03-24

### Added

- External endpoint definition added to package.yaml [Read more](https://sema4.ai/docs/team-edition/marketplace/snowflake-admin#managing-external-access)

## [1.1.2] - 2025-03-06

### Changed

- Dependency versions updated

## [1.1.1] - 2025-01-09

### Changed

- Dependency versions updated

## [1.1.0] - 2024-01-03

### Added

- Create a ticket based on the provided attributes
- Delete ticket with ticket id

### Changed

- Dependency versions updated

### Fixed

- Fix type issue in the Ticket
- Fix action returns

## [1.0.1] - 2024-07-31

Description changed.

### Added

### Changed

- Improved the description of the package in `package.yaml`

### Removed

## [1.0.0] - 2024-07-09

First version published, changelog tracking starts.

### Added

- Search for the tickets based on different attributes such as status, description, assignee, etc
- Get the ticket comments
- Assign a ticket to a user or a group
- Update the status of the ticket
- Search for users based on different attributes
- List all available groups

### Changed

### Fixed

### Removed
