-- Expone denominadores y causas de exclusión (pueden solaparse).
SELECT tipo_taxi, count(*) AS registros_originales,
       count_if(fecha_coherente) AS fechas_validas,
       count_if(fecha_coherente AND trip_distance > 0 AND trip_distance <= 100
         AND duracion_minutos > 0 AND duracion_minutos <= 1440
         AND total_amount > 0 AND fare_amount >= 0) AS mediciones_validas,
       count_if(NOT fecha_coherente OR fecha_coherente IS NULL) AS fecha_excluida,
       count_if(trip_distance IS NULL OR trip_distance <= 0 OR trip_distance > 100) AS distancia_alerta,
       count_if(duracion_minutos IS NULL OR duracion_minutos <= 0 OR duracion_minutos > 1440) AS duracion_alerta,
       count_if(total_amount IS NULL OR total_amount <= 0 OR fare_amount IS NULL OR fare_amount < 0) AS importe_alerta
FROM viajes_eda GROUP BY tipo_taxi ORDER BY tipo_taxi;
