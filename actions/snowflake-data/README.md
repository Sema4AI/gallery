# Snowflake Data

Action Package for interacting with Snowflake data warehouse resources.

Possible actions with this package are:

- Query Snowflake databases in an SQL-like manner
- Get comprehensive information about available tables, columns, and sample data
- Execute secure SELECT queries with built-in safety checks

## Prompts

```
What tables are available in the database and what do they contain?
```

> Here's information about all available tables:
>
> **CUSTOMERS** (1,247 rows)
> - Columns: customer_id (NUMBER), name (VARCHAR), email (VARCHAR), created_date (DATE)
> - Sample data shows customer records with IDs, names, email addresses, and creation dates
>
> **ORDERS** (5,832 rows) 
> - Columns: order_id (NUMBER), customer_id (NUMBER), amount (NUMBER), order_date (DATE)
> - Sample data shows order transactions with amounts ranging from $50 to $2,500

```
Show me the top 5 customers by total order value this year
```

> Here are the top 5 customers by total order value in 2024:
>
> 1. **Acme Corporation** - Total: $125,400 (23 orders)
> 2. **Global Industries** - Total: $98,750 (18 orders) 
> 3. **Tech Solutions Inc** - Total: $87,200 (31 orders)
> 4. **Metro Enterprises** - Total: $76,300 (15 orders)
> 5. **Prime Manufacturing** - Total: $68,900 (22 orders)

```
What's the average order value by month for the last 6 months?
```

> Here's the average order value by month for the last 6 months:
>
> - **October 2024**: $342.50 (156 orders)
> - **September 2024**: $298.75 (189 orders)
> - **August 2024**: $367.20 (203 orders)
> - **July 2024**: $285.40 (178 orders)
> - **June 2024**: $312.80 (167 orders)
> - **May 2024**: $289.60 (145 orders)

## Authorization

This action package uses Snowflake's standard authentication methods to connect to your data warehouse.

To authenticate with Snowflake, you need to provide the following connection information, or have your Studio linked to Snowflake.

### Setting up Snowflake Connection

1. **Ensure proper permissions:**
   - Your user account needs `SELECT` permissions on the tables you want to query
   - For the `get_tables_info` action, you need access to `INFORMATION_SCHEMA`

2. **Configure warehouse and database:**
   - Make sure the specified warehouse is running or can be auto-resumed
   - Verify the database and schema names are correct and accessible

### Security Features

- **Query Safety**: Only `SELECT` queries are allowed - all other operations (DROP, DELETE, INSERT, etc.) are blocked
- **Input Validation**: Queries are validated before execution to prevent dangerous operations
- **Error Handling**: Comprehensive error messages help diagnose connection and query issues
- **Automatic Wrapping**: Queries are automatically wrapped in the proper Snowflake connection context