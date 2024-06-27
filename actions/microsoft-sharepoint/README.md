# Microsoft Sharepoint

Action package for interaction with Microsoft Sharepoint resources.

Currently capably of downloading a file, uploading a file, searching files, listing all sites
that user knows, getting lists of a site and creating a list for a site.

## Prompts

## Authorization

In order to use the action package you need to go into https://portal.azure.com and register new Azure Entra ID (formerly Azure AD) application.

Grant the application necessary scopes to use actions.

    - Files.Read
    - Files.Read.All
    - Files.ReadWrite
    - Sites.Read.All
    - Sites.ReadWrite.All

## Caveats

Lists are created by using generic "genericList" template, which means that they will contain "title" column by default.
