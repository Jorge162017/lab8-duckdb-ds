-- Año de partición, no año de recogida: conserva las anomalías originales.
SELECT year(mes_archivo) AS anio, tipo_taxi,
       count(DISTINCT archivo) AS archivos, count(*) AS registros,
       min(mes_archivo) AS primer_mes, max(mes_archivo) AS ultimo_mes
FROM viajes WHERE year(mes_archivo) IN (2024, 2026)
GROUP BY anio, tipo_taxi ORDER BY anio, tipo_taxi;
