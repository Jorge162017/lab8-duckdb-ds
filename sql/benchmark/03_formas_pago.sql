-- Conteos y totales negativos por categoría; conserva el pago nulo.
SELECT tipo_taxi, payment_type, count(*) AS viajes,
       count_if(total_amount < 0) AS totales_negativos
FROM {{fuente}}
WHERE recogida >= mes_archivo AND recogida < mes_archivo + INTERVAL 1 MONTH
GROUP BY tipo_taxi, payment_type ORDER BY tipo_taxi, payment_type;
