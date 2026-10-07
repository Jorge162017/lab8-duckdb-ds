-- Los códigos 0 a 6 están descritos en los diccionarios TLC.
SELECT tipo_taxi, payment_type, count(*) AS registros,
       count_if(total_amount < 0) AS totales_negativos,
       count_if(total_amount = 0) AS totales_cero,
       count_if(passenger_count IS NULL) AS pasajeros_nulos
FROM viajes
GROUP BY tipo_taxi, payment_type ORDER BY tipo_taxi, payment_type;
