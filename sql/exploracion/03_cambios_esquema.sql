-- Compara los campos y tipos de cada archivo; no solo la cantidad de columnas.
WITH esquema AS (
    SELECT file_name, name, duckdb_type
    FROM parquet_schema(['data/raw/yellow/*/*.parquet', 'data/raw/green/*/*.parquet'])
    WHERE num_children IS NULL
)
SELECT regexp_extract(file_name, '(yellow|green)_tripdata_', 1) AS tipo_taxi,
       regexp_extract(file_name, '_([0-9]{4}-[0-9]{2})\.parquet$', 1) AS mes,
       count(*) AS columnas,
       string_agg(name || ':' || duckdb_type, ', ' ORDER BY name) AS firma_esquema
FROM esquema
GROUP BY file_name
ORDER BY tipo_taxi, mes;
