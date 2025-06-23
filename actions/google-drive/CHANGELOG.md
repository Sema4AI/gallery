# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.3.0] - 2025-06-23

### Added

- Action `get_file_by_id` attaches file into the Files

## [1.2.0] - 2025-06-16

### Added

- New `upload_file` action to upload files to Google Drive with support for:
  - File selection via chat interface
  - Optional parent folder specification
  - Optional file sharing with customizable roles
  - Full support for shared drives

### Changed

- Dependency versions updated.
- Improved `get_files_by_query` action:
  - Now supports returning only basic file info, searching all drives, and saving results as CSV
  - Added support for searching by parent folder name in queries (e.g., "'My Folder' in parents")
  - Improved error handling and reporting

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

## [1.0.5] - 2025-01-09

### Changed

- Dependency versions updated

## [1.0.4] - 2024-10-07

### Changed

- Bump core dependencies

## [1.0.3] - 2024-10-04

### Fixed

- Enhanced functionality to allow searching for comments in a file by both name and ID.

## [1.0.2] - 2024-08-08

### Added

- You can now search for files in all shared drives using the `search_all_drives` option in the `get_files_by_query` action.

### Fixed

- Fixed an issue with retrieving file contents from shared drives.

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

- Get the file details based on unique id
- Retrieve files that match a specific criteria (e.g: files created two days ago, files containing a specific word)
- Get the contents of a file
- Share a file with an email address
- Get all comments associated with a file

### Changed

### Fixed

### Removed
