-- Misma población temporal del EDA: recogida coherente con el mes del archivo.
SELECT tipo_taxi, mes_archivo, count(*) AS viajes
FROM {{fuente}}
WHERE recogida >= mes_archivo AND recogida < mes_archivo + INTERVAL 1 MONTH
GROUP BY tipo_taxi, mes_archivo ORDER BY tipo_taxi, mes_archivo;
