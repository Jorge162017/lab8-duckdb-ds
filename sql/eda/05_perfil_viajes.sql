-- Perfil del subconjunto con mediciones válidas. Percentiles aproximados.
SELECT tipo_taxi, count(*) AS viajes,
       avg(trip_distance) AS distancia_media_millas,
       approx_quantile(trip_distance, 0.5) AS distancia_mediana_millas,
       approx_quantile(trip_distance, 0.95) AS distancia_p95_millas,
       avg(duracion_minutos) AS duracion_media_minutos,
       approx_quantile(duracion_minutos, 0.5) AS duracion_mediana_minutos,
       approx_quantile(duracion_minutos, 0.95) AS duracion_p95_minutos,
       avg(total_amount) AS total_medio_usd,
       approx_quantile(total_amount, 0.5) AS total_mediano_usd,
       approx_quantile(total_amount, 0.95) AS total_p95_usd
FROM viajes_mediciones_validas GROUP BY tipo_taxi ORDER BY tipo_taxi;
