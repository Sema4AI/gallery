# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

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
