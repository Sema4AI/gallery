# Microsoft Sharepoint

Action package for interaction with Microsoft Sharepoint resources.

Currently capably of downloading a file, uploading a file, searching files, listing all sites
that user knows, getting lists of a site and creating a list for a site.

## Prompt Examples

```
Get a file related to studio from Community site
```

> I found a file related to "studio" in the Community site:
>
> File Name: Sema4.ai Studio (sneak peek) (1).pdf
> Location: Sema4.ai
> Created By: Tommi Holmgren
> Created Date: 2023-11-15
> Last Modified Date: 2023-11-15
> Would you like to download this file?

```
Uploaded /Users/tommi/.robocorp/sema4ai-desktop/uploads/5ddd5f53-05c4-4333-be5d-4b3b276a7dfa/molkky-game-rules.pdf.

upload this file to alerts-dev-tommi
```

> The file was uploaded successfully. You can find the file at the following location:
>
> File Name: molkky-game-rules.pdf
> Location: Shared documents

## Authorization

In order to use the action package you need to go into https://portal.azure.com and register new Azure Entra ID (formerly Azure AD) application. Follow the detailed instructions [here](https://sema4.ai/docs/actions/auth/microsoft).

Scopes in use:

    - Files.Read
    - Files.Read.All
    - Files.ReadWrite
    - Sites.Read.All
    - Sites.ReadWrite.All

## Caveats

Lists are created by using generic "genericList" template, which means that they will contain "title" column by default.
