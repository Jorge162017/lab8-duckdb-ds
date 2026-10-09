-- Parámetros opcionales de Metabase: año de archivo y tipo yellow/green.
WITH base AS NOT MATERIALIZED (
 SELECT *, date_diff('second', recogida, llegada)/60.0 AS duracion_minutos
 FROM viajes_duckdb WHERE TRUE
 [[AND year(mes_archivo) = {{anio}}]]
 [[AND tipo_taxi = {{tipo_taxi}}]]
), temporal AS NOT MATERIALIZED (
 SELECT * FROM base WHERE recogida >= mes_archivo AND recogida < mes_archivo + INTERVAL 1 MONTH
), mediciones AS NOT MATERIALIZED (
 SELECT * FROM temporal WHERE trip_distance > 0 AND trip_distance <= 100
 AND duracion_minutos > 0 AND duracion_minutos <= 1440
 AND total_amount > 0 AND fare_amount >= 0
)
SELECT year(mes_archivo) AS anio,tipo_taxi,count(DISTINCT archivo) AS archivos,
 count(DISTINCT mes_archivo) AS meses,count(*) AS registros,
 min(mes_archivo) AS primer_mes,max(mes_archivo) AS ultimo_mes
 FROM base GROUP BY anio,tipo_taxi ORDER BY anio,tipo_taxi;
