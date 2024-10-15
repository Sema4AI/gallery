# Microsoft 365 Excel

Action Package interacting Microsoft 365 Excel files

Possible actions with this package are:

- Create Workbook
- Add Worksheet to Workbook
- Get Workbook By Name
- Add Sheet
- Get Worksheet
- Update Range

## Prompts

```
Create a workbook called Demo
```

> The workbook "Demo" has been created successfully. You can access it using the following link:
> [Open Workbook](www.example.com).
> Is there anything else you would like to do with this workbook?

```
Get the workbook Demo
```

> I found the workbook "Demo.xlsx". It contains one worksheet named "Sheet1".
> You can view the workbook [here](www.example.com).
> What would you like to do next?

```
Add a new sheet to it called Test AI
```

> The new sheet "Test AI" has been successfully added to the workbook "Demo.xlsx".
> Is there anything else you would like to do?

```
Generate a random 5 by 10 table and insert it at BB34
```

> It looks like I used an incorrect operation type.
> The valid operations are "replace", "insert_shift_right", and "insert_shift_down".

```
Insert shift down
```

> The random 5 by 10 table has been successfully inserted at cell BB34 in the "Test AI" sheet, with the existing data shifted down.

```
Get the contest of Test AI
```

> The "Test AI" worksheet contains the following data:
> | CD55 | CE55 | CF55 | CG55 | CH55 |
> |------|------|------|------|------|
> | A1 | B1 | C1 | D1 | E1 |
> | A2 | B2 | C2 | D2 | E2 |
> | A3 | B3 | C3 | D3 | E3 |
> | A4 | B4 | C4 | D4 | E4 |
> | A5 | B5 | C5 | D5 | E5 |
> | A6 | B6 | C6 | D6 | E6 |
> | A7 | B7 | C7 | D7 | E7 |
> | A8 | B8 | C8 | D8 | E8 |
> | A9 | B9 | C9 | D9 | E9 |
> | A10 | B10 | C10 | D10 | E10 |

## Authorization

This package uses OAuth for user authenticaion. In Sema4.ai Studio you can either use the Sema4.ai provided public OAuth app credentials, or create your own client. In Control Room, you are expected to create the private client regardless.

### Creating a Microsoft Entra Enterprise app for authentication

In order to use the action package you need to go into https://portal.azure.com and register new Azure Entra ID (formerly Azure AD) application. Follow the detailed instructions [here](https://sema4.ai/docs/actions/auth/microsoft).

Scopes in use:

    - Files.Read
    - Files.ReadWrite
