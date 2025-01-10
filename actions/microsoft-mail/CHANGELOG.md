# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

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
