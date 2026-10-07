-- Medias del subconjunto declarado en el EDA; no se usan percentiles aproximados.
SELECT tipo_taxi, count(*) AS viajes,
       avg(trip_distance) AS distancia_media_millas,
       avg(date_diff('second', recogida, llegada) / 60.0) AS duracion_media_minutos,
       avg(total_amount) AS total_medio_usd
FROM {{fuente}}
WHERE recogida >= mes_archivo AND recogida < mes_archivo + INTERVAL 1 MONTH
  AND trip_distance > 0 AND trip_distance <= 100
  AND date_diff('second', recogida, llegada) > 0
  AND date_diff('second', recogida, llegada) <= 86400
  AND total_amount > 0 AND fare_amount >= 0
GROUP BY tipo_taxi ORDER BY tipo_taxi;
