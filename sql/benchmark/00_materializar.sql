-- La fuente externa ya armoniza nombres y columnas, sin limpiar ni filtrar filas.
-- Se conserva el mismo esquema lógico, procedencia y todos los registros.
CREATE TABLE viajes_duckdb AS SELECT * FROM viajes_parquet;
CHECKPOINT;
