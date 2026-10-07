-- Divide por el número de veces que cada día aparece en los meses disponibles.
-- ISO: 1=lunes, ..., 7=domingo; evita comparar conteos con calendarios desiguales.
WITH meses AS (
    SELECT DISTINCT tipo_taxi, mes_archivo FROM viajes_eda
), calendario AS (
    SELECT tipo_taxi, CAST(dia AS DATE) AS fecha
    FROM meses, LATERAL generate_series(mes_archivo, last_day(mes_archivo), INTERVAL 1 DAY) AS fechas(dia)
), dias AS (
    SELECT tipo_taxi, isodow(fecha) AS dia_semana, count(*) AS dias_calendario
    FROM calendario GROUP BY tipo_taxi, dia_semana
), conteos AS (
    SELECT tipo_taxi, isodow(recogida) AS dia_semana, count(*) AS viajes
    FROM viajes_fechas_validas GROUP BY tipo_taxi, dia_semana
)
SELECT d.tipo_taxi, d.dia_semana, d.dias_calendario, coalesce(c.viajes, 0) AS viajes,
       coalesce(c.viajes, 0)::DOUBLE / d.dias_calendario AS viajes_por_dia
FROM dias d LEFT JOIN conteos c USING (tipo_taxi, dia_semana)
ORDER BY d.tipo_taxi, d.dia_semana;
