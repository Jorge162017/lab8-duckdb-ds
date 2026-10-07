-- Promedio diario: usa días del mes, incluidos posibles días sin viajes.
SELECT tipo_taxi, mes_archivo, count(*) AS viajes,
       day(last_day(mes_archivo)) AS dias_calendario,
       count(DISTINCT CAST(recogida AS DATE)) AS dias_con_viajes,
       round(count(*)::DOUBLE / day(last_day(mes_archivo)), 2) AS viajes_por_dia
FROM viajes_fechas_validas
GROUP BY tipo_taxi, mes_archivo ORDER BY tipo_taxi, mes_archivo;
