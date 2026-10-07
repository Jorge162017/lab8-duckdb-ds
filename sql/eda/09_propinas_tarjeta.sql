-- TLC: las propinas en efectivo no están incluidas. No se comparan con tarjeta.
-- Denominador de la tasa: tarifa base fare_amount, no total_amount.
SELECT tipo_taxi, count(*) AS viajes_tarjeta_elegibles,
       count_if(tip_amount = 0) AS viajes_sin_propina_registrada,
       100.0 * count_if(tip_amount = 0) / count(*) AS porcentaje_sin_propina,
       avg(tip_amount) AS propina_media_usd,
       approx_quantile(tip_amount, 0.5) AS propina_mediana_usd,
       avg(100.0 * tip_amount / fare_amount) AS tasa_media_porcentaje,
       approx_quantile(100.0 * tip_amount / fare_amount, 0.5) AS tasa_mediana_porcentaje
FROM viajes_mediciones_validas
WHERE payment_type = 1 AND fare_amount > 0 AND tip_amount >= 0
GROUP BY tipo_taxi ORDER BY tipo_taxi;
