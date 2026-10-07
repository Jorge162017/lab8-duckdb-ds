-- Campos disponibles en ambos taxis; ausencia de columna y valor nulo
-- se distinguen usando 02_esquemas y 03_cambios_esquema.
SELECT tipo_taxi, count(*) AS registros,
       count_if(recogida IS NULL) AS recogida_nula,
       count_if(llegada IS NULL) AS llegada_nula,
       count_if(passenger_count IS NULL) AS pasajeros_nulos,
       count_if(trip_distance IS NULL) AS distancia_nula,
       count_if(total_amount IS NULL) AS total_nulo,
       count_if(payment_type IS NULL) AS pago_nulo,
       count_if(ratecode_id IS NULL) AS tarifa_nula,
       count_if(store_and_fwd_flag IS NULL) AS envio_nulo,
       count_if(zona_origen IS NULL OR zona_destino IS NULL) AS alguna_zona_nula
FROM viajes GROUP BY tipo_taxi ORDER BY tipo_taxi;
