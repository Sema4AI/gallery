# Microsoft OneDrive

Action package for interaction with Microsoft OneDrive.

Currently supporting:

- Create a new folder in OneDrive
- Delete a file or folder from OneDrive
- Rename a file or folder in OneDrive
- Upload a file to OneDrive
- Retrieve detailed information about a file or folder in OneDrive using its ID
- Recursively list all folders in OneDrive starting from a specified root folder
- List items in a specified OneDrive folder
- List items shared with me in OneDrive
- Search for items in OneDrive by name or content
- Download file or files from OneDrive to local storage:

## Prompt Examples

## Authorization

In order to use the action package you need to go into https://portal.azure.com and register new Azure Entra ID (formerly Azure AD) application. Follow the detailed instructions [here](https://sema4.ai/docs/actions/auth/microsoft).

Scopes in use:

    - Files.ReadWrite
    - Files.Read
    - Files.Read.All
