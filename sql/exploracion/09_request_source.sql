-- Separa presencia estructural del campo y valores efectivamente reportados.
-- NULL en enero-mayo proviene de una columna que no existía.
SELECT tipo_taxi, mes_archivo, request_source, count(*) AS registros
FROM viajes
GROUP BY tipo_taxi, mes_archivo, request_source
ORDER BY tipo_taxi, mes_archivo, request_source;
