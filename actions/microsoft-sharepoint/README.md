# Microsoft Sharepoint

Action package for interaction with Microsoft Sharepoint resources.

Currently capable of downloading a file, uploading a file, searching files, listing all sites
that user knows, getting lists of a site, creating a list for a site, and adding, updating, deleting, or retrieving items in a list.

## Prompt Examples

```
List items in Issue tracker list (Communication site) in table format
```

> Here are the items from the "Issue tracker" list in the "Communication site" presented in a table format:
>
> | ID | Title                  | Status      | Created             | Modified            |
> |----|------------------------|-------------|---------------------|---------------------|
> | 23 | Test item              | New         | 2025-05-06 14:14:45 | 2025-05-06 14:14:45 |
> | 24 | Something wrong        | In progress | 2025-05-06 15:18:50 | 2025-05-06 15:59:43 |
> | 25 |                        | New         | 2025-05-06 16:00:25 | 2025-05-06 16:00:25 |
> | 26 | Was there anything wrong? | In progress | 2025-05-06 16:08:22 | 2025-05-06 16:26:12 |

```
Delete list item 25
```

> The item with ID 25 has been successfully deleted from the "Issue tracker" list in the "Communication site." If there's anything else you need, feel free to ask!


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
Uploaded molkky-game-rules.pdf

upload this file to alerts-dev-tommi
```

> The file was uploaded successfully. You can find the file at the following location:
>
> File Name: molkky-game-rules.pdf
> Location: Shared documents

## Authorization

This package uses OAuth for user authenticaion. In Sema4.ai Studio you can either use the Sema4.ai provided public OAuth app credentials, or create your own client. In Control Room, you are expected to create the private client regardless.

### Creating a Microsoft Entra Enterprise app for authentication

In order to use the action package you need to go into https://portal.azure.com and register new Azure Entra ID (formerly Azure AD) application. Follow the detailed instructions [here](https://sema4.ai/docs/build-agents/prebuilt-actions/authentication/microsoft).

Scopes in use:

    - Files.Read
    - Files.Read.All
    - Files.ReadWrite
    - Sites.Read.All
    - Sites.Manage.All

## Caveats

Lists are created by using generic "genericList" template, which means that they will contain "title" column by default.
