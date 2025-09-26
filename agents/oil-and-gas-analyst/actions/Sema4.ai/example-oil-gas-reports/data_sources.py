"""
The data_sources.py is used to define both the datasources as well as the data server bootstrap.
"""

from typing import Annotated
from sema4ai.data import DataSource, DataSourceSpec

OilGasDataSource = Annotated[
    DataSource,
    DataSourceSpec(
        name="public_demo",
        engine="postgres",
        description="Oil & Gas Report Data",
    ),
]