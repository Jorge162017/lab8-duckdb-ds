-- Asociación descriptiva; no estima un efecto causal ni una tarifa por milla.
WITH grupos AS (
    SELECT *, CASE WHEN trip_distance <= 1 THEN 1 WHEN trip_distance <= 2 THEN 2
                  WHEN trip_distance <= 5 THEN 3 WHEN trip_distance <= 10 THEN 4
                  WHEN trip_distance <= 20 THEN 5 ELSE 6 END AS orden,
       CASE WHEN trip_distance <= 1 THEN '(0, 1]' WHEN trip_distance <= 2 THEN '(1, 2]'
            WHEN trip_distance <= 5 THEN '(2, 5]' WHEN trip_distance <= 10 THEN '(5, 10]'
            WHEN trip_distance <= 20 THEN '(10, 20]' ELSE '(20, 100]' END AS intervalo_millas
    FROM viajes_mediciones_validas
)
SELECT tipo_taxi, orden, intervalo_millas, count(*) AS viajes,
       approx_quantile(total_amount, 0.5) AS total_mediano_usd,
       approx_quantile(duracion_minutos, 0.5) AS duracion_mediana_minutos
FROM grupos GROUP BY tipo_taxi, orden, intervalo_millas
ORDER BY tipo_taxi, orden;
