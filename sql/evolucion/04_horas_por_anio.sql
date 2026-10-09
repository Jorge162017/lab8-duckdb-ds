SELECT year(mes_archivo) AS anio,tipo_taxi,hour(recogida) AS hora,count(*) AS viajes,
 100.0*count(*)/sum(count(*)) OVER(PARTITION BY year(mes_archivo),tipo_taxi) AS porcentaje
 FROM viajes_duckdb WHERE recogida>=mes_archivo AND recogida<mes_archivo+INTERVAL 1 MONTH
 GROUP BY anio,tipo_taxi,hora ORDER BY tipo_taxi,anio,hora;
