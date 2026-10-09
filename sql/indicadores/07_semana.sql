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
 , meses AS (SELECT DISTINCT tipo_taxi,mes_archivo FROM base),
 calendario AS (SELECT tipo_taxi,isodow(dia) AS dia FROM meses,
 LATERAL generate_series(mes_archivo,last_day(mes_archivo),INTERVAL 1 DAY) AS fechas(dia)),
 dias AS (SELECT tipo_taxi,dia,count(*) AS dias_calendario FROM calendario GROUP BY tipo_taxi,dia),
 conteos AS (SELECT tipo_taxi,isodow(recogida) AS dia,count(*) AS viajes FROM temporal GROUP BY tipo_taxi,dia),
 promedios AS (SELECT d.tipo_taxi,d.dia,coalesce(c.viajes,0) AS viajes,d.dias_calendario,
 coalesce(c.viajes,0)::DOUBLE/d.dias_calendario AS promedio FROM dias d LEFT JOIN conteos c USING(tipo_taxi,dia))
 SELECT CASE dia WHEN 1 THEN 'Lunes' WHEN 2 THEN 'Martes' WHEN 3 THEN 'Miércoles'
 WHEN 4 THEN 'Jueves' WHEN 5 THEN 'Viernes' WHEN 6 THEN 'Sábado' ELSE 'Domingo' END AS dia_semana,
 tipo_taxi,promedio AS viajes_por_dia,
 100.0*promedio/(sum(viajes) OVER(PARTITION BY tipo_taxi)::DOUBLE/sum(dias_calendario) OVER(PARTITION BY tipo_taxi)) AS indice_base100
 FROM promedios ORDER BY dia,tipo_taxi;
