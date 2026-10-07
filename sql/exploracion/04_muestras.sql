-- Cinco filas por tipo; muestra de inspección, no muestra estadística aleatoria.
(SELECT * FROM viajes WHERE tipo_taxi = 'yellow' LIMIT 5)
UNION ALL
(SELECT * FROM viajes WHERE tipo_taxi = 'green' LIMIT 5);
