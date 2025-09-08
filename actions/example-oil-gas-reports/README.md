# Example - Oil Gas Reports Demo

> **⚠️ DISCLAIMER: This is a demonstration and example action package only. It is not intended for production use and should only be used for learning, testing, and educational purposes.**

Action Package demonstrating oil and gas production data analysis using PostgreSQL database queries, showcasing well production tracking, field analysis, and decline curve modeling.

This package showcases how to extract and analyze various types of oil and gas production data including well production details, field-level aggregations, monthly trends, and advanced analytics like decline curve fitting.

## Features

- **Well Production Tracking**: Get production details for specific wells with oil, water, and gas production data
- **Field Analysis**: Aggregate production data by field with total production figures and well counts
- **Company Operations**: Find wells operated by specific companies with location and field information
- **Monthly Trends**: Analyze monthly production patterns and trends for wells and fields
- **Geographic Analysis**: Find wells within specified radius using latitude/longitude coordinates
- **Advanced Analytics**: Perform exponential decline curve fitting for production forecasting
- **Location Services**: Get well coordinates and geographic information
- **Structured Data**: All results are returned as well-defined tables for easy integration

## Prompts

```
Get all wells in the database and show me the top 5 producing wells.
```

> The search has been completed successfully. Here are the results:
>
> **Available Wells:**
> - Well A-001, Well B-002, Well C-003, Well D-004, Well E-005
>
> **Top 5 Producing Wells:**
> 1. Well A-001 - Total Production: 15,420 barrels
> 2. Well B-002 - Total Production: 12,850 barrels
> 3. Well C-003 - Total Production: 11,200 barrels
> 4. Well D-004 - Total Production: 9,750 barrels
> 5. Well E-005 - Total Production: 8,900 barrels

```
Show me production details for Well A-001 and find wells within 5km radius.
```

> The analysis has been completed successfully:
>
> **Well A-001 Production Details:**
> - Oil: 1,250 barrels
> - Water: 890 barrels  
> - Gas: 2,100 MCF
> - Field: Eagle Ford
> - Company: Example Energy Corp
>
> **Nearby Wells (within 5km):**
> - Well B-002 (2.3km) - Example Energy Corp
> - Well C-003 (4.1km) - Example Energy Corp
> - Well D-004 (4.8km) - Different Energy Inc

```
Analyze monthly production trends for Eagle Ford field in 2023.
```

> The monthly trend analysis for Eagle Ford field in 2023 has been completed:
>
> **Monthly Production Trends:**
> | Month | Total Oil | Total Water | Total Gas | Active Wells |
> |-------|-----------|-------------|-----------|--------------|
> | Jan   | 45,200    | 32,100      | 89,500    | 12           |
> | Feb   | 47,800    | 34,200      | 92,300    | 12           |
> | Mar   | 49,100    | 35,600      | 94,800    | 13           |
> | ...   | ...       | ...         | ...       | ...          |

## Database Details

- **Database**: PostgreSQL demo database
- **Schema**: public_demo.og_production_reports
- **Access**: Read-only demo access
- **Data Format**: Returns structured tables with production metrics

## Available Actions

The package provides the following query actions:
- `get_wells()` - List all available wells
- `get_production_for_well(wellName)` - Get production details for a specific well
- `get_wells_by_company(company)` - Find wells operated by a company
- `get_total_production_by_field(fieldName)` - Aggregate production by field
- `get_top_producing_wells(limit)` - Rank wells by total production
- `get_monthly_production_trends(fieldName, year)` - Analyze monthly trends
- `find_wells_within_radius(wellName, radius)` - Geographic well search
- `fit_exponential_decline_curve(wellName, startDate, endDate)` - Advanced analytics

## Response Structure

All actions return structured `Table` objects containing:
- Production metrics (Oil, Water, Gas)
- Well identification (WellName, API_WELLNO, FileNo)
- Location data (Latitude, Longitude)
- Field and company information
- Date ranges and time series data
- Calculated analytics and trends

## Caveats

- This is a demo package using a public PostgreSQL database
- Data is read-only and may be limited compared to production systems
- Geographic calculations use simplified distance formulas
- Decline curve analysis is for educational purposes only
- Structured for demonstration and learning purposes