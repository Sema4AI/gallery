from data_sources import OilGasDataSource
from typing import Annotated
from sema4ai.actions import ActionError, Response, Table
from sema4ai.data import DataSource, query, get_connection
import pandas
import numpy as np
import math
from scipy import stats
from datetime import datetime

@query
def get_wells() -> Response[Table]:
    """
    Get the name of each well with production results.

    Args:
        
    Returns:
        List of distinct well names.
    """

    sql = """
        SELECT DISTINCT(WellName)
        FROM public_demo.og_production_reports
        ORDER BY WellName ASC
        LIMIT 10;
    """

    result = get_connection().query(sql)
    return Response(result=result.to_table())

@query
def get_production_for_well(wellName: str) -> Response[Table]:
    """
    Get production details for a specific well.

    Args:
        wellName: Name of the specific well.

    Returns:
        str: The complete production results for the well.
    """
    query = """
        SELECT * FROM public_demo.og_production_reports
        WHERE WELLNAME = $wellName;
        """
    params = {'wellName': wellName}

    result = get_connection().query(query=query, params=params)
    return Response(result=result.to_table())

@query
def get_wells_by_company(
    company: str) -> Response[Table]:
    """
    Get all wells operated by a specific company.

    Args:
        company: Name of the company.

    Returns:
        str: List of wells operated by the company.
    """
    company = "%" + company + "%"
    query = """
        SELECT DISTINCT WellName, API_WELLNO, FieldName
        FROM public_demo.og_production_reports
        WHERE Company LIKE $company
        ORDER BY WellName;
        """
    params = {'company': company}

    result = get_connection().query(query=query, params=params)
    return Response(result=result.to_table())

@query
def get_total_production_by_field(datasource: OilGasDataSource,
    fieldName: str) -> Response[Table]:
    """
    Get total oil, water, and gas production for a specific field.

    Args:
        fieldName: Name of the field.

    Returns:
        str: Total production figures for the field.
    """
    query = """
    SELECT FieldName,
        SUM(CAST(Oil AS NUMERIC)) as TotalOil,
        SUM(CAST(Wtr AS NUMERIC)) as TotalWater,
        SUM(CAST(Gas AS NUMERIC)) as TotalGas
    FROM og_production_reports
    WHERE FieldName = $fieldName
    GROUP BY FieldName;
    """
    params = {'fieldName': fieldName}

    result = datasource.native_query(query=query, params=params)
    return Response(result=result.to_table())

@query
def get_top_producing_wells(limit: int) -> Response[Table]:
    """
    Get the top producing wells based on total combined production.

    Args:
        limit: Number of top wells to return.

    Returns:
        str: List of top producing wells with their production figures.
    """
    query = """
    SELECT * FROM public_demo (
        SELECT wellname, 
            SUM(oil) as TotalOil, 
            SUM(wtr) as TotalWtr, 
            SUM(gas) as TotalGas,
            SUM(oil) + SUM(wtr) + SUM(gas) as TotalProduction
        FROM og_production_reports
        WHERE oil != 'NaN'::NUMERIC 
        AND wtr != 'NaN'::NUMERIC 
        AND gas != 'NaN'::NUMERIC
        GROUP BY wellname
        ORDER BY TotalProduction DESC
        LIMIT $limit
    );
    """
    params = {'limit': limit}

    result = get_connection().query(query=query, params=params)
    return Response(result=result.to_table())

@query
def get_top_producing_wells_by_field(fieldName: str, limit: int) -> Response[Table]:
    """
    Get the top producing wells based on oil production for a specific field.

    Args:
        fieldName: Name of the field to filter by - make sure the case is all upper case.
        limit: Number of top wells to return.

    Returns:
        str: List of top producing wells with their production figures for the specified field.
    """
    query = """
    SELECT WellName, 
        SUM(CAST(Oil AS NUMERIC)) as Oil, 
        SUM(CAST(Wtr AS NUMERIC)) as Wtr, 
        SUM(CAST(Gas AS NUMERIC)) as Gas
    FROM public_demo.og_production_reports
    WHERE CAST(Oil AS NUMERIC) > 0
        AND FieldName = $fieldName
    GROUP BY WellName
    ORDER BY Oil DESC
    LIMIT $limit;
    """
    params = {'limit': limit, 'fieldName': fieldName}

    result = get_connection().query(query=query, params=params)
    return Response(result=result.to_table())

@query
def get_production_by_date_range_and_field(
    startDate: str,
    endDate: str,
    fieldName: str) -> Response[Table]:
    """
    Get total production figures within a specific date range for a given field.

    Args:
        startDate: Start date of the range (format: 'MM/DD/YYYY').
        endDate: End date of the range (format: 'MM/DD/YYYY').
        fieldName: Name of the field to filter by.

    Returns:
        str: Total production figures within the date range for the specified field.
    """
    query = """
        SELECT 
            FieldName,
            SUM(CAST(Oil AS NUMERIC)) as TotalOil,
            SUM(CAST(Wtr AS NUMERIC)) as TotalWater,
            SUM(CAST(Gas AS NUMERIC)) as TotalGas,
            SUM(CAST(GasSold AS NUMERIC)) as TotalGasSold,
            SUM(CAST(Flared AS NUMERIC)) as TotalFlared,
            COUNT(DISTINCT WellName) as WellCount
        FROM public_demo.og_production_reports
        WHERE ReportDate BETWEEN $start_date AND $end_date
        AND FieldName = $field_name
        GROUP BY FieldName;
        """
    params = {
        'start_date': startDate,
        'end_date': endDate,
        'field_name': fieldName
    }

    result = get_connection().query(query=query, params=params)
    return Response(result=result.to_table())

@query
def get_well_location(wellName: str) -> Response[Table]:
    """
    Get the locations of a specific.

    Args:
        wellName: Name of the well.

    Returns:
        str: Latitude and longitude for a specific well.
    """
    query = """
        SELECT DISTINCT WellName, Lat, Long
        FROM public_demo.og_production_reports
        WHERE WellName LIKE $wellname
        ORDER BY WellName;
        """

    params = {'wellname': wellName}

    result = get_connection().query(query=query, params=params)
    return Response(result=result.to_table())

@query
def get_monthly_production_for_well(datasource: OilGasDataSource, wellName: str, year: int) -> Response[Table]:
    """
    Get monthly production details for a specific well in a given year.

    Args:
        wellName: Name of the specific well.
        year: Year for which to retrieve data.

    Returns:
        str: Monthly production results for the well.
    """
    query = """
    SELECT
        DATE_TRUNC ('MONTH', reportdate) AS month,
        SUM(CAST(Oil AS NUMERIC)) AS total_oil,
        SUM(CAST(Wtr AS NUMERIC)) AS total_water,
        SUM(CAST(Gas AS NUMERIC)) AS total_gas,
        AVG(CAST(days AS NUMERIC)) AS avg_days
    FROM
        og_production_reports
    WHERE
        wellname ILIKE $wellName
        AND EXTRACT(YEAR FROM reportdate) = $year
    GROUP BY
        DATE_TRUNC ('MONTH', reportdate)
    ORDER BY month
    """
    params = {'wellName': wellName, 'year': year}

    result = datasource.native_query(query=query, params=params)
    return Response(result=result.to_table())

@query
def compare_well_monthly_production(
    wellName: str,
    startDate: str,
    endDate: str) -> Response[Table]:
    """
    Compare monthly production for a given well over a specified period.

    Args:
        wellName: List of well names to compare.
        startDate: Start date of the comparison period (format: 'MM/DD/YYYY').
        endDate: End date of the comparison period (format: 'MM/DD/YYYY').

    Returns:
        str: Monthly production comparison for the specified wells.
    """
    query = """
        SELECT 
            WellName,
            DATE_TRUNC('month', ReportDate) as month,
            SUM(CAST(Oil AS NUMERIC)) as TotalOil,
            SUM(CAST(Wtr AS NUMERIC)) as TotalWater,
            SUM(CAST(Gas AS NUMERIC)) as TotalGas
        FROM public_demo.og_production_reports
        WHERE WellName = $wellname
            AND ReportDate BETWEEN $start_date AND $end_date
        GROUP BY WellName, DATE_TRUNC('month', ReportDate)
        ORDER BY WellName, month;
        """
    params = {'wellname': wellName, 'start_date': startDate, 'end_date': endDate}

    result = get_connection().query(query=query, params=params)
    return Response(result=result.to_table())

@query
def get_monthly_production_trends(fieldName: str, year: str) -> Response[Table]:
    """
    Get monthly production trends for a specific field in a given year.

    Args:
        fieldName: Name of the field, make sure the parameter is used in all lower case 'fieldname'
        year: Year for which to retrieve data.

    Returns:
        str: Monthly production trends for the field.
    """
    query = """
        SELECT 
            DATE_TRUNC('month', ReportDate) as month,
            SUM(CAST(Oil AS NUMERIC)) as TotalOil,
            SUM(CAST(Wtr AS NUMERIC)) as TotalWater,
            SUM(CAST(Gas AS NUMERIC)) as TotalGas,
            COUNT(DISTINCT WellName) as ActiveWells
        FROM public_demo.og_production_reports
        WHERE FieldName = $fieldname
            AND EXTRACT(YEAR FROM ReportDate) = $year
        GROUP BY DATE_TRUNC('month', ReportDate)
        ORDER BY month;
        """
    params = {'fieldname': fieldName, 'year': year}

    result = get_connection().query(query=query, params=params)
    return Response(result=result.to_table())

@query
def find_wells_within_radius(datasource: OilGasDataSource, wellName: str, radius: int) -> Response[Table]:
    """
    Find wells within a specified radius of a given well.

    Args:
        wellName: Name of the well to use as the center point.
        radius: Radius in meters.

    Returns:
        str: List of wells within the specified radius.
    """
    query = """
        SELECT DISTINCT p2.wellname, p2.company
        FROM og_production_reports p1
        JOIN og_production_reports p2
        ON p1.wellname <> p2.wellname
        WHERE p1.wellname = $wellname
        AND (
            6371000 * 2 * ASIN(
            SQRT(
                POWER(SIN(RADIANS((p2.lat - p1.lat) / 2.0)), 2) +
                COS(RADIANS(p1.lat)) * COS(RADIANS(p2.lat)) *
                POWER(SIN(RADIANS((p2.long - p1.long) / 2.0)), 2)
            )
            )
        ) <= $radius;
    """
    params = {'wellname': wellName, 'radius': radius}

    result = datasource.native_query(query=query, params=params)
    return Response(result=result.to_table())
    

@query
def fit_exponential_decline_curve(
    wellName: str,
    startDate: str,
    endDate: str
) -> Response[str]:
    """
    Fit an exponential decline curve to the production data of a specific well.

    Args:
        wellName: Name of the well
        startDate: Start date of the analysis period (format: 'MM/DD/YYYY')
        endDate: End date of the analysis period (format: 'MM/DD/YYYY')

    Returns:
        Parameters of the fitted exponential decline curve.
    """
    # Convert input dates from MM/DD/YYYY to YYYY-MM-DD for SQL
    start_date_obj = datetime.strptime(startDate, '%m/%d/%Y')
    end_date_obj = datetime.strptime(endDate, '%m/%d/%Y')
    sql_start_date = start_date_obj.strftime('%Y-%m-%d')
    sql_end_date = end_date_obj.strftime('%Y-%m-%d')

    query = """
    SELECT 
        ReportDate,
        Oil
    FROM public_demo.og_production_reports
    WHERE WellName = $well_name
    AND ReportDate BETWEEN $start_date AND $end_date
    AND CAST(Oil AS NUMERIC) > 0
    ORDER BY ReportDate
    """
    params = {'well_name': wellName, 'start_date': sql_start_date, 'end_date': sql_end_date}
    result = get_connection().query(query=query, params=params).as_dataframe()
    
    if not result.empty:
        # Handle case-insensitive column names
        col_date = next((col for col in result.columns if col.lower() == 'reportdate'), None)
        col_oil = next((col for col in result.columns if col.lower() == 'oil'), None)
        if col_date is None or col_oil is None:
            return Response(result="Required columns (ReportDate, Oil) not found in the data.")

        # Updated datetime parsing to handle timestamps
        dates = [datetime.strptime(str(date).split('.')[0], '%Y-%m-%d') for date in result[col_date]]
        production = result[col_oil].astype(float).tolist()
        
        # Calculate days since first production
        first_date = min(dates)
        days = [(date - first_date).days for date in dates]
        
        # Use numpy and scipy for curve fitting
        log_production = np.log(production)
        slope, intercept, r_value, p_value, std_err = stats.linregress(days, log_production)
        
        q_i = math.exp(intercept)
        D = -slope
        tau = 1 / D
        
        result_dict = {
            'WellName': wellName,
            'Initial Production (q_i)': round(q_i, 2),
            'Decline Rate (D)': round(D, 6),
            'Characteristic Time (tau)': round(tau, 2),
            'R-squared': round(r_value**2, 4)
        }
        return Response(result=pandas.DataFrame([result_dict]).to_markdown())
    
    return Response(result="No data available for the specified well and date range.")

@query
def get_full_company_name(company: str) -> Response[Table]:
    """
    Get the full company name that match the given search term.

    Args:
        company: Partial name of the company to search for.

    Returns:
        Table: List of distinct company names matching the search term.
    """
    company = "%" + company.upper() + "%"
    query = """
        SELECT DISTINCT Company
        FROM public_demo.og_production_reports
        WHERE Company LIKE $company
        ORDER BY Company;
        """
    params = {'company': company}

    result = get_connection().query(query=query, params=params)
    return Response(result=result.to_table())

@query
def get_well_file_number(wellName: str) -> Response[Table]:
    """
    Get the file number for a specific well.

    Args:
        wellName: Name of the well to search for.

    Returns:
        Table: The file number for the specified well.
    """
    query = """
        SELECT DISTINCT WellName, FileNo
        FROM public_demo.og_production_reports
        WHERE WellName = $wellName;
        """
    params = {'wellName': wellName}

    result = get_connection().query(query=query, params=params)
    return Response(result=result.to_table())