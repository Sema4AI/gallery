# Actions Bootstrapper

Action Package to bootstrap new action packages.

This action package is used by the Action Writer Agent, which helps users quickly create new actions using publicly available API documentation.

For more details, refer to the following: [Action Writer Agent](https://github.com/Sema4AI/cookbook/tree/main/agents/action-writer)

The Actions Bootstrapper action package provides endpoints for setting up and managing action packages. These include bootstrapping a new action package, updating dependencies, opening the package in VSCode, and retrieving action run logs from the action server.

## Prompts

`Create a new action package named "MyNewAction".`

> _... bootstraps a new action package with the specified name and sets it up in the home directory_

`Update the dependencies for "MyNewAction".`

> _... updates the_ `_package.yaml_` _file with the specified dependencies for the given action package_

`Open "MyNewAction" in VSCode.`

> _... opens the specified action package in VSCode for editing and review_

`Fetch the logs for the latest run from the action server.`

> _... retrieves the logs from the most recent run of an action from the specified action server URL_

## Authorization

Uses publicly available data - no need for API keys.