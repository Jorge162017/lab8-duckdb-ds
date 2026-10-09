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
 , grupos AS (SELECT tipo_taxi,CASE WHEN trip_distance<=1 THEN 1 WHEN trip_distance<=2 THEN 2
 WHEN trip_distance<=5 THEN 3 WHEN trip_distance<=10 THEN 4 WHEN trip_distance<=20 THEN 5 ELSE 6 END AS orden
 FROM mediciones)
 SELECT CASE orden WHEN 1 THEN '(0,1] mi' WHEN 2 THEN '(1,2] mi' WHEN 3 THEN '(2,5] mi'
 WHEN 4 THEN '(5,10] mi' WHEN 5 THEN '(10,20] mi' ELSE '(20,100] mi' END AS intervalo,
 tipo_taxi,count(*) AS viajes,100.0*count(*)/sum(count(*)) OVER(PARTITION BY tipo_taxi) AS porcentaje
 FROM grupos GROUP BY tipo_taxi,orden ORDER BY orden,tipo_taxi;
