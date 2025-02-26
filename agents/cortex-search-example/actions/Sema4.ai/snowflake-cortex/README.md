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

### Cortex Search: Configuration

When using the actions, you need to configure several secrets for authentication and service configuration. These include:
- Search Service Name
- Warehouse
- Database
- Schema

These values are stored as secrets in your Sema4.ai Studio or Control Room, and requested from you when creating or deploying the agent. Snowflake has a great [tutorial](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/tutorials/cortex-search-tutorial-1-search) for setting up a Cortex Search service using Airbnb data as an example. If you have completed this tutorial, you can use the values from the tutorial as the secrets for the actions.

- Service Name: "AIRBNB_SVC"
- Warehouse: "COMPUTE_WH" (this depends on your Snowflake account and may be different)
- Database: "CORTEX_SEARCH_TUTORIAL_DB"
- Schema: "PUBLIC"

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

#### Cortex Analyst Configuration

When using these actions, you need to configure several secrets:
- Semantic Model File location
- Warehouse
- Database
- Schema

These values are stored in your Sema4.ai Studio or Control Room and requested from you when creating or deploying the agent.

Example values:

- Semantic Model File: "@PRODUCTION_RESULTS.PUBLIC.STAGE1/oil_gas.yml"
- Warehouse: COMPUTE_WH
- Database: PRODUCTION_RESULTS
- Schema: PUBLIC