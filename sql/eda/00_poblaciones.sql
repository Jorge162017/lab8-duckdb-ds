-- Parte de las vistas externas definidas en sql/exploracion/00_fuentes.sql.
-- No se corrigen ni modifican los Parquet.
CREATE OR REPLACE VIEW viajes_eda AS
SELECT *, date_diff('second', recogida, llegada) / 60.0 AS duracion_minutos,
       recogida >= mes_archivo AND recogida < mes_archivo + INTERVAL 1 MONTH AS fecha_coherente
FROM viajes;
CREATE OR REPLACE VIEW viajes_fechas_validas AS
SELECT * FROM viajes_eda WHERE fecha_coherente;
-- Umbrales exploratorios para comparar mediciones; no reglas oficiales.
-- Pasajeros y tipo de pago NO son criterios de exclusión.
CREATE OR REPLACE VIEW viajes_mediciones_validas AS
SELECT * FROM viajes_fechas_validas
WHERE trip_distance > 0 AND trip_distance <= 100
  AND duracion_minutos > 0 AND duracion_minutos <= 1440
  AND total_amount > 0 AND fare_amount >= 0;
