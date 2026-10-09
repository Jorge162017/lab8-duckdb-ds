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
SELECT 100.0*count_if(trip_distance>0 AND trip_distance<=100 AND duracion_minutos>0 AND duracion_minutos<=1440 AND total_amount>0 AND fare_amount>=0)/nullif(count(*),0) AS porcentaje FROM temporal;
