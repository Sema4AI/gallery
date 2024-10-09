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

```
List my .png files
```

> I found several .png files in your OneDrive:
>
> 1. actions.png
>    Created: 2024-10-03
>    Size: 19.8 KB
>    Download
>
> 2. veryslow.png
>    Created: 2024-10-02
>    Size: 16.2 KB
>    Download

```
List my folders
```

> Here are your folders:
>
> 1. Apps
> 2. Attachments
> 3. Documents
>    -- Office Scripts
> 4. images
> 5. newfolder
>    -- newfolder/newfolder
>
> You can click on the folder names to open them.

## Authorization

This package uses OAuth for user authenticaion. In Sema4.ai Studio you can either use the Sema4.ai provided public OAuth app credentials, or create your own client. In Control Room, you are expected to create the private client regardless.

### Creating a Microsoft Entra Enterprise app for authentication

In order to use the action package you need to go into https://portal.azure.com and register new Azure Entra ID (formerly Azure AD) application. Follow the detailed instructions [here](https://sema4.ai/docs/actions/auth/microsoft).

Scopes in use:

    - Files.Read
    - Files.Read.All
    - Files.ReadWrite
