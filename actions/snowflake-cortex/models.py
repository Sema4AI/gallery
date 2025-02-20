from datetime import datetime

from pydantic import BaseModel, Field
from typing_extensions import Annotated

class Warehouse(BaseModel):
    name: Annotated[str, Field(description="The name of the warehouse")]
    size: Annotated[str, Field(description="The size of the warehouse")]
    state: Annotated[str, Field(description="The state of the warehouse")]
    owner: Annotated[str, Field(description="The owner of the warehouse")]

class Schema(BaseModel):
    model_config = {"populate_by_name": True}

    schema_name: Annotated[
        str, Field(description="The name of the schema", alias="SCHEMA_NAME")
    ]
    schema_owner: Annotated[
        str | None, Field(description="The owner of the schema", alias="SCHEMA_OWNER")
    ] = None
    created: Annotated[
        datetime | None,
        Field(description="The date the schema was created", alias="CREATED"),
    ] = None
    last_altered: Annotated[
        datetime | None,
        Field(description="The date the schema was last altered", alias="LAST_ALTERED"),
    ] = None

class Table(BaseModel):
    model_config = {"populate_by_name": True}

    table_name: Annotated[
        str, Field(description="The name of the table", alias="TABLE_NAME")
    ]
    table_type: Annotated[
        str, Field(description="The type of the table", alias="TABLE_TYPE")
    ]

class Column(BaseModel):
    model_config = {"populate_by_name": True}

    column_name: Annotated[
        str, Field(description="The name of the column", alias="COLUMN_NAME")
    ]
    data_type: Annotated[
        str, Field(description="The data type of the column", alias="DATA_TYPE")
    ]
    is_nullable: Annotated[
        str, Field(description="Whether the column is nullable", alias="IS_NULLABLE")
    ]

class PutStageFile(BaseModel):
    source: Annotated[str, Field(description="The source file")]
    status: Annotated[str, Field(description="The status of the file")]
