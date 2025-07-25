# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.3.1] - 2025-06-18

- Updated sema4ai-actions version carrying a new version of pydantic

## [1.3.0] - 2025-06-09

### Added

- Add parameter `fetch_attachments` to actions `search_emails` and `get_email_content` to get attachments into the Files.

## [1.2.1] - 2025-04-04

### Changed

- Dependency versions updated

## [1.2.0] - 2025-03-24

### Added

- External endpoint definition added to package.yaml [Read more](https://sema4.ai/docs/team-edition/marketplace/snowflake-admin#managing-external-access)

## [1.1.4] - 2025-03-06

### Changed

- Dependency versions updated

## [1.1.3] - 2025-01-09

### Changed

- Dependency versions updated

## [1.1.2] - 2024-10-08

### Changed

- Updated core dependencies

## [1.1.1] - 2024-07-31

Description changed.

### Added

### Changed

- Improved the description of the package in `package.yaml`

### Fixed

### Removed

## [1.1.0] - 2024-07-09

### Changed

- Can now create an formatted email by sending Markdown as the body. Affected actions: `Create Draft` and `Send Email`

## [1.0.0] - 2024-07-09

First version published, changelog tracking starts.

### Added
- Send email (to, subject, body, cc and bcc fields)
- Search for emails
- Set email content
- Move email (identifying an e-mail and moving it into a folder, including trash (delete))
- Create draft
- Update draft
- List drafts
- Send draft

### Changed

### Fixed

### Removed
