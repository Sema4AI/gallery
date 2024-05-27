# Google Drive

Action Package interacting with Google Drive resources.

Possible actions with this package are:

- get file details based on unique id
- retrieve files that match a specific query (e.g: files created two days ago, files containing a specific word)
- get the contents of a file
- share a file with an email address
- get all comments associated with a file

## Prompts

```
Give me the details about the file named "Doctest".
```

> Here are the details about the file named "Doctest":
>
> * Name: Doctest
> * File ID: 1-cbO3a1M9Yf2YO7qDxDhFumD2FM4JOBEU-ogyTTcdY0
> * Type: Google Docs Document
> * Created Time: April 29, 2024, 14:28:38 UTC
> * Last Modified Time: May 7, 2024, 11:56:40 UTC
> * Size: 3,477 bytes
> * Version: 54
> * Owner(s):
>   * robocorp-service-account@robocorpproject-420009.iam.gserviceaccount.com (Primary Owner)
> * Permissions:
>   * jondoe.robocorp@gmail.com (Writer)
>   * robocorp-service-account@robocorpproject-420009.iam.gserviceaccount.com (Owner)
> 
> You can access the document through this link: [View Document](link to document).

```
Give me all the files that were updated in the past 2 days
```

> Here are the files updated in the past two days:
> 1. Doctest (Google Docs)
>    * View Link
>    * Last modified on May 9th, 2024, by robocorp-service-account
> 2. Testing (Google Sheets)
>    * View Link
>    * Last modified on May 9th, 2024, by robocorp-service-account
> 3. Orders (Google Sheets)
>   * View Link
>   * Last modified on May 9th, 2024, by jondoe.robocorp


```
List all comments associated with Doctest
```

> Here are the comments on the document Doctest:
>
> 1. "misspelled word"
>    * Author: John Doe
>    * Created: May 7th, 2024
>    * Resolved: No
> 2. "great job!"
>    * Author: John Doe
>    * Created: May 7th, 2024
>    * Resolved: no

## Authorization

This action package uses Google OAuth2 flow to authenticate user.

Scopes in use:

    - https://www.googleapis.com/auth/drive.readonly
    - https://www.googleapis.com/auth/drive.metadata.readonly
    - https://www.googleapis.com/auth/drive.file
