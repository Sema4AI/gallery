# Google Sheets

Action Package interacting with Google Sheets resources.

The package is able to create, read and add / update rows in a spreadsheet. You can also retrieve a schema of a spreadsheet to understand how it is structured.

## Prompts

> Create a new spreadsheet called Testing.

```
I've created a new spreadsheet named "Testing." You can access it [here](link to file).
```

> Add the following rows to the newly created document:
Order, Item, Price
1, Macbook, 2000
2, iPad, 1000
3, iPhone, 1000

```
The rows have been successfully added to the "Testing" spreadsheet. You can view the updated data [here](link to file).
```

> Create a new worksheet called "Finance" in the "Testing" file and add the following rows to it:
Year, Quarter, Revenue
2023, 1, 50000
2023, 2, 200000
2023, 3, 160000
2023, 4, 350000
2024, 1, 250000

```
I've created a new worksheet named "Finance" in the "Testing" spreadsheet and added your data. You can view it using this link: [Finance Worksheet](link to worksheet).
```

> Give me the contents of "Testing" file

```
The "Testing" file contains the following sheets and data:

1. Sheet1:
    * Order, Item, Price
    * 1, Macbook, 2000
    * 2, iPad, 1000
    * 3, iPhone, 1000
2. Finance:
    * Year, Quarter, Revenue
    * 2023, 1, 50000
    * 2023, 2, 200000
    * 2023, 3, 160000
    * 2023, 4, 350000
    * 2024, 1, 250000
```

## Authorization


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


If you are testing the actions locally with the action-server then add the `devdata/.env` file with the 
newly created json key or pass it as `google_credentials` request parameter.
