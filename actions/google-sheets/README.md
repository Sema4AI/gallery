# Google Sheets

Action Package interacting with Google Sheets resources.

The package is able to create, read and add / update rows in a spreadsheet. You can also retrieve a schema of a spreadsheet to understand how it is structured.

## Prompts

```
Create a new spreadsheet called Testing.
```

> I've created a new spreadsheet named "Testing." You can access it [here](link to file).

```
Add the following rows to the newly created document:
Order, Item, Price
1, Macbook, 2000
2, iPad, 1000
3, iPhone, 1000
```

> The rows have been successfully added to the "Testing" spreadsheet. You can view the updated data [here](link to file).

```
Create a new worksheet called "Finance" in the "Testing" file and add the following rows to it:
Year, Quarter, Revenue
2023, 1, 50000
2023, 2, 200000
2023, 3, 160000
2023, 4, 350000
2024, 1, 250000
```

> I've created a new worksheet named "Finance" in the "Testing" spreadsheet and added your data. You can view it using this link: [Finance Worksheet](link to worksheet).

```
Give me the contents of "Testing" file
```

> The "Testing" file contains the following sheets and data:
>
> 1. Sheet1:
>    * Order, Item, Price
>    * 1, Macbook, 2000
>    * 2, iPad, 1000
>    * 3, iPhone, 1000
> 2. Finance:
>    * Year, Quarter, Revenue
>    * 2023, 1, 50000
>    * 2023, 2, 200000
>    * 2023, 3, 160000
>    * 2023, 4, 350000
>    * 2024, 1, 250000

## Authorization

This action package uses Google OAuth2 flow to authenticate user.

Scopes in use:

    - https://www.googleapis.com/auth/spreadsheets
    - https://www.googleapis.com/auth/drive
