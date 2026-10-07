-- Cuenta registros y archivos sin materializar los viajes.
SELECT tipo_taxi, mes_archivo, archivo, count(*) AS registros
FROM viajes
GROUP BY tipo_taxi, mes_archivo, archivo
ORDER BY tipo_taxi, mes_archivo, archivo;
