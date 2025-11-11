## Sema.4ai Action Package

This is a python project, but a little different. You should use the `action-server` command line tool (which should be installed
on the user's computer and in the $PATH) to run tests, linting, formatting, and typechecks. These are generally provided
as `dev-tasks` in that `package.yaml` file.

Example: to run a `test` dev-task, you would run the command `action-server devenv -v task test`

## General tips

- Prefer python modules which are small and maintainable.
- Following modern Python with typed arguments and return values.
- Leverage third-party libraries like Pydantic when adding code, following standard conventions and best-practices.
- Write a new unit tests when you fix a bug or add new functionality.
- ALWAYS prefer to update existing tests rather than add net-new code.
- NEVER write end-to-end tests. It is better to write no test than to write a massive "do everything" test.
- Focus first on accomplishing the task on hand and make sure tests are functional. Only when the task is
  provably done, considering linting and formatting.
