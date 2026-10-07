-- Los campos ausentes en 2024 deben conservarse como NULL, no imputarse con cero.
SELECT year(mes_archivo) AS anio, tipo_taxi, count(*) AS registros,
       count_if(cbd_congestion_fee IS NULL) AS cbd_congestion_fee_nulo,
       count_if(request_source IS NULL) AS request_source_nulo,
       count_if(passenger_count IS NULL) AS pasajeros_nulos,
       count_if(payment_type IS NULL) AS pago_nulo
FROM viajes WHERE year(mes_archivo) IN (2024, 2026)
GROUP BY anio, tipo_taxi ORDER BY anio, tipo_taxi;
