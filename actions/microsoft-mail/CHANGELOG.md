# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [2.2.0] - 2026-01-30

### Added

- Added `emails_as_csv` action for exporting email search results as CSV files attached to chat

### Fixed

- Fixed `add_category` to return a descriptive success message instead of the raw API response
- Fixed `remove_category` to return a descriptive success message instead of the raw API response
- Removed debug `print()` statements from `add_category` and attachment handling in `support.py`

## [2.1.1] - 2025-10-30

### Changed

- Enhanced attachment handling to support Chat Files API integration. Actions can now accept files uploaded to chat context by using `chat.get_file_content()` with automatic fallback to local filesystem paths.

## [2.1.0] - 2025-09-04

### Added

- Added `has_attachments` boolean parameter to `list_emails` action for filtering emails with attachments
- Added comprehensive Microsoft Graph API OData query syntax examples in `list_emails` docstring
- Added actions for adding/removing category to/from an email.

### Changed

- Enhanced folder-specific endpoint usage for inbox queries to improve reliability

## [2.0.0] - 2025-09-04

## BREAKING CHANGE

- Attachment saving no longer supports local filesystem. Instead files are saved into Agent Chat Files.

### Added

- Added `get_email_by_subject` action

### Changed

- Modified `save_attachments` parameter in `get_email_by_id` action from string to boolean with default False
- When `save_attachments=True`, attachments are now saved with Files API
- Removed `make_dirs` parameter as it's no longer needed with the new attachment approach
- Updated dependencies

## [1.4.2] - 2025-08-07

### Changed

- Update sema4ai-actions to `1.4.1` version

## [1.4.1] - 2025-06-18

- Updated sema4ai-actions version carrying a new version of pydantic

## [1.4.0] - 2025-04-15

### Changed

- Use `sema4ai-http-helper` to make HTTP requests which now supports certificates and proxies

## [1.3.1] - 2025-04-04

### Changed

- Dependency versions updated

## [1.3.0] - 2025-03-24

### Added

- External endpoint definition added to package.yaml [Read more](https://sema4.ai/docs/team-edition/marketplace/snowflake-admin#managing-external-access)

## [1.2.1] - 2025-03-06

### Changed

- Dependency versions updated

## [1.2.0] - 2025-01-21

### Add

- Add parameters `save_attachments` and `make_dirs` to action `get_email_by_id`.
  The former can be given `downloads` as value and then attachments will be saved
  to user's Downloads folder.

## [1.1.1] - 2025-01-09

### Changed

- Dependency versions updated

## [1.1.0] - 2024-10-18

### Add

- Action `flag_email` added.
- Add parameter `max_emails_to_return` to action `list_emails` to minimize action response size

## [1.0.4] - 2024-10-03

### Changed

- Dependency versions updated

## [1.0.3] - 2024-10-01

- Change `get_email_by_id` to return only `bodyPreview` by default.
  By setting new `show_full_body` parameter to `True` the `body` of email can be
  still retrieved.
- Add special handling for "inbox" folder with `list_emails` actions

## [1.0.2] - 2024-09-26

Fix problems with action scopes. Improvements on error handling.

## [1.0.1] - 2024-09-23

Fix problem where `list_messages` response is missing `id` property.

### Fixed

Action `list_messages` will always return `id` property even if it
is not specifically requested in the action call.

## [1.0.0] - 2024-09-20

First version published, changelog tracking starts.

### Added

- Basic set of actions to handle emails for Outlook account.

### Changed

### Fixed

### Removed
