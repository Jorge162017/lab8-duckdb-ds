-- Tipos físicos Parquet y tipos interpretados por DuckDB, por archivo.
SELECT file_name AS archivo, name AS columna, type AS tipo_parquet,
       duckdb_type AS tipo_duckdb, repetition_type AS repeticion
FROM parquet_schema(['data/raw/yellow/*/*.parquet', 'data/raw/green/*/*.parquet'])
WHERE num_children IS NULL
ORDER BY archivo, column_id;
