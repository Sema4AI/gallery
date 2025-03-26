# Snowflake Cortex Integration

This action package provides seamless integration with Snowflake Cortex Analyst capabilities.

## Available Actions

### Cortex Analyst Integration

#### `ask_cortex_analyst`
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