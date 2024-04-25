# Authentication

To access spreadsheets via Google Sheets actions you need to authenticate and authorize your application.

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

### create_spreadsheet
Create a new SpreadSheet with the given name.

### get_sheet_content
Get the worksheet's content paginated with default limit set to 100 rows starting from the first one. The parameters `limit` and `from_row` are configurable.

### get_spreadsheet_schema
Get an insight on how each worksheet within the spreadsheet is organised.

### add_sheet_rows
Adds new rows to the specified worksheet. The input is a list of rows where each row is a list of columns.

### update_sheet_rows
Update a cell or a range of cells in a worksheet using A1 or R1:C1 notation.
