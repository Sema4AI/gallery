import logging
import re
from typing import Any

from data_sources import DocumentIntelligenceDataSource
from sema4ai.actions import ActionError, Response, Table
from sema4ai.data import query
from sema4ai_docint.agent_server_client import AgentServerClient
from sema4ai_docint.models import DataModel, initialize_dataserver
from sema4ai_docint.models.constants import PROJECT_NAME
from sema4ai_docint.utils import normalize_name

logger = logging.getLogger(__name__)


def _normalize_identifier(identifier: str) -> str:
    """Normalize a SQL identifier by removing quotes and converting to lowercase.

    Args:
        identifier: The identifier to normalize

    Returns:
        str: The normalized identifier
    """
    return identifier.replace('"', "").replace("'", "").lower()


def _references_allowed_view(sql_query: str, views: list[dict]) -> bool:
    """Check if the SQL query references at least one of the allowed views in the FROM clause.

    Args:
        sql_query: The SQL query to check
        views: List of allowed views

    Returns:
        bool: True if the query references at least one allowed view, False otherwise
    """
    view_names = [_normalize_identifier(view.get("name", "")) for view in views]
    sql_lower = sql_query.lower().replace('"', "").replace("'", "")
    for view_name in view_names:
        if not view_name:
            continue
        if re.search(
            rf"from\s+document_intelligence\.{re.escape(view_name)}\b", sql_lower
        ):
            return True
    return False


@query
def execute_natural_language_query(
    datasource: DocumentIntelligenceDataSource,
    data_model_name: str,
    natural_language_query: str = "",
    document_id: str | None = None,
) -> Response[dict[str, Any]]:
    """Execute a natural language query against the data model's views.

    Args:
        datasource: The document intelligence data source connection
        data_model_name: The name of the data model
        natural_language_query: The natural language query to execute
        document_id: The id of the document to query. If not provided, the query will be executed on set of documents.
    Returns:
        Response[dict[str, Any]]: Query results with columns, rows, and SQL query used
    Raises:
        ActionError: If data model not found, no views available, or query generation/execution fails
    """
    data_model_name = normalize_name(data_model_name)
    data_model = DataModel.find_by_name(datasource, data_model_name)
    if not data_model:
        raise ActionError(f"Data model with name {data_model_name} not found")

    if not data_model.views:
        raise ActionError(f"No views found for data model {data_model_name}")

    # Initialize the objects in MindsDB (project)
    try:
        initialize_dataserver(PROJECT_NAME, data_model.views)
    except Exception as e:
        raise ActionError(
            "Failed to create the document intelligence data-server project"
        ) from e

    # Generate SQL query from natural language
    client = AgentServerClient()

    max_retries = 3
    attempt = 0

    # Gather view reference data
    view_reference_data = []
    for view in data_model.views:
        try:
            # Get sample data from the view which will also give us column information
            sample_data_query = f"""
            SELECT DISTINCT ON (document_layout) *
            FROM document_intelligence.{view["name"]}
            ORDER BY document_layout, document_id
            LIMIT 5;
            """
            sample_data = datasource.execute_sql(sample_data_query)

            # Extract column information from the sample data
            sample_data_list = []

            if sample_data and sample_data.to_table().columns:
                # Get column names
                column_names = sample_data.to_table().columns

                # Convert all sample data rows to dictionaries
                if sample_data.to_table().rows:
                    for row in sample_data.to_table().rows:
                        sample_data_list.append(dict(zip(column_names, row)))

            view_reference_data.append(
                {
                    "name": view["name"],
                    "columns": column_names,  # Just pass the column names
                    "sample_data": sample_data_list,  # Now contains all distinct schema rows
                }
            )
        except Exception as e:
            logger.warning(
                f"Could not gather reference data for view {view['name']}: {str(e)}"
            )
            # Continue with other views even if one fails
            continue
    while attempt < max_retries:
        try:
            sql_query = client.generate_natural_language_query_on_views(
                natural_language_query,
                data_model.views,
                document_id=document_id,
                view_reference_data=view_reference_data,
            )

            # Validate the generated SQL query
            sql_query = sql_query.strip()
            logger.info(f"Generated natural language query SQL Query: {sql_query}")

            if not sql_query.lower().startswith("select"):
                raise ActionError("Generated query must be a SELECT statement")

            # Check that the query only references our views
            if not _references_allowed_view(sql_query, data_model.views):
                view_names = [
                    _normalize_identifier(view.get("name", ""))
                    for view in data_model.views
                ]
                raise ActionError(
                    f"Query must reference at least one view from: {view_names}"
                )

            # Execute the query
            try:
                results = datasource.execute_sql(sql_query)
                if results is None:
                    return Response(result={"columns": [], "rows": []})

                # Convert results to table format
                table = results.to_table()
                result_dict = {
                    "columns": table.columns,
                    "rows": table.rows,
                    "description": f"Generated SQL query: {sql_query}",
                }
                if not table.rows:
                    result_dict["message"] = "No data found for the given document."
                return Response(result=result_dict)
            except Exception as e:
                # Only retry if it's a SQL error
                if "sql" in str(e).lower():
                    attempt += 1
                    if attempt < max_retries:
                        logger.warning(
                            f"SQL error occurred, retrying (attempt {attempt + 1}/{max_retries}): {e}"
                        )
                        continue
                raise ActionError(f"Failed to execute query: {e}")

        except Exception as e:
            # Don't retry for non-SQL errors
            raise ActionError(f"Failed to generate SQL query: {e}")

    raise ActionError(
        f"Failed to generate valid SQL query after {max_retries} attempts"
    )


@query
def run_sql(
    datasource: DocumentIntelligenceDataSource,
    sql_query: str,
) -> Response[Table]:
    """Execute the provided SQL query against the data source.

    Args:
        datasource: The document intelligence data source connection
        sql_query: The SQL query to execute
    Returns:
        Response[Table]: The query results as a table
    Raises:
        ActionError: If the query execution fails
    """

    results = datasource.execute_sql(sql_query)
    if results is None:
        # Query returned no result set (i.e. DML)
        return Response(result=Table(columns=[], rows=[]))

    return Response(result=results.to_table())
