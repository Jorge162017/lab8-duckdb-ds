-- Hasta tres ejemplos por alerta. Las alertas pueden solaparse.
(SELECT 'fecha_fuera_mes_archivo' AS alerta, tipo_taxi, archivo, recogida,
        llegada, passenger_count, trip_distance, fare_amount, total_amount, payment_type
 FROM viajes
 WHERE recogida < mes_archivo OR recogida >= mes_archivo + INTERVAL 1 MONTH LIMIT 3)
UNION ALL
(SELECT 'duracion_negativa', tipo_taxi, archivo, recogida,
        llegada, passenger_count, trip_distance, fare_amount, total_amount, payment_type
 FROM viajes WHERE llegada < recogida LIMIT 3)
UNION ALL
(SELECT 'distancia_mayor_100_millas', tipo_taxi, archivo, recogida,
        llegada, passenger_count, trip_distance, fare_amount, total_amount, payment_type
 FROM viajes WHERE trip_distance > 100 LIMIT 3)
UNION ALL
(SELECT 'total_negativo', tipo_taxi, archivo, recogida,
        llegada, passenger_count, trip_distance, fare_amount, total_amount, payment_type
 FROM viajes WHERE total_amount < 0 LIMIT 3);
