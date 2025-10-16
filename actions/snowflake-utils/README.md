# Snowflake Utilities

A comprehensive set of actions for working with Snowflake databases. Enables agents to discover, query, and interact with Snowflake data and stages.

## What it does

**Discovery & Permissions:**
- View session info (current user, role, warehouse, database, schema)
- Show grants and permissions for troubleshooting access issues
- List databases, schemas, tables, views, semantic views, and stages

**Data Access:**
- Execute SQL queries and return results as tables
- List files in Snowflake stages with metadata
- Download files from stages directly into chat

**Access Validation:**
- Check permissions on databases and schemas
- Detailed error messages with hints for resolving permission issues

> **Note:** This package is designed for development and debugging in Sema4.ai Studio. Review security implications before deploying to production.
