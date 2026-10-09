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
 , mensual AS (
 SELECT tipo_taxi,mes_archivo AS mes,count(*) AS viajes,
 count(*)::DOUBLE/day(last_day(mes_archivo)) AS viajes_por_dia
 FROM temporal GROUP BY tipo_taxi,mes_archivo
 )
 SELECT mes,tipo_taxi,viajes,viajes_por_dia,
 100.0*viajes_por_dia/first_value(viajes_por_dia) OVER(PARTITION BY tipo_taxi ORDER BY mes) AS indice_base100
 FROM mensual ORDER BY mes,tipo_taxi;
