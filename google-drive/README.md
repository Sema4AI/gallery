# Google Drive

Action Package interacting with Google Drive resources.

Possible actions with this package are:

- get file details based on unique id
- retrieve files that match a specific query (e.g: files created two days ago, files containing a specific word)
- get the contents of a file
- share a file with an email address
- get all comments associated with a file

## Prompts

```Give me the details about file id 1-cbO3a1M9Yf2YO7qDxDhFumD2FM4JOBEU-ogyTTcdY0.```

```
Here's some information about the file with ID 1-cbO3a1M9Yf2YO7qDxDhFumD2FM4JOBEU-ogyTTcdY0:

* Name: Doctest
* Type: Google Docs Document
* Created Time: April 29, 2024, 14:28:38 UTC
* Last Modified Time: May 7, 2024, 11:56:40 UTC
* Size: 3,477 bytes
* Version: 54
* Owner(s):
    * robocorp-service-account@robocorpproject-420009.iam.gserviceaccount.com (Primary Owner)
* Permissions:
    * jondoe.robocorp@gmail.com (Writer)
    * robocorp-service-account@robocorpproject-420009.iam.gserviceaccount.com (Owner)
You can access the document through this link: [View Document](link to document).
```

```Give me all the files that were updated in the past 2 days```

```
Here are the files updated in the past two days:
1. Doctest (Google Docs)
    * View Link
    * Last modified on May 9th, 2024, by robocorp-service-account
2. Testing (Google Sheets)
    * View Link
    * Last modified on May 9th, 2024, by robocorp-service-account
3. Orders (Google Sheets)
    * View Link
    * Last modified on May 9th, 2024, by jondoe.robocorp
```

```List all comments associated with Doctest```

```
Here are the comments on the document Doctest:

1. "misspelled word"
    * Author: John Doe
    * Created: May 7th, 2024
    * Resolved: No
2. "great job!"
    * Author: John Doe
    * Created: May 7th, 2024
    * Resolved: no
```

## Authorization

To access spreadsheets via Google Sheets actions you need to authenticate and authorize your application.

Right now we support Service Account credentials which can be setup following these steps:
1. [Head to Google Developers Console](https://console.cloud.google.com/apis/dashboard) and create a new project (or select the one you already have).
2. Enable API Access for the Project if you haven’t done it yet.
3. Go to "APIs & Services > Credentials" and choose "Create credentials > Service account key".
4. Fill out the form.
5. Click “Create and continue” and then “Done”.
6. Press “Manage service accounts” above Service Accounts.
7. Press on ⋮ near recently created service account and select “Manage keys” and then click on “ADD KEY > Create new key”.
8. Select JSON key type and press “Create”.

When testing actions locally with the action server, create a `devdata/.env` file based on the `devdata/.env.template`, including the newly created JSON key. 
Alternatively, you can provide it as a `google_credentials` form field in Action Server UI.
