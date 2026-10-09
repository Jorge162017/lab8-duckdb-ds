SELECT year(mes_archivo) AS anio,month(mes_archivo) AS mes,tipo_taxi,count(*) AS viajes,
 day(last_day(mes_archivo)) AS dias_calendario,
 count(*)::DOUBLE/day(last_day(mes_archivo)) AS viajes_por_dia
 FROM viajes_duckdb WHERE recogida>=mes_archivo AND recogida<mes_archivo+INTERVAL 1 MONTH
 GROUP BY anio,mes,tipo_taxi,mes_archivo ORDER BY tipo_taxi,anio,mes;
