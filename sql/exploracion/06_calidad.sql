-- Alertas de exploración: no implican que todos estos registros sean errores.
-- Un viaje >24 h, distancia >100 millas o >6 pasajeros se marca para revisión.
SELECT tipo_taxi, count(*) AS registros,
       min(recogida) AS primera_recogida, max(recogida) AS ultima_recogida,
       count_if(recogida < mes_archivo OR recogida >= mes_archivo + INTERVAL 1 MONTH) AS fecha_fuera_mes_archivo,
       count_if(llegada < recogida) AS duracion_negativa,
       count_if(llegada = recogida) AS duracion_cero,
       count_if(llegada - recogida > INTERVAL 24 HOUR) AS duracion_mayor_24h,
       count_if(trip_distance < 0) AS distancia_negativa,
       count_if(trip_distance = 0) AS distancia_cero,
       count_if(trip_distance > 100) AS distancia_mayor_100_millas,
       count_if(passenger_count <= 0) AS pasajeros_no_positivos,
       count_if(passenger_count > 6) AS pasajeros_mayor_6,
       count_if(fare_amount < 0) AS tarifa_negativa,
       count_if(total_amount < 0) AS total_negativo,
       count_if(total_amount = 0) AS total_cero,
       count_if(tip_amount < 0) AS propina_negativa,
       count_if(payment_type NOT BETWEEN 0 AND 6) AS pago_codigo_no_documentado,
       count_if(ratecode_id NOT IN (1, 2, 3, 4, 5, 6, 99)) AS tarifa_codigo_no_documentado
FROM viajes GROUP BY tipo_taxi ORDER BY tipo_taxi;
