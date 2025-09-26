"""
The data_sources.py is used to define both the datasources as well as the data server bootstrap.
"""

from typing import Annotated

from sema4ai.data import DataSource, DataSourceSpec

DocumentIntelligenceDataSource = Annotated[
    DataSource,
    DataSourceSpec(
        name="DocumentIntelligence",
        engine="postgres",
        description="Document Intelligence DB",
    ),
]
