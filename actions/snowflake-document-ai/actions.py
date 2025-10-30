from sema4ai.actions import action, Response, Secret, chat
from sema4ai.data import get_snowflake_connection
import os
import shutil
import tempfile
import datetime


@action
def list_stage_files(
    database_name: Secret, schema_name: Secret, stage_name: Secret, limit: int = 10
) -> Response[list]:
    """
    Lists the most recently modified files in a specific Snowflake stage.

    Args:
        database_name: The name of the database containing the stage
        schema_name: The name of the schema containing the stage
        stage_name: The name of the stage
        limit: Maximum number of files to return (default: 10)

    Returns:
        A list of the most recently modified files in the specified stage with their details
    """
    try:
        with get_snowflake_connection() as conn:
            cursor = conn.cursor()

            # Access Secret values with .value and then apply upper()
            db_name = database_name.value.upper()
            schema = schema_name.value.upper()
            stage = stage_name.value.upper()

            # Use fully qualified stage name
            fully_qualified_stage = f'@"{db_name}"."{schema}"."{stage}"'

            # Use a query to list, order, and limit the results in Snowflake
            query = f"""
            SELECT * 
            FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
            ORDER BY "last_modified" DESC
            LIMIT {limit}
            """

            # First execute LIST to populate results
            cursor.execute(f"LIST {fully_qualified_stage}")

            # Then query those results with ordering and limiting
            cursor.execute(query)

            # Convert result to list of dicts
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]

            return Response(result=result)
    except Exception as e:
        return Response(
            error=f"Error listing files in stage {database_name.value}.{schema_name.value}.{stage_name.value}: {str(e)}"
        )


@action
def parse_document(
    filename: str,
    database_name: Secret,
    schema_name: Secret,
    stage_name: Secret,
    stage_path: str = "",
) -> Response[dict]:
    """
    Uploads a file (PDF, PPTX, DOCX, JPEG, JPG, PNG, TIFF, TIF, HTML, TXT) from the chat to a specified Snowflake stage and parses it's content using Snowflake Document AI.

    Args:
        filename: The name of the file to upload from chat
        database_name: The database containing the stage
        schema_name: The schema containing the stage
        stage_name: The name of the stage
        stage_path: Optional subfolder path within the stage

    Returns:
        Details of the uploaded file, and the json string of the document ai processing results.
    """
    try:
        print(f"Starting process_document for file: {filename}")

        # Get the file from chat
        print("Getting file from chat...")
        chat_file = chat.get_file(filename)
        temp_file_path = str(chat_file)
        print(f"Got file: {temp_file_path}")

        # Extract just the original filename without path
        original_filename = os.path.basename(filename)
        print(f"Original filename: {original_filename}")

        # Create a filename with timestamp to ensure uniqueness
        file_base, file_ext = os.path.splitext(original_filename)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{file_base}_{timestamp}{file_ext}"
        print(f"Using unique filename: {unique_filename}")

        # Create a temporary directory to hold our renamed file
        print("Creating temporary directory...")
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a path for our correctly named file
            correct_name_path = os.path.join(temp_dir, unique_filename)
            print(f"Correct name path: {correct_name_path}")

            # Copy the temporary file to our new path with the correct name
            print("Copying file...")
            shutil.copy2(temp_file_path, correct_name_path)

            print("Establishing Snowflake connection...")
            with get_snowflake_connection() as conn:
                cursor = conn.cursor()
                print("Connected to Snowflake")

                # Access Secret values
                db_name = database_name.value.upper()
                schema = schema_name.value.upper()
                stage = stage_name.value.upper()
                print(f"Using stage: {db_name}.{schema}.{stage}")

                # Construct fully qualified stage name
                fully_qualified_stage = f'@"{db_name}"."{schema}"."{stage}"'

                # Add path if provided
                stage_location = fully_qualified_stage
                if stage_path:
                    # Remove leading/trailing slashes to avoid path issues
                    clean_path = stage_path.strip("/")
                    if clean_path:
                        stage_location = f"{fully_qualified_stage}/{clean_path}"
                print(f"Stage location: {stage_location}")

                # Record the upload time to use for polling
                upload_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                print(f"Upload time: {upload_time}")

                # Execute PUT command with the correctly named file
                put_command = f"PUT 'file://{correct_name_path}' '{stage_location}' OVERWRITE=TRUE AUTO_COMPRESS=FALSE SOURCE_COMPRESSION=NONE"
                print(
                    f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')}] Executing PUT command to upload file..."
                )
                try:
                    cursor.execute(put_command)
                    print(
                        f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')}] PUT command executed successfully"
                    )
                except Exception as put_error:
                    print(
                        f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')}] Error executing PUT command: {str(put_error)}"
                    )
                    raise

                # Get results of the upload
                result_rows = cursor.fetchall()
                status = cursor.sfqid
                print(
                    f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')}] Upload completed with status ID: {status}"
                )
                print(
                    f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')}] File upload status: {result_rows}"
                )

                # Create file paths for the response
                if stage_path:
                    clean_path = stage_path.strip("/")
                    stage_file_path = (
                        f"{clean_path}/{unique_filename}"
                        if clean_path
                        else unique_filename
                    )
                else:
                    stage_file_path = unique_filename

                # Create the fully qualified path including the file (like @DB.SCHEMA.STAGE/path/file.ext)
                fully_qualified_path = f"@{db_name}.{schema}.{stage}/{stage_file_path}"
                print(
                    f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')}] File uploaded to: {fully_qualified_path}"
                )

                # Prepare the upload result
                upload_result = {
                    "status": "success",
                    "original_file": original_filename,
                    "file": unique_filename,
                    "stage": f"{db_name}.{schema}.{stage}",
                    "stage_path": stage_file_path,
                    "fully_qualified_path": fully_qualified_path,
                    "upload_time": upload_time,
                    "query_id": status,
                }
                print("Upload completed successfully")

                # TODO: handle image (OCR) files differently than others - page splitting does not work for them

                # Now do the parsing
                query = f"""
                SELECT AI_PARSE_DOCUMENT (
                    TO_FILE('{fully_qualified_path}'),
                    {{'mode': 'LAYOUT' , 'page_split': true}}) AS parsed_document;
                """
                print(f"Executing query: {query}")
                cursor.execute(query)

                print("Fetching results...")
                rows = cursor.fetchall()
                print(f"Got {len(rows) if rows else 0} results")

                processing_result = None
                if rows and len(rows) > 0:
                    # Convert row to dict
                    columns = [desc[0] for desc in cursor.description]
                    processing_result = dict(zip(columns, rows[0]))
                    print(f"Available columns: {columns}")
                    print(
                        f"Found processing result with {len(processing_result)} fields"
                    )
                else:
                    print("No processing results found")

                print("Query completed")

                # Combine upload result with parsed result
                combined_result = {"upload": upload_result, "parsed": processing_result}
                print("Returning combined result")

                return Response(result=combined_result)

    except Exception as e:
        error_msg = f"Error processing document {filename}: {str(e)}"
        print(f"ERROR: {error_msg}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        return Response(error=error_msg)
