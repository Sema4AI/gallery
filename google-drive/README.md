# Authentication

To access files information via Google Drive actions you need to authenticate and authorize your application.

Right now we support Service Account credentials which can be setup following these steps:
1. [Head to Google Developers Console](https://console.cloud.google.com/apis/dashboard) and create a new project (or select the one you already have).
2. Enable API Access for the Project if you haven’t done it yet.
3. Go to "APIs & Services > Credentials" and choose "Create credentials > Service account key".
4. Fill out the form
5. Click “Create and continue” and then “Done”.
6. Press “Manage service accounts” above Service Accounts.
7. Press on ⋮ near recently created service account and select “Manage keys” and then click on “ADD KEY > Create new key”.
8. Select JSON key type and press “Create”.


If you are testing the actions locally with the action-server then update the `devdata/.env.template` file with the 
newly created json key or pass it as `credentials` request parameter.

# Actions

The following actions are contained with this package:

### get_file_by_id
Get a file from Google Drive by id

### get_files_by_query
Get all files from Google Drive that match the given query. 
Check possible queries on Google Drive API documentation: https://developers.google.com/drive/api/guides/search-files.

### get_file_contents
Get the file contents. Currently only Google Docs and Spreadsheets are supported.

### share_document
Share the file with someone. Possible roles that can be given are: reader, writer, commenter, organizer or file organizer.

### list_file_comments
List all the comments associated with a file.