-- Porcentajes dentro de cada tipo; evita que el volumen amarillo oculte al verde.
SELECT tipo_taxi, hour(recogida) AS hora, count(*) AS viajes,
       100.0 * count(*) / sum(count(*)) OVER (PARTITION BY tipo_taxi) AS porcentaje_tipo
FROM viajes_fechas_validas
GROUP BY tipo_taxi, hora ORDER BY tipo_taxi, hora;
