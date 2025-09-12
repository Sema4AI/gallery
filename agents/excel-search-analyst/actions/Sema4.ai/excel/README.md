# Excel

Action Package operating on local Excel files directly, without requiring any processor app installed on the system nor depending on the UI.

This is currently capable of managing workbooks (Excel files) and their worksheets (sheets), while adding rows, changing cell values and retrieving info about the workbook/sheet content itself.

On Windows and Mac machines with Excel installation, the action `find_cross_reference` will use Excel to trigger save on workbook so that visible cell values can be detected.

## Prompts

```
Give me the schema for an workbook called "data" found in the "output" folder.
```

> The schema for the workbook named "data.xlsx" found in the "output" folder has been successfully retrieved. The workbook contains a sheet named "MySheet" with the top row having two columns labeled "Name" and "Age".

```
Nice! Now please add some rows to that file with the following content:
Cosmin, 31
Mark, 6
```

> The rows with the content [["Cosmin", "31"], ["Mark", "6"]] have been successfully added to the "MySheet" in the "data.xlsx" workbook located in the "output" folder, with the correct headers ["Name", "Age"] as previously retrieved.

```
Awesome! You've really done a great job, now get me back the full table content of that sheet we've been operating on.
```

> The full table content of "MySheet" in the "data.xlsx" workbook located in the "output" folder has been successfully retrieved. Here's the content:
>
> | Name   | Age |
> | ------ | --- |
> | Cosmin | 31  |
> | Mark   | 6   |

## Caveats

- It currently operates on strings only (even with numbers) and it doesn't support fancy cell formatting or macros.
- It works with local file paths, usually relative from the place the Agent is running, and sometimes it might forget the original file path it was operating on, misplacing it with a non-existent file.
