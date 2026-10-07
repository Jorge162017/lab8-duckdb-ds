-- Muestra el efecto del filtrado en tamaños y medias; no atribuye todo a un único filtro.
SELECT 'Fechas válidas, sin filtros de medición' AS poblacion, tipo_taxi,
       count(*) AS viajes, avg(trip_distance) AS distancia_media_millas,
       avg(duracion_minutos) AS duracion_media_minutos, avg(total_amount) AS total_medio_usd
FROM viajes_fechas_validas GROUP BY tipo_taxi
UNION ALL
SELECT 'Fechas y mediciones válidas', tipo_taxi, count(*), avg(trip_distance),
       avg(duracion_minutos), avg(total_amount)
FROM viajes_mediciones_validas GROUP BY tipo_taxi
ORDER BY tipo_taxi, poblacion;
