-- Presencia física de las columnas y tipos por año; NULL lógico no implica dato faltante.
SELECT CAST(regexp_extract(file_name, '_([0-9]{4})-[0-9]{2}\.parquet$', 1) AS INTEGER) AS anio,
       regexp_extract(file_name, '(yellow|green)_tripdata_', 1) AS tipo_taxi,
       name AS columna, duckdb_type AS tipo_original,
       count(DISTINCT file_name) AS archivos_con_columna
FROM parquet_schema(['data/raw/yellow/*/*.parquet', 'data/raw/green/*/*.parquet'])
WHERE num_children IS NULL
  AND regexp_extract(file_name, '_([0-9]{4})-[0-9]{2}\.parquet$', 1) IN ('2024', '2026')
GROUP BY anio, tipo_taxi, columna, tipo_original
ORDER BY tipo_taxi, columna, anio, tipo_original;
