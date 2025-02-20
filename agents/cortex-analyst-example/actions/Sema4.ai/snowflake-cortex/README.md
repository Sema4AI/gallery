# Snowflake Cortex Integration

This action package provides seamless integration with Snowflake Cortex services, specifically focusing on Cortex Search and Cortex Analyst capabilities.

## Available Actions

### Cortex Search

#### `cortex_get_search_specification`
Retrieves the configuration details for a Cortex Search service, including:
- Search column specification
- Attribute columns
- Service configuration

#### `cortex_search`
Executes searches against your Cortex Search service with:
- Custom query support
- Column filtering
- Result limiting
- Flexible filtering options

### Cortex Search: Runbook Additions

Before using these actions, you need to specify the search service name and the correct database and schema to execute queries against.

The Search Service specifies which search index to use for executing search operations. It's crucial for Cortex Search to know where to look for relevant data. *In your Runbook, replace the following with the right values for your environment.*

```text
Service Name: AIRBNB_SVC
Warehouse: COMPUTE_WH
Database: CORTEX_SEARCH_TUTORIAL_DB
Schema: PUBLIC
```

### Cortex Analyst Integration

#### `cortex_analyst_message`
Enables natural language interactions with your data through Cortex Analyst:
- Semantic model integration
- Natural language query processing
- SQL generation capabilities

#### `snowflake_execute_query`
Provides direct query execution capabilities against Snowflake:
- Secure connection handling
- Parameter support
- Warehouse/Database/Schema configuration

#### Cortex Analyst Runbook Additions

Before using these actions, you need to specify the correct location of your semantic model file and the correct database and schema to execute queries against.

The Semantic Model File defines the structure and relationships of your data, enabling Cortex Analyst to understand your data context.

```text
Semantic Model File: "@PRODUCTION_RESULTS.PUBLIC.STAGE1/oil_gas.yml"
```

To ensure your queries are executed against the correct database and schema, add the following to your runbook:

```text
Warehouse: COMPUTE_WH
Database: PRODUCTION_RESULTS
Schema: PUBLIC
```
