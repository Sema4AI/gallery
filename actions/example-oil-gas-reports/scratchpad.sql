-- from get_wells()
SELECT DISTINCT(`WellName`)
FROM oil_gas.production_reports
ORDER BY `WellName` ASC
LIMIT 10;

-- from get_production_for_well()
SELECT * FROM oil_gas.production_reports
WHERE WELLNAME = 'BILL 14-23 1H';

-- from get_wells_by_company()
SELECT DISTINCT WellName, API_WELLNO, FieldName
FROM oil_gas.production_reports
WHERE Company = 'GRAYSON MILL OPERATING, LLC'
ORDER BY WellName;

SELECT DISTINCT WellName, API_WELLNO, FieldName
FROM oil_gas.production_reports
WHERE Company LIKE '%HESS%'
ORDER BY WellName;

-- from get_total_production_by_field()
select * from oil_gas(
    SELECT FieldName,
        SUM(Oil) as TotalOil,
        SUM(Wtr) as TotalWater,
        SUM(Gas) as TotalGas
    FROM production_reports
    WHERE FieldName = 'ALEXANDER'
    GROUP BY FieldName
);

-- from get_top_producing_wells()
SELECT WellName, 
    SUM(Oil) as Oil, 
    SUM(Wtr) as Wtr, 
    SUM(Gas) as Gas
FROM oil_gas.production_reports
WHERE Oil > 0
GROUP BY WellName
ORDER BY Oil DESC
LIMIT 10;

-- from get_top_producing_wells_by_field()
SELECT WellName, 
    SUM(Oil) as Oil, 
    SUM(Wtr) as Wtr, 
    SUM(Gas) as Gas
FROM oil_gas.production_reports
WHERE Oil > 0
    AND FieldName = 'ALEXANDER'
GROUP BY WellName
ORDER BY SUM(Oil) DESC
LIMIT 10;

-- from get_production_by_date_range_and_field()
SELECT 
    FieldName,
    SUM(Oil) as TotalOil,
    SUM(Wtr) as TotalWater,
    SUM(Gas) as TotalGas,
    SUM(GasSold) as TotalGasSold,
    SUM(Flared) as TotalFlared,
    COUNT(DISTINCT WellName) as WellCount
FROM oil_gas.production_reports
WHERE ReportDate BETWEEN '2024-01-01' AND '2024-10-01'
AND FieldName = 'ALEXANDER'
GROUP BY FieldName;

-- from get_well_location()
SELECT DISTINCT WellName, Lat, Long
FROM oil_gas.production_reports
WHERE WellName LIKE 'TARTAR USA 13-20H'
ORDER BY WellName;

-- from get_monthly_production_for_well()
select * from oil_gas(
    SELECT
        DATE_TRUNC ('MONTH', reportdate) AS month,
        SUM(Oil) AS total_oil,
        SUM(Wtr) AS total_water,
        SUM(Gas) AS total_gas,
        AVG(days) AS avg_days
    FROM
        production_reports
    WHERE
        wellname ILIKE 'PORTER 26-35 4H'
        AND YEAR (reportdate) = 2024
    GROUP BY
        DATE_TRUNC ('MONTH', reportdate)
    ORDER BY month
);

-- from compare_well_monthly_production()
SELECT 
    WellName,
    DATE_TRUNC('month', ReportDate) as month,
    SUM(Oil) as TotalOil,
    SUM(Wtr) as TotalWater,
    SUM(Gas) as TotalGas
FROM oil_gas.production_reports
WHERE WellName = 'Porter 26-35 4H'
    AND ReportDate BETWEEN '2024-01-01' AND '2024-08-31'
GROUP BY WellName, DATE_TRUNC('month', ReportDate)
ORDER BY WellName, month;

-- from get_monthly_production_trends()
SELECT 
    DATE_TRUNC('month', ReportDate) as month,
    SUM(Oil) as TotalOil,
    SUM(Wtr) as TotalWater,
    SUM(Gas) as TotalGas,
    COUNT(DISTINCT WellName) as ActiveWells
FROM oil_gas.production_reports
WHERE FieldName = 'NORTH FORK'
    AND EXTRACT(YEAR FROM ReportDate) = '2024'
GROUP BY DATE_TRUNC('month', ReportDate)
ORDER BY month;

-- from find_wells_within_radius()
SELECT * FROM oil_gas(
SELECT
  DISTINCT p2.wellname,
  p2.company
FROM
  production_reports AS p1
  JOIN production_reports AS p2 ON ST_DWITHIN (
    ST_MAKEPOINT (p1.long, p1.lat),
    ST_MAKEPOINT (p2.long, p2.lat),
    200
  )
  AND p1.wellname <> p2.wellname
WHERE
  p1.wellname = 'TEDDY FEDERAL 12X-5F');

-- from fit_exponential_decline_curve()
SELECT 
    ReportDate,
    Oil
FROM oil_gas.production_reports
WHERE WellName = 'Porter 26-35 4H'
AND ReportDate BETWEEN '2024-01-01' AND '2024-08-01'
AND Oil > 0
ORDER BY ReportDate;

-- Utilities for Predictive Modeling
DESCRIBE models.oil_production_model;

DESCRIBE models.oil_production_model.features;

DESCRIBE models.oil_production_model.model;

DESCRIBE models.oil_production_model.jsonai;

/*
DESCRIBE models.water_production_model;

DESCRIBE models.gas_production_model;
*/
-- from predict_oil_production_for_well()
SELECT 
    m.REPORTDATE,
    m.WELLNAME,
    m.OIL,
    m.OIL_explain
FROM 
    `models`.oil_production_model AS m
    JOIN oil_gas.production_reports AS t 
WHERE 
    t.REPORTDATE > LATEST
    AND t.WELLNAME = 'TARTAR USA 13-20H';

/* -- from predict_water_production_for_well()
SELECT 
    m.REPORTDATE,
    m.WTR,
    m.WELLNAME
FROM 
    `models`.water_production_model AS m
    JOIN oil_gas.production_reports AS t 
WHERE   
    t.REPORTDATE > LATEST
    AND t.WELLNAME = 'TARTAR USA 13-20H';
*/

/* -- from predict_gas_production_for_well()
SELECT 
    m.REPORTDATE,
    m.GAS,
    m.WELLNAME
FROM 
    `models`.gas_production_model AS m
    JOIN oil_gas.production_reports AS t 
WHERE   
    t.REPORTDATE > LATEST
    AND t.WELLNAME = 'TARTAR USA 13-20H';
*/

SELECT DISTINCT Company
FROM oil_gas.production_reports
WHERE Company LIKE '%HESS%'
ORDER BY Company;