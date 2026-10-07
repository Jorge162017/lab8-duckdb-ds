-- Lista exacta de fuentes y conteo por archivo para contrastar con PyArrow.
SELECT year(mes_archivo) AS anio, tipo_taxi, mes_archivo, archivo,
       count(*) AS registros
FROM viajes WHERE year(mes_archivo) IN (2024, 2026)
GROUP BY anio, tipo_taxi, mes_archivo, archivo
ORDER BY anio, tipo_taxi, mes_archivo;
