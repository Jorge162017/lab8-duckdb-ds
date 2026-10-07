-- Distribuciones por intervalos explícitos; porcentajes por tipo y variable.
WITH intervalos AS (
    SELECT tipo_taxi, 'distancia_millas' AS variable,
       CASE WHEN trip_distance <= 1 THEN 1 WHEN trip_distance <= 2 THEN 2
            WHEN trip_distance <= 5 THEN 3 WHEN trip_distance <= 10 THEN 4
            WHEN trip_distance <= 20 THEN 5 ELSE 6 END AS orden,
       CASE WHEN trip_distance <= 1 THEN '(0, 1]' WHEN trip_distance <= 2 THEN '(1, 2]'
            WHEN trip_distance <= 5 THEN '(2, 5]' WHEN trip_distance <= 10 THEN '(5, 10]'
            WHEN trip_distance <= 20 THEN '(10, 20]' ELSE '(20, 100]' END AS intervalo
    FROM viajes_mediciones_validas
    UNION ALL
    SELECT tipo_taxi, 'duracion_minutos',
       CASE WHEN duracion_minutos <= 5 THEN 1 WHEN duracion_minutos <= 10 THEN 2
            WHEN duracion_minutos <= 20 THEN 3 WHEN duracion_minutos <= 40 THEN 4
            WHEN duracion_minutos <= 60 THEN 5 ELSE 6 END,
       CASE WHEN duracion_minutos <= 5 THEN '(0, 5]' WHEN duracion_minutos <= 10 THEN '(5, 10]'
            WHEN duracion_minutos <= 20 THEN '(10, 20]' WHEN duracion_minutos <= 40 THEN '(20, 40]'
            WHEN duracion_minutos <= 60 THEN '(40, 60]' ELSE '(60, 1440]' END
    FROM viajes_mediciones_validas
    UNION ALL
    SELECT tipo_taxi, 'total_usd',
       CASE WHEN total_amount <= 10 THEN 1 WHEN total_amount <= 20 THEN 2
            WHEN total_amount <= 40 THEN 3 WHEN total_amount <= 80 THEN 4
            WHEN total_amount <= 150 THEN 5 ELSE 6 END,
       CASE WHEN total_amount <= 10 THEN '(0, 10]' WHEN total_amount <= 20 THEN '(10, 20]'
            WHEN total_amount <= 40 THEN '(20, 40]' WHEN total_amount <= 80 THEN '(40, 80]'
            WHEN total_amount <= 150 THEN '(80, 150]' ELSE '(150, +∞)' END
    FROM viajes_mediciones_validas
)
SELECT tipo_taxi, variable, orden, intervalo, count(*) AS viajes,
       100.0 * count(*) / sum(count(*)) OVER (PARTITION BY tipo_taxi, variable) AS porcentaje
FROM intervalos GROUP BY tipo_taxi, variable, orden, intervalo
ORDER BY variable, tipo_taxi, orden;
