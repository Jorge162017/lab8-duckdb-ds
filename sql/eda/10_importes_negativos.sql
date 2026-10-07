-- Proporción negativa dentro de cada categoría, no solamente conteos.
SELECT tipo_taxi, payment_type, count(*) AS viajes_categoria,
       count_if(total_amount < 0) AS totales_negativos,
       100.0 * count_if(total_amount < 0) / count(*) AS porcentaje_negativo_categoria
FROM viajes_fechas_validas
GROUP BY tipo_taxi, payment_type ORDER BY tipo_taxi, payment_type;
