-- Percentiles aproximados sobre los valores originales, sin limpiar.
WITH valores AS (
    SELECT tipo_taxi, trip_distance, total_amount, passenger_count,
           date_diff('second', recogida, llegada) / 60.0 AS duracion_minutos
    FROM viajes
)
SELECT tipo_taxi,
       min(trip_distance) AS distancia_min, max(trip_distance) AS distancia_max,
       approx_quantile(trip_distance, [0.5, 0.95, 0.99]) AS distancia_p50_p95_p99,
       min(total_amount) AS total_min, max(total_amount) AS total_max,
       approx_quantile(total_amount, [0.5, 0.95, 0.99]) AS total_p50_p95_p99,
       min(duracion_minutos) AS duracion_min, max(duracion_minutos) AS duracion_max,
       approx_quantile(duracion_minutos, [0.5, 0.95, 0.99]) AS duracion_p50_p95_p99,
       min(passenger_count) AS pasajeros_min, max(passenger_count) AS pasajeros_max
FROM valores GROUP BY tipo_taxi ORDER BY tipo_taxi;
