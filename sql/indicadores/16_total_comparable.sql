-- Comparación de tres años: ignora el filtro de año, pero acepta el tipo de taxi.
WITH comparacion AS (
-- Cobertura común en los tres años y ambos tipos. No equipara 12 meses con 8.
WITH cobertura AS (SELECT DISTINCT year(mes_archivo) AS anio,month(mes_archivo) AS mes,tipo_taxi FROM viajes_duckdb),
 comunes AS (SELECT mes FROM cobertura GROUP BY mes HAVING count(*)=6),
 datos AS NOT MATERIALIZED (SELECT *,year(mes_archivo) AS anio,date_diff('second',recogida,llegada)/60.0 AS duracion
 FROM viajes_duckdb WHERE month(mes_archivo) IN (SELECT mes FROM comunes)
 AND recogida>=mes_archivo AND recogida<mes_archivo+INTERVAL 1 MONTH),
 volumen AS (SELECT anio,tipo_taxi,count(*) AS viajes,
 100.0*count_if(payment_type=1)/count(*) AS porcentaje_tarjeta,
 100.0*count_if(payment_type=2)/count(*) AS porcentaje_efectivo,
 100.0*count_if(passenger_count IS NULL)/count(*) AS porcentaje_pasajeros_nulos,
 100.0*count_if(total_amount<0)/count(*) AS porcentaje_totales_negativos
 FROM datos GROUP BY anio,tipo_taxi),
 calendario AS (SELECT c.anio,c.tipo_taxi,sum(day(last_day(make_date(c.anio,c.mes,1)))) AS dias
 FROM cobertura c JOIN comunes USING(mes) GROUP BY c.anio,c.tipo_taxi),
 mediciones AS (SELECT anio,tipo_taxi,count(*) AS viajes_mediciones,
 approx_quantile(trip_distance,0.5) AS distancia_mediana,
 approx_quantile(duracion,0.5) AS duracion_mediana,
 approx_quantile(total_amount,0.5) AS total_mediano_usd
 FROM datos WHERE trip_distance>0 AND trip_distance<=100 AND duracion>0 AND duracion<=1440
 AND total_amount>0 AND fare_amount>=0 GROUP BY anio,tipo_taxi)
 SELECT v.*,c.dias,v.viajes::DOUBLE/c.dias AS viajes_por_dia,m.viajes_mediciones,
 m.distancia_mediana,m.duracion_mediana,m.total_mediano_usd
 FROM volumen v JOIN calendario c USING(anio,tipo_taxi) JOIN mediciones m USING(anio,tipo_taxi)
 ORDER BY tipo_taxi,anio
)
SELECT CAST(anio AS VARCHAR) AS anio,tipo_taxi,total_mediano_usd FROM comparacion WHERE TRUE [[AND tipo_taxi = {{tipo_taxi}}]] ORDER BY anio,tipo_taxi;
