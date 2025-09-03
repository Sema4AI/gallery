"""
The data_sources.py is used to define both the datasources as well as the data server bootstrap.
"""

from typing import Annotated
from sema4ai.data import DataSource, DataSourceSpec

SnowflakeDataSource = Annotated[
    DataSource,
    DataSourceSpec(
        name="snowflake_database",
        engine="snowflake",
        description="Your snowflake data source",
    )
]