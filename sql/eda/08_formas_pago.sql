-- Conserva NULL y Flex Fare; usa la población con fechas válidas.
SELECT tipo_taxi, payment_type,
       CASE payment_type WHEN 0 THEN 'Flex Fare' WHEN 1 THEN 'Tarjeta'
            WHEN 2 THEN 'Efectivo' WHEN 3 THEN 'Sin cargo' WHEN 4 THEN 'Disputa'
            WHEN 5 THEN 'Desconocido' WHEN 6 THEN 'Anulado'
            ELSE CASE WHEN payment_type IS NULL THEN 'Sin dato' ELSE 'No documentado' END END AS forma_pago,
       count(*) AS viajes,
       100.0 * count(*) / sum(count(*)) OVER (PARTITION BY tipo_taxi) AS porcentaje_tipo
FROM viajes_fechas_validas
GROUP BY tipo_taxi, payment_type ORDER BY tipo_taxi, payment_type;
