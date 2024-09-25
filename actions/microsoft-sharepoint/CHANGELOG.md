# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [2.0.0] - 2024-09-25

### Added

- Added "my site" into output of "get_all_sharepoint_sites" action.

### Changed

- Instead of having action to return just a "site_id" it will return
  all site information. Renamed action to "search_for_site".
- Improved error handling for the actions.

## [1.0.1] - 2024-08-08

Code refactors and fixes.

### Fixed

- Improve error messages
- Allow listing lists for "My Lists"

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
