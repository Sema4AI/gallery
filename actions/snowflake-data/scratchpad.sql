select * from snowflake_database (
    SELECT * FROM PRODUCTION_REPORTS LIMIT 10
);

select * from snowflake_database (
    select database_name from SNOWFLAKE.information_schema.databases
        order by database_name
);

select * from snowflake_database (
    SELECT CURRENT_DATABASE()
);


select * from snowflake_database (
    SELECT CURRENT_SCHEMA()
);

select * from snowflake_database (
    SELECT schema_name, schema_owner, created, last_altered
    FROM information_schema.schemata
    WHERE catalog_name = CURRENT_DATABASE()
    ORDER BY schema_name
);

-- Get Tables
select * from snowflake_database (
    SELECT table_name, table_type
    FROM information_schema.tables
    WHERE table_type = 'BASE TABLE'
    ORDER BY table_name
);

SELECT * FROM snowflake_database (
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'TRANSCRIPTS'
    ORDER BY column_name
);

SELECT * FROM snowflake_database (
    SELECT COUNT(*) FROM PRODUCTION_REPORTS
);

SELECT * FROM snowflake_database (
    SELECT * FROM PRODUCTION_REPORTS SAMPLE (10 ROWS)
);