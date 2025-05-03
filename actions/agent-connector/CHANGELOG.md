# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [4.0.0] - 2025-05-03

**Breaking changes as this aciont package is modified to use the public Agent API.**

### Changed

- When ran locally with SDK or Studio, check the API port from the PID file
- When ran in Agent Compute, get the end point from environment variable
- Add secret for API key to be used in cloud
- Updated to use the public Agent API - and updated terminology and action names to match the public API
- Dependency versions updated
- Updated icon

## [3.1.0] - 2025-04-15

### Changed

- Use `sema4ai-http-helper` to make HTTP requests which now supports certificates and proxies

## [3.0.1] - 2025-04-04

### Changed

- Dependency versions updated

## [3.0.0] - 2025-03-28

### Changed

> Potential breaking change:
> Updated actions return typing to use `Response` from sema4ai-actions
> The content is the same but just has a pydantic type on it.
> Should not affect Agents using this, but is a change worth noting.

- Support `SEMA4AI_AGENT_SERVER_API_URL` for giving the Agent Server url
  - Expected format: `https://localhost:<port>/api/v1`
  - If not given looks for Agent Server in localhost ports 8990 and 8000
- General cleanup and updates.

## [2.0.2] - 2025-03-06

### Changed

- Dependency versions updated

## [2.0.1] - 2025-01-09

- Update dependencies

## [2.0.0] - 2024-10-09

- Support new version of Agent API

## [1.0.1] - 2024-10-09

- Update dependencies

## [1.0.0] - 2024-07-25

First version published, changelog tracking starts.

### Added

### Changed

### Fixed

### Removed
