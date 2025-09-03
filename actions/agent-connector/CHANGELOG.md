# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

### [4.1.0] - 2025-08-21

### Added

- New `ask_agent()` function - the simplest way to ask an agent a question by name
  - Automatically creates new conversations when needed
  - Supports existing conversation IDs for follow-up messages
  - Returns conversation ID and agent response in a structured format
- New `MessageResponse` model for structured message responses
- New `AgentResult` model for agent lookup results with suggestions
- Centralized agent name resolution logic with intelligent suggestions
- Custom string matching algorithm for finding closest agent names

### Changed

- Enhanced `get_agent_by_name()` function to return suggestions when agent not found
  - Now returns available agent names and closest match suggestions
  - Better error handling with helpful messages
- Replaced `difflib` dependency with custom string matching function
- Improved function ordering with `ask_agent()` as the primary interface
- Updated function documentation to guide users toward `ask_agent()` for common use cases

### Improved

- Better user experience with intelligent agent name suggestions
- Centralized code for agent resolution to eliminate duplication
- More intuitive function naming (`ask_agent` vs `send_message_to_agent_by_name`)
- Enhanced error messages with available agent names and suggestions

### [4.0.5] - 2025-08-07

### Changed

- Update sema4ai-actions to `1.4.1` version

## [4.0.4] - 2025-07-01

- Add backwards compatibility with older Studio versions

## [4.0.3] - 2025-06-18

- Updated sema4ai-actions version carrying a new version of pydantic

## [4.0.2] - 2025-06-11

### Fixed

- Fixed a bug where agent response was not stringified resulting in a type error at run time.

## [4.0.1] - 2025-05-05

### Changed

- Updated to work with Agent Compute 1.2.2 which has a environment variable for the API URL. NOTE: Use previous version of the action if you are using Agent Compute 1.2.1 or earlier.

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
