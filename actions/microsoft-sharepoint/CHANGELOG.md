# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [3.0.1] - 2025-08-07

### Changed

- Update sema4ai-actions to `1.4.1` version

## [3.0.0] - 2025-06-30

### Added

- Support for using chat files in SharePoint file actions:
  - You can now search, download, and upload files using chat file attachments in the SharePoint integration.

### Removed

- Support for local file management

## [2.3.1] - 2025-06-18

- Updated sema4ai-actions version carrying a new version of pydantic

## [2.3.0] - 2025-05-06

### Added

- CRUD actions for Sharepoint list items

## [2.2.0] - 2025-04-15

### Changed

- Use `sema4ai-http-helper` to make HTTP requests which now supports certificates and proxies

## [2.1.1] - 2025-04-04

### Changed

- Dependency versions updated

## [2.1.0] - 2025-03-24

### Added

- External endpoint definition added to package.yaml [Read more](https://sema4.ai/docs/team-edition/marketplace/snowflake-admin#managing-external-access)

## [2.0.2] - 2025-03-06

### Changed

- Dependency versions updated

## [2.0.1] - 2025-01-09

### Changed

- Dependency versions updated

## [2.0.0] - 2024-10-07

### Added

- Added "my site" into output of "get_all_sharepoint_sites" action.

### Changed

- Dependency versions updated
- Improved the description of the package in `package.yaml`
- Instead of having action to return just a "site_id" it will return
  all site information. Renamed action to "search_for_site".
- Improved error handling for the actions.

## [1.0.1] - 2024-07-31

- Description changed.

### Added

### Changed

- Improved the description of the package in `package.yaml`

### Fixed

### Removed

## [1.0.0] - 2024-07-04

First version published, changelog tracking starts.

### Added

- Microsoft Entra ID (Oauth2) authentication for actions
- Download a file
- Upload a file
- Search files
- List all sites
- Get lists for a site
- Create a list for a site

### Changed

### Fixed

### Removed
