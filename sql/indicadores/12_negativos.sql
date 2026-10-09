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
SELECT CASE payment_type WHEN 0 THEN 'Flex Fare' WHEN 1 THEN 'Tarjeta' WHEN 2 THEN 'Efectivo'
 WHEN 3 THEN 'Sin cargo' WHEN 4 THEN 'Disputa' WHEN 5 THEN 'Desconocido' WHEN 6 THEN 'Anulado' ELSE 'Sin dato' END AS forma_pago,
 tipo_taxi,count(*) AS viajes_categoria,count_if(total_amount<0) AS negativos,
 100.0*count_if(total_amount<0)/count(*) AS porcentaje_negativo
 FROM temporal GROUP BY tipo_taxi,payment_type ORDER BY payment_type,tipo_taxi;
