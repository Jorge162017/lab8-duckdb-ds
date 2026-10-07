-- Consulta selectiva: intervalo fijo presente en los tres tamaños.
SELECT tipo_taxi, zona_origen, count(*) AS viajes, avg(total_amount) AS total_medio_usd
FROM {{fuente}}
WHERE recogida >= TIMESTAMP '2024-01-10 00:00:00'
  AND recogida < TIMESTAMP '2024-01-17 00:00:00'
  AND recogida >= mes_archivo AND recogida < mes_archivo + INTERVAL 1 MONTH
  AND payment_type = 1 AND trip_distance > 0 AND trip_distance <= 100
  AND total_amount > 0
GROUP BY tipo_taxi, zona_origen ORDER BY tipo_taxi, zona_origen;
