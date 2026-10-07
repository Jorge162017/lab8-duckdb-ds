-- Inventario representativo: permite observar optimizaciones de conteo.
SELECT tipo_taxi, count(*) AS viajes
FROM {{fuente}}
GROUP BY tipo_taxi ORDER BY tipo_taxi;
