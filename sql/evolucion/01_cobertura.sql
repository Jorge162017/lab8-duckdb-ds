SELECT year(mes_archivo) AS anio,tipo_taxi,count(DISTINCT archivo) AS archivos,
 count(DISTINCT mes_archivo) AS meses,count(*) AS registros FROM viajes_duckdb
 GROUP BY anio,tipo_taxi ORDER BY anio,tipo_taxi;
